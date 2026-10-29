"""Aim 1, the primary endpoint, with the quality of the lines and what the signal-to-noise threshold removes.

python3 analysis/primary_endpoint/report.py [--data <data folder>] [--observer SJ] [--out <folder>]

Reads the whole loops placed blind (PROTOCOL.md) through `capillary.aims`, the
protocol's analysis, and adds what a report on them needs:

- the quality of each line: its shape (length, points, spacing, whether it
  crosses itself), how far it kept from the stabilizer's black strip, the
  stabilization of its recording over the rest, and its measurement
  (signal-to-noise, the jackknife interval, the two halves of the rest, the two
  limbs), and whether the observer's ranking found the measurable loops;
- what the signal-to-noise threshold removes: each loop's pattern shift and its
  limbs' are computed once from the saved space-time diagrams (cached in
  estimates.csv) and judged at thresholds from 4 to 14 as
  `capillary.aims.recount` judges them at one. At the app's 8 this must give
  the saved results exactly, or the script stops;
- aim 1 per study as the protocol fixes it, with the sensitivity analyses it
  lists (the reference only, the mean of the counted loops, thresholds 7 and 9),
  95% intervals for the typical error and CV (chi-square), the limits of
  agreement (`capillary.agreement.bland_altman`) and the ratio limits;
- exploratory, not in the protocol: the first visit against the second.

Writes into Reports/primary_endpoint/ (or --out) loops.csv, recordings.csv,
pairs.csv, aim1.csv, threshold_sweep.csv and estimates.csv, which name the
recordings, and dashboard/*.json, the report's data, which name only the study,
participant and visit (no recording names, dates or blind codes, so that a later
blind placement of the same recordings stays blind). The report's page
(dashboard/index.html here) reads those files; README.md says how to publish them.
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

REPOSITORY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPOSITORY)

from capillary import agreement, aims, datasets, inventory, pattern_shift, stabilize  # noqa: E402
from capillary.spacetime import Centreline  # noqa: E402
from capillary.video import probe_video  # noqa: E402

#: The protocol's threshold and its sensitivity analyses; the sweep around them.
PRIMARY_SNR = pattern_shift.MIN_SNR
SENSITIVITY_SNR = (7.0, 9.0)
THRESHOLDS = tuple(float(t) for t in np.round(np.arange(4.0, 14.01, 0.5), 1))
#: Loops this close to the threshold are listed: they would change sides at 7 or 9 and nearby.
NEAR = (6.0, 10.0)
#: The analyses of PROTOCOL.md: the value of each recording, and the threshold.
ANALYSES = {
    'primary': ('value_mm_s', PRIMARY_SNR, 'Reference, else first backup that counts (protocol)', 'Protocol'),
    'reference_only': ('reference_only_mm_s', PRIMARY_SNR, 'Reference capillary only', 'Reference only'),
    'mean': ('mean_mm_s', PRIMARY_SNR, 'Mean of all counted loops', 'Mean of loops'),
    'snr7': ('value_mm_s', SENSITIVITY_SNR[0], 'Signal-to-noise threshold 7', 'Threshold 7'),
    'snr9': ('value_mm_s', SENSITIVITY_SNR[1], 'Signal-to-noise threshold 9', 'Threshold 9'),
}
STUDIES = ('ESMOKE', 'ISMOKE')
ESTIMATE_COLUMNS = ['recording', 'dataset', 'diagram_bytes', 'diagram_mtime', 'apex_px', 'speed_px_per_frame', 'snr',
                    'in_range', 'ci95_low_px', 'ci95_high_px', 'blocks', 'start_speed_px_per_frame', 'start_snr',
                    'start_in_range', 'end_speed_px_per_frame', 'end_snr', 'end_in_range']


# ------------------------------------------------------------------------------------------- the loops

def _number(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def shape(points) -> dict:
    """A line's clicked points: how many, their spacing, and how far apart its two ends lie."""
    p = np.asarray(points, dtype=float).reshape(-1, 2)
    steps = np.hypot(*np.diff(p, axis=0).T) if len(p) > 1 else np.array([math.nan])
    return {'points_n': len(p), 'spacing_median_px': float(np.median(steps)), 'spacing_max_px': float(np.max(steps)),
            'ends_apart_px': float(np.hypot(*(p[0] - p[-1]))) if len(p) > 1 else math.nan,
            'crosses_itself': aims._crosses_itself(points)}


def provenance_extras(statistics_dir: str, loop_table: pd.DataFrame) -> pd.DataFrame:
    """What `capillary.aims.collect` leaves out of each loop's provenance: the picture check, the halves, the limbs."""
    rows = []
    for row in loop_table.itertuples(index=False):
        record = datasets.read_provenance(
            datasets.line_dataset_files(statistics_dir, row.recording, row.dataset)['provenance']) or {}
        summary, picture = record.get('summary') or {}, record.get('picture') or {}
        rows.append({'recording': row.recording, 'dataset': row.dataset, **shape(row.points),
                     'clearance_px': _number(picture.get('clearance_px')),
                     'relabelled': bool(record.get('relabelled')),
                     **{key: _number(summary.get(f'pattern_shift_{key}'))
                        for key in ('first_half_mm_s', 'first_half_snr', 'second_half_mm_s', 'second_half_snr',
                                    'start_limb_mm_s', 'start_limb_snr', 'end_limb_mm_s', 'end_limb_snr')}})
    return pd.DataFrame(rows)


