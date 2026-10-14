"""The aims from the saved centre-line data sets: each recording's resting velocity, and aim 1's statistics.

python3 -m capillary.aims [--data <data folder>] [--observer <code>] [--out <folder>]

A recording's resting red-cell velocity is the mean over its capillary loops
(the plan of 2026-10-14, DEVLOG):

- every centre-line data set drawn round a whole loop
  (`capillary.pattern_shift.WHOLE_LOOP`) and measured within the official
  rest (``phase`` 'rest');
- counted when its pooled pattern shift is resolved (signal-to-noise 8 or
  more, the app's rule), its limbs did not move opposite ways along the line
  (``loop_movement``: the picture moving, not flow) and it was measured on a
  stabilized video;
- as the velocity's size: its sign only says which end of the line lies on
  the arterial limb.

The number of loops placed and counted is kept with each mean. Two loops of
one recording that lie on top of each other (`DUPLICATE_PX`) are listed, as
one capillary probably drawn twice; they are not removed, which is for the
observer to decide. Each observer's data sets are summarized on their own.

Aim 1, inter-day reproducibility, uses each participant's before-exposure
recording of both visits, as `capillary.inventory` chooses them, for every
participant with a mean at both. Per study:

- the within-subject coefficient of variation: the typical error (SD of the
  differences / sqrt 2) over the mean of all values, in %;
- the smallest detectable change, 2.77 x the typical error (1.96 x sqrt 2);
- Bland-Altman of active minus control: the bias and 95% limits of agreement;
- ICC(A,1): two-way, absolute agreement, single measurement (McGraw & Wong
  1996), with its 95% interval (`capillary.agreement`).

Also the CV on the log scale (exp(SD of the log differences / sqrt 2) - 1),
for velocities spread over several-fold.

Writes loops.csv, recordings.csv, aim1_pairs.csv and aim1.csv into
``Reports/aims/`` of the data folder (or --out) and prints a summary.
"""

from __future__ import annotations

import argparse
import csv
import glob
import math
import os
import sys
from typing import Optional, Sequence

import numpy as np
import pandas as pd

from . import agreement, datasets, inventory, pattern_shift
from .spacetime import Centreline

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: The range a loop must lie in, as the data set's summary names its official phase.
REST = 'rest'
#: The folder of the stabilized videos (`gui.settings.DataFolder.stabilized`).
STABILIZED_FOLDER = 'StabilizedVideos'
#: Two loops of one recording are flagged as one capillary drawn twice when at least half of the shorter
#: lies within this distance (px) of the other.
DUPLICATE_PX = 6.0
DUPLICATE_SHARE = 0.5
#: The smallest detectable change in typical errors: 1.96 x sqrt(2).
SDC_FACTOR = 2.77
COLUMNS = ('observer', 'recording', 'dataset', 'created', 'role', 'phase', 'video_folder', 'first_frame',
           'last_frame', 'seconds', 'length_px', 'velocity_mm_s', 'snr', 'resolved', 'ci95_low_mm_s',
           'ci95_high_mm_s', 'arterial_end', 'loop_movement', 'points')


