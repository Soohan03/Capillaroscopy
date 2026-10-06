"""Saved measurements on disk: file names, formats, and how a data set was made.

Every measurement the GUI saves is a *data set*: a few files in ``Statistics/``
named ``<stem>___<name>___<part>``, where ``<stem>`` is the video file name
without extension and ``<name>`` is what the user typed. The report code reads
them back from there. Data sets written by earlier versions of the app use the
same names and formats, so they stay readable.

Velocity data set (Analyze page)
    ``___cross_correlation.csv``  mean intensity of box 1 (row 0) and box 2
                                  (row 1), one column per frame
    ``___distance_vector.csv``    box separation in pixels, one row per frame
    ``___blur_vector.csv``        sharpness score (`capillary.quality`), per frame
    ``___report.csv``             written by the report (`Caper.CrossCorrelation`)

Frames outside the measured range are NaN. Since the 2026-10 GUI rebuild each
data set also gets ``___velocity_provenance.json`` recording the video, boxes,
frame range, calibration and software version behind it, so the numbers can be
traced back and reproduced.

Versions before 2026-10-06 also had an optical-flow measurement, saved as
``___flow.pickle`` and ``___mask.pickle`` (plus ``___flow_provenance.json``)
with plots in ``Reports/``. Nothing reads those any more; they are only moved
to the trash together with their recording (`legacy_flow_dataset_paths`).

Time points marked on a recording live in ``<stem>_registered_time_points.csv``
(one underscore), in seconds from the start of the video.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
import re
import subprocess
from typing import Iterable, Optional

import numpy as np
import pandas as pd

SEPARATOR = '___'

VELOCITY_INPUTS = ('cross_correlation', 'distance_vector', 'blur_vector')

#: Plot and summary files the velocity report writes to ``Reports/``, by role.
#: Note the missing separator before the plot names, kept from the original.
VELOCITY_REPORT_FILES = {
    'velocity': 'velocity.png',
    'velocity_above_zero': 'velocity_above_zero.png',
    'correlation': 'correlation.png',
    'velocity_above_zero_with_correlation': 'velocity_above_zero_with_correlation.png',
    'summary': '___report_summary.csv',
}

#: Files of an optical-flow data set from before 2026-10-06, after ``<stem>___<name>___``:
#: the first marks the data set; the plots are in ``Reports/``, the rest in ``Statistics/``.
LEGACY_FLOW_STATISTICS = ('flow.pickle', 'mask.pickle', 'flow_provenance.json')
LEGACY_FLOW_REPORTS = ('up_and_down_.png', 'omnidirectional_.png')

#: Shortest range the velocity report can use: its longest window is 301 frames.
MIN_VELOCITY_FRAMES = 301

_FORBIDDEN_NAME_CHARACTERS = '<>:"/\\|?*'


# --------------------------------------------------------------------------- names

def dataset_prefix(directory: str, stem: str, name: str) -> str:
    """``<directory>/<stem>___<name>``, the common start of a data set's files."""
    return os.path.join(directory, f'{stem}{SEPARATOR}{name}')


def velocity_dataset_files(statistics_dir: str, stem: str, name: str) -> dict:
    """Paths of a velocity data set's files, keyed by part."""
    prefix = dataset_prefix(statistics_dir, stem, name)
    files = {part: f'{prefix}{SEPARATOR}{part}.csv' for part in VELOCITY_INPUTS}
    files['report'] = f'{prefix}{SEPARATOR}report.csv'
    files['provenance'] = f'{prefix}{SEPARATOR}velocity_provenance.json'
    return files


def velocity_report_files(reports_dir: str, stem: str, name: str) -> dict:
    """Paths of the files the velocity report writes to ``Reports/``."""
    prefix = dataset_prefix(reports_dir, stem, name)
    return {role: prefix + suffix for role, suffix in VELOCITY_REPORT_FILES.items()}


def time_points_file(statistics_dir: str, stem: str) -> str:
    return os.path.join(statistics_dir, f'{stem}_registered_time_points.csv')


def _names_with_suffix(directory: str, stem: str, suffix: str) -> list[str]:
    head = f'{stem}{SEPARATOR}'
    pattern = os.path.join(glob.escape(directory), glob.escape(head) + '*' + glob.escape(suffix))
    names = []
    for path in glob.glob(pattern):
        base = os.path.basename(path)
        names.append(base[len(head):len(base) - len(suffix)])
    return sorted(set(names))


def list_velocity_datasets(statistics_dir: str, stem: str) -> list[str]:
    """Names of the velocity data sets saved for `stem`, sorted."""
    return _names_with_suffix(statistics_dir, stem, f'{SEPARATOR}cross_correlation.csv')


def validate_dataset_name(name: str) -> Optional[str]:
    """Why `name` cannot be used for a data set, or None if it can.

    Names become part of file names, so they must be usable on Windows too and
    must not contain the ``___`` that separates the parts of a file name.
    """
    if name is None or name.strip() == '':
        return 'Enter a name for the data set.'
    if name != name.strip():
        return 'The name must not start or end with a space.'
    if len(name) > 80:
        return 'Use at most 80 characters.'
    if SEPARATOR in name:
        return 'The name must not contain "___" (three underscores).'
    bad = sorted({c for c in name if c in _FORBIDDEN_NAME_CHARACTERS or ord(c) < 32})
    if bad:
        shown = ' '.join(repr(c)[1:-1] if ord(c) >= 32 else '\\x%02x' % ord(c) for c in bad)
        return f'These characters cannot be used in file names: {shown}'
    if name.endswith('.'):
        return 'The name must not end with a dot.'
    return None