def _estimate(diagram) -> tuple:
    found = pattern_shift.pattern_shift(diagram)
    return found.speed_px_per_frame, found.snr, bool(found.in_range), found.ci95, found.blocks


def estimates(statistics_dir: str, loop_table: pd.DataFrame, cache_path: str) -> pd.DataFrame:
    """Each loop's pattern shift and each limb's, as `pattern_shift.summarize` and `loop_limbs` compute them, kept
    in `cache_path` and computed again only for a diagram that changed."""
    cached = pd.read_csv(cache_path) if os.path.exists(cache_path) else pd.DataFrame(columns=ESTIMATE_COLUMNS)
    cached = {(r.recording, r.dataset): r for r in cached.itertuples(index=False)}
    rows = []
    for row in loop_table.itertuples(index=False):
        path = datasets.line_dataset_files(statistics_dir, row.recording, row.dataset)['space_time']
        status = os.stat(path)
        old = cached.get((row.recording, row.dataset))
        if old is not None and old.diagram_bytes == status.st_size and old.diagram_mtime == status.st_mtime:
            rows.append(old._asdict())
            continue
        diagram = np.asarray(np.load(path, allow_pickle=False), dtype=float)
        speed, snr, in_range, ci95, blocks = _estimate(diagram)
        apex = Centreline.from_points(row.points).apex_arc_px()
        split = int(round(apex))
        limbs = [_estimate(diagram[:, :split + 1]), _estimate(diagram[:, split:])]
        rows.append({'recording': row.recording, 'dataset': row.dataset, 'diagram_bytes': status.st_size,
                     'diagram_mtime': status.st_mtime, 'apex_px': apex, 'speed_px_per_frame': speed, 'snr': snr,
                     'in_range': in_range, 'ci95_low_px': ci95[0], 'ci95_high_px': ci95[1], 'blocks': blocks,
                     **{f'{side}_{key}': value for side, limb in zip(('start', 'end'), limbs)
                        for key, value in zip(('speed_px_per_frame', 'snr', 'in_range'), limb[:3])}})
    out = pd.DataFrame(rows, columns=ESTIMATE_COLUMNS)
    out.to_csv(cache_path, index=False)
    return out


