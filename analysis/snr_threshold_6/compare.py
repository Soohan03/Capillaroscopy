"""A signal-to-noise cutoff of 6 beside the protocol's 8: the PI's question of 2026-11-06 (post hoc, after unblinding).

python3 analysis/snr_threshold_6/compare.py [--data <data folder>] [--observer SJ]

Run first, from the repository (the protocol's own run and its sensitivity analyses are already in
Reports/aims/, written as analysis/primary_endpoint/README.md says):

    python3 -m capillary.aims --min-snr 6 --out Reports/aims/sensitivity_minsnr6
    python3 -m capillary.aims --min-snr 6 --value mean --out Reports/aims/sensitivity_minsnr6_valuemean
    python3 -m capillary.aims --min-snr 6 --value reference-only --out Reports/aims/sensitivity_minsnr6_valuereferenceonly
    python3 -m capillary.aims --min-snr 8 --out Reports/aims/check_minsnr8_recomputed

The script

- checks that the recompute at 8 (the path ``--min-snr`` takes: every loop's pattern shift and its limbs' computed
  again from the saved space-time diagram) gives the protocol's tables to float precision, and that every run
  judged the same loops. Otherwise it stops: the runs at 6 would differ from the protocol by more than the cutoff;
- compares the runs at 6 with the protocol: the loops whose judgement changes, the recordings whose value changes,
  aim 1 (with the report's 95% intervals, `analysis/primary_endpoint/report.py`) and aim 2 side by side, with 7
  and 9 (the protocol's sensitivity analyses) and the protocol's other values (the mean of the counted loops, the
  reference only);
- counts what each cutoff lets through where there should be no flow, with the protocol's own filter (the ``s1_``
  columns of the coarse-filter analysis, `analysis/coarse_filter/`): synthetic clips without flow
  (analysis/coarse_filter/synthetic_results.csv) and the blind loops' own lines over the cuff occlusion
  (Reports/coarse_filter/measurements.csv); and whether the loops each cutoff counts at rest run the same way
  after release, where they count there too;
- writes the report page's tables into dashboard/ here, naming recordings by study, participant, visit and
  before or after exposure only.
"""

from __future__ import annotations

import argparse
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPOSITORY = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPOSITORY)
sys.path.insert(0, os.path.join(REPOSITORY, 'analysis', 'primary_endpoint'))
import report  # noqa: E402  (aim 1 with the primary report's 95% intervals)

from capillary import aims, datasets, inventory, pattern_shift  # noqa: E402

OUT = os.path.join(HERE, 'dashboard')
PROTOCOL = pattern_shift.MIN_SNR
CUTOFF = 6.0
#: Each run compared: (value, cutoff) -> its folder under Reports/aims/, as the commands above write them.
RUNS = {
    ('protocol', 8.0): '',
    ('protocol', 6.0): 'sensitivity_minsnr6',
    ('protocol', 7.0): 'sensitivity_minsnr7',
    ('protocol', 9.0): 'sensitivity_minsnr9',
    ('mean', 8.0): 'sensitivity_valuemean',
    ('mean', 6.0): 'sensitivity_minsnr6_valuemean',
    ('reference_only', 8.0): 'sensitivity_valuereferenceonly',
    ('reference_only', 6.0): 'sensitivity_minsnr6_valuereferenceonly',
}
#: The protocol's run made again through the recompute path (--min-snr 8).
CHECK = 'check_minsnr8_recomputed'
VALUE_TEXT = {'protocol': 'Reference, else the first backup that counts (protocol)',
              'mean': 'Mean of all counted loops', 'reference_only': 'Reference capillary only'}
TABLES = ('loops', 'recordings', 'aim1_pairs', 'aim1', 'aim2_values', 'aim2')
STUDY_KEYS = {aims.POOLED: 'pooled', 'ESMOKE': 'ESMOKE', 'ISMOKE': 'ISMOKE'}
STUDY_LABELS = {'pooled': 'Both studies', 'ESMOKE': 'ESMOKE', 'ISMOKE': 'ISMOKE'}
#: The cutoffs of the checks where there should be no flow.
NULL_CUTOFFS = (5.0, 6.0, 7.0, 8.0, 9.0)
WHEN = {'före': 'before', 'efter': 'after'}
#: The slowest speed the protocol's pattern shift searches (px/frame); a loop found there is not resolved.
SLOWEST = pattern_shift.MIN_SPEED
AIM1_COLUMNS = ('participants_wanted', 'participants', 'one_visit_only', 'neither_visit', 'mean_active_mm_s',
                'mean_control_mm_s', 'grand_mean_mm_s', 'typical_error_mm_s', 'te_ci_low_mm_s', 'te_ci_high_mm_s',
                'cv_percent', 'cv_ci_low', 'cv_ci_high', 'cv_log_percent', 'cv_log_ci_low', 'cv_log_ci_high',
                'sdc_mm_s', 'ba_bias', 'ba_bias_ci_low', 'ba_bias_ci_high', 'ba_loa_low', 'ba_loa_high', 'icc_a1',
                'icc_a1_ci_low', 'icc_a1_ci_high')
