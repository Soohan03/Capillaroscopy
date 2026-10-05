"""Which recordings exist in the data folder and what has been done to each.

A recording is everything that shares a video's file stem: the raw capture in
``RecordedVideos/``, the stabilized copy in ``StabilizedVideos/``, the optical
flow in ``Flows/``, data sets and time points in ``Statistics/``, plots in
``Reports/``. The GUI shows one entry per recording instead of one per file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from capillary.datasets import SEPARATOR

from .settings import DataFolder

VIDEO_EXTENSIONS = ('.avi', '.mp4')


@dataclass
class Recording:
    stem: str
    raw: Optional[str] = None
    stabilized: Optional[str] = None
    flow: Optional[str] = None
    velocity_sets: list = field(default_factory=list)
    flow_sets: list = field(default_factory=list)

    @property
    def video(self) -> Optional[str]:
        """The video to analyse: the stabilized copy if there is one, else the raw capture."""
        return self.stabilized or self.raw

    @property
    def is_stabilized(self) -> bool:
        return self.stabilized is not None

    @property
    def has_flow(self) -> bool:
        return self.flow is not None

    @property
    def flow_summary(self) -> Optional[str]:
        """The pickle beside the flow video (average flow, intensity, vessel mask)."""
        return os.path.splitext(self.flow)[0] + '.pickle' if self.flow else None

    @property
    def dataset_count(self) -> int:
        return len(self.velocity_sets) + len(self.flow_sets)


def video_files(folder: str) -> list[str]:
    """Video files directly inside `folder` (hidden files and subfolders excluded)."""
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return []
    return sorted(entry.path for entry in entries
                  if entry.is_file() and not entry.name.startswith('.')
                  and os.path.splitext(entry.name)[1].lower() in VIDEO_EXTENSIONS)


def stem_of(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _datasets(statistics: str, stems) -> dict:
    """``{stem: (velocity names, flow names)}`` from one listing of ``Statistics/``.

    A file belongs to the known stem it starts with, so names containing the
    separator (possible in data sets from older versions) still match.
    """
    found = {}
    try:
        names = [entry.name for entry in os.scandir(statistics) if entry.is_file()]
    except OSError:
        return found
    endings = ((f'{SEPARATOR}cross_correlation.csv', 0), (f'{SEPARATOR}flow.pickle', 1))
    for file_name in names:
        for ending, kind in endings:
            if not file_name.endswith(ending):
                continue
            prefix = file_name[:-len(ending)]
            start = prefix.find(SEPARATOR)
            while start != -1:
                if prefix[:start] in stems:
                    found.setdefault(prefix[:start], ([], []))[kind].append(prefix[start + len(SEPARATOR):])
                    break
                start = prefix.find(SEPARATOR, start + 1)
    return found


def scan(folder: DataFolder) -> list[Recording]:
    """All recordings in `folder`, sorted by name."""
    recordings: dict[str, Recording] = {}

    def get(path):
        stem = stem_of(path)
        return recordings.setdefault(stem, Recording(stem))

    for path in video_files(folder.recorded):
        get(path).raw = path
    for path in video_files(folder.stabilized):
        get(path).stabilized = path
    for path in video_files(folder.flows):
        # a flow video is only usable together with its summary pickle (vessel mask)
        if os.path.isfile(os.path.splitext(path)[0] + '.pickle'):
            get(path).flow = path

    for stem, (velocity, flow) in _datasets(folder.statistics, set(recordings)).items():
        recordings[stem].velocity_sets = sorted(velocity)
        recordings[stem].flow_sets = sorted(flow)
    return sorted(recordings.values(), key=lambda r: r.stem.lower())
