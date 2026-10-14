"""The same lines on the old and the re-stabilized videos: what changed, line by line.

python analysis/aim1_feasibility/restabilized/compare_runs.py

The first run (../results.csv, on the videos as stabilized on 2026-10-11/12) against this one (results.csv,
the lines moved onto the re-stabilized videos by move_lines.py). The slow range of the first run is the
`stretched` variant of the slow-range validation (../../pattern_shift_slow_flow/real_results.csv, window
rest), which is `pattern_shift(min_speed=SLOW_MIN_SPEED)` on the first run's diagrams, as measure.py now
measures it. For each level (summarize.py): the lines counted in both runs, in one only, and how far the
velocities of lines counted in both agree. Per recording: limbs counted at each level in each run, with the
stabilizer's median match at rest before and after (moves.csv).

Writes compare_runs.csv (one row per line in both runs) and prints the tables.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common  # noqa: E402
from summarize import LEVELS, SLOW, mark_levels  # noqa: E402

SLOW_VALIDATION = os.path.join(common.REPO, 'analysis', 'pattern_shift_slow_flow', 'real_results.csv')
KEY = ['recording', 'line']


def first_run() -> pd.DataFrame:
    """The first run's results with its slow range (from the slow-range validation), marked at every level."""
    results = pd.read_csv(os.path.join(common.HERE, 'results.csv'))
    slow = pd.read_csv(SLOW_VALIDATION)
    slow = slow[(slow['variant'] == 'stretched') & (slow['window'] == 'rest')].set_index(KEY)
    fps = 30.0
    joined = results.set_index(KEY)
    to_mm_s = fps * common.MM_PER_PIXEL
    joined['slow_pattern_shift_resolved'] = slow['resolved'].astype(bool)
    joined['slow_pattern_shift_speed_px_per_frame'] = slow['speed']
    joined['slow_pattern_shift_snr'] = slow['snr']
    joined['slow_pattern_shift_velocity_mm_s'] = (slow['speed'] * to_mm_s).where(slow['resolved'].astype(bool))
    if joined['slow_pattern_shift_resolved'].isna().any():
        raise ValueError('lines of the first run missing from the slow-range validation')
    return mark_levels(joined.reset_index())


def main() -> None:
    old = first_run()
    new = mark_levels(pd.read_csv(os.path.join(HERE, 'results.csv')))
    levels = LEVELS + (SLOW,)
    columns = ['kind', 'length_px', 'on_ridge', 'pattern_shift_snr', 'slow_pattern_shift_snr'] + \
        [f'{level}_mm_s' for level in levels]
    both = old.set_index(KEY)[columns].join(new.set_index(KEY)[columns], lsuffix='_old', rsuffix='_new', how='inner')
    both = both.reset_index()
    both.to_csv(os.path.join(HERE, 'compare_runs.csv'), index=False)
    limbs = both[both['kind_old'] == 'limb']
    tissue = both[both['kind_old'] == 'tissue']
    print(f'{len(both)} lines in both runs ({len(limbs)} limbs, {len(tissue)} through tissue); '
          f'{len(new) - len(both)} new lines (FP01_W)\n')

    rows = []
    for level in levels:
        a, b = limbs[f'{level}_mm_s_old'], limbs[f'{level}_mm_s_new']
        counted = a.notna() & b.notna()
        ratio = (b / a)[counted]
        rows.append({'level': level, 'first run': int(a.notna().sum()), 'rerun': int(b.notna().sum()),
                     'both': int(counted.sum()), 'first only': int((a.notna() & b.isna()).sum()),
                     'rerun only': int((a.isna() & b.notna()).sum()),
                     'same direction': int((np.sign(a) == np.sign(b))[counted].sum()),
                     'ratio median': ratio.median(), 'ratio min': ratio.min(), 'ratio max': ratio.max(),
                     'largest difference (mm/s)': (b - a)[counted].abs().max()})
    pd.set_option('display.width', 220)
    pd.set_option('display.max_columns', 30)
    print('Limbs counted at each level, first run against rerun (velocities of limbs counted in both: rerun / first)')
    print(pd.DataFrame(rows).round(3).to_string(index=False))

    for score in ('pattern_shift_snr', 'slow_pattern_shift_snr'):
        change = limbs[f'{score}_new'] - limbs[f'{score}_old']
        print(f'\n{score}, rerun - first run, limbs: median {change.median():+.2f}, quartiles '
              f'{change.quantile(0.25):+.2f} to {change.quantile(0.75):+.2f}, range {change.min():+.2f} to '
              f'{change.max():+.2f}; tissue lines: highest {tissue[f"{score}_old"].max():.1f} -> '
              f'{tissue[f"{score}_new"].max():.1f}')

    print('\nLimbs that changed at the default rule (resolved) or the slow range:')
    changed = limbs[(limbs['resolved_mm_s_old'].notna() != limbs['resolved_mm_s_new'].notna())
                    | (limbs['slow_mm_s_old'].notna() != limbs['slow_mm_s_new'].notna())]
    shown = changed[['recording', 'line', 'pattern_shift_snr_old', 'pattern_shift_snr_new', 'resolved_mm_s_old',
                     'resolved_mm_s_new', 'slow_pattern_shift_snr_old', 'slow_pattern_shift_snr_new', 'slow_mm_s_old',
                     'slow_mm_s_new']].copy()
    shown['recording'] = shown['recording'].str.replace(r'_\d\d-\w{3}-\d{4}_.*$', '', regex=True)
    print(shown.round(3).to_string(index=False))

    moves = pd.read_csv(os.path.join(HERE, 'moves.csv')).set_index('recording')
    per = []
    for stem, part in limbs.groupby('recording', sort=False):
        row = {'recording': stem.split('_')[0] + '_' + stem.split('_')[1],
               'match at rest': f"{moves.loc[stem, 'old_rest_match']:.2f} -> {moves.loc[stem, 'new_rest_match']:.2f}",
               'limbs': len(part)}
        for level in levels:
            row[level] = f"{int(part[f'{level}_mm_s_old'].notna().sum())} -> {int(part[f'{level}_mm_s_new'].notna().sum())}"
        per.append(row)
    print('\nPer recording, limbs counted: first run -> rerun')
    print(pd.DataFrame(per).to_string(index=False))


if __name__ == '__main__':
    main()
