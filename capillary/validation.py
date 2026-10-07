"""Validating the centre-line velocity on real recordings: blinded reading of the streaks by observers.

A recording has no ground truth, so the automatic estimate
(`capillary.spacetime`) is compared with people reading the same space-time
diagrams by hand, the way the slope of the streaks has been read in
capillaroscopy before (Cap-Image, Klyscz et al. 1997):

1. A **reading set** is made from saved centre-line data sets. From each, a
   few of the 3-s blocks the estimator measured are drawn at random, never
   overlapping; by default half of them from blocks the estimator resolved
   and the rest from blocks it did not, so that both kinds get read. The
   blocks are copied into the set, which therefore never changes, even if a
   data set is measured again or moved to the trash.
2. Every observer reads every block, in an order of their own, without seeing
   where it comes from or what the estimator found. They draw lines along the
   streaks (the slope of a block is the mean slope of its lines) or mark it as
   having no clear streaks. One observer's pass through the set is a
   **reading**; a second session by the same observer, in a new order, gives
   the repeatability.
3. The **agreement** is computed afterwards: the estimator against each
   reading and against the mean of the observers, the observers against each
   other, and each observer's sessions against each other (`compare`, with
   the statistics of `capillary.agreement`).

On disk, in ``Validation/<set name>/`` in the data folder::

    set.json                    what the set holds and how it was drawn
    blocks.npz                  the blocks (float32, frames x positions), by item id
    readings/<observer>_s<session>.json    one reading each
    report/                     agreement tables (here) and plots (Caper.py)

Nothing here imports a GUI toolkit.
"""

from __future__ import annotations

import datetime
import hashlib
import math
import os
import random
import re
import shutil
from dataclasses import dataclass, field
from itertools import combinations
from typing import Callable, Iterable, Optional, Sequence

import numpy as np
import pandas as pd

from . import agreement, datasets, spacetime

FORMAT = 1
SET_FILE = 'set.json'
BLOCKS_FILE = 'blocks.npz'
READINGS_DIR = 'readings'
REPORT_DIR = 'report'
REPORT_FILES = {'items': 'agreement_items.csv', 'summary': 'agreement_summary.csv', 'readings': 'readings.csv',
                'bland_altman': 'bland_altman.png', 'scatter': 'scatter.png'}

#: Blocks drawn from each data set when a reading set is made.
DEFAULT_BLOCKS_PER_DATASET = 6
#: A drawn line must span at least this many frames: one flatter in time gives no usable slope.
MIN_LINE_FRAMES = 4.0
#: What an observer can decide about a block.
SLOPE, NO_STREAKS = 'slope', 'no streaks'
#: Observer codes: initials or a short name; they become part of file names.
_OBSERVER = re.compile(r'^[A-Z0-9][A-Z0-9-]{0,15}$')
#: The folder in ``Validation/`` that holds the line-placement comparison (`capillary.placement`).
RESERVED_NAME = 'line_placement'

DISPLAY = ('The block as observers see it: the mean of every position over time and the mean of every frame along '
           'the line removed, contrast from the 1st to the 99th percentile, position along the line across (its '
           'first point on the left), time downwards, one pixel along the line as wide as one frame is tall.')

NAN = float('nan')


# ------------------------------------------------------------------------------ items

@dataclass(frozen=True)
class Item:
    """One block of a reading set: rows ``start_row`` .. ``start_row + frames - 1`` of a data set's diagram."""

    id: str
    recording: str
    dataset: str
    start_row: int
    first_frame: int            # video frame of the block's first row
    frames: int
    positions: int              # samples along the line (its length in px + 1)
    fps: float
    mm_per_pixel: float
    estimate: dict              # the data set's own result for this block when the set was made

    @property
    def mm_s_per_px_frame(self) -> float:
        """Velocity in mm/s of a speed of 1 px/frame along the line."""
        return self.fps * self.mm_per_pixel

    @property
    def centre_time_s(self) -> float:
        return (self.first_frame + self.frames / 2) / self.fps

    def as_record(self) -> dict:
        return {'id': self.id, 'recording': self.recording, 'dataset': self.dataset, 'start_row': self.start_row,
                'first_frame': self.first_frame, 'frames': self.frames, 'positions': self.positions,
                'fps': self.fps, 'mm_per_pixel': self.mm_per_pixel, 'estimate_when_drawn': self.estimate}

    @classmethod
    def from_record(cls, record: dict) -> 'Item':
        return cls(id=str(record['id']), recording=record['recording'], dataset=record['dataset'],
                   start_row=int(record['start_row']), first_frame=int(record['first_frame']),
                   frames=int(record['frames']), positions=int(record['positions']), fps=float(record['fps']),
                   mm_per_pixel=float(record['mm_per_pixel']), estimate=dict(record.get('estimate_when_drawn') or {}))


