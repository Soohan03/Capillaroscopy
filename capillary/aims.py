"""The aims from the saved centre-line data sets: each recording's resting velocity, and aim 1's statistics.

python3 -m capillary.aims [--data <data folder>] [--observer <code>] [--out <folder>] [--progress] [--unblind]

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

While the app is in blind placement the results stay hidden unless --unblind
is passed. ``--progress`` shows how far placement got instead, under the codes
the app lists the recordings by: each one's loop names and what to fix, with
no velocity or score.
"""

from __future__ import annotations

import argparse
import csv
import glob
import math
import os
import re
import sys
from typing import Optional, Sequence

import numpy as np
import pandas as pd
from scipy import stats

from . import agreement, blinding, datasets, inventory, pattern_shift
from .spacetime import Centreline

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: The app's settings: its data folder, the observer's code and whether blind placement is on.
SETTINGS = os.path.join(REPOSITORY, 'settings.csv')
#: The settings.csv row the app keeps blind placement in (`gui.blind.SETTING`).
BLIND_SETTING = 'blind_placement'
#: The data set names the app suggests for whole loops, in the order they are placed. By the protocol
#: (PROTOCOL.md) the observer places a recording's loops in the order of their ranking: loop1 is the
#: reference capillary, loop2 and loop3 its backups.
LOOP_NAME = re.compile(r'^loop(\d+)$')
RANKED_LOOPS = 3
#: What a recording's value can be (--value): the protocol's (the reference, else the first backup that
#: counts), the reference capillary's alone, or the mean of all counted loops; columns of `per_recording`.
VALUES = {'reference': 'value_mm_s', 'reference-only': 'reference_only_mm_s', 'mean': 'mean_mm_s'}
#: Aim 2's recordings of a participant, as columns of `aim2_recordings`.
AIM2_RECORDINGS = ('active_before_recording', 'active_after_recording', 'control_before_recording',
                   'control_after_recording')
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
           'last_frame', 'seconds', 'fps', 'mm_per_pixel', 'length_px', 'velocity_mm_s', 'snr', 'resolved',
           'ci95_low_mm_s', 'ci95_high_mm_s', 'arterial_end', 'loop_movement', 'points')


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
            'fps': fps, 'mm_per_pixel': _number(record.get('mm_per_pixel')), 'length_px': _number(line.get('length_px')),
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


def _judge(out: pd.DataFrame) -> pd.DataFrame:
    """`out` (whole loops) with ``why_not``, ``counted`` and ``speed_mm_s`` (`loops`)."""
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
    return out


def recount(loop_table: pd.DataFrame, statistics_dir: str, min_snr: float) -> pd.DataFrame:
    """`loop_table` (`loops`) judged at another signal-to-noise threshold: a sensitivity analysis (PROTOCOL.md).

    Each loop's pattern shift, and its limbs' for the movement check, is computed again from its saved
    space-time diagram (``___space_time.npy``: the frames the app measured, as it measured them) and judged
    at `min_snr`; at the app's 8 that gives the saved results. The other conditions stay. A loop whose
    diagram is missing is not counted.
    """
    out = loop_table.copy()
    missing = []
    for i in out.index:
        row = out.loc[i]
        path = datasets.line_dataset_files(statistics_dir, row['recording'], row['dataset'])['space_time']
        try:
            diagram = np.load(path, allow_pickle=False)
        except (OSError, ValueError):
            missing.append(i)
            out.loc[i, ['resolved', 'velocity_mm_s']] = [False, math.nan]
            continue
        whole = pattern_shift.pattern_shift(diagram)
        resolved = whole.is_resolved(min_snr)
        out.loc[i, ['resolved', 'snr', 'velocity_mm_s']] = [
            resolved, whole.snr, whole.speed_px_per_frame * row['fps'] * row['mm_per_pixel'] if resolved else math.nan]
        apex = Centreline.from_points(row['points']).apex_arc_px() if len(row['points']) >= 2 else None
        out.loc[i, 'loop_movement'] = apex is not None and pattern_shift.loop_limbs(
            diagram, apex, row['fps'], row['mm_per_pixel'], min_snr=min_snr)['loop_movement']
    out = _judge(out)
    out.loc[missing, 'why_not'] = 'no space-time diagram saved'
    return out


