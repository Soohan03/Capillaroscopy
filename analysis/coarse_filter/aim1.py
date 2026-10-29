"""Aim 1 with PLAN.md's post-hoc rule, beside the protocol's (run after checks.py real).

python3 analysis/coarse_filter/aim1.py

Each recording's value is the protocol's (the reference, else the first backup that counts), with a loop counting
by step 1 (the protocol) or step 2 (the coarser filter, from 3, 5 or 8 px/frame). Statistics as
analysis/primary_endpoint/report.py gives them. Writes aim1.csv here (per study, no names) and pairs.csv and
loops.csv in Reports/coarse_filter/ (with names), and prints the summary.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'primary_endpoint'))
import checks  # noqa: E402
import report  # noqa: E402
import rule  # noqa: E402

from capillary import aims  # noqa: E402


def rule_loops(loops_: pd.DataFrame, rest: pd.DataFrame, floor) -> pd.DataFrame:
    """`loops_` (the blind loops) counted by the rule from `floor` (None: the protocol, step 1 only)."""
    j = rule.judge(rest, rule.MAIN_FLOOR if floor is None else floor).set_index(['recording', 'dataset'])
    j = j.loc[list(zip(loops_['recording'], loops_['dataset']))]
    out = loops_.copy()
    counts = j['s1_counts'] if floor is None else j['counts']
    speed = j['s1_speed'] if floor is None else j['speed_px_per_frame']
    out['counted'] = counts.to_numpy()
    out['step'] = np.where(out['counted'], j['step'].to_numpy(), 0)
    out['speed_mm_s'] = np.where(out['counted'], np.abs(speed.to_numpy()) * out['fps'] * out['mm_per_pixel'], np.nan)
    return out


def main() -> int:
    loops_ = checks.blind_loops()
    t = pd.read_csv(os.path.join(checks.out_dir(), 'measurements.csv'))
    rest = t[t['window'] == 'rest']
    wanted = aims.aim1_recordings()
    rows, pairs_all, loops_all = [], [], []
    for label, floor in [('protocol', None)] + [(f'rule from {f:g} px/frame', f) for f in rule.FLOORS]:
        counted = rule_loops(loops_, rest, floor)
        recordings = aims.per_recording(counted)
        pairs = aims.aim1_pairs(recordings, wanted)
        steps = counted.set_index(['recording', 'dataset'])['step']
        for visit in ('active', 'control'):
            pairs[f'{visit}_step'] = [steps.get((r, d), 0) if d else 0 for r, d in
                                      zip(pairs[f'{visit}_recording'], pairs[f'{visit}_from'])]
        for study, stats_ in report.aim1_table(pairs).items():
            rows.append({'analysis': label, 'study': study,
                         'loops_counted': int(counted['counted'].sum()),
                         'loops_by_step2': int((counted['step'] == 2).sum()),
                         'recordings_with_value': int(np.isfinite(recordings['value_mm_s']).sum()), **stats_})
        pairs_all.append(pairs.assign(analysis=label))
        loops_all.append(counted.drop(columns='points').assign(analysis=label))
    table = pd.DataFrame(rows)
    table.to_csv(os.path.join(HERE, 'aim1.csv'), index=False)
    pd.concat(pairs_all).to_csv(os.path.join(checks.out_dir(), 'pairs.csv'), index=False)
    pd.concat(loops_all).to_csv(os.path.join(checks.out_dir(), 'loops.csv'), index=False)

    pd.set_option('display.width', 250)
    columns = ['analysis', 'study', 'loops_counted', 'loops_by_step2', 'recordings_with_value', 'participants',
               'grand_mean_mm_s', 'typical_error_mm_s', 'cv_percent', 'cv_ci_low', 'cv_ci_high', 'cv_log_percent',
               'sdc_mm_s', 'ba_bias', 'ba_loa_low', 'ba_loa_high', 'icc_a1', 'icc_a1_ci_low', 'icc_a1_ci_high']
    print(table[columns].round(3).to_string(index=False))
    main_loops = loops_all[1]
    by_step = main_loops[main_loops['counted']].groupby('step')['speed_mm_s']
    print('\nCounted loops by step (from 5 px/frame), mm/s:')
    print(by_step.describe().round(3).to_string())
    return 0


if __name__ == '__main__':
    sys.exit(main())