def validate_set_name(name: str) -> Optional[str]:
    """Why `name` cannot be used for a reading set (it becomes a folder name), or None."""
    message = datasets.validate_dataset_name(name)
    if message is None and name.startswith('.'):
        return 'The name must not start with a dot.'
    if message is None and name.lower() == RESERVED_NAME:
        return f'"{name}" is the folder of the line-placement comparison; choose another name.'
    return message.replace('data set', 'reading set') if message else None


def normalize_observer(text: str) -> str:
    return (text or '').strip().upper()


def validate_observer(text: str) -> Optional[str]:
    """Why `text` cannot be used as an observer code, or None."""
    code = normalize_observer(text)
    if not code:
        return 'Enter the observer\'s initials.'
    if not _OBSERVER.match(code):
        return 'Use up to 16 letters, digits or dashes, for example initials such as SJ.'
    return None


# -------------------------------------------------------------------------- choosing

def choose_blocks(starts: Sequence[int], resolved: Sequence[bool], count: int, block_frames: int,
                  balanced: bool, rng: np.random.Generator) -> list[int]:
    """Up to `count` of `starts` whose blocks (`block_frames` long) do not overlap, drawn at random.

    With `balanced`, half of them (rounded up) come from the resolved blocks
    and the rest from the unresolved ones; if one kind runs short, the other
    makes up the difference.
    """
    starts = np.asarray(starts, dtype=int)
    resolved = np.asarray(resolved, dtype=bool)
    chosen: list[int] = []

    def draw(pool, wanted):
        for start in rng.permutation(pool):
            if len(chosen) >= wanted:
                return
            if all(abs(int(start) - other) >= block_frames for other in chosen):
                chosen.append(int(start))

    if balanced:
        draw(starts[resolved], (count + 1) // 2)
        draw(starts[~resolved], count)
        draw(starts, count)
    else:
        draw(starts, count)
    return sorted(chosen)


def _source_blocks(diagram: np.ndarray, blocks: pd.DataFrame, first_frame: int, block_frames: int,
                   step_frames: int) -> list[dict]:
    """The blocks the estimator measured in a diagram, with its result for each (computed if not saved)."""
    found = []
    for start in range(0, diagram.shape[0] - block_frames + 1, step_frames):
        centre = first_frame + start + block_frames // 2
        if centre in blocks.index:
            row = blocks.loc[centre]
            estimate = {'speed_px_per_frame': float(row['speed_px_per_frame']), 'snr': float(row['snr']),
                        'coherence': float(row['coherence']), 'resolved': bool(row['resolved'])}
        else:
            result = spacetime.streak_speed(diagram[start:start + block_frames])
            estimate = {'speed_px_per_frame': result.speed_px_per_frame, 'snr': result.snr,
                        'coherence': result.coherence, 'resolved': result.resolved}
        found.append({'start': start, 'estimate': estimate})
    return found


def _estimator_settings() -> dict:
    return {'block_frames': spacetime.DEFAULT_BLOCK_FRAMES, 'step_frames': spacetime.DEFAULT_STEP_FRAMES,
            'min_snr': spacetime.MIN_SNR, 'min_coherence': spacetime.MIN_COHERENCE, 'k_max': spacetime.K_MAX,
            'omega_taper': [spacetime.TAPER_START, spacetime.MAX_OMEGA],
            'fastest_fraction': spacetime.FASTEST_FRACTION}


# -------------------------------------------------------------------------- the set

@dataclass
class ReadingSet:
    directory: str
    record: dict
    items: list[Item]
    _blocks: Optional[dict] = field(default=None, repr=False)

    @property
    def name(self) -> str:
        return self.record['name']

    @property
    def seed(self) -> int:
        return int(self.record['seed'])

    @property
    def readings_dir(self) -> str:
        return os.path.join(self.directory, READINGS_DIR)

    @property
    def report_dir(self) -> str:
        return os.path.join(self.directory, REPORT_DIR)

    def report_files(self) -> dict:
        return {role: os.path.join(self.report_dir, name) for role, name in REPORT_FILES.items()}

    def item(self, item_id: str) -> Item:
        for item in self.items:
            if item.id == item_id:
                return item
        raise KeyError(item_id)

    def block(self, item_id: str) -> np.ndarray:
        """The block of `item_id` exactly as it was drawn: frames x positions."""
        if self._blocks is None:
            with np.load(os.path.join(self.directory, BLOCKS_FILE), allow_pickle=False) as data:
                self._blocks = {key: np.asarray(data[key]) for key in data.files}
        return self._blocks[item_id]

    def reading_path(self, observer: str, session: int) -> str:
        return os.path.join(self.readings_dir, f'{normalize_observer(observer)}_s{int(session)}.json')

    def readings(self) -> list['Reading']:
        """The readings saved so far, by observer and session."""
        found = []
        try:
            names = sorted(os.listdir(self.readings_dir))
        except OSError:
            return []
        for file_name in names:
            if file_name.endswith('.json'):
                try:
                    found.append(Reading.load(os.path.join(self.readings_dir, file_name)))
                except (OSError, ValueError, KeyError, TypeError):
                    continue
        return sorted(found, key=lambda reading: (reading.observer, reading.session))

    def open_reading(self, observer: str, session: int) -> 'Reading':
        """The reading of `observer` in `session`: the saved one, or a new one in its own order (saved on first use)."""
        observer = normalize_observer(observer)
        path = self.reading_path(observer, session)
        if os.path.exists(path):
            reading = Reading.load(path)
            missing = [item.id for item in self.items if item.id not in reading.order]
            reading.order += missing                      # cannot happen with an unchanged set; never lose items
            return reading
        return Reading(path=path, set_name=self.name, observer=observer, session=int(session),
                       order=reading_order([item.id for item in self.items], self.seed, observer, session))

    def next_session(self, observer: str) -> int:
        """The session an observer should open: their unfinished one, else the one after their last."""
        sessions = [r for r in self.readings() if r.observer == normalize_observer(observer)]
        unfinished = [r.session for r in sessions if not r.is_complete]
        if unfinished:
            return min(unfinished)
        return max((r.session for r in sessions), default=0) + 1

    def source_summary(self) -> list[dict]:
        return list(self.record.get('sources', []))


def list_reading_sets(validation_dir: str) -> list[str]:
    """Names of the reading sets in `validation_dir`, sorted."""
    try:
        entries = list(os.scandir(validation_dir))
    except OSError:
        return []
    return sorted((entry.name for entry in entries
                   if entry.is_dir() and not entry.name.startswith('.')
                   and os.path.isfile(os.path.join(entry.path, SET_FILE))), key=str.lower)


def load_reading_set(validation_dir: str, name: str) -> ReadingSet:
    directory = os.path.join(validation_dir, name)
    record = datasets.read_provenance(os.path.join(directory, SET_FILE))
    if record is None:
        raise FileNotFoundError(f'{name} is not a reading set (no readable {SET_FILE})')
    return ReadingSet(directory=directory, record=record, items=[Item.from_record(r) for r in record['items']])


def create_reading_set(validation_dir: str, statistics_dir: str, name: str, sources: Iterable[tuple[str, str]],
                       blocks_per_dataset: int = DEFAULT_BLOCKS_PER_DATASET, balanced: bool = True,
                       seed: Optional[int] = None, fallback_mm_per_pixel: Optional[float] = None,
                       progress: Optional[Callable[[float], None]] = None) -> ReadingSet:
    """Draw blocks from the centre-line data sets `sources` (``(recording, data set)`` pairs) into a new set.

    `seed` makes the drawing (and every observer's order) reproducible; a
    random one is chosen and recorded if it is None. The set is written to a
    hidden folder first and moved into place when complete.
    """
    message = validate_set_name(name)
    if message:
        raise ValueError(message)
    target = os.path.join(validation_dir, name)
    if os.path.exists(target):
        raise FileExistsError(f'A reading set named "{name}" already exists.')
    sources = sorted(set((str(stem), str(dataset)) for stem, dataset in sources))
    if not sources:
        raise ValueError('Choose at least one centre-line data set.')
    blocks_per_dataset = int(blocks_per_dataset)
    if blocks_per_dataset < 1:
        raise ValueError('Draw at least one block from each data set.')
    seed = int(seed) if seed is not None else random.SystemRandom().randrange(1, 1_000_000)
    rng = np.random.default_rng(seed)
    block_frames, step_frames = spacetime.DEFAULT_BLOCK_FRAMES, spacetime.DEFAULT_STEP_FRAMES

    drawn, arrays, source_records = [], [], []
    for number, (stem, dataset) in enumerate(sources):
        diagram, blocks = datasets.load_line_dataset(statistics_dir, stem, dataset)
        record = datasets.read_provenance(datasets.line_dataset_files(statistics_dir, stem, dataset)['provenance'])
        record = record or {}
        fps = float((record.get('video') or {}).get('fps') or 30.0)
        mm_per_pixel = record.get('mm_per_pixel') or fallback_mm_per_pixel
        if not mm_per_pixel:
            raise ValueError(f'The calibration of "{dataset}" ({stem}) is not known.')
        first_frame = int((record.get('frames') or {}).get('first', 0))
        candidates = _source_blocks(diagram, blocks, first_frame, block_frames, step_frames)
        starts = [candidate['start'] for candidate in candidates]
        resolved = [candidate['estimate']['resolved'] for candidate in candidates]
        chosen = choose_blocks(starts, resolved, blocks_per_dataset, block_frames, balanced, rng)
        estimates = {candidate['start']: candidate['estimate'] for candidate in candidates}
        for start in chosen:
            drawn.append(dict(recording=stem, dataset=dataset, start_row=start, first_frame=first_frame + start,
                              frames=block_frames, positions=int(diagram.shape[1]), fps=fps,
                              mm_per_pixel=float(mm_per_pixel), estimate=estimates[start]))
            arrays.append(np.asarray(diagram[start:start + block_frames], dtype=np.float32))
        source_records.append({
            'recording': stem, 'dataset': dataset, 'frames': record.get('frames'),
            'line_length_px': (record.get('line') or {}).get('length_px', float(diagram.shape[1] - 1)),
            'fps': fps, 'mm_per_pixel': float(mm_per_pixel), 'blocks_measured': len(candidates),
            'blocks_resolved': int(sum(resolved)), 'blocks_drawn': len(chosen),
            'resolved_drawn': int(sum(estimates[start]['resolved'] for start in chosen))})
        if progress is not None:
            progress((number + 1) / len(sources))
    if not drawn:
        raise ValueError('The chosen data sets hold no complete block of '
                         f'{block_frames} frames to draw from.')

    # item numbers in a random order, so they say nothing about where a block comes from
    order = rng.permutation(len(drawn))
    width = max(3, len(str(len(drawn))))
    items, blocks_by_id = [], {}
    for number, index in enumerate(order, start=1):
        item = Item(id=f'b{number:0{width}d}', **drawn[index])
        items.append(item)
        blocks_by_id[item.id] = arrays[index]

    record = {
        'format': FORMAT,
        'kind': 'reading set',
        'name': name,
        'created': datetime.datetime.now().isoformat(timespec='seconds'),
        'seed': seed,
        'sampling': {
            'blocks_per_dataset': blocks_per_dataset, 'balanced': bool(balanced), 'block_frames': block_frames,
            'step_frames': step_frames,
            'rule': ('From every data set, blocks the estimator measured were drawn at random without overlap'
                     + (', half of them (rounded up) from resolved blocks and the rest from unresolved ones, '
                        'either kind making up for a shortage of the other.' if balanced else '.')),
        },
        'display': DISPLAY,
        'estimator': _estimator_settings(),
        'sources': source_records,
        'items': [item.as_record() for item in items],
        'software': datasets.software_version(),
    }
    partial = os.path.join(validation_dir, '.partial', name)
    shutil.rmtree(partial, ignore_errors=True)
    os.makedirs(os.path.join(partial, READINGS_DIR))
    try:
        np.savez_compressed(os.path.join(partial, BLOCKS_FILE), **blocks_by_id)
        datasets.write_json(os.path.join(partial, SET_FILE), record)
        os.replace(partial, target)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    try:
        os.rmdir(os.path.dirname(partial))           # only if no other set is being made
    except OSError:
        pass
    return load_reading_set(validation_dir, name)


# --------------------------------------------------------------------------- readings

def reading_order(item_ids: Sequence[str], seed: int, observer: str, session: int) -> list[str]:
    """The order one observer reads the items in one session: random, but the same every time it is asked."""
    key = f'{int(seed)}:{normalize_observer(observer)}:{int(session)}'.encode()
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(key).digest()[:8], 'little'))
    return [item_ids[i] for i in rng.permutation(len(item_ids))]