def _number(value) -> float:
    """`value` as a float; NaN for None (NaN read back from JSON) and anything else not a number."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def collect(statistics_dir: str) -> pd.DataFrame:
    """One row per centre-line data set in `statistics_dir`, from its provenance (columns `COLUMNS`)."""
    rows = []
    for path in sorted(glob.glob(os.path.join(statistics_dir, f'*{datasets.SEPARATOR}line_provenance.json'))):
        record = datasets.read_provenance(path)
        if not record or record.get('kind') != 'line':
            continue
        summary, line = record.get('summary') or {}, record.get('line') or {}
        frames, video = record.get('frames') or {}, record.get('video') or {}
        fps = _number(video.get('fps'))
        count = _number(frames.get('count'))
        rows.append({
            'observer': record.get('observer') or '', 'recording': inventory.nfc(record.get('recording') or ''),
            'dataset': record.get('dataset') or '', 'created': record.get('created') or '',
            'role': line.get('role') or '', 'phase': summary.get('phase') or '',
            'video_folder': video.get('folder') or '', 'first_frame': _number(frames.get('first')),
            'last_frame': _number(frames.get('last')), 'seconds': count / fps if fps > 0 else math.nan,
            'length_px': _number(line.get('length_px')),
            'velocity_mm_s': _number(summary.get('pattern_shift_velocity_mm_s')),
            'snr': _number(summary.get('pattern_shift_snr')), 'resolved': bool(summary.get('pattern_shift_resolved')),
            'ci95_low_mm_s': _number(summary.get('pattern_shift_ci95_low_mm_s')),
            'ci95_high_mm_s': _number(summary.get('pattern_shift_ci95_high_mm_s')),
            'arterial_end': summary.get('arterial_end') or '', 'loop_movement': bool(summary.get('loop_movement')),
            'points': line.get('points') or []})
    return pd.DataFrame(rows, columns=list(COLUMNS))


def _overlap(first, second, spacing_px: float = 2.0) -> float:
    """The share of the shorter line that lies within `DUPLICATE_PX` of the other."""
    try:
        a, _ = Centreline.from_points(first).sample_positions(spacing_px)
        b, _ = Centreline.from_points(second).sample_positions(spacing_px)
    except (TypeError, ValueError):
        return 0.0
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    distances = np.hypot(shorter[:, None, 0] - longer[None, :, 0], shorter[:, None, 1] - longer[None, :, 1])
    return float(np.mean(distances.min(axis=1) <= DUPLICATE_PX))


def loops(table: pd.DataFrame) -> pd.DataFrame:
    """The whole loops of `table` (`collect`), with whether each is counted, its speed, and possible duplicates.

    Adds ``counted``; ``speed_mm_s``, the velocity's size where counted (else NaN); ``why_not``, why a loop
    is not counted; and ``duplicate_of``, the other loops of the recording it lies on.
    """
    out = table[table['role'] == pattern_shift.WHOLE_LOOP].copy().reset_index(drop=True)
    finite = np.isfinite(out['velocity_mm_s'].astype(float))
    reasons = [
        (out['phase'] != REST, 'not within the official rest'),
        (out['video_folder'] != STABILIZED_FOLDER, 'not on a stabilized video'),
        (~out['resolved'].astype(bool) | ~finite, 'not resolved'),
        (out['loop_movement'].astype(bool), 'limbs moved opposite ways (movement)'),
    ]
    out['why_not'] = [', '.join(text for mask, text in reasons if mask.iloc[i]) for i in range(len(out))]
    out['counted'] = out['why_not'] == ''
    out['speed_mm_s'] = out['velocity_mm_s'].abs().where(out['counted'])
    duplicates = [[] for _ in range(len(out))]
    for _, group in out.groupby(['observer', 'recording']):
        index = list(group.index)
        for i, first in enumerate(index):
            for second in index[i + 1:]:
                if _overlap(out.at[first, 'points'], out.at[second, 'points']) >= DUPLICATE_SHARE:
                    duplicates[first].append(out.at[second, 'dataset'])
                    duplicates[second].append(out.at[first, 'dataset'])
    out['duplicate_of'] = [', '.join(names) for names in duplicates]
    return out


def per_recording(loop_table: pd.DataFrame) -> pd.DataFrame:
    """One row per observer and recording: loops placed within the rest, counted, and the mean of the counted."""
    rows = []
    rest = loop_table[loop_table['phase'] == REST]
    for (observer, recording), group in rest.groupby(['observer', 'recording'], sort=True):
        speeds = group.loc[group['counted'], 'speed_mm_s'].astype(float)
        rows.append({'observer': observer, 'recording': recording, 'loops_placed': len(group),
                     'loops_counted': len(speeds), 'mean_mm_s': speeds.mean() if len(speeds) else math.nan,
                     'sd_mm_s': speeds.std(ddof=1) if len(speeds) > 1 else math.nan,
                     'speeds_mm_s': ', '.join(f'{v:.4f}' for v in sorted(speeds))})
    return pd.DataFrame(rows, columns=['observer', 'recording', 'loops_placed', 'loops_counted', 'mean_mm_s',
                                       'sd_mm_s', 'speeds_mm_s'])


def aim1_recordings(table: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Each participant's before-exposure recordings that aim 1 uses: study, subject, active and control names."""
    if table is None:
        table = inventory.recordings()
        table = inventory.mark_use(table, inventory.participants(table))
    used = table[table['used_for'].fillna('').str.contains(r'aims? 1\b') & (table['phase'] == 'före')]
    rows = []
    for (study, subject), group in used.groupby(['study', 'subject'], sort=False):
        names = {role: inventory.nfc(group.loc[group['role'] == role, 'name'].iloc[0])
                 if (group['role'] == role).any() else '' for role in ('active', 'control')}
        rows.append({'study': study, 'subject': subject, 'active_recording': names['active'],
                     'control_recording': names['control']})
    return pd.DataFrame(rows, columns=['study', 'subject', 'active_recording', 'control_recording'])