def judged(loop_table: pd.DataFrame, found: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """`loop_table` judged at signal-to-noise `threshold` from the cached estimates, as `aims.recount` judges it."""
    e = found.set_index(['recording', 'dataset']).loc[list(zip(loop_table['recording'], loop_table['dataset']))]
    out = loop_table.copy()
    resolved = (e['in_range'].astype(bool) & (e['snr'] >= threshold)).to_numpy()
    out['resolved'] = resolved
    out['snr'] = e['snr'].to_numpy()
    out['velocity_mm_s'] = np.where(resolved, e['speed_px_per_frame'].to_numpy() * out['fps'] * out['mm_per_pixel'],
                                    math.nan)
    start = (e['start_in_range'].astype(bool) & (e['start_snr'] >= threshold)).to_numpy()
    end = (e['end_in_range'].astype(bool) & (e['end_snr'] >= threshold)).to_numpy()
    opposite = np.sign(e['start_speed_px_per_frame'].to_numpy()) != np.sign(e['end_speed_px_per_frame'].to_numpy())
    out['loop_movement'] = start & end & opposite
    return aims._judge(out)


def check_against_saved(loop_table: pd.DataFrame, found: pd.DataFrame) -> None:
    """Stop unless the cached estimates judge every loop at the app's threshold as its saved data set does."""
    again = judged(loop_table, found, PRIMARY_SNR)
    differ = (again['counted'] != loop_table['counted']) | ~np.isclose(
        again['speed_mm_s'].fillna(-1.0), loop_table['speed_mm_s'].fillna(-1.0), rtol=1e-9, atol=0)
    differ |= ~np.isclose(again['snr'], loop_table['snr'], rtol=1e-9, equal_nan=True)
    if differ.any():
        raise SystemExit(f'{int(differ.sum())} loops judged differently from their saved data sets; nothing written')


def failure(row) -> str:
    """Why a loop does not count, the first reason in the order of the protocol's checks."""
    if row.counted:
        return 'counted'
    if row.crosses_itself:
        return 'crosses itself'
    if not row.snr >= PRIMARY_SNR:
        return 'signal-to-noise below 8'
    if not row.in_range:
        return 'speed at the edge of the searched range'
    if row.loop_movement:
        return 'limbs moved opposite ways'
    return row.why_not


# ----------------------------------------------------------------------------------------- recordings

def recording_info() -> tuple:
    """The 90 recordings the aims use (study, participant, visit, before or after) and the participants."""
    table = inventory.recordings()
    people = inventory.participants(table)
    table = inventory.mark_use(table, people)
    used = table[table['used_for'].fillna('') != ''].copy()
    used['recording'] = used['name'].map(inventory.nfc)
    used['when'] = used['phase'].map({'före': 'before', 'efter': 'after'})
    used = used.rename(columns={'role': 'visit'})          # active or control ('role' is a line's role)
    return used[['recording', 'study', 'subject', 'visit', 'when', 'date', 'used_for']].reset_index(drop=True), people


def stabilization(folder: str, names) -> pd.DataFrame:
    """Each recording's stabilization over its official rest: the match, the frames placed by the references, and
    the share of the frame that every rest frame shows (where a line may lie)."""
    rows = []
    for name in names:
        video = os.path.join(folder, aims.STABILIZED_FOLDER, f'{name}.avi')
        shifts = stabilize.read_shifts(video)
        size = probe_video(video) if shifts is not None else None
        window = stabilize.rest_window(video, size.fps, size.frame_count) if size is not None else None
        if window is None:
            rows.append({'recording': name})
            continue
        part = shifts.loc[window[0]:window[1]]
        area = stabilize.picture_area(shifts, (size.height, size.width), *window)
        share = (max(0.0, area[2] - area[0]) * max(0.0, area[3] - area[1]) / (size.width * size.height)
                 if area else math.nan)
        rows.append({'recording': name, 'rest_match_median': float(part['match'].median()),
                     'rest_by_references': float((part['placed_by'] == 'references').mean()),
                     'rest_picture_share': share})
    return pd.DataFrame(rows, columns=['recording', 'rest_match_median', 'rest_by_references', 'rest_picture_share'])


# ------------------------------------------------------------------------------------------------ aim 1

def _te_interval(differences) -> tuple:
    """The typical error (SD of the differences / sqrt 2) and its 95% interval (chi-square, n - 1 df)."""
    d = np.asarray(differences, dtype=float)
    if d.size < 2:
        return math.nan, math.nan, math.nan
    df = d.size - 1
    te = float(np.std(d, ddof=1) / math.sqrt(2))
    return te, te * math.sqrt(df / stats.chi2.ppf(0.975, df)), te * math.sqrt(df / stats.chi2.ppf(0.025, df))


def reproducibility(active, control) -> dict:
    """`capillary.aims.reproducibility` with the intervals a report needs (see the module docstring)."""
    a, c = np.asarray(active, dtype=float), np.asarray(control, dtype=float)
    keep = np.isfinite(a) & np.isfinite(c)
    a, c = a[keep], c[keep]
    out = aims.reproducibility(a, c)
    n = out['participants']
    te, te_low, te_high = _te_interval(a - c)
    mean = out['grand_mean_mm_s']
    out.update(te_ci_low_mm_s=te_low, te_ci_high_mm_s=te_high,
               cv_ci_low=100 * te_low / mean if n else math.nan, cv_ci_high=100 * te_high / mean if n else math.nan,
               sdc_percent=aims.SDC_FACTOR * out['cv_percent'])
    positive = n >= 2 and bool(np.all(a > 0) and np.all(c > 0))
    log_te, log_low, log_high = _te_interval(np.log(a) - np.log(c)) if positive else (math.nan,) * 3
    out.update(cv_log_ci_low=100 * (math.exp(log_low) - 1) if positive else math.nan,
               cv_log_ci_high=100 * (math.exp(log_high) - 1) if positive else math.nan)
    limits = agreement.bland_altman(a, c)
    out.update({f'ba_{key}': limits[key] for key in limits if key != 'n'})
    ratio = agreement.bland_altman_ratio(a, c)
    out.update({f'ratio_{key}': ratio[key] for key in ratio if key != 'n'})
    out['sd_between_mm_s'] = float(np.std((a + c) / 2, ddof=1)) if n >= 2 else math.nan
    out['paired_t_p'] = float(stats.ttest_rel(a, c).pvalue) if n >= 2 else math.nan
    return out


def aim1_table(pairs: pd.DataFrame) -> dict:
    """`reproducibility` per study, with how many participants had a value at one visit only, or at neither."""
    out = {}
    for study in STUDIES:
        group = pairs[pairs['study'] == study]
        both = np.isfinite(group['active_mm_s']) & np.isfinite(group['control_mm_s'])
        one = np.isfinite(group['active_mm_s']) ^ np.isfinite(group['control_mm_s'])
        out[study] = {'participants_wanted': len(group), 'one_visit_only': int(one.sum()),
                      'neither_visit': int((~both & ~one).sum()),
                      **reproducibility(group.loc[both, 'active_mm_s'], group.loc[both, 'control_mm_s'])}
    return out


#: Each aim's recordings per participant (`capillary.aims`), read once.
WANTED = {}


def analysis(loop_table: pd.DataFrame, found: pd.DataFrame, threshold: float, value: str) -> tuple:
    """The loops judged at `threshold`, each recording's values, aim 1's pairs (`value`) and statistics, and aim 2's
    values (only to count who has all four)."""
    if not WANTED:
        WANTED.update(aim1=aims.aim1_recordings(), aim2=aims.aim2_recordings())
    loops_ = judged(loop_table, found, threshold)
    recordings = aims.per_recording(loops_)
    pairs = aims.aim1_pairs(recordings, WANTED['aim1'], value)
    complete = aims.aim2_values(recordings, WANTED['aim2'], value)
    return loops_, recordings, pairs, aim1_table(pairs), complete


def aim2_complete(values: pd.DataFrame) -> dict:
    """How many participants of aim 2 have a value in all four recordings, per study (no results)."""
    columns = [f'{column[:-len("_recording")]}_mm_s' for column in aims.AIM2_RECORDINGS]
    out = {}
    for study in STUDIES:
        group = values[values['study'] == study]
        out[study] = {'wanted': len(group),
                      'complete': int(np.isfinite(group[columns].to_numpy(dtype=float)).all(axis=1).sum())}
    return out


def sweep(loop_table: pd.DataFrame, found: pd.DataFrame) -> pd.DataFrame:
    """What every threshold of `THRESHOLDS` keeps: loops, recordings, participants, and aim 1's CV and ICC."""
    rows = []
    for threshold in THRESHOLDS:
        loops_, recordings, pairs, stats_, complete = analysis(loop_table, found, threshold, 'value_mm_s')
        row = {'threshold': threshold, 'loops_counted': int(loops_['counted'].sum()),
               'recordings_with_value': int(np.isfinite(recordings['value_mm_s']).sum()),
               'references_counted': int(np.isfinite(recordings['reference_only_mm_s']).sum())}
        complete = aim2_complete(complete)
        for study in STUDIES:
            row.update({f'{study}_participants': stats_[study]['participants'],
                        f'{study}_cv_percent': stats_[study]['cv_percent'],
                        f'{study}_cv_log_percent': stats_[study]['cv_log_percent'],
                        f'{study}_icc_a1': stats_[study]['icc_a1'],
                        f'{study}_aim2_complete': complete[study]['complete']})
        rows.append(row)
    return pd.DataFrame(rows)


def visit_order(pairs: pd.DataFrame, people: pd.DataFrame) -> dict:
    """Exploratory: the second visit against the first (by date), per study and together."""
    order = people.set_index(['study', 'subject'])[['first_visit', 'days_apart']]
    both = pairs[np.isfinite(pairs['active_mm_s']) & np.isfinite(pairs['control_mm_s'])].copy()
    first = [order.at[(s, p), 'first_visit'] if (s, p) in order.index else '' for s, p in
             zip(both['study'], both['subject'])]
    both['first_visit'] = first
    both = both[both['first_visit'].isin(['active', 'control'])]
    second = np.where(both['first_visit'] == 'active', both['control_mm_s'], both['active_mm_s'])
    earlier = np.where(both['first_visit'] == 'active', both['active_mm_s'], both['control_mm_s'])
    out = {}
    for label, mask in [(study, (both['study'] == study).to_numpy()) for study in STUDIES] + [
            ('both studies', np.ones(len(both), dtype=bool))]:
        d = second[mask] - earlier[mask]
        n = int(d.size)
        mean = float(d.mean()) if n else math.nan
        half = float(stats.t.ppf(0.975, n - 1) * d.std(ddof=1) / math.sqrt(n)) if n >= 2 else math.nan
        out[label] = {'participants': n, 'second_minus_first_mm_s': mean, 'ci_low': mean - half, 'ci_high': mean + half,
                      'p': float(stats.ttest_1samp(d, 0.0).pvalue) if n >= 2 else math.nan,
                      'active_first': int((both.loc[mask, 'first_visit'] == 'active').sum())}
    return out


# --------------------------------------------------------------------------------------------- output

def _clean(value):
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return None if not np.isfinite(value) else round(float(value), 6)
    return value


def records(frame: pd.DataFrame, columns) -> list:
    return [_clean(dict(zip(columns, values))) for values in frame[list(columns)].itertuples(index=False, name=None)]


def _median(values) -> float:
    values = pd.Series(values, dtype=float).dropna()
    return float(values.median()) if len(values) else math.nan


def _keys(frame: pd.DataFrame, columns) -> list:
    return [' '.join(str(part) for part in parts) for parts in zip(*(frame[column] for column in columns))]


OUTCOMES = ('counted', 'signal-to-noise below 8', 'speed at the edge of the searched range', 'limbs moved opposite ways',
            'crosses itself')
AIMS_TEXT = {'aims 1, 2': '1 and 2', 'aim 1': '1', 'aim 2': '2'}


def method_rows() -> list:
    """The protocol's settings, as the report's Methods page lists them."""
    low, high = SENSITIVITY_SNR
    rows = [
        ('line', 'Line', 'Whole loop: from the base of one limb, over the apex, to the base of the other',
         'Placed blind, up to three loops per recording in the order of the ranking (loop1 the reference)'),
        ('frames', 'Frames measured', f'The official rest, from {inventory.REST_MARGIN_S:g} s after the video starts '
                                      f'to {inventory.REST_MARGIN_S:g} s before the cuff goes on',
         'Official occlusion times exported from DynCap'),
        ('velocity', 'Velocity', f'Pattern shift pooled over the rest: shifts over 1-{pattern_shift.MAX_LAG} frames, '
                                 f'speeds from {pattern_shift.MIN_SPEED:g} px/frame',
         'Rows band-passed along the line (difference of Gaussians, sigma '
         f'{pattern_shift.BANDPASS_PX[0]:g} and {pattern_shift.BANDPASS_PX[1]:g} px); its size is used, its sign '
         'only shows the arterial end'),
        ('scale', 'Scale', '30 frames/s; 1.329 µm per pixel (0.4 mm over 301 px)',
         'Frame rate checked consistent with the official times on all 60 aims recordings of the first check'),
        ('qc', 'Quality control', f'Signal-to-noise {PRIMARY_SNR:g} or more with the speed inside the searched '
                                  'range; limbs not moving opposite ways; within the rest; on a stabilized video',
         f'Sensitivity analyses at {low:g} and {high:g}'),
        ('picture', 'Picture check', f'Every sample of the line {stabilize.EDGE_MARGIN_PX:g} px or more from the black '
                                     'strip stabilizing leaves, in every frame of the rest',
         'Lines that fail are refused when measured'),
        ('value', "A recording's value", 'The reference capillary (loop1) if it counts, else the first backup that '
                                         'counts; else missing',
         'Secondary: the mean of all counted loops'),
        ('te', 'Typical error', 'SD of the differences between the visits / √2',
         '95% interval from the chi-square distribution with n - 1 degrees of freedom'),
        ('cv', 'Within-subject CV', 'Typical error / mean of all values; on the log scale exp(SD of the log '
                                    'differences / √2) - 1', "Its interval is the typical error's, over the same mean"),
        ('sdc', 'Smallest detectable change', f'{aims.SDC_FACTOR:g} × typical error (1.96 × √2)', ''),
        ('ba', 'Bland-Altman', 'Active minus control visit: bias with its 95% interval, limits bias ± 1.96 SD',
         'Intervals of the limits as Bland & Altman (1999); ratio limits on the log scale'),
        ('icc', 'ICC(A,1)', 'Two-way, absolute agreement, single measurement (McGraw & Wong 1996)',
         'With its 95% interval'),
    ]
    return [{'key': key, 'parameter': name, 'value': value, 'note': note} for key, name, value, note in rows]


def report_files(loops_: pd.DataFrame, recordings: pd.DataFrame, pairs: pd.DataFrame, analyses: dict,
                 sweep_table: pd.DataFrame, order: dict, gaps: pd.Series, created: pd.Series, observer: str,
                 tryouts: int) -> dict:
    """The report's data, a list of rows per file: study, participant and visit, never a recording's name."""
    loops_, recordings, pairs = loops_.copy(), recordings.copy(), pairs.copy()
    visit = ['study', 'subject', 'visit', 'when']
    value_of = set(zip(recordings['recording'], recordings['value_from']))
    loops_['key'] = _keys(loops_, visit + ['dataset'])
    loops_['recording_key'] = _keys(loops_, visit)
    loops_['is_value'] = [(r, d) in value_of for r, d in zip(loops_['recording'], loops_['dataset'])]
    loops_['ci_rel_pct'] = 100 * loops_['ci_relative_half_width']
    for column in ('first_half_mm_s', 'second_half_mm_s', 'start_limb_mm_s', 'end_limb_mm_s'):
        loops_[column] = loops_[column].abs()
    loop_rows = records(loops_, [
        'key', 'recording_key', 'study', 'subject', 'visit', 'when', 'dataset', 'rank', 'outcome', 'counted',
        'is_value', 'snr', 'in_range', 'speed_mm_s', 'speed_px_per_frame', 'length_mm', 'points_n',
        'spacing_median_px', 'clearance_px', 'ci_rel_pct', 'first_half_mm_s', 'first_half_snr', 'second_half_mm_s',
        'second_half_snr', 'start_limb_mm_s', 'start_limb_snr', 'end_limb_mm_s', 'end_limb_snr', 'arterial_end',
        'crosses_itself', 'relabelled'])

    recordings['key'] = _keys(recordings, visit)
    recordings['aims'] = recordings['used_for'].map(lambda text: AIMS_TEXT.get(text.split(':')[0], text))
    recordings['picture_pct'] = 100 * recordings['rest_picture_share']
    recordings['value_from'] = recordings['value_from'].replace('', 'none')
    recordings['note'] = np.where(recordings['loops_placed'] > 0, '',
                                  np.where(recordings['picture_pct'] <= 0, 'No line fits in the picture over the rest',
                                           'No lines'))
    recording_rows = records(recordings, [
        'key', 'study', 'subject', 'visit', 'when', 'aims', 'loops_placed', 'loops_counted', 'value_mm_s',
        'value_from', 'reference_only_mm_s', 'mean_mm_s', 'sd_mm_s', 'rest_match_median', 'picture_pct', 'note'])

    a, c = pairs['active_mm_s'].astype(float), pairs['control_mm_s'].astype(float)
    both = np.isfinite(a) & np.isfinite(c)
    pairs['key'] = _keys(pairs, ['study', 'subject'])
    pairs['status'] = np.select([both, np.isfinite(c), np.isfinite(a)], ['both visits', 'control only', 'active only'],
                                'neither')
    pairs['mean_mm_s'] = ((a + c) / 2).where(both)
    pairs['diff_mm_s'] = (a - c).where(both)
    pairs['ratio'] = (a / c).where(both)
    for column in ('active_from', 'control_from'):
        pairs[column] = pairs[column].replace('', 'none')
    pair_rows = records(pairs, [
        'key', 'study', 'subject', 'status', 'control_mm_s', 'control_from', 'control_loops_counted',
        'control_loops_placed', 'active_mm_s', 'active_from', 'active_loops_counted', 'active_loops_placed',
        'mean_mm_s', 'diff_mm_s', 'ratio', 'first_visit', 'days_apart',
        *[f'{v}_{key}_mm_s' for key in ('reference_only', 'mean', 'snr7', 'snr9') for v in ('control', 'active')]])

    aim1_rows = []
    for place, (key, (_, threshold, label, short)) in enumerate(ANALYSES.items()):
        for study in STUDIES:
            found = analyses[key]['aim1'][study]
            aim1_rows.append({'key': f'{key} {study}', 'analysis': key, 'label': label, 'short': short, 'order': place,
                              'threshold': threshold, 'study': study,
                              **{name: value for name, value in found.items()}})

    sweep_rows = records(sweep_table.assign(key=sweep_table['threshold'].map(lambda t: f'{t:g}')),
                         ['key'] + list(sweep_table.columns))

    counts = []

    def add(group, level, place, label, by_study):
        counts.append({'key': f'{group} {level} {place}', 'group': group, 'level': level, 'order': place,
                       'label': label, 'esmoke': int(by_study.get('ESMOKE', 0)),
                       'ismoke': int(by_study.get('ISMOKE', 0)),
                       'total': int(by_study.get('ESMOKE', 0)) + int(by_study.get('ISMOKE', 0))})

    def per_study(frame):
        return frame['study'].value_counts().to_dict()

    add('funnel', 'Recordings', 1, 'Used by the aims', per_study(recordings))
    add('funnel', 'Recordings', 2, 'With lines', per_study(recordings[recordings['loops_placed'] > 0]))
    add('funnel', 'Recordings', 3, 'With a value (a loop that counts)',
        per_study(recordings[np.isfinite(recordings['value_mm_s'].astype(float))]))
    candidate = ~loops_['crosses_itself'].astype(bool)
    strong = candidate & (loops_['snr'] >= PRIMARY_SNR)
    add('funnel', 'Loops', 1, 'Placed', per_study(loops_))
    add('funnel', 'Loops', 2, 'Candidates (the line does not cross itself)', per_study(loops_[candidate]))
    add('funnel', 'Loops', 3, f'Signal-to-noise {PRIMARY_SNR:g} or more', per_study(loops_[strong]))
    add('funnel', 'Loops', 4, 'Speed inside the searched range', per_study(loops_[strong & loops_['in_range']]))
    add('funnel', 'Loops', 5, 'Limbs agree: counted', per_study(loops_[loops_['counted']]))
    has_a, has_c = np.isfinite(a), np.isfinite(c)
    add('funnel', 'Aim 1 participants', 1, 'Wanted', per_study(pairs))
    add('funnel', 'Aim 1 participants', 2, 'A value at one visit or both', per_study(pairs[has_a | has_c]))
    add('funnel', 'Aim 1 participants', 3, 'A value at both visits', per_study(pairs[both]))
    for key in ('primary',):
        complete = analyses[key]['aim2_complete']
        add('funnel', 'Aim 2 participants', 1, 'Wanted', {s: complete[s]['wanted'] for s in STUDIES})
        add('funnel', 'Aim 2 participants', 2, 'A value in all four recordings',
            {s: complete[s]['complete'] for s in STUDIES})
    for rank_ in (1, 2, 3):
        mine = loops_[loops_['rank'] == rank_]
        for place, outcome in enumerate(OUTCOMES):
            add('outcome', f'loop{rank_}', place, outcome, per_study(mine[mine['outcome'] == outcome]))
    for when in ('before', 'after'):
        mine = recordings[recordings['when'] == when]
        for place, source in enumerate(('loop1', 'loop2', 'loop3', 'none')):
            add('source', when, place, source, per_study(mine[mine['value_from'] == source]))

    order_rows = [{'key': label, 'group': label, **values} for label, values in order.items()]

    counted = loops_[loops_['counted']]
    halves = counted[np.isfinite(counted['first_half_mm_s']) & np.isfinite(counted['second_half_mm_s'])]
    limbs = counted[np.isfinite(counted['start_limb_mm_s']) & np.isfinite(counted['end_limb_mm_s'])]
    spread = counted.groupby('recording_key')['speed_mm_s'].agg(['count', 'mean', 'std', 'min', 'max'])
    spread = spread[spread['count'] >= 2]
    per_rec = loops_.groupby('recording_key').size()
    by_rank = loops_.groupby('rank')['counted'].agg(['size', 'sum'])
    value = np.isfinite(recordings['value_mm_s'].astype(float))
    # the loops at the slowest speed searched: what they would add if they counted (counts only)
    below = loops_[loops_['outcome'] == OUTCOMES[1]]
    edge = loops_[loops_['outcome'] == OUTCOMES[2]]
    gain = set(edge['recording_key']) & set(recordings.loc[~value, 'key'])
    now = {key for key, has in zip(recordings['key'], value) if has}
    with_edge = now | gain
    edge_gain = {}
    for study in STUDIES:
        mine = pairs[pairs['study'] == study]
        visits = [(f'{study} {p} control before', f'{study} {p} active before') for p in mine['subject']]
        edge_gain[study] = (sum(c in with_edge and a in with_edge for c, a in visits)
                            - sum(c in now and a in now for c, a in visits))
    candidates = loops_[~loops_['crosses_itself'].astype(bool)]
    summary = {
        'key': 'all', 'observer': observer, 'snr_threshold': PRIMARY_SNR, 'snr_low': SENSITIVITY_SNR[0],
        'snr_high': SENSITIVITY_SNR[1], 'near_low': NEAR[0], 'near_high': NEAR[1],
        'recordings': len(recordings), 'recordings_esmoke': int((recordings['study'] == 'ESMOKE').sum()),
        'recordings_ismoke': int((recordings['study'] == 'ISMOKE').sum()),
        'recordings_with_lines': int((recordings['loops_placed'] > 0).sum()),
        'recordings_without_lines': int((recordings['loops_placed'] == 0).sum()),
        'loops_placed': len(loops_), 'loops_counted': int(loops_['counted'].sum()),
        **{f'loops_{name}': int((loops_['outcome'] == outcome).sum()) for name, outcome in zip(
            ('counted_check', 'snr_below', 'range_edge', 'movement', 'crossing'), OUTCOMES)},
        'recordings_1_loop': int((per_rec == 1).sum()), 'recordings_2_loops': int((per_rec == 2).sum()),
        'recordings_3_loops': int((per_rec == 3).sum()),
        'recordings_with_value': int(value.sum()),
        'recordings_reference': int((recordings['value_from'] == 'loop1').sum()),
        'recordings_backup': int(recordings['value_from'].isin(['loop2', 'loop3']).sum()),
        'recordings_missing': int((~value).sum()),
        'placement_date': str(created.min())[:10], 'placement_first': str(created.min())[11:16],
        'placement_last': str(created.max())[11:16],
        'seconds_per_line_median': float(gaps[gaps < 600].median()),
        'relabelled_lines': int(loops_['relabelled'].sum()),
        'relabelled_recordings': int(loops_.loc[loops_['relabelled'].astype(bool), 'recording_key'].nunique()),
        'tryout_lines': tryouts,
        'length_mm_median': _median(loops_['length_mm']), 'length_mm_q1': float(loops_['length_mm'].quantile(.25)),
        'length_mm_q3': float(loops_['length_mm'].quantile(.75)), 'points_median': _median(loops_['points_n']),
        'spacing_px_median': _median(loops_['spacing_median_px']),
        'clearance_px_min': float(loops_['clearance_px'].min()), 'clearance_px_median': _median(loops_['clearance_px']),
        'snr_median': _median(loops_['snr']), 'snr_median_counted': _median(counted['snr']),
        'ci_rel_pct_median': _median(counted['ci_rel_pct']),
        'halves_both': len(halves),
        'halves_diff_pct_median': _median(100 * (halves['second_half_mm_s'] - halves['first_half_mm_s']).abs()
                                          / ((halves['second_half_mm_s'] + halves['first_half_mm_s']) / 2)),
        'limbs_both': len(limbs),
        'speed_px_median': _median(counted['speed_px_per_frame']),
        'speed_px_max': float(counted['speed_px_per_frame'].max()) if len(counted) else math.nan,
        'speed_mm_s_median': _median(counted['speed_mm_s']),
        'speed_mm_s_min': float(counted['speed_mm_s'].min()) if len(counted) else math.nan,
        'speed_mm_s_max': float(counted['speed_mm_s'].max()) if len(counted) else math.nan,
        'rest_match_median': _median(recordings['rest_match_median']),
        'picture_pct_median': _median(recordings['picture_pct']),
        **{f'placed_rank{int(r)}': int(row['size']) for r, row in by_rank.iterrows()},
        **{f'counted_rank{int(r)}': int(row['sum']) for r, row in by_rank.iterrows()},
        **{f'counted_pct_rank{int(r)}': 100 * float(row['sum']) / row['size'] for r, row in by_rank.iterrows()},
        'snr_below_median': _median(below['snr']),
        'near_below': int((candidates['snr'].between(NEAR[0], PRIMARY_SNR, inclusive='left')).sum()),
        'near_above': int((candidates['snr'].between(PRIMARY_SNR, NEAR[1])).sum()),
        'edge_snr_median': _median(edge['snr']),
        'search_floor_px': pattern_shift.MIN_SPEED,
        'search_floor_mm_s': pattern_shift.MIN_SPEED * float(loops_['fps'].median()) * float(loops_['mm_per_pixel'].median()),
        'edge_recordings_gain': len(gain),
        'edge_aim1_gain_esmoke': edge_gain['ESMOKE'], 'edge_aim1_gain_ismoke': edge_gain['ISMOKE'],
        'recordings_2plus_counted': len(spread),
        'between_loop_cv_pct_median': _median(100 * spread['std'] / spread['mean']),
        'max_min_ratio_median': _median(spread['max'] / spread['min']),
        'max_min_ratio_max': float((spread['max'] / spread['min']).max()) if len(spread) else math.nan,
    }
    summary.pop('loops_counted_check')
    return {'summary': [summary], 'loops': loop_rows, 'recordings': recording_rows, 'pairs': pair_rows,
            'aim1': aim1_rows, 'sweep': sweep_rows, 'counts': counts, 'visit_order': order_rows,
            'method': method_rows()}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--data', default=None, help="the app's data folder (default: from settings.csv)")
    parser.add_argument('--observer', default=None, help="the observer's code (default: the app's)")
    parser.add_argument('--out', default=None, help='where to write (default: Reports/primary_endpoint/)')
    args = parser.parse_args(argv)
    folder = args.data or aims.default_data_folder() or REPOSITORY
    observer = (args.observer or aims.default_observer() or '').upper()
    statistics_dir = os.path.join(folder, 'Statistics')
    out_dir = args.out or os.path.join(folder, 'Reports', 'primary_endpoint')
    os.makedirs(out_dir, exist_ok=True)

    table = aims.collect(statistics_dir)
    table = table[table['observer'] == observer]
    loop_table = aims.loops(table)
    found = estimates(statistics_dir, loop_table, os.path.join(out_dir, 'estimates.csv'))
    check_against_saved(loop_table, found)
    info, people = recording_info()

    # every loop, judged by the protocol, with its quality
    loops_ = loop_table.drop(columns='points').merge(provenance_extras(statistics_dir, loop_table),
                                                     on=['recording', 'dataset'])
    e = found.set_index(['recording', 'dataset'])
    loops_['in_range'] = [bool(e.at[(r, d), 'in_range']) for r, d in zip(loops_['recording'], loops_['dataset'])]
    loops_['speed_px_per_frame'] = [abs(e.at[(r, d), 'speed_px_per_frame']) for r, d in
                                    zip(loops_['recording'], loops_['dataset'])]
    loops_['ci_relative_half_width'] = (loops_['ci95_high_mm_s'] - loops_['ci95_low_mm_s']).abs() / 2 / \
        loops_['velocity_mm_s'].abs()
    loops_['rank'] = loops_['dataset'].map(aims.rank)
    loops_['length_mm'] = loops_['length_px'] * loops_['mm_per_pixel']
    loops_['outcome'] = [failure(row) for row in loops_.itertuples(index=False)]
    loops_ = loops_.merge(info, on='recording', how='left')
    created = pd.to_datetime(loops_['created'])
    gaps = created.sort_values().diff().dt.total_seconds()

    # each recording: its values by the protocol, and its stabilization
    analyses, pairs_by, recordings_by = {}, {}, {}
    for key, (value, threshold, _, _) in ANALYSES.items():
        _, recordings, pairs, stats_, complete = analysis(loop_table, found, threshold, value)
        analyses[key] = {'aim1': stats_, 'aim2_complete': aim2_complete(complete)}
        pairs_by[key], recordings_by[key] = pairs, recordings
    recordings = info.merge(recordings_by['primary'].drop(columns='observer'), on='recording', how='left')
    recordings = recordings.merge(stabilization(folder, recordings['recording']), on='recording', how='left')
    recordings['loops_placed'] = recordings['loops_placed'].fillna(0).astype(int)
    recordings['loops_counted'] = recordings['loops_counted'].fillna(0).astype(int)
    recordings['value_from'] = recordings['value_from'].fillna('')

    # aim 1's pairs, by the protocol, with how the visits fell
    order = people.set_index(['study', 'subject'])
    pairs = pairs_by['primary'].copy()
    pairs['first_visit'] = [order.at[(s, p), 'first_visit'] if (s, p) in order.index else '' for s, p in
                            zip(pairs['study'], pairs['subject'])]
    pairs['days_apart'] = [order.at[(s, p), 'days_apart'] if (s, p) in order.index else math.nan for s, p in
                           zip(pairs['study'], pairs['subject'])]
    for key in ('reference_only', 'mean', 'snr7', 'snr9'):
        other = pairs_by[key].set_index(['study', 'subject'])
        for visit in ('active', 'control'):
            pairs[f'{visit}_{key}_mm_s'] = [other.at[(s, p), f'{visit}_mm_s'] for s, p in
                                            zip(pairs['study'], pairs['subject'])]

    sweep_table = sweep(loop_table, found)

    # tables with the recordings' names, for checking; the report's data without them
    loops_.to_csv(os.path.join(out_dir, 'loops.csv'), index=False)
    recordings.to_csv(os.path.join(out_dir, 'recordings.csv'), index=False)
    pairs.to_csv(os.path.join(out_dir, 'pairs.csv'), index=False)
    pd.DataFrame([{'analysis': key, 'study': study, **analyses[key]['aim1'][study]} for key in ANALYSES
                  for study in STUDIES]).to_csv(os.path.join(out_dir, 'aim1.csv'), index=False)
    sweep_table.to_csv(os.path.join(out_dir, 'threshold_sweep.csv'), index=False)
    other = table[(table['role'] != pattern_shift.WHOLE_LOOP) & table['recording'].isin(info['recording'])]
    files = report_files(loops_, recordings, pairs, analyses, sweep_table, visit_order(pairs_by['primary'], people),
                         gaps, created, observer, len(other))
    folder_out = os.path.join(out_dir, 'dashboard')
    os.makedirs(folder_out, exist_ok=True)
    for name, rows in files.items():
        with open(os.path.join(folder_out, f'{name}.json'), 'w', encoding='utf-8') as handle:
            json.dump(_clean(rows), handle, ensure_ascii=False, separators=(',', ':'))
    print(f'{len(loops_)} whole loops of observer {observer or "(any)"}; written to {out_dir}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