def line_speed(lines: Iterable[Sequence[float]]) -> float:
    """Mean slope of drawn lines, in px along the vessel per frame; NaN if none is usable.

    Each line is ``(frame, position, frame, position)`` of its two ends in the
    block's rows and columns. Positive slopes run towards the line's last point.
    """
    slopes = [(p1 - p0) / (t1 - t0) for t0, p0, t1, p1 in lines if abs(t1 - t0) >= MIN_LINE_FRAMES]
    return float(np.mean(slopes)) if slopes else NAN


def usable_line(line: Sequence[float]) -> bool:
    t0, _, t1, _ = line
    return abs(t1 - t0) >= MIN_LINE_FRAMES


@dataclass
class Reading:
    """One observer's pass through a reading set, saved after every block."""

    path: str
    set_name: str
    observer: str
    session: int
    order: list[str]
    entries: dict = field(default_factory=dict)       # item id -> what was decided
    started: str = ''
    updated: str = ''

    @property
    def key(self) -> str:
        return f'{self.observer}_s{self.session}'

    @property
    def label(self) -> str:
        return f'{self.observer}, session {self.session}'

    @property
    def read_count(self) -> int:
        return sum(1 for item_id in self.order if self.outcome(item_id))

    @property
    def is_complete(self) -> bool:
        return bool(self.order) and self.read_count == len(self.order)

    def outcome(self, item_id: str) -> Optional[str]:
        return (self.entries.get(item_id) or {}).get('outcome')

    def lines(self, item_id: str) -> list[list[float]]:
        return [list(map(float, line)) for line in (self.entries.get(item_id) or {}).get('lines', [])]

    def speed(self, item_id: str) -> float:
        """The slope read for `item_id` (px/frame), NaN unless lines were drawn."""
        if self.outcome(item_id) != SLOPE:
            return NAN
        return line_speed(self.lines(item_id))

    def seconds(self, item_id: str) -> float:
        value = (self.entries.get(item_id) or {}).get('seconds')
        return float(value) if value is not None else NAN

    def first_unread(self) -> Optional[int]:
        for index, item_id in enumerate(self.order):
            if not self.outcome(item_id):
                return index
        return None

    def record_lines(self, item_id: str, lines: Iterable[Sequence[float]], seconds: float = NAN) -> None:
        usable = [[round(float(v), 3) for v in line] for line in lines if usable_line(line)]
        if not usable:
            raise ValueError('Draw at least one line along a streak.')
        self._set(item_id, {'outcome': SLOPE, 'lines': usable, 'speed_px_per_frame': line_speed(usable)}, seconds)

    def record_no_streaks(self, item_id: str, seconds: float = NAN) -> None:
        self._set(item_id, {'outcome': NO_STREAKS, 'lines': []}, seconds)

    def clear(self, item_id: str) -> None:
        if item_id in self.entries:
            del self.entries[item_id]
            self.save()

    def _set(self, item_id: str, entry: dict, seconds: float) -> None:
        if item_id not in self.order:
            raise KeyError(item_id)
        entry['seconds'] = round(float(seconds), 1) if math.isfinite(seconds) else None
        entry['read_at'] = datetime.datetime.now().isoformat(timespec='seconds')
        self.entries[item_id] = entry
        self.save()

    def save(self) -> None:
        now = datetime.datetime.now().isoformat(timespec='seconds')
        self.started = self.started or now
        self.updated = now
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        datasets.write_json(self.path, {
            'format': FORMAT, 'kind': 'reading', 'set': self.set_name, 'observer': self.observer,
            'session': self.session, 'started': self.started, 'updated': self.updated,
            'lines': 'each line is [frame, position, frame, position] of its ends in the block (rows, columns); '
                     'the slope of a block is the mean of its lines, in px along the line per frame',
            'order': self.order, 'items': self.entries})

    @classmethod
    def load(cls, path: str) -> 'Reading':
        record = datasets.read_provenance(path)
        if record is None or record.get('kind') != 'reading':
            raise ValueError(f'{path} is not a reading')
        return cls(path=path, set_name=record.get('set', ''), observer=normalize_observer(record['observer']),
                   session=int(record['session']), order=[str(i) for i in record['order']],
                   entries=dict(record.get('items') or {}), started=record.get('started', ''),
                   updated=record.get('updated', ''))


