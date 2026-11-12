"""The tables the placement repeat's report page reads, from compare's tables (run `repeat.py compare` first).

python3 analysis/placement_repeat/dashboard.py     (writes dashboard/*.csv here)

- recordings.csv: recordings.csv with each recording named by study, participant, visit and whether it came
  before or after exposure, instead of its file name (the code stays);
- loop_pairs.csv: each loop of the repeat that lies on a loop of the first placement (``lies_on_first`` of
  loops.csv) with both readings, the speed each found in px/frame (from its provenance) and what came of it;
- summary.csv: summary.csv with a short ``key`` per comparison;
- aim1.csv: aim 1 pooled over both studies by the protocol, the row the report page shows
  (``Reports/primary_endpoint/dashboard/aim1.json`` in the main data folder), for comparison.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import repeat  # noqa: E402

from capillary import datasets, inventory  # noqa: E402

OUT = os.path.join(HERE, 'dashboard')
WHEN = {'före': 'before', 'efter': 'after'}
EXPOSURE = {'W': 'nicotine', 'S': 'nicotine', 'Q': 'control', 'C': 'control'}
SUMMARY_KEYS = ('reference', 'velocity', 'value', 'mean', 'loops')
#: The slowest speed the protocol's pattern shift searches (px/frame): a loop found there is not resolved.
SLOWEST = 1.0
#: Yes/no columns, written as the words the page shows ('' where there is nothing to say).
YES_NO = {True: 'yes', False: 'no', 'True': 'yes', 'False': 'no'}
RECORDING_FLAGS = ('same_reference', 'first_reference_counted', 'repeat_reference_counted', 'values_same_capillary')
PAIR_FLAGS = ('first_counted', 'repeat_counted')


def _words(column: pd.Series) -> pd.Series:
    return column.map(lambda value: YES_NO.get(value, '') if isinstance(value, (bool, np.bool_, str)) else '')


def names() -> pd.DataFrame:
    """Study, participant, visit and before/after of every recording the inventory knows, by name (NFC)."""
    table = inventory.recordings()
    out = pd.DataFrame({'recording': table['name'].map(inventory.nfc), 'study': table['study'],
                        'participant': table['subject'], 'visit': table['condition'],
                        'exposure': table['condition'].map(EXPOSURE), 'when': table['phase'].map(WHEN)})
    out['label'] = out['study'] + ' ' + out['participant'] + ' ' + out['visit'] + ' ' + out['when']
    return out.drop_duplicates('recording').set_index('recording')


def _speed(statistics_dir: str, stem: str, dataset: str) -> float:
    """The size of the speed (px/frame) a loop's pooled pattern shift found, from its provenance (the sign says
    only which way the line was drawn)."""
    record = datasets.read_provenance(datasets.line_dataset_files(statistics_dir, stem, dataset)['provenance'])
    value = ((record or {}).get('summary') or {}).get('pattern_shift_speed_px_per_frame')
    return abs(float(value)) if value is not None else np.nan


def _outcome(first: pd.Series, again: pd.Series) -> str:
    if first['counted'] and again['counted']:
        return 'counted both times'
    if first['counted'] or again['counted']:
        return 'counted once'
    scored = [row for row in (first, again) if row['snr'] >= 8]
    if scored:
        if not all(row['speed_px_per_frame'] == SLOWEST for row in scored):
            raise SystemExit('A loop scored 8 or more without counting, away from the slowest speed: look at it.')
        return 'at the slowest speed searched'
    return 'below 8 both times'


def loop_pairs(loops: pd.DataFrame, labels: pd.DataFrame, record: dict) -> pd.DataFrame:
    folders = {'first': os.path.join(record['main_data_folder'], repeat.STATISTICS),
               'repeat': os.path.join(repeat.DEFAULT_FOLDER, repeat.STATISTICS)}
    loops = loops.copy()
    loops['speed_px_per_frame'] = [_speed(folders[row.placement], row.recording, row.dataset)
                                   for row in loops.itertuples(index=False)]
    first = loops[loops['placement'] == 'first'].set_index(['recording', 'dataset'])
    rows = []
    for again in loops[(loops['placement'] == 'repeat') & loops['lies_on_first'].fillna('').ne('')].to_dict('records'):
        before = first.loc[(again['recording'], again['lies_on_first'])]
        rows.append({'code': again['code'], 'recording': labels.at[again['recording'], 'label'],
                     'first_loop': again['lies_on_first'], 'repeat_loop': again['dataset'], 'overlap': again['overlap'],
                     'first_snr': before['snr'], 'repeat_snr': again['snr'],
                     'first_speed_px_per_frame': before['speed_px_per_frame'],
                     'repeat_speed_px_per_frame': again['speed_px_per_frame'],
                     'first_counted': bool(before['counted']), 'repeat_counted': bool(again['counted']),
                     'first_mm_s': before['speed_mm_s'], 'repeat_mm_s': again['speed_mm_s'],
                     'outcome': _outcome(before, pd.Series(again))})
    return pd.DataFrame(rows)


def aim1_pooled(main_folder: str) -> pd.DataFrame:
    path = os.path.join(main_folder, 'Reports', 'primary_endpoint', 'dashboard', 'aim1.json')
    with open(path, encoding='utf-8') as handle:
        rows = [row for row in json.load(handle) if row.get('key') == 'primary pooled']
    if len(rows) != 1:
        raise SystemExit(f'No single pooled primary row in {path}')
    keep = ('study', 'participants_wanted', 'participants', 'grand_mean_mm_s', 'typical_error_mm_s', 'cv_percent',
            'cv_ci_low', 'cv_ci_high', 'cv_log_percent', 'sdc_mm_s', 'icc_a1', 'icc_a1_ci_low', 'icc_a1_ci_high')
    return pd.DataFrame([{key: rows[0].get(key) for key in keep}])


def main() -> int:
    record = repeat._manifest(repeat.DEFAULT_FOLDER)
    labels = names()
    recordings = pd.read_csv(os.path.join(HERE, 'recordings.csv'))
    loops = pd.read_csv(os.path.join(HERE, 'loops.csv'))
    summary = pd.read_csv(os.path.join(HERE, 'summary.csv'))
    if len(summary) != len(SUMMARY_KEYS):
        raise SystemExit('summary.csv does not have the comparisons this script names')
    stems = recordings['recording'].map(inventory.nfc)
    out = labels.loc[stems, ['label', 'study', 'participant', 'visit', 'exposure', 'when']].reset_index(drop=True)
    recordings = pd.concat([recordings[['code']], out, recordings.drop(columns=['code', 'recording', 'study'])], axis=1)
    loops['recording'] = loops['recording'].map(inventory.nfc)
    pairs = loop_pairs(loops, labels, record)
    for frame, flags in ((recordings, RECORDING_FLAGS), (pairs, PAIR_FLAGS)):
        for column in flags:
            frame[column] = _words(frame[column])
    summary.insert(0, 'key', SUMMARY_KEYS)
    os.makedirs(OUT, exist_ok=True)
    recordings.to_csv(os.path.join(OUT, 'recordings.csv'), index=False)
    pairs.to_csv(os.path.join(OUT, 'loop_pairs.csv'), index=False)
    summary.to_csv(os.path.join(OUT, 'summary.csv'), index=False)
    aim1_pooled(record['main_data_folder']).to_csv(os.path.join(OUT, 'aim1.csv'), index=False)
    print(f'{len(recordings)} recordings, {len(pairs)} loop pairs ({pairs["outcome"].value_counts().to_dict()}) '
          f'in {OUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