def suggest_dataset_name(existing: Iterable[str], base: str = 'set') -> str:
    """The first of ``set1``, ``set2``, ... not in `existing`."""
    taken = set(existing)
    number = 1
    while f'{base}{number}' in taken:
        number += 1
    return f'{base}{number}'


# --------------------------------------------------------------------- time points

def load_time_points(path: str) -> list[float]:
    """Time points (seconds) from a ``_registered_time_points.csv``; [] if none."""
    try:
        values = pd.read_csv(path)['0'].to_numpy(dtype=float)
    except (FileNotFoundError, KeyError, ValueError, pd.errors.EmptyDataError):
        return []
    return [float(v) for v in values if np.isfinite(v)]


def save_time_points(path: str, seconds: Iterable[float]) -> None:
    """Write time points (seconds) in the format `load_time_points` reads."""
    pd.DataFrame(sorted(float(s) for s in seconds)).to_csv(path)


# --------------------------------------------------------------- writing data sets

def _framewise(values, start: int, frame_count: int) -> np.ndarray:
    """`values` placed at frames ``start...`` of a NaN vector `frame_count` long."""
    values = np.asarray(values, dtype=float)
    out = np.full(frame_count, np.nan)
    stop = min(frame_count, start + values.size)
    out[start:stop] = values[:stop - start]
    return out


def write_velocity_dataset(
    statistics_dir: str,
    stem: str,
    name: str,
    a,
    b,
    distance_px: float,
    blur,
    start_frame: int,
    frame_count: int,
) -> dict:
    """Save the inputs of a velocity report; returns the paths written.

    `a` and `b` are the per-frame mean intensities of box 1 and box 2 for the
    frames ``start_frame, start_frame + 1, ...``; `blur` is the sharpness of
    the same frames. Every file covers all `frame_count` frames of the video,
    NaN outside the measured range, in the layout the report reads.
    """
    files = velocity_dataset_files(statistics_dir, stem, name)
    intensity = np.vstack([
        _framewise(a, start_frame, frame_count),
        _framewise(b, start_frame, frame_count),
    ])
    measured = np.isfinite(intensity[0])
    distance = np.where(measured, float(distance_px), np.nan)

    pd.DataFrame(intensity).to_csv(files['cross_correlation'])
    pd.DataFrame(distance).to_csv(files['distance_vector'])
    pd.DataFrame(_framewise(blur, start_frame, frame_count)).to_csv(files['blur_vector'])
    return {part: files[part] for part in VELOCITY_INPUTS}


# --------------------------------------------------------------------- provenance

def software_version(repository: Optional[str] = None) -> dict:
    """Git commit of the code that is running, if it can be determined."""
    repository = repository or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    info = {'git_commit': None, 'git_uncommitted_changes': None}
    try:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repository, capture_output=True,
                                text=True, timeout=5)
        if commit.returncode == 0:
            info['git_commit'] = commit.stdout.strip()
            status = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=repository,
                                    capture_output=True, text=True, timeout=5)
            if status.returncode == 0:
                info['git_uncommitted_changes'] = bool(status.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return info


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f'not JSON serializable: {type(value).__name__}')


def _clean(value):
    """NaN and infinity become None, so the file is strict JSON."""
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return value


def write_provenance(path: str, record: dict) -> None:
    """Write a provenance record, adding when it was written."""
    record = dict(record)
    record.setdefault('written', datetime.datetime.now().isoformat(timespec='seconds'))
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(_clean(record), handle, indent=2, ensure_ascii=False, default=_json_default)
        handle.write('\n')


def read_provenance(path: str) -> Optional[dict]:
    """The provenance record at `path`, or None for data sets made before it existed."""
    try:
        with open(path, encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


# -------------------------------------------------------------------- whole data set

def dataset_paths(statistics_dir: str, reports_dir: str, stem: str, name: str) -> list[str]:
    """Every file belonging to one velocity data set that exists on disk.

    Used to move a data set to the trash as a unit; names are matched exactly,
    so ``Test`` never picks up the files of ``Test2``.
    """
    candidates = list(velocity_dataset_files(statistics_dir, stem, name).values())
    candidates += list(velocity_report_files(reports_dir, stem, name).values())
    return [path for path in candidates if os.path.exists(path)]


def legacy_flow_dataset_paths(statistics_dir: str, reports_dir: str, stem: str, name: str) -> list[str]:
    """Every file of an optical-flow data set from before 2026-10-06 that exists on disk."""
    statistics = dataset_prefix(statistics_dir, stem, name) + SEPARATOR
    reports = dataset_prefix(reports_dir, stem, name) + SEPARATOR
    candidates = [statistics + part for part in LEGACY_FLOW_STATISTICS]
    candidates += [reports + part for part in LEGACY_FLOW_REPORTS]
    return [path for path in candidates if os.path.exists(path)]


_SAFE_STEM = re.compile(r'[^\w\-. ]+', re.UNICODE)


def safe_file_part(text: str) -> str:
    """`text` with characters that do not belong in a file name replaced by '_'."""
    return _SAFE_STEM.sub('_', text).strip(' .') or 'recording'