# -------------------------------------------------------------------------- agreement

def estimate_items(reading_set: ReadingSet, progress: Optional[Callable[[float], None]] = None) -> pd.DataFrame:
    """The estimator's result for every block, computed again now with the current code (index: item id)."""
    rows = []
    for number, item in enumerate(reading_set.items):
        result = spacetime.streak_speed(reading_set.block(item.id))
        resolved = result.resolved
        rows.append({'item': item.id, 'speed_px_per_frame': result.speed_px_per_frame, 'snr': result.snr,
                     'coherence': result.coherence, 'in_range': result.in_range, 'resolved': resolved,
                     'velocity_mm_s': result.speed_px_per_frame * item.mm_s_per_px_frame if resolved else NAN})
        if progress is not None:
            progress((number + 1) / len(reading_set.items))
    return pd.DataFrame(rows).set_index('item')


def first_sessions(readings: Sequence[Reading]) -> list[Reading]:
    """Each observer's earliest session, by observer."""
    first = {}
    for reading in sorted(readings, key=lambda r: (r.observer, r.session)):
        first.setdefault(reading.observer, reading)
    return list(first.values())


def agreement_table(reading_set: ReadingSet, readings: Sequence[Reading], estimates: pd.DataFrame) -> pd.DataFrame:
    """One row per block: where it comes from, the estimator's result, and every reading of it.

    For each reading ``<observer>_s<session>``: ``_outcome`` (``slope``,
    ``no streaks`` or empty if not read yet), ``_lines``, ``_speed_px_per_frame``,
    ``_velocity_mm_s`` and ``_seconds``. With two or more observers,
    ``observers_velocity_mm_s`` is the mean of their first sessions where all
    of them drew lines, and ``observers_readable`` is 1 where all drew lines,
    0 where none did, empty where they disagree or a block is not read yet.
    """
    rows = []
    first = first_sessions(readings)
    for item in reading_set.items:
        estimate = estimates.loc[item.id]
        row = {'item': item.id, 'recording': item.recording, 'dataset': item.dataset,
               'first_frame': item.first_frame, 'centre_time_s': item.centre_time_s, 'frames': item.frames,
               'line_length_px': item.positions - 1, 'fps': item.fps, 'mm_per_pixel': item.mm_per_pixel,
               'auto_speed_px_per_frame': float(estimate['speed_px_per_frame']), 'auto_snr': float(estimate['snr']),
               'auto_coherence': float(estimate['coherence']), 'auto_resolved': bool(estimate['resolved']),
               'auto_velocity_mm_s': float(estimate['velocity_mm_s'])}
        for reading in readings:
            outcome = reading.outcome(item.id) or ''
            speed = reading.speed(item.id)
            row[f'{reading.key}_outcome'] = outcome
            row[f'{reading.key}_lines'] = len(reading.lines(item.id)) if outcome else NAN
            row[f'{reading.key}_speed_px_per_frame'] = speed
            row[f'{reading.key}_velocity_mm_s'] = speed * item.mm_s_per_px_frame
            row[f'{reading.key}_seconds'] = reading.seconds(item.id)
        if len(first) >= 2:
            velocities = [row[f'{r.key}_velocity_mm_s'] for r in first]
            outcomes = [row[f'{r.key}_outcome'] for r in first]
            row['observers_velocity_mm_s'] = float(np.mean(velocities)) if all(map(math.isfinite, velocities)) else NAN
            if all(o == SLOPE for o in outcomes):
                row['observers_readable'] = 1.0
            elif all(o == NO_STREAKS for o in outcomes):
                row['observers_readable'] = 0.0
            else:
                row['observers_readable'] = NAN
        rows.append(row)
    return pd.DataFrame(rows)


