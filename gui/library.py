"""Which recordings exist in the data folder and what has been done to each.

A recording is everything that shares a video's file stem: the raw capture in
``RecordedVideos/``, the stabilized copy in ``StabilizedVideos/``, data sets
and time points in ``Statistics/``, plots in ``Reports/``. The GUI shows one
entry per recording instead of one per file.

Versions before 2026-10-06 also computed optical flow, into ``Flows/``, and
measured it into flow data sets. Those files are not shown any more, but a
recording keeps a list of them so that moving it to the trash takes them along.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from capillary.datasets import LEGACY_FLOW_STATISTICS, SEPARATOR, legacy_flow_dataset_paths

from .settings import DataFolder

VIDEO_EXTENSIONS = ('.avi', '.mp4')


@dataclass
class Recording:
    stem: str
    raw: Optional[str] = None
    stabilized: Optional[str] = None
    velocity_sets: list = field(default_factory=list)
    #: files of the removed optical-flow feature: the flow video and its summary
    #: in Flows/, flow data sets and their plots
    legacy_flow_files: list = field(default_factory=list)

    @property
    def video(self) -> Optional[str]:
        """The video to analyse: the stabilized copy if there is one, else the raw capture."""
        return self.stabilized or self.raw

    @property
    def is_stabilized(self) -> bool:
        return self.stabilized is not None

    @property
    def dataset_count(self) -> int:
        return len(self.velocity_sets)


def _files(folder: str) -> list[str]:
    """Files directly inside `folder` (hidden files and subfolders excluded)."""
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return []
    return sorted(entry.path for entry in entries if entry.is_file() and not entry.name.startswith('.'))


def video_files(folder: str) -> list[str]:
    """Video files directly inside `folder` (hidden files and subfolders excluded)."""
    return [path for path in _files(folder) if os.path.splitext(path)[1].lower() in VIDEO_EXTENSIONS]


def stem_of(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _datasets(statistics: str, stems) -> dict:
    """``{stem: (velocity names, legacy flow names)}`` from one listing of ``Statistics/``.

    A file belongs to the known stem it starts with, so names containing the
    separator (possible in data sets from older versions) still match.
    """
    found = {}
    try:
        names = [entry.name for entry in os.scandir(statistics) if entry.is_file()]
    except OSError:
        return found
    endings = ((f'{SEPARATOR}cross_correlation.csv', 0), (f'{SEPARATOR}{LEGACY_FLOW_STATISTICS[0]}', 1))
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

    # only recordings with a video are listed; old flow files are attached to them
    for path in _files(folder.flows):
        if stem_of(path) in recordings:
            recordings[stem_of(path)].legacy_flow_files.append(path)
    for stem, (velocity, flow) in _datasets(folder.statistics, set(recordings)).items():
        recording = recordings[stem]
        recording.velocity_sets = sorted(velocity)
        for name in sorted(flow):
            recording.legacy_flow_files += legacy_flow_dataset_paths(folder.statistics, folder.reports, stem, name)
    return sorted(recordings.values(), key=lambda r: r.stem.lower())
