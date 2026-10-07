"""Persistent settings (``settings.csv``) and the layout of the data folder.

``settings.csv`` keeps the two-column layout the app has always used (and that
``python -m capillary.cli`` reads ``mm_per_pixel`` from)::

    ,0
    Application_path,/path/to/data
    mm_per_pixel,0.001328903654
    box_size,12

Rows this version does not know about are kept when the file is saved. Each
computer has its own file (git ignores it); without one, the app asks for the
data folder on first start.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import Optional

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(APP_DIR, 'settings.csv')

#: Spatial calibration of the original study microscope; recalibrate when the optics change.
DEFAULT_MM_PER_PIXEL = 0.001328903654
#: Box size the Analyze tab has always started with (its size fields read 12 x 12).
DEFAULT_BOX_SIZE = 12

_KNOWN_KEYS = ('Application_path', 'mm_per_pixel', 'box_size')


@dataclass
class Settings:
    data_folder: str
    mm_per_pixel: float = DEFAULT_MM_PER_PIXEL
    box_size: int = DEFAULT_BOX_SIZE
    path: str = SETTINGS_FILE
    extra: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: str = SETTINGS_FILE) -> Optional['Settings']:
        """The saved settings, or None on first start (no file or no data folder)."""
        try:
            with open(path, newline='', encoding='utf-8') as handle:
                rows = [row for row in csv.reader(handle) if len(row) >= 2 and row[0].strip()]
        except (OSError, UnicodeDecodeError):
            return None
        values = {row[0].strip(): row[1].strip() for row in rows}
        folder = values.get('Application_path', '')
        if not folder:
            return None
        try:
            mm_per_pixel = float(values.get('mm_per_pixel', DEFAULT_MM_PER_PIXEL))
            if not mm_per_pixel > 0:
                raise ValueError
        except ValueError:
            mm_per_pixel = DEFAULT_MM_PER_PIXEL
        try:
            box_size = int(values.get('box_size', DEFAULT_BOX_SIZE))
            if not 2 <= box_size <= 200:
                raise ValueError
        except ValueError:
            box_size = DEFAULT_BOX_SIZE
        extra = {k: v for k, v in values.items() if k not in _KNOWN_KEYS}
        return cls(data_folder=folder, mm_per_pixel=mm_per_pixel, box_size=box_size, path=path, extra=extra)

    def save(self) -> None:
        rows = [['', '0'],
                ['Application_path', self.data_folder],
                ['mm_per_pixel', repr(float(self.mm_per_pixel))],
                ['box_size', str(int(self.box_size))]]
        rows += [[key, value] for key, value in self.extra.items()]
        with open(self.path, 'w', newline='', encoding='utf-8') as handle:
            csv.writer(handle, lineterminator='\n').writerows(rows)

    @property
    def um_per_pixel(self) -> float:
        return self.mm_per_pixel * 1000.0


@dataclass(frozen=True)
class DataFolder:
    """The research data folder and its fixed subfolders."""

    root: str

    @property
    def recorded(self) -> str:
        return os.path.join(self.root, 'RecordedVideos')

    @property
    def stabilized(self) -> str:
        return os.path.join(self.root, 'StabilizedVideos')

    @property
    def flows(self) -> str:
        """Optical flow from versions before 2026-10-06; only read to trash it with its recording."""
        return os.path.join(self.root, 'Flows')

    @property
    def statistics(self) -> str:
        return os.path.join(self.root, 'Statistics')

    @property
    def reports(self) -> str:
        return os.path.join(self.root, 'Reports')

    @property
    def validation(self) -> str:
        """Reading sets: blocks read by observers to validate the centre-line velocity (created when needed)."""
        return os.path.join(self.root, 'Validation')

    @property
    def trash(self) -> str:
        """Where deleted videos and data sets are moved; empty it by hand."""
        return os.path.join(self.root, '.trash')

    def partial(self, folder: str) -> str:
        """Hidden folder inside `folder` where a job writes its output until it is complete."""
        return os.path.join(folder, '.partial')

    def ensure(self) -> None:
        for folder in (self.recorded, self.stabilized, self.statistics, self.reports):
            os.makedirs(folder, exist_ok=True)