def _readable(table: pd.DataFrame, source: str) -> np.ndarray:
    """1 where `source` gave a velocity, 0 where it judged there was none, NaN where it has not judged."""
    if source == 'auto':
        return table['auto_resolved'].astype(float).to_numpy()
    if source == 'observers':
        return table['observers_readable'].to_numpy(dtype=float)
    outcome = table[f'{source}_outcome'].fillna('')
    return np.where(outcome == SLOPE, 1.0, np.where(outcome == NO_STREAKS, 0.0, NAN))


def _velocity_column(source: str) -> str:
    return {'auto': 'auto_velocity_mm_s', 'observers': 'observers_velocity_mm_s'}.get(source,
                                                                                      f'{source}_velocity_mm_s')


def _comparison(table: pd.DataFrame, name: str, kind: str, first: str, second: str, first_label: str,
                second_label: str, confidence: float) -> dict:
    a = table[_velocity_column(first)].to_numpy(dtype=float)
    b = table[_velocity_column(second)].to_numpy(dtype=float)
    ba = agreement.bland_altman(a, b, confidence)
    ratio = agreement.bland_altman_ratio(a, b, confidence)
    icc = agreement.icc(np.column_stack([a, b]), confidence)
    kappa = agreement.cohens_kappa(_readable(table, first), _readable(table, second), confidence)
    row = {'comparison': name, 'kind': kind, 'first': first_label, 'second': second_label,
           'first_column': _velocity_column(first), 'second_column': _velocity_column(second),
           'judged_by_both': kappa['n'], 'pairs': ba['n']}
    row.update({key: value for key, value in ba.items() if key != 'n'})
    if kind == 'within observer':
        row['repeatability_coefficient'] = agreement.LOA_Z * ba['sd']
    row.update({'ratio_pairs': ratio['n'], 'ratio': ratio['ratio'], 'ratio_ci_low': ratio['ratio_ci_low'],
                'ratio_ci_high': ratio['ratio_ci_high'], 'ratio_loa_low': ratio['loa_low'],
                'ratio_loa_high': ratio['loa_high']})
    row.update({'icc_agreement': icc['agreement'], 'icc_agreement_ci_low': icc['agreement_ci_low'],
                'icc_agreement_ci_high': icc['agreement_ci_high'], 'icc_consistency': icc['consistency'],
                'icc_consistency_ci_low': icc['consistency_ci_low'],
                'icc_consistency_ci_high': icc['consistency_ci_high']})
    row['same_direction'] = agreement.same_direction(a, b)['fraction']
    row.update({'readable_both': kappa['both'], 'readable_first_only': kappa['first_only'],
                'readable_second_only': kappa['second_only'], 'readable_neither': kappa['neither'],
                'readable_agreement': kappa['agreement'], 'kappa': kappa['kappa'],
                'kappa_ci_low': kappa['kappa_ci_low'], 'kappa_ci_high': kappa['kappa_ci_high']})
    return row