AIM2_COLUMNS = ('participants_wanted', 'incomplete', 'participants', 'mean_before_mm_s', 'mean_after_mm_s',
                'change_mm_s', 'change_ci_low_mm_s', 'change_ci_high_mm_s', 'change_sd_mm_s', 't_test_p', 'wilcoxon_p',
                'ratio', 'ratio_ci_low', 'ratio_ci_high', 'log_t_test_p')


# ------------------------------------------------------------------------------------------------- reading

def load(folder: str, observer: str) -> dict:
    """The six tables `capillary.aims` writes into `folder`, for `observer`."""
    out = {}
    for name in TABLES:
        path = os.path.join(folder, f'{name}.csv')
        if not os.path.exists(path):
            raise SystemExit(f'{path} is missing: run the commands at the top of this script first')
        table = pd.read_csv(path)
        out[name] = table[table['observer'] == observer].reset_index(drop=True)
    return out


def same_numbers(a: pd.DataFrame, b: pd.DataFrame) -> list:
    """The columns in which `a` and `b` differ beyond float precision (text exactly, numbers to 1e-9)."""
    if list(a.columns) != list(b.columns) or len(a) != len(b):
        return ['(columns or rows)']
    differ = []
    for column in a.columns:
        x, y = a[column], b[column]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            xv, yv = x.to_numpy(float), y.to_numpy(float)
            if not (np.array_equal(np.isnan(xv), np.isnan(yv))
                    and np.allclose(xv[~np.isnan(xv)], yv[~np.isnan(yv)], rtol=1e-9, atol=1e-12)):
                differ.append(column)
        elif not x.fillna('').astype(str).equals(y.fillna('').astype(str)):
            differ.append(column)
    return differ


def labels() -> pd.DataFrame:
    """Study, participant, visit and before/after of every recording the inventory knows, by name (NFC)."""
    table = inventory.recordings()
    out = pd.DataFrame({'recording': table['name'].map(inventory.nfc), 'study': table['study'],
                        'participant': table['subject'], 'visit': table['condition'],
                        'when': table['phase'].map(WHEN)})
    out['label'] = out['study'] + ' ' + out['participant'] + ' ' + out['visit'] + ' ' + out['when']
    return out.drop_duplicates('recording').set_index('recording')


def uses(protocol: dict) -> dict:
    """recording -> the aims that use it ('aim 1', 'aim 2' or 'aims 1, 2'), from the protocol's tables."""
    found = {}
    for column in ('active_recording', 'control_recording'):
        for name in protocol['aim1_pairs'][column].dropna():
            found.setdefault(inventory.nfc(name), set()).add('1')
    for column in aims.AIM2_RECORDINGS:
        for name in protocol['aim2_values'][column].dropna():
            found.setdefault(inventory.nfc(name), set()).add('2')
    return {name: ('aims ' if len(which) > 1 else 'aim ') + ', '.join(sorted(which)) for name, which in found.items()}


def saved_speed(statistics_dir: str, recording: str, dataset: str) -> float:
    """The size of the speed (px/frame) a loop's pooled pattern shift found, from its provenance (saved whether or
    not it was resolved; its sign says only which way the line was drawn)."""
    record = datasets.read_provenance(datasets.line_dataset_files(statistics_dir, recording, dataset)['provenance'])
    value = ((record or {}).get('summary') or {}).get('pattern_shift_speed_px_per_frame')
    return abs(float(value)) if value is not None else math.nan


# --------------------------------------------------------------------------------------------- the loops