def aim1_pairs(recordings: pd.DataFrame, wanted: pd.DataFrame) -> pd.DataFrame:
    """Per observer and participant of `wanted` (`aim1_recordings`): each visit's mean and its loops."""
    rows = []
    observers = sorted(recordings['observer'].unique()) if len(recordings) else []
    for observer in observers:
        mine = recordings[recordings['observer'] == observer].set_index('recording')
        for person in wanted.itertuples(index=False):
            row = {'observer': observer, 'study': person.study, 'subject': person.subject}
            for role in ('active', 'control'):
                name = getattr(person, f'{role}_recording')
                found = name in mine.index
                row.update({f'{role}_recording': name,
                            f'{role}_loops_placed': int(mine.at[name, 'loops_placed']) if found else 0,
                            f'{role}_loops_counted': int(mine.at[name, 'loops_counted']) if found else 0,
                            f'{role}_mm_s': float(mine.at[name, 'mean_mm_s']) if found else math.nan})
            rows.append(row)
    return pd.DataFrame(rows)


def reproducibility(active, control) -> dict:
    """Aim 1's statistics of paired values (one pair per participant; pairs with a missing value left out)."""
    a, c = np.asarray(active, dtype=float), np.asarray(control, dtype=float)
    keep = np.isfinite(a) & np.isfinite(c)
    a, c = a[keep], c[keep]
    n = int(a.size)
    out = {'participants': n, 'mean_active_mm_s': a.mean() if n else math.nan,
           'mean_control_mm_s': c.mean() if n else math.nan, 'grand_mean_mm_s': np.r_[a, c].mean() if n else math.nan}
    typical = float(np.std(a - c, ddof=1) / math.sqrt(2)) if n >= 2 else math.nan
    positive = n >= 2 and bool(np.all(a > 0) and np.all(c > 0))
    log_typical = float(np.std(np.log(a) - np.log(c), ddof=1) / math.sqrt(2)) if positive else math.nan
    out.update(typical_error_mm_s=typical, cv_percent=100 * typical / out['grand_mean_mm_s'] if n else math.nan,
               cv_log_percent=100 * (math.exp(log_typical) - 1) if math.isfinite(log_typical) else math.nan,
               sdc_mm_s=SDC_FACTOR * typical)
    limits = agreement.bland_altman(a, c)
    out.update({f'ba_{key}': limits[key] for key in ('bias', 'bias_ci_low', 'bias_ci_high', 'loa_low', 'loa_high')})
    icc = agreement.icc(np.column_stack([a, c])) if n else {}
    out.update(icc_a1=icc.get('agreement', math.nan), icc_a1_ci_low=icc.get('agreement_ci_low', math.nan),
               icc_a1_ci_high=icc.get('agreement_ci_high', math.nan))
    return out


def aim1(pairs: pd.DataFrame) -> pd.DataFrame:
    """`reproducibility` per observer and study, with how many participants had a value at one visit only."""
    rows = []
    for (observer, study), group in pairs.groupby(['observer', 'study'], sort=True):
        both = np.isfinite(group['active_mm_s']) & np.isfinite(group['control_mm_s'])
        one = np.isfinite(group['active_mm_s']) ^ np.isfinite(group['control_mm_s'])
        rows.append({'observer': observer, 'study': study, 'participants_wanted': len(group),
                     'one_visit_only': int(one.sum()), 'neither_visit': int((~both & ~one).sum()),
                     **reproducibility(group.loc[both, 'active_mm_s'], group.loc[both, 'control_mm_s'])})
    return pd.DataFrame(rows)


def default_data_folder(settings_path: str = os.path.join(REPOSITORY, 'settings.csv')) -> Optional[str]:
    """The app's data folder from settings.csv (``Application_path``), if there is one."""
    try:
        with open(settings_path, newline='', encoding='utf-8') as handle:
            for row in csv.reader(handle):
                if len(row) >= 2 and row[0].strip() == 'Application_path' and row[1].strip():
                    return row[1].strip()
    except (OSError, UnicodeDecodeError):
        pass
    return None