def compare(table: pd.DataFrame, readings: Sequence[Reading], confidence: float = 0.95) -> list[dict]:
    """Every comparison the reading set allows, one summary row each (velocities in mm/s).

    - ``automatic vs observer``: the estimator against each reading;
    - ``automatic vs observers``: against the mean of the observers' first
      sessions (with two or more observers);
    - ``between observers``: first sessions pairwise and, with three or more
      observers, the ICC of all of them;
    - ``within observer``: each observer's first session against each later one.

    The first measurement of a pair is the one named first; differences are
    first minus second.
    """
    readings = sorted(readings, key=lambda r: (r.observer, r.session))
    rows = [_comparison(table, f'Automatic vs {r.label}', 'automatic vs observer', 'auto', r.key, 'automatic',
                        r.label, confidence) for r in readings]
    first = first_sessions(readings)
    if len(first) >= 2:
        names = ', '.join(r.observer for r in first)
        rows.append(_comparison(table, f'Automatic vs mean of observers ({names})', 'automatic vs observers',
                                'auto', 'observers', 'automatic', 'mean of observers', confidence))
        for one, other in combinations(first, 2):
            rows.append(_comparison(table, f'{one.label} vs {other.label}', 'between observers', one.key, other.key,
                                    one.label, other.label, confidence))
        if len(first) >= 3:
            ratings = np.column_stack([table[f'{r.key}_velocity_mm_s'].to_numpy(dtype=float) for r in first])
            icc = agreement.icc(ratings, confidence)
            rows.append({'comparison': f'All observers ({names})', 'kind': 'between observers', 'first': names,
                         'second': '', 'pairs': icc['n'], 'icc_agreement': icc['agreement'],
                         'icc_agreement_ci_low': icc['agreement_ci_low'],
                         'icc_agreement_ci_high': icc['agreement_ci_high'], 'icc_consistency': icc['consistency'],
                         'icc_consistency_ci_low': icc['consistency_ci_low'],
                         'icc_consistency_ci_high': icc['consistency_ci_high']})
    by_observer: dict[str, list[Reading]] = {}
    for reading in readings:
        by_observer.setdefault(reading.observer, []).append(reading)
    for observer, sessions in by_observer.items():
        for later in sessions[1:]:
            rows.append(_comparison(table, f'{observer}: session {sessions[0].session} vs session {later.session}',
                                    'within observer', sessions[0].key, later.key, sessions[0].label, later.label,
                                    confidence))
    return rows