def status(row: pd.Series, cutoff: float) -> str:
    """What became of a loop judged at `cutoff` (a row of capillary.aims' loops.csv, with ``speed_px_per_frame``)."""
    if row['counted']:
        return 'counted'
    why = row['why_not'] if isinstance(row['why_not'], str) else ''
    if 'crosses itself' in why:
        return 'crosses itself'
    if 'movement' in why:
        return 'limbs moved opposite ways'
    if why == 'not resolved':
        if row['snr'] < cutoff:
            return 'below the cutoff'
        if math.isclose(row['speed_px_per_frame'], SLOWEST):
            return 'at the slowest speed searched'
        return 'outside the range searched'
    return why


def loop_table(runs: dict, names: pd.DataFrame, used: dict, statistics_dir: str) -> pd.DataFrame:
    key = ['recording', 'dataset']
    at8 = runs[('protocol', PROTOCOL)]['loops'].set_index(key)
    at6 = runs[('protocol', CUTOFF)]['loops'].set_index(key)
    rows = []
    for (recording, dataset), first in at8.iterrows():
        second = at6.loc[(recording, dataset)]
        speed = saved_speed(statistics_dir, recording, dataset)
        name = inventory.nfc(recording)
        row = {'label': names.at[name, 'label'], 'study': names.at[name, 'study'],
               'participant': names.at[name, 'participant'], 'visit': names.at[name, 'visit'],
               'when': names.at[name, 'when'], 'loop': dataset, 'aims': used.get(name, ''),
               'snr': float(first['snr']), 'speed_px_per_frame': speed,
               'status_8': status(pd.Series({**first.to_dict(), 'speed_px_per_frame': speed}), PROTOCOL),
               'status_6': status(pd.Series({**second.to_dict(), 'speed_px_per_frame': speed}), CUTOFF),
               'speed_mm_s_8': first['speed_mm_s'], 'speed_mm_s_6': second['speed_mm_s']}
        if not math.isclose(float(first['snr']), float(second['snr']), rel_tol=1e-9):
            raise SystemExit(f'{recording} {dataset}: the score differs between the runs')
        rows.append(row)
    out = pd.DataFrame(rows)
    # Changed: counted at one cutoff and not at the other (a loop may stay out for another reason).
    out['changed'] = np.where((out['status_8'] == 'counted') != (out['status_6'] == 'counted'), 'yes', 'no')
    odd = out[(out['status_8'] == 'outside the range searched') | (out['status_6'] == 'outside the range searched')]
    if len(odd):
        raise SystemExit(f'{len(odd)} loops scored above the cutoff outside the range away from {SLOWEST:g} px/frame: '
                         'look at them before reading this comparison')
    return out


# ------------------------------------------------------------------------------------- the recordings

def _value(table: pd.DataFrame, name: str, column: str) -> float:
    row = table[table['recording'].map(inventory.nfc) == name]
    return float(row[column].iloc[0]) if len(row) else math.nan


#: Each aim's two recordings of a participant (columns ``<prefix>_recording`` and ``<prefix>_mm_s``), and what to call
#: the other one when it has no value.
PAIRS = (('aim 1', 'aim1_pairs', (('active', 'on the other visit'), ('control', 'on the other visit'))),
         ('aim 2', 'aim2_values', (('active_before', 'before exposure'), ('active_after', 'after exposure'))))


def _effect(name: str, at6: dict, at8: dict) -> str:
    """What a changed value does to the aims: the pair it belongs to, at both cutoffs."""
    out = []
    for aim, table, columns in PAIRS:
        for row6, row8 in zip(at6[table].to_dict('records'), at8[table].to_dict('records')):
            if (row6['study'], row6['subject']) != (row8['study'], row8['subject']):
                raise SystemExit(f'{table}: the runs list the participants in another order')
            names = [inventory.nfc(row6[f'{c}_recording']) if isinstance(row6[f'{c}_recording'], str) else ''
                     for c, _ in columns]
            if name not in names:
                continue
            both6 = all(np.isfinite(row6[f'{c}_mm_s']) for c, _ in columns)
            both8 = all(np.isfinite(row8[f'{c}_mm_s']) for c, _ in columns)
            if both6 and not both8:
                out.append(f'enters {aim}')
            elif both6:
                out.append(f'changes its {aim} pair')
            elif both8:
                out.append(f'leaves {aim}')
            else:
                other = columns[1 - names.index(name)][1]
                out.append(f'{aim}: no value {other}')
    return '; '.join(out) or 'not used by the aims'