def loops(table: pd.DataFrame) -> pd.DataFrame:
    """The whole loops of `table` (`collect`), with whether each is counted, its speed, and possible duplicates.

    Adds ``counted``; ``speed_mm_s``, the velocity's size where counted (else NaN); ``why_not``, why a loop
    is not counted; and ``duplicate_of``, the other loops of the recording it lies on.
    """
    out = _judge(table[table['role'] == pattern_shift.WHOLE_LOOP].copy().reset_index(drop=True))
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
    """One row per observer and recording: loops placed within the rest and counted, and its values.

    - ``value_mm_s``, the protocol's value (PROTOCOL.md): the reference capillary (``loop1``) if it counts,
      else the first backup that counts in the order of the ranking (``loop2``, ``loop3``); ``value_from``
      names the loop used;
    - ``reference_only_mm_s``: the reference capillary's, without backups;
    - ``mean_mm_s``: the mean of all counted loops (the plan before 2026-10-29), with their SD and speeds.
    """
    rows = []
    rest = loop_table[loop_table['phase'] == REST]
    for (observer, recording), group in rest.groupby(['observer', 'recording'], sort=True):
        speeds = group.loc[group['counted'], 'speed_mm_s'].astype(float)
        ranked = group.assign(rank=group['dataset'].map(rank))
        ranked = ranked[ranked['rank'].between(1, RANKED_LOOPS)].sort_values('rank')
        used = ranked[ranked['counted']]
        reference = ranked[(ranked['rank'] == 1) & ranked['counted']]
        rows.append({'observer': observer, 'recording': recording, 'loops_placed': len(group),
                     'loops_counted': len(speeds),
                     'value_mm_s': float(used['speed_mm_s'].iloc[0]) if len(used) else math.nan,
                     'value_from': used['dataset'].iloc[0] if len(used) else '',
                     'reference_only_mm_s': float(reference['speed_mm_s'].iloc[0]) if len(reference) else math.nan,
                     'mean_mm_s': speeds.mean() if len(speeds) else math.nan,
                     'sd_mm_s': speeds.std(ddof=1) if len(speeds) > 1 else math.nan,
                     'speeds_mm_s': ', '.join(f'{v:.4f}' for v in sorted(speeds))})
    return pd.DataFrame(rows, columns=['observer', 'recording', 'loops_placed', 'loops_counted', 'value_mm_s',
                                       'value_from', 'reference_only_mm_s', 'mean_mm_s', 'sd_mm_s', 'speeds_mm_s'])


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


def _visit_values(recordings: pd.DataFrame, wanted: pd.DataFrame, columns: Sequence[str], value: str) -> pd.DataFrame:
    """Per observer and participant of `wanted`: for each of its recording `columns` (``<prefix>_recording``)
    the recording, its loops placed and counted, the loop its value comes from and the value (`value`)."""
    rows = []
    observers = sorted(recordings['observer'].unique()) if len(recordings) else []
    for observer in observers:
        mine = recordings[recordings['observer'] == observer].set_index('recording')
        for person in wanted.itertuples(index=False):
            row = {'observer': observer, 'study': person.study, 'subject': person.subject}
            for column in columns:
                prefix, name = column[:-len('_recording')], getattr(person, column)
                found = bool(name) and name in mine.index
                speed = float(mine.at[name, value]) if found else math.nan
                row.update({column: name,
                            f'{prefix}_loops_placed': int(mine.at[name, 'loops_placed']) if found else 0,
                            f'{prefix}_loops_counted': int(mine.at[name, 'loops_counted']) if found else 0,
                            f'{prefix}_from': _source(mine.loc[name], value) if found and np.isfinite(speed) else '',
                            f'{prefix}_mm_s': speed})
            rows.append(row)
    return pd.DataFrame(rows)


def _source(recording: pd.Series, value: str) -> str:
    """Where a recording's `value` comes from: the loop, or 'mean of N'."""
    if value == 'value_mm_s':
        return recording['value_from']
    if value == 'reference_only_mm_s':
        return 'loop1'
    return f'mean of {int(recording["loops_counted"])}'


def aim1_pairs(recordings: pd.DataFrame, wanted: pd.DataFrame, value: str = 'value_mm_s') -> pd.DataFrame:
    """Per observer and participant of `wanted` (`aim1_recordings`): each visit's value (column `value` of
    `per_recording`) and its loops."""
    return _visit_values(recordings, wanted, ('active_recording', 'control_recording'), value)


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