def readings_summary(reading_set: ReadingSet, readings: Sequence[Reading]) -> pd.DataFrame:
    """Per reading: how far it got, how many blocks had streaks, how long reading took."""
    rows = []
    for reading in readings:
        outcomes = [reading.outcome(item.id) for item in reading_set.items]
        seconds = np.array([reading.seconds(item.id) for item in reading_set.items], dtype=float)
        seconds = seconds[np.isfinite(seconds)]
        rows.append({'observer': reading.observer, 'session': reading.session, 'items': len(reading_set.items),
                     'read': sum(1 for o in outcomes if o), 'slopes': outcomes.count(SLOPE),
                     'no_streaks': outcomes.count(NO_STREAKS),
                     'median_seconds_per_item': float(np.median(seconds)) if seconds.size else NAN,
                     'started': reading.started, 'updated': reading.updated})
    return pd.DataFrame(rows, columns=['observer', 'session', 'items', 'read', 'slopes', 'no_streaks',
                                       'median_seconds_per_item', 'started', 'updated'])


def write_report_tables(reading_set: ReadingSet, table: pd.DataFrame, comparisons: Sequence[dict],
                        readings: Sequence[Reading]) -> dict:
    """Write the per-block table, the comparisons and the readings to the set's report folder."""
    files = reading_set.report_files()
    os.makedirs(reading_set.report_dir, exist_ok=True)
    table.to_csv(files['items'], index=False)
    pd.DataFrame(list(comparisons)).to_csv(files['summary'], index=False)
    readings_summary(reading_set, readings).to_csv(files['readings'], index=False)
    return {role: files[role] for role in ('items', 'summary', 'readings')}


def read_comparisons(path: str) -> Optional[list[dict]]:
    """Comparisons saved as a summary table (missing values None); None if there is no table.

    An empty file means the report was made but had nothing to compare: [].
    """
    try:
        frame = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return []
    except (OSError, ValueError):
        return None
    return [{key: (None if isinstance(value, float) and math.isnan(value) else value)
             for key, value in row.items()} for row in frame.to_dict('records')]


def load_comparisons(reading_set: ReadingSet) -> Optional[list[dict]]:
    """The comparisons written by the last agreement report, or None if there is none."""
    return read_comparisons(reading_set.report_files()['summary'])
