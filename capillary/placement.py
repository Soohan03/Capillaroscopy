"""Reproducibility of the whole centre-line measurement: one capillary measured by different observers.

The blinded reading (`capillary.validation`) checks the estimator on fixed
diagrams. A real measurement also depends on where its line is drawn: which
stretch of which vessel, how close to its middle. Here centre-line data sets
that measure the same capillary over the same frames are found, and their
median velocities compared between observers (inter-observer) and between two
measurements by one observer (intra-observer).

Matching is automatic. Two data sets of a recording measure the same capillary
if their lines run along each other: at least `MIN_LINE_OVERLAP` of one line
lies within `MATCH_PX` of the other. They measure the same frames if their
frame ranges overlap by at least `MIN_FRAME_OVERLAP` of the frames either of
them covers. A line drawn the other way round is compared with its sign
reversed. Every connected set of matching data sets is one *capillary*.

The observer of a data set is what was entered on the Centre line page when it
was measured (``observer`` in its provenance); data sets without one take part
in no comparison.

Nothing here imports a GUI toolkit.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd

from . import agreement, datasets, validation
from .spacetime import Centreline

#: Lines whose samples lie this close (px) count as running along each other.
MATCH_PX = 5.0
#: Share of one line that must run along the other.
MIN_LINE_OVERLAP = 0.5
#: Share of the frames measured by either that both must have measured.
MIN_FRAME_OVERLAP = 0.8
#: Folder in ``Validation/`` for the report (a name reading sets may not take).
REPORT_DIR = validation.RESERVED_NAME
REPORT_FILES = {'measurements': 'measurements.csv', 'capillaries': 'capillaries.csv', 'summary': 'summary.csv',
                'bland_altman': 'bland_altman.png', 'scatter': 'scatter.png'}

NAN = float('nan')


@dataclass(frozen=True)
class Measurement:
    """What a centre-line data set says about where it measured and what it found."""

    recording: str
    dataset: str
    observer: str                 # '' if not recorded
    points: tuple
    first_frame: int
    last_frame: int
    median_mm_s: float
    resolved_fraction: float
    created: str

    @property
    def frames(self) -> int:
        return self.last_frame - self.first_frame + 1


def load_measurements(statistics_dir: str, sources: Iterable[tuple[str, str]]) -> list[Measurement]:
    """The centre-line data sets `sources` (``(recording, data set)``) that recorded their line and frames."""
    found = []
    for stem, name in sources:
        record = datasets.read_provenance(datasets.line_dataset_files(statistics_dir, stem, name)['provenance'])
        try:
            points = tuple((float(x), float(y)) for x, y in record['line']['points'])
            first, last = int(record['frames']['first']), int(record['frames']['last'])
        except (TypeError, KeyError, ValueError):
            continue
        summary = record.get('summary') or {}
        median = summary.get('median')
        resolved = summary.get('resolved_fraction')
        found.append(Measurement(recording=stem, dataset=name,
                                 observer=(record.get('observer') or '').strip().upper(), points=points,
                                 first_frame=first, last_frame=last,
                                 median_mm_s=float(median) if median is not None else NAN,
                                 resolved_fraction=float(resolved) if resolved is not None else NAN,
                                 created=str(record.get('created') or '')))
    return found


def line_overlap(a_points: Sequence, b_points: Sequence, tolerance: float = MATCH_PX) -> tuple[float, float, int]:
    """How far two lines run along each other.

    Returns the share of line a within `tolerance` px of line b, the share of
    b within `tolerance` of a, and +1 if they run the same way where they
    meet, -1 if opposite (+1 if they do not meet).
    """
    a_positions, a_normals = Centreline.from_points(a_points).sample_positions(1.0)
    b_positions, b_normals = Centreline.from_points(b_points).sample_positions(1.0)
    distance = np.hypot(a_positions[:, None, 0] - b_positions[None, :, 0],
                        a_positions[:, None, 1] - b_positions[None, :, 1])
    near_a = distance.min(axis=1) <= tolerance
    near_b = distance.min(axis=0) <= tolerance
    direction = 1
    if near_a.any():
        nearest = distance.argmin(axis=1)[near_a]
        # the normals are the tangents turned by 90 degrees, so their dot product compares the tangents
        dots = np.sum(a_normals[near_a] * b_normals[nearest], axis=1)
        direction = 1 if float(np.mean(dots)) >= 0 else -1
    return float(near_a.mean()), float(near_b.mean()), direction


def frame_overlap(a: Measurement, b: Measurement) -> float:
    """Frames both measured, as a share of the frames either measured."""
    shared = min(a.last_frame, b.last_frame) - max(a.first_frame, b.first_frame) + 1
    either = max(a.last_frame, b.last_frame) - min(a.first_frame, b.first_frame) + 1
    return max(0, shared) / either if either > 0 else 0.0


def match(a: Measurement, b: Measurement) -> Optional[int]:
    """+1 or -1 (their lines' relative direction) if `a` and `b` measure the same capillary and frames, else None."""
    if a.recording != b.recording or frame_overlap(a, b) < MIN_FRAME_OVERLAP:
        return None
    covered_a, covered_b, direction = line_overlap(a.points, b.points)
    return direction if max(covered_a, covered_b) >= MIN_LINE_OVERLAP else None


def group_measurements(measurements: Sequence[Measurement]) -> list[list[tuple[Measurement, int]]]:
    """Capillaries measured more than once: each a list of (measurement, sign), the sign turning every
    velocity into the direction of the group's first line. Sorted by recording, then by creation."""
    ordered = sorted(measurements, key=lambda m: (m.recording, m.created, m.dataset))
    edges: dict[int, list[tuple[int, int]]] = {i: [] for i in range(len(ordered))}
    for i, j in combinations(range(len(ordered)), 2):
        direction = match(ordered[i], ordered[j])
        if direction is not None:
            edges[i].append((j, direction))
            edges[j].append((i, direction))
    seen, groups = set(), []
    for start in range(len(ordered)):
        if start in seen or not edges[start]:
            continue
        signs, queue = {start: 1}, [start]
        while queue:
            current = queue.pop()
            for other, direction in edges[current]:
                if other not in signs:
                    signs[other] = signs[current] * direction
                    queue.append(other)
        seen.update(signs)
        groups.append([(ordered[i], signs[i]) for i in sorted(signs)])
    return groups


def placement_tables(groups: Sequence[Sequence[tuple[Measurement, int]]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(one row per data set, one row per capillary).

    Per capillary and observer: ``<observer>_velocity_mm_s`` is the median of
    that observer's first data set on it (in the direction of the capillary's
    first line), ``<observer>_repeat_velocity_mm_s`` that of their second.
    """
    rows, capillaries = [], []
    for number, group in enumerate(groups, start=1):
        capillary = f'c{number:02d}'
        row = {'capillary': capillary, 'recording': group[0][0].recording, 'datasets': len(group),
               'observers': ', '.join(sorted({m.observer for m, _ in group if m.observer})) or ''}
        taken: dict[str, int] = {}
        for measurement, sign in group:
            velocity = sign * measurement.median_mm_s
            rows.append({'capillary': capillary, 'recording': measurement.recording, 'dataset': measurement.dataset,
                         'observer': measurement.observer, 'first_frame': measurement.first_frame,
                         'last_frame': measurement.last_frame, 'reversed': sign < 0,
                         'median_velocity_mm_s': velocity, 'resolved_fraction': measurement.resolved_fraction,
                         'created': measurement.created})
            if not measurement.observer:
                continue
            count = taken.get(measurement.observer, 0)
            if count == 0:
                row[f'{measurement.observer}_velocity_mm_s'] = velocity
                row[f'{measurement.observer}_dataset'] = measurement.dataset
            elif count == 1:
                row[f'{measurement.observer}_repeat_velocity_mm_s'] = velocity
                row[f'{measurement.observer}_repeat_dataset'] = measurement.dataset
            taken[measurement.observer] = count + 1
        capillaries.append(row)
    return pd.DataFrame(rows), pd.DataFrame(capillaries)


def _pair(table: pd.DataFrame, name: str, kind: str, first_column: str, second_column: str, first: str,
          second: str, confidence: float) -> dict:
    a = table[first_column].to_numpy(dtype=float) if first_column in table else np.full(len(table), NAN)
    b = table[second_column].to_numpy(dtype=float) if second_column in table else np.full(len(table), NAN)
    ba = agreement.bland_altman(a, b, confidence)
    ratio = agreement.bland_altman_ratio(a, b, confidence)
    icc = agreement.icc(np.column_stack([a, b]), confidence)
    row = {'comparison': name, 'kind': kind, 'first': first, 'second': second, 'first_column': first_column,
           'second_column': second_column, 'pairs': ba['n']}
    row.update({key: value for key, value in ba.items() if key != 'n'})
    if kind == 'within observer':
        row['repeatability_coefficient'] = agreement.LOA_Z * ba['sd']
    row.update({'ratio_pairs': ratio['n'], 'ratio': ratio['ratio'], 'ratio_ci_low': ratio['ratio_ci_low'],
                'ratio_ci_high': ratio['ratio_ci_high'], 'ratio_loa_low': ratio['loa_low'],
                'ratio_loa_high': ratio['loa_high'],
                'icc_agreement': icc['agreement'], 'icc_agreement_ci_low': icc['agreement_ci_low'],
                'icc_agreement_ci_high': icc['agreement_ci_high'], 'icc_consistency': icc['consistency'],
                'icc_consistency_ci_low': icc['consistency_ci_low'],
                'icc_consistency_ci_high': icc['consistency_ci_high'],
                'same_direction': agreement.same_direction(a, b)['fraction']})
    return row


def compare_placements(capillaries: pd.DataFrame, confidence: float = 0.95) -> list[dict]:
    """Median velocities of the same capillaries: every pair of observers, all of them, and repeats by one."""
    observers = sorted(column[:-len('_velocity_mm_s')] for column in capillaries.columns
                       if column.endswith('_velocity_mm_s') and not column.endswith('_repeat_velocity_mm_s'))
    rows = [_pair(capillaries, f'{one} vs {other}', 'between observers', f'{one}_velocity_mm_s',
                  f'{other}_velocity_mm_s', one, other, confidence) for one, other in combinations(observers, 2)]
    if len(observers) >= 3:
        ratings = np.column_stack([capillaries[f'{o}_velocity_mm_s'].to_numpy(dtype=float) for o in observers])
        icc = agreement.icc(ratings, confidence)
        rows.append({'comparison': f'All observers ({", ".join(observers)})', 'kind': 'between observers',
                     'first': ', '.join(observers), 'second': '', 'pairs': icc['n'],
                     'icc_agreement': icc['agreement'], 'icc_agreement_ci_low': icc['agreement_ci_low'],
                     'icc_agreement_ci_high': icc['agreement_ci_high'], 'icc_consistency': icc['consistency'],
                     'icc_consistency_ci_low': icc['consistency_ci_low'],
                     'icc_consistency_ci_high': icc['consistency_ci_high']})
    for observer in observers:
        repeat = f'{observer}_repeat_velocity_mm_s'
        if repeat in capillaries and capillaries[repeat].notna().any():
            rows.append(_pair(capillaries, f'{observer}: first vs second measurement', 'within observer',
                              f'{observer}_velocity_mm_s', repeat, f'{observer}, first',
                              f'{observer}, second', confidence))
    return rows


def write_report_tables(report_dir: str, measurements: pd.DataFrame, capillaries: pd.DataFrame,
                        comparisons: Sequence[dict]) -> dict:
    os.makedirs(report_dir, exist_ok=True)
    files = {role: os.path.join(report_dir, name) for role, name in REPORT_FILES.items()}
    measurements.to_csv(files['measurements'], index=False)
    capillaries.to_csv(files['capillaries'], index=False)
    pd.DataFrame(list(comparisons)).to_csv(files['summary'], index=False)
    return {role: files[role] for role in ('measurements', 'capillaries', 'summary')}