def _name(value) -> str:
    return inventory.nfc(value) if isinstance(value, str) and value else ''


def aim2_recordings(people: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Each participant's four recordings that aim 2 uses (`capillary.inventory`), before and after exposure
    on the active and the control visit."""
    if people is None:
        people = inventory.participants(inventory.recordings())
    rows = [{'study': person['study'], 'subject': person['subject'],
             **{f'{role}_{when}_recording': _name(person[f'{role}_{phase}'])
                for role in ('active', 'control') for when, phase in (('before', 'före'), ('after', 'efter'))}}
            for person in people.to_dict('records') if person.get('aim2', 'no') != 'no']
    return pd.DataFrame(rows, columns=['study', 'subject', *AIM2_RECORDINGS])


def aim2_values(recordings: pd.DataFrame, wanted: pd.DataFrame, value: str = 'value_mm_s') -> pd.DataFrame:
    """Per observer and participant of `wanted` (`aim2_recordings`): the value of each of its four recordings
    (column `value` of `per_recording`) and their loops."""
    return _visit_values(recordings, wanted, AIM2_RECORDINGS, value)


def _mean_ci(values) -> tuple:
    """The mean of `values` and its 95% confidence interval (t distribution); NaN interval below 2 values."""
    values = np.asarray(values, dtype=float)
    if not values.size:
        return math.nan, math.nan, math.nan
    mean = float(values.mean())
    if values.size < 2:
        return mean, math.nan, math.nan
    half = float(stats.t.ppf(0.975, values.size - 1) * values.std(ddof=1) / math.sqrt(values.size))
    return mean, mean - half, mean + half


def response(active_before, active_after, control_before, control_after) -> dict:
    """Aim 2's statistics: the change after minus before on each visit and their difference, active minus
    control (participants with all four values).

    The difference: its mean with a 95% confidence interval, a paired t-test (one-sample on the differences)
    and the Wilcoxon signed-rank test. On the log scale: each visit's ratio after / before (geometric mean)
    and the ratio of the two, with its interval and t-test.
    """
    ab, aa, cb, ca = (np.asarray(v, dtype=float) for v in (active_before, active_after, control_before,
                                                             control_after))
    keep = np.isfinite(ab) & np.isfinite(aa) & np.isfinite(cb) & np.isfinite(ca)
    ab, aa, cb, ca = ab[keep], aa[keep], cb[keep], ca[keep]
    n = int(ab.size)
    change_active, change_control = aa - ab, ca - cb
    difference = change_active - change_control
    out = {'participants': n}
    for label, values in (('change_active', change_active), ('change_control', change_control),
                          ('difference', difference)):
        mean, low, high = _mean_ci(values)
        out.update({f'{label}_mm_s': mean, f'{label}_ci_low_mm_s': low, f'{label}_ci_high_mm_s': high})
    out['difference_sd_mm_s'] = float(difference.std(ddof=1)) if n >= 2 else math.nan
    out['t_test_p'] = float(stats.ttest_1samp(difference, 0.0).pvalue) if n >= 2 else math.nan
    out['wilcoxon_p'] = float(stats.wilcoxon(difference).pvalue) if np.any(difference != 0) else math.nan
    positive = n >= 2 and bool(np.all(ab > 0) and np.all(aa > 0) and np.all(cb > 0) and np.all(ca > 0))
    log_active = np.log(aa / ab) if positive else np.array([])
    log_control = np.log(ca / cb) if positive else np.array([])
    out['ratio_active'] = math.exp(log_active.mean()) if positive else math.nan
    out['ratio_control'] = math.exp(log_control.mean()) if positive else math.nan
    mean, low, high = _mean_ci(log_active - log_control) if positive else (math.nan,) * 3
    out.update(ratio_of_ratios=math.exp(mean) if positive else math.nan,
               ratio_of_ratios_ci_low=math.exp(low) if positive else math.nan,
               ratio_of_ratios_ci_high=math.exp(high) if positive else math.nan,
               log_t_test_p=float(stats.ttest_1samp(log_active - log_control, 0.0).pvalue) if positive else math.nan)
    return out


def aim2(values: pd.DataFrame) -> pd.DataFrame:
    """`response` per observer and study, with how many participants miss a value."""
    rows = []
    columns = [f'{column[:-len("_recording")]}_mm_s' for column in AIM2_RECORDINGS]
    for (observer, study), group in values.groupby(['observer', 'study'], sort=True):
        complete = np.isfinite(group[columns].to_numpy(dtype=float)).all(axis=1)
        rows.append({'observer': observer, 'study': study, 'participants_wanted': len(group),
                     'incomplete': int((~complete).sum()), **response(*(group[column] for column in columns))})
    return pd.DataFrame(rows)


def rank(dataset: str) -> float:
    """The place of a loop in the observer's ranking, from its name: 1 for ``loop1`` (the reference); NaN for
    a name the protocol does not rank."""
    match = LOOP_NAME.match(dataset or '')
    return float(match.group(1)) if match else math.nan


def _in_ranking_order(dataset: str) -> tuple:
    """Sort key: loop1, loop2, ... first, then any other name."""
    place = rank(dataset)
    return (place if np.isfinite(place) else math.inf, dataset)


def aims_studies() -> dict:
    """``{name: study}`` of the recordings the aims use (`capillary.inventory`), names NFC."""
    table = inventory.recordings()
    table = inventory.mark_use(table, inventory.participants(table))
    used = table[table['used_for'].fillna('') != '']
    return {inventory.nfc(name): study for name, study in zip(used['name'], used['study'])}


def progress(table: pd.DataFrame, studies: dict) -> str:
    """How far blind placement got, without a single result: the report of ``--progress``.

    Per recording the aims use (`studies`, ``{name: study}``), under its code as the app lists it: the names
    of its data sets and what the protocol asks to fix (no loop1, a gap or more than `RANKED_LOOPS` in the
    ranking, a line that is not a whole loop or not over the official rest, one capillary drawn twice). No
    velocity, score or count of loops that count is shown, so the observer can read it while placing.
    """
    codes = blinding.codes(studies)
    mine = table[table['recording'].isin(studies)]
    lines, waiting, placed = [], [], {}
    problems = 0
    for name in sorted(studies, key=codes.get):
        group = mine[mine['recording'] == name]
        if not len(group):
            waiting.append(codes[name])
            continue
        loops_ = group[group['role'] == pattern_shift.WHOLE_LOOP]
        ranked = [(name_, rank(name_)) for name_ in loops_['dataset']]
        found = sorted(r for _, r in ranked if np.isfinite(r))
        issues = []
        other = group.loc[group['role'] != pattern_shift.WHOLE_LOOP, 'dataset']
        if len(other):
            issues.append(f'not a whole loop: {", ".join(sorted(other))}')
        unranked = sorted(name_ for name_, r in ranked if not np.isfinite(r))
        if unranked:
            issues.append(f'not named loop1-loop{RANKED_LOOPS}: {", ".join(unranked)}')
        if len(loops_) and 1 not in found:
            issues.append('no loop1 (the reference)')
        gaps = [f'loop{r}' for r in range(2, int(max(found, default=1))) if r not in found]
        if gaps:
            issues.append(f'{", ".join(gaps)} missing')
        beyond = [f'loop{int(r)}' for r in found if r > RANKED_LOOPS]
        if beyond:
            issues.append(f'more than {RANKED_LOOPS} loops: {", ".join(beyond)}')
        for mask, text in ((loops_['phase'] != REST, 'not over the official rest'),
                           (loops_['video_folder'] != STABILIZED_FOLDER, 'not on the stabilized video')):
            if mask.any():
                issues.append(f'{text}: {", ".join(sorted(loops_.loc[mask, "dataset"]))}')
        points = list(zip(loops_['dataset'], loops_['points']))
        for i, (first, first_points) in enumerate(points):
            for second, second_points in points[i + 1:]:
                if _overlap(first_points, second_points) >= DUPLICATE_SHARE:
                    issues.append(f'{first} and {second} lie on the same capillary')
        problems += bool(issues)
        placed[name] = len(loops_)
        names = ' '.join(sorted(group['dataset'], key=_in_ranking_order))
        lines.append(f'  {codes[name]}  {names}' + (f'   <- {"; ".join(issues)}' if issues else ''))
    out = []
    for study in sorted(set(studies.values())):
        names = [n for n in studies if studies[n] == study]
        out.append(f'{study}: {sum(n in placed for n in names)} of {len(names)} recordings have lines')
    counts = pd.Series(list(placed.values()), dtype=int)
    if len(counts):
        tally = ', '.join(f'{int((counts == n).sum())} with {n}' for n in sorted(counts.unique()))
        out.append(f'Whole loops per recording: {tally}; recordings with something to fix: {problems}')
    out += lines
    if waiting:
        out.append(f'No lines yet ({len(waiting)}): {" ".join(waiting)}')
    elsewhere = table.loc[~table['recording'].isin(studies), 'recording'].nunique()
    if elsewhere:
        out.append(f'(Also data sets on {elsewhere} recording{"s" if elsewhere > 1 else ""} the aims do not use.)')
    return '\n'.join(out)


def _setting(key: str, settings_path: Optional[str] = None) -> Optional[str]:
    """A row of the app's settings.csv (`SETTINGS`), if it has one."""
    try:
        with open(settings_path or SETTINGS, newline='', encoding='utf-8') as handle:
            for row in csv.reader(handle):
                if len(row) >= 2 and row[0].strip() == key and row[1].strip():
                    return row[1].strip()
    except (OSError, UnicodeDecodeError):
        pass
    return None


def default_data_folder(settings_path: Optional[str] = None) -> Optional[str]:
    """The app's data folder from settings.csv (``Application_path``), if there is one."""
    return _setting('Application_path', settings_path)


def default_observer(settings_path: Optional[str] = None) -> Optional[str]:
    """The observer code the app last saved a data set with (settings.csv ``observer``), upper case."""
    observer = _setting('observer', settings_path)
    return observer.upper() if observer else None


def blind_placement_on(settings_path: Optional[str] = None) -> bool:
    """Whether the app is in blind placement (`gui.blind`)."""
    return _setting(BLIND_SETTING, settings_path) == '1'


def _fmt(value, digits: int = 3) -> str:
    return '–' if value is None or not np.isfinite(value) else f'{value:.{digits}f}'


VALUE_TEXT = {'value_mm_s': 'the reference capillary, or its first backup that counts (PROTOCOL.md)',
              'reference_only_mm_s': 'the reference capillary only (loop1)',
              'mean_mm_s': 'the mean of all counted loops'}


def report(loop_table: pd.DataFrame, recordings: pd.DataFrame, pairs: pd.DataFrame, stats: pd.DataFrame,
           value: str = 'value_mm_s', aim2_stats: Optional[pd.DataFrame] = None) -> str:
    """The printed summary, with each recording's `value` (a column of `per_recording`)."""
    lines = []
    if not len(loop_table):
        return 'No whole-loop data sets found.'
    lines.append(f"Each recording's value: {VALUE_TEXT[value]}")
    for observer, mine in loop_table.groupby('observer', sort=True):
        lines.append(f'Observer {observer or "(none)"}: {len(mine)} whole loops in {mine["recording"].nunique()} '
                     f'recordings, {int(mine["counted"].sum())} counted')
        for reason, count in mine.loc[~mine['counted'], 'why_not'].value_counts().items():
            lines.append(f'  not counted, {reason}: {count}')
        for row in mine[mine['duplicate_of'] != ''].itertuples(index=False):
            lines.append(f'  check: {row.recording} {row.dataset} lies on {row.duplicate_of}')
        values = recordings[recordings['observer'] == observer]
        has = np.isfinite(values[value].astype(float))
        sources = values.loc[has, 'value_from'].value_counts().sort_index() if value == 'value_mm_s' else None
        lines.append(f'  recordings with a value: {int(has.sum())} of {len(values)}' +
                     (f' (from {", ".join(f"{name} in {count}" for name, count in sources.items())})'
                      if sources is not None and len(sources) else ''))
        lines.append(f'  recordings with a mean of counted loops: {int(np.isfinite(values["mean_mm_s"]).sum())}, '
                     f'from {_counts(values)} loops each')
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
    for row in (aim2_stats if aim2_stats is not None else pd.DataFrame()).itertuples(index=False):
        lines.append('')
        lines.append(f'Aim 2, {row.study}, observer {row.observer or "(none)"}: {row.participants} of '
                     f'{row.participants_wanted} participants with a value in all four recordings')
        if row.participants:
            lines.append(f'  change after - before: active {_fmt(row.change_active_mm_s)} mm/s '
                         f'({_fmt(row.change_active_ci_low_mm_s)} to {_fmt(row.change_active_ci_high_mm_s)}), '
                         f'control {_fmt(row.change_control_mm_s)} mm/s ({_fmt(row.change_control_ci_low_mm_s)} '
                         f'to {_fmt(row.change_control_ci_high_mm_s)})')
            lines.append(f'  difference active - control: {_fmt(row.difference_mm_s)} mm/s (95% CI '
                         f'{_fmt(row.difference_ci_low_mm_s)} to {_fmt(row.difference_ci_high_mm_s)}); paired '
                         f't-test p {_fmt(row.t_test_p)}, Wilcoxon p {_fmt(row.wilcoxon_p)}')
            lines.append(f'  as ratios after / before: active {_fmt(row.ratio_active, 2)}, control '
                         f'{_fmt(row.ratio_control, 2)}; active / control {_fmt(row.ratio_of_ratios, 2)} (95% CI '
                         f'{_fmt(row.ratio_of_ratios_ci_low, 2)} to {_fmt(row.ratio_of_ratios_ci_high, 2)}), '
                         f'p {_fmt(row.log_t_test_p)}')
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
    parser.add_argument('--progress', action='store_true',
                        help="how far blind placement got, by code, without results (default observer: the app's)")
    parser.add_argument('--unblind', action='store_true',
                        help='show the results although blind placement is on in the app')
    parser.add_argument('--value', choices=list(VALUES), default='reference',
                        help="each recording's value: the protocol's (default), the reference capillary's alone, "
                             'or the mean of all counted loops')
    parser.add_argument('--min-snr', type=float, default=None,
                        help="count loops at another signal-to-noise threshold than the app's 8, recomputed from "
                             'the saved space-time diagrams (a sensitivity analysis)')
    args = parser.parse_args(argv)
    folder = args.data or default_data_folder()
    if not folder:
        parser.error('no data folder: pass --data, or set one in the app (settings.csv)')
    table = collect(os.path.join(folder, 'Statistics'))
    if args.progress:
        observer = (args.observer or default_observer() or '').upper()
        print(f'Observer {observer or "(any)"}:')
        print(progress(table[table['observer'] == observer] if observer else table, aims_studies()))
        return 0
    if blind_placement_on() and not args.unblind:
        print('Blind placement is on in the app, so the results stay hidden until every recording has its lines.\n'
              'Use --progress to see how far it got, or --unblind to show the results.', file=sys.stderr)
        return 2
    if args.observer is not None:
        table = table[table['observer'] == args.observer.upper()]
    value = VALUES[args.value]
    loop_table = loops(table)
    if args.min_snr is not None:
        loop_table = recount(loop_table, os.path.join(folder, 'Statistics'), args.min_snr)
        print(f'Loops counted at signal-to-noise {args.min_snr:g}, recomputed from the saved space-time diagrams')
    recordings = per_recording(loop_table)
    pairs = aim1_pairs(recordings, aim1_recordings(), value)
    aim1_stats = aim1(pairs) if len(pairs) else pd.DataFrame()
    aim2_table = aim2_values(recordings, aim2_recordings(), value)
    aim2_stats = aim2(aim2_table) if len(aim2_table) else pd.DataFrame()
    out = args.out or os.path.join(folder, 'Reports', 'aims')
    os.makedirs(out, exist_ok=True)
    loop_table.drop(columns='points').to_csv(os.path.join(out, 'loops.csv'), index=False)
    recordings.to_csv(os.path.join(out, 'recordings.csv'), index=False)
    pairs.to_csv(os.path.join(out, 'aim1_pairs.csv'), index=False)
    aim1_stats.to_csv(os.path.join(out, 'aim1.csv'), index=False)
    aim2_table.to_csv(os.path.join(out, 'aim2_values.csv'), index=False)
    aim2_stats.to_csv(os.path.join(out, 'aim2.csv'), index=False)
    print(report(loop_table, recordings, pairs, aim1_stats, value, aim2_stats))
    print(f'\nTables in {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