def recording_changes(runs: dict, names: pd.DataFrame, used: dict) -> pd.DataFrame:
    at8, at6 = runs[('protocol', PROTOCOL)], runs[('protocol', CUTOFF)]
    a = at8['recordings'].assign(name=at8['recordings']['recording'].map(inventory.nfc)).set_index('name')
    b = at6['recordings'].assign(name=at6['recordings']['recording'].map(inventory.nfc)).set_index('name')
    rows = []
    for name in a.index:
        v8, v6 = a.at[name, 'value_mm_s'], b.at[name, 'value_mm_s']
        same = (np.isnan(v8) and np.isnan(v6)) or (np.isfinite(v8) and np.isfinite(v6) and math.isclose(v8, v6, rel_tol=1e-9))
        from8, from6 = (a.at[name, 'value_from'] if isinstance(a.at[name, 'value_from'], str) else '',
                        b.at[name, 'value_from'] if isinstance(b.at[name, 'value_from'], str) else '')
        if same and from8 == from6:
            continue
        rows.append({'label': names.at[name, 'label'], 'study': names.at[name, 'study'],
                     'participant': names.at[name, 'participant'], 'aims': used.get(name, ''),
                     'value_8_mm_s': v8, 'from_8': from8, 'value_6_mm_s': v6, 'from_6': from6,
                     'effect': _effect(name, at6, at8)})
    return pd.DataFrame(rows, columns=['label', 'study', 'participant', 'aims', 'value_8_mm_s', 'from_8',
                                       'value_6_mm_s', 'from_6', 'effect'])


# ------------------------------------------------------------------------------------------- the aims

def aim1_pair_rows(runs: dict) -> pd.DataFrame:
    """Every aim 1 participant with a value at both visits at 8 or at 6: the two visits' values at each cutoff."""
    a = runs[('protocol', PROTOCOL)]['aim1_pairs'].set_index(['study', 'subject'])
    b = runs[('protocol', CUTOFF)]['aim1_pairs'].set_index(['study', 'subject'])
    rows = []
    for key in a.index:
        in8 = bool(np.isfinite(a.at[key, 'active_mm_s']) and np.isfinite(a.at[key, 'control_mm_s']))
        in6 = bool(np.isfinite(b.at[key, 'active_mm_s']) and np.isfinite(b.at[key, 'control_mm_s']))
        if in8 or in6:
            rows.append({'label': f'{key[0]} {key[1]}', 'study': key[0], 'participant': key[1],
                         'nicotine_8_mm_s': a.at[key, 'active_mm_s'], 'control_8_mm_s': a.at[key, 'control_mm_s'],
                         'nicotine_6_mm_s': b.at[key, 'active_mm_s'], 'nicotine_6_from': b.at[key, 'active_from'],
                         'control_6_mm_s': b.at[key, 'control_mm_s'], 'control_6_from': b.at[key, 'control_from'],
                         'in_aim1_8': 'yes' if in8 else 'no', 'in_aim1_6': 'yes' if in6 else 'no'})
    return pd.DataFrame(rows)


def aim1_rows(runs: dict) -> pd.DataFrame:
    """Aim 1 for every run, with the report's intervals; checked against capillary.aims' own aim1.csv."""
    rows = []
    for (value, cutoff), run in runs.items():
        table = report.aim1_table(run['aim1_pairs'])
        own = run['aim1'].set_index('study')
        for study, key in STUDY_KEYS.items():
            stats_ = table[study]
            for column in ('participants', 'cv_percent', 'icc_a1'):
                mine, theirs = stats_[column], own.at[study, column]
                if not ((pd.isna(mine) and pd.isna(theirs)) or math.isclose(mine, theirs, rel_tol=1e-9)):
                    raise SystemExit(f'aim 1 {value} {cutoff:g} {study} {column}: {mine} against {theirs}')
            rows.append({'key': f'{value} {cutoff:g} {key}', 'value': value, 'value_text': VALUE_TEXT[value],
                         'cutoff': cutoff, 'study': key, 'study_label': STUDY_LABELS[key],
                         **{c: stats_[c] for c in AIM1_COLUMNS}})
    return pd.DataFrame(rows)


def aim2_rows(runs: dict) -> pd.DataFrame:
    rows = []
    for (value, cutoff), run in runs.items():
        own = run['aim2'].set_index('study')
        for study, key in STUDY_KEYS.items():
            rows.append({'key': f'{value} {cutoff:g} {key}', 'value': value, 'value_text': VALUE_TEXT[value],
                         'cutoff': cutoff, 'study': key, 'study_label': STUDY_LABELS[key],
                         **{c: own.at[study, c] for c in AIM2_COLUMNS}})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------ where there is no flow