def _fmt(value, digits: int = 3) -> str:
    return '–' if value is None or not np.isfinite(value) else f'{value:.{digits}f}'


def report(loop_table: pd.DataFrame, recordings: pd.DataFrame, pairs: pd.DataFrame, stats: pd.DataFrame) -> str:
    """The printed summary."""
    lines = []
    if not len(loop_table):
        return 'No whole-loop data sets found.'
    for observer, mine in loop_table.groupby('observer', sort=True):
        lines.append(f'Observer {observer or "(none)"}: {len(mine)} whole loops in {mine["recording"].nunique()} '
                     f'recordings, {int(mine["counted"].sum())} counted')
        for reason, count in mine.loc[~mine['counted'], 'why_not'].value_counts().items():
            lines.append(f'  not counted, {reason}: {count}')
        for row in mine[mine['duplicate_of'] != ''].itertuples(index=False):
            lines.append(f'  check: {row.recording} {row.dataset} lies on {row.duplicate_of}')
        values = recordings[recordings['observer'] == observer]
        lines.append(f'  recordings with a mean: {int(np.isfinite(values["mean_mm_s"]).sum())} of {len(values)}, '
                     f'from {_counts(values)} counted loops each')
    for row in stats.itertuples(index=False):
        lines.append('')
        lines.append(f'Aim 1, {row.study}, observer {row.observer or "(none)"}: {row.participants} of '
                     f'{row.participants_wanted} participants with a mean at both visits ({row.one_visit_only} at '
                     f'one only)')
        if row.participants:
            lines.append(f'  mean {_fmt(row.grand_mean_mm_s)} mm/s (active {_fmt(row.mean_active_mm_s)}, control '
                         f'{_fmt(row.mean_control_mm_s)}); typical error {_fmt(row.typical_error_mm_s)} mm/s, CV '
                         f'{_fmt(row.cv_percent, 0)}% (log scale {_fmt(row.cv_log_percent, 0)}%), smallest detectable '
                         f'change {_fmt(row.sdc_mm_s)} mm/s')
            lines.append(f'  Bland-Altman active - control: bias {_fmt(row.ba_bias)} mm/s (95% CI '
                         f'{_fmt(row.ba_bias_ci_low)} to {_fmt(row.ba_bias_ci_high)}), limits {_fmt(row.ba_loa_low)} '
                         f'to {_fmt(row.ba_loa_high)}; ICC(A,1) {_fmt(row.icc_a1, 2)} ({_fmt(row.icc_a1_ci_low, 2)} '
                         f'to {_fmt(row.icc_a1_ci_high, 2)})')
    return '\n'.join(lines)


def _counts(values: pd.DataFrame) -> str:
    counted = values.loc[np.isfinite(values['mean_mm_s']), 'loops_counted']
    if not len(counted):
        return 'no'
    return f'{int(counted.min())}-{int(counted.max())} (median {counted.median():g})'


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--data', default=None, help="the app's data folder (default: from settings.csv)")
    parser.add_argument('--observer', default=None, help='only this observer\'s data sets')
    parser.add_argument('--out', default=None, help='where to write the tables (default: Reports/aims/)')
    args = parser.parse_args(argv)
    folder = args.data or default_data_folder()
    if not folder:
        parser.error('no data folder: pass --data, or set one in the app (settings.csv)')
    table = collect(os.path.join(folder, 'Statistics'))
    if args.observer is not None:
        table = table[table['observer'] == args.observer]
    loop_table = loops(table)
    recordings = per_recording(loop_table)
    pairs = aim1_pairs(recordings, aim1_recordings())
    stats = aim1(pairs) if len(pairs) else pd.DataFrame()
    out = args.out or os.path.join(folder, 'Reports', 'aims')
    os.makedirs(out, exist_ok=True)
    loop_table.drop(columns='points').to_csv(os.path.join(out, 'loops.csv'), index=False)
    recordings.to_csv(os.path.join(out, 'recordings.csv'), index=False)
    pairs.to_csv(os.path.join(out, 'aim1_pairs.csv'), index=False)
    stats.to_csv(os.path.join(out, 'aim1.csv'), index=False)
    print(report(loop_table, recordings, pairs, stats))
    print(f'\nTables in {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