def counts(t: pd.DataFrame, cutoff: float) -> pd.Series:
    """`capillary.aims`' rule on the coarse-filter measurements (the protocol's filter, ``s1_``): resolved at
    `cutoff`, the limbs not resolved opposite ways at `cutoff`, the line not crossing itself."""
    def resolved(prefix):
        return t[f'{prefix}in_range'].astype(bool) & (t[f'{prefix}snr'] >= cutoff)
    movement = resolved('s1_start_') & resolved('s1_end_') & (np.sign(t['s1_start_speed']) != np.sign(t['s1_end_speed']))
    return resolved('s1_') & ~movement & ~t['crosses_itself'].astype(bool)


def null_checks(data: str) -> tuple:
    synthetic = pd.read_csv(os.path.join(REPOSITORY, 'analysis', 'coarse_filter', 'synthetic_results.csv'))
    real = pd.read_csv(os.path.join(data, 'Reports', 'coarse_filter', 'measurements.csv'))
    null = synthetic[synthetic['speed'] == 0].reset_index(drop=True)
    occlusion = real[(real['window'] == 'occlusion') & real['picture_ok'].astype(bool)].reset_index(drop=True)
    rest = real[real['window'] == 'rest'].reset_index(drop=True)
    after = real[(real['window'] == 'after release') & real['picture_ok'].astype(bool)].reset_index(drop=True)
    rows = []
    for cutoff in NULL_CUTOFFS:
        at_rest = rest[counts(rest, cutoff)].set_index(['recording', 'dataset'])
        after_too = after[counts(after, cutoff)].set_index(['recording', 'dataset'])
        both = at_rest.index.intersection(after_too.index)
        same = np.sign(at_rest.loc[both, 's1_speed']) == np.sign(after_too.loc[both, 's1_speed'])
        rows.append({'cutoff': cutoff, 'synthetic_clips': len(null), 'synthetic_flow': int(counts(null, cutoff).sum()),
                     'occlusion_lines': len(occlusion), 'occlusion_flow': int(counts(occlusion, cutoff).sum()),
                     'rest_loops': len(rest), 'rest_counted': int(len(at_rest)),
                     'after_release_counted_too': int(len(both)), 'after_release_same_way': int(same.sum())})
    in_range = null[null['s1_in_range'].astype(bool)]
    facts = {'synthetic_highest_in_range': float(in_range['s1_snr'].max()), 'synthetic_highest': float(null['s1_snr'].max())}
    occlusion = occlusion.assign(counts_6=counts(occlusion, CUTOFF))
    after = after.assign(counts_6=counts(after, CUTOFF))
    return pd.DataFrame(rows), facts, rest.set_index(['recording', 'dataset']), \
        occlusion.set_index(['recording', 'dataset']), after.set_index(['recording', 'dataset'])


def changed_loops(loops: pd.DataFrame, runs: dict, measured: tuple) -> pd.DataFrame:
    """The loops whose judgement changes, with the protocol's filter on their lines in the occlusion and after
    release, judged at 6 as at rest (`counts`): flow in the occlusion; counted after release, and the same way as
    at rest. 'not measured': the line left the picture there, or the recording has no official release."""
    rest, occlusion, after = measured
    at8 = runs[('protocol', PROTOCOL)]['loops']
    keys = list(zip(at8['recording'], at8['dataset']))
    rows = []
    for i in loops.index[loops['changed'] == 'yes']:
        key = keys[i]
        row = loops.loc[i].to_dict()
        r = rest.loc[key] if key in rest.index else None
        o = occlusion.loc[key] if key in occlusion.index else None
        a = after.loc[key] if key in after.index else None
        counted_after = a is not None and bool(a['counts_6'])
        row.update({
            'occlusion_snr': float(o['s1_snr']) if o is not None else math.nan,
            'occlusion_flow_at_6': ('yes' if bool(o['counts_6']) else 'no') if o is not None else 'not measured',
            'after_release_snr': float(a['s1_snr']) if a is not None else math.nan,
            'after_release_counted_at_6': ('yes' if counted_after else 'no') if a is not None else 'not measured',
            'after_release_same_way': ('yes' if np.sign(a['s1_speed']) == np.sign(r['s1_speed']) else 'no')
            if counted_after and r is not None else ''})
        rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------- printing

def _fmt(value, digits=3):
    return '–' if value is None or (isinstance(value, float) and not np.isfinite(value)) else f'{value:.{digits}f}'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--data', default=None, help="the app's data folder (default: from settings.csv)")
    parser.add_argument('--observer', default='SJ', help="the study's observer (default SJ)")
    args = parser.parse_args(argv)
    data = args.data or aims.default_data_folder()
    if not data:
        parser.error('no data folder: pass --data')
    folder = os.path.join(data, 'Reports', 'aims')
    runs = {key: load(os.path.join(folder, sub), args.observer) for key, sub in RUNS.items()}
    protocol = runs[('protocol', PROTOCOL)]

    print('The recompute at 8 against the protocol\'s run:')
    check = load(os.path.join(folder, CHECK), args.observer)
    differ = {name: same_numbers(protocol[name], check[name]) for name in TABLES}
    differ = {name: columns for name, columns in differ.items() if columns}
    if differ:
        raise SystemExit(f'  differs: {differ}')
    print('  the same to float precision in all six tables')
    reference = protocol['loops'][['recording', 'dataset']]
    for key, run in runs.items():
        if not run['loops'][['recording', 'dataset']].equals(reference):
            raise SystemExit(f'the run {key} judged other loops than the protocol\'s: run every command again')
    print(f'  every run judged the same {len(reference)} loops\n')

    names = labels()
    used = uses(protocol)
    statistics_dir = os.path.join(data, 'Statistics')
    loops = loop_table(runs, names, used, statistics_dir)
    null, facts, *measured = null_checks(data)
    changed = changed_loops(loops, runs, tuple(measured))
    recordings = recording_changes(runs, names, used)
    pairs = aim1_pair_rows(runs)
    aim1 = aim1_rows(runs)
    aim2 = aim2_rows(runs)

    band = loops[(loops['snr'] >= CUTOFF) & (loops['snr'] < PROTOCOL)]
    in_aims = set(used)
    recordings8 = protocol['recordings'].assign(name=protocol['recordings']['recording'].map(inventory.nfc))
    recordings6 = runs[('protocol', CUTOFF)]['recordings'].assign(
        name=runs[('protocol', CUTOFF)]['recordings']['recording'].map(inventory.nfc))
    summary = {
        'loops': len(loops),
        'counted_8': int((loops['status_8'] == 'counted').sum()),
        'counted_6': int((loops['status_6'] == 'counted').sum()),
        'band': len(band),
        'band_gained': int((band['status_6'] == 'counted').sum()),
        'band_slowest': int((band['status_6'] == 'at the slowest speed searched').sum()),
        'band_crossing': int((band['status_6'] == 'crosses itself').sum()),
        'gained': int(((loops['status_6'] == 'counted') & (loops['status_8'] != 'counted')).sum()),
        'lost': int(((loops['status_8'] == 'counted') & (loops['status_6'] != 'counted')).sum()),
        'lost_in_aims': int(((loops['status_8'] == 'counted') & (loops['status_6'] != 'counted')
                             & (loops['aims'] != '')).sum()),
        'gained_in_aims': int(((loops['status_6'] == 'counted') & (loops['status_8'] != 'counted')
                               & (loops['aims'] != '')).sum()),
        'below_6': int((loops['snr'] < CUTOFF).sum()),
        'median_snr_below_8': float(loops.loc[(loops['status_8'] == 'below the cutoff'), 'snr'].median()),
        'recordings_aims': len(in_aims),
        'with_value_8': int(recordings8[recordings8['name'].isin(in_aims)]['value_mm_s'].notna().sum()),
        'with_value_6': int(recordings6[recordings6['name'].isin(in_aims)]['value_mm_s'].notna().sum()),
        'values_changed': len(recordings),
        'values_changed_aims': int((recordings['aims'] != '').sum()),
        'synthetic_highest_in_range': facts['synthetic_highest_in_range'],
    }
    gained = changed[changed['status_6'] == 'counted']
    summary.update({
        'gained_snr_low': float(gained['snr'].min()), 'gained_snr_high': float(gained['snr'].max()),
        'gained_measured_after_release': int((gained['after_release_counted_at_6'] != 'not measured').sum()),
        'gained_counted_after_release': int((gained['after_release_counted_at_6'] == 'yes').sum()),
        'gained_same_way_after_release': int((gained['after_release_same_way'] == 'yes').sum()),
        'gained_measured_occlusion': int((gained['occlusion_flow_at_6'] != 'not measured').sum()),
        'gained_flow_in_occlusion': int((gained['occlusion_flow_at_6'] == 'yes').sum()),
    })

    print(f'Loops: {summary["counted_8"]} of {summary["loops"]} count at 8, {summary["counted_6"]} at 6. '
          f'{summary["band"]} score from 6 to under 8: {summary["band_gained"]} count at 6, {summary["band_slowest"]} '
          f'sit at the slowest speed searched, {summary["band_crossing"]} cross themselves. Lost at 6: {summary["lost"]} '
          f'({summary["lost_in_aims"]} in a recording the aims use).')
    columns = ['label', 'loop', 'aims', 'snr', 'status_8', 'status_6', 'speed_mm_s_6', 'occlusion_snr',
               'occlusion_flow_at_6', 'after_release_snr', 'after_release_counted_at_6', 'after_release_same_way']
    with pd.option_context('display.width', 250, 'display.max_columns', 20):
        print(changed[columns].to_string(index=False, float_format=lambda v: f'{v:.3f}'))
        print(f'\nRecordings the aims use with a value: {summary["with_value_8"]} of {summary["recordings_aims"]} at 8, '
              f'{summary["with_value_6"]} at 6. Values that change:')
        print(recordings.to_string(index=False, float_format=lambda v: f'{v:.4f}'))
        print('\nAim 1\'s participants with both visits at either cutoff:')
        print(pairs.to_string(index=False, float_format=lambda v: f'{v:.4f}'))
    print('\nWhere there should be no flow (the protocol\'s filter):')
    print(null.to_string(index=False))
    print(f'  synthetic clips without flow: the highest score inside the range searched is '
          f'{facts["synthetic_highest_in_range"]:.2f} (anywhere {facts["synthetic_highest"]:.2f})')
    print(f'  the {summary["gained"]} loops gained: flow in the occlusion in {summary["gained_flow_in_occlusion"]} of '
          f'{summary["gained_measured_occlusion"]} measured there; after release {summary["gained_measured_after_release"]} '
          f'measured, {summary["gained_counted_after_release"]} counted there at 6, '
          f'{summary["gained_same_way_after_release"]} of them the same way as at rest')

    show = ['participants', 'grand_mean_mm_s', 'typical_error_mm_s', 'cv_percent', 'cv_ci_low', 'cv_ci_high',
            'cv_log_percent', 'sdc_mm_s', 'ba_bias', 'ba_loa_low', 'ba_loa_high', 'icc_a1', 'icc_a1_ci_low', 'icc_a1_ci_high']
    for study in STUDY_KEYS.values():
        rows = aim1[aim1['study'] == study].set_index('key')[show].T
        print(f'\nAim 1, {study}')
        print(rows.to_string(float_format=lambda v: f'{v:.3f}'))
    show = ['participants', 'mean_before_mm_s', 'mean_after_mm_s', 'change_mm_s', 'change_ci_low_mm_s',
            'change_ci_high_mm_s', 't_test_p', 'wilcoxon_p', 'ratio', 'log_t_test_p']
    for study in STUDY_KEYS.values():
        rows = aim2[aim2['study'] == study].set_index('key')[show].T
        print(f'\nAim 2, {study}')
        print(rows.to_string(float_format=lambda v: f'{v:.3f}'))

    os.makedirs(OUT, exist_ok=True)
    aim1.to_csv(os.path.join(OUT, 'aim1.csv'), index=False)
    aim2.to_csv(os.path.join(OUT, 'aim2.csv'), index=False)
    loops.to_csv(os.path.join(OUT, 'loops.csv'), index=False)
    changed.to_csv(os.path.join(OUT, 'changed_loops.csv'), index=False)
    recordings.to_csv(os.path.join(OUT, 'changed_values.csv'), index=False)
    pairs.to_csv(os.path.join(OUT, 'aim1_pairs.csv'), index=False)
    null.to_csv(os.path.join(OUT, 'null_checks.csv'), index=False)
    pd.DataFrame([{'key': key, 'value': value} for key, value in summary.items()]).to_csv(
        os.path.join(OUT, 'summary.csv'), index=False)
    print(f'\nThe report page\'s tables in {OUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
