"""Whole loops against their arterial and venous limbs on the recordings, and the arterial limb's yield (2026-11-03)

python analysis/whole_loop_limbs/real_limbs.py

Reads the aim-1 check's rerun on the re-stabilized videos (16 before-exposure ESMOKE recordings of 8
participants, lines placed by Claude Code before anything was measured; not the study's blind lines):
`../aim1_feasibility/restabilized/results.csv` (every limb and every whole loop) and
`../whole_loop/loops.csv` (each whole loop with its limbs' best speeds and scores).

1. Which speed a whole loop reports. In loops where each limb has its own best speed (score 5 or more,
   resolved or not) and the limbs run opposite ways, as flow must, the whole loop's speed is set
   against the arterial limb's, the venous limb's and their mean.
2. Why the arterial limb resolves less often. In loops whose whole-loop line was counted, so that its
   direction names the arterial limb, the two limbs of each loop are compared: how prominent the
   vessel is on the resting image (`on_ridge`, the band-passed image along the line, 0-1), the
   pattern shift's score, the speed, the line's length, and whether each resolved on its own. Sign
   tests, two-sided.

Writes real_limbs.csv (one row per loop of part 2) and prints both parts.
"""
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RESULTS = os.path.join(REPO, 'analysis', 'aim1_feasibility', 'restabilized', 'results.csv')
LOOPS = os.path.join(REPO, 'analysis', 'whole_loop', 'loops.csv')
OUT = os.path.join(HERE, 'real_limbs.csv')
#: A limb's best speed is used in part 1 from this score up (resolved or not).
MIN_LIMB_SNR = 5.0
#: In part 1, an arterial limb this many times as fast as the venous one counts as clearly faster.
CLEARLY_FASTER = 1.2


def sign_test(k: int, n: int) -> float:
    """Two-sided p of k of n pairs going one way when either way is equally likely."""
    tail = sum(math.comb(n, i) for i in range(max(k, n - k), n + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def whole_against_limbs(loops: pd.DataFrame) -> pd.DataFrame:
    """Part 1: counted whole loops whose two limbs both have a best speed scoring MIN_LIMB_SNR and run opposite ways."""
    rows = []
    for loop in loops.itertuples(index=False):
        counted = np.isfinite(loop.whole_resolved_mm_s) and not loop.contradicted_resolved
        if not counted or not isinstance(loop.limb_speeds_px_per_frame, str):
            continue
        speeds = [float(v) for v in loop.limb_speeds_px_per_frame.split(';')]
        snrs = [float(v) for v in loop.limb_snrs.split(';')]
        # limbs are traced from base to apex: towards the apex (positive) is the arterial limb
        if not all(np.isfinite(speeds)) or min(snrs) < MIN_LIMB_SNR or np.sign(speeds[0]) == np.sign(speeds[1]):
            continue
        arterial, venous = (0, 1) if speeds[0] > 0 else (1, 0)
        rows.append({'recording': loop.recording, 'loop': loop.loop, 'whole': abs(loop.speed_px_per_frame),
                     'arterial': abs(speeds[arterial]), 'venous': abs(speeds[venous]),
                     'arterial_snr': snrs[arterial], 'venous_snr': snrs[venous]})
    return pd.DataFrame(rows)


def limb_pairs(results: pd.DataFrame) -> pd.DataFrame:
    """Part 2: per counted whole loop (the movement rule applied), its arterial and venous limb side by side."""
    limbs = results[results['kind'] == 'limb'].set_index(['recording', 'line'])
    loops = results[(results['kind'] == 'loop') & results['pattern_shift_resolved'].astype(bool)]
    by_loop = pd.read_csv(LOOPS).set_index(['recording', 'loop'])
    rows = []
    for loop in loops.itertuples(index=False):
        if by_loop.loc[(loop.recording, loop.loop), 'contradicted_resolved']:
            continue                                     # its limbs ran the same way: the picture moved
        arterial_name = loop.arterial_limb
        venous_name = loop.second_limb if arterial_name == loop.first_limb else loop.first_limb
        a, v = limbs.loc[(loop.recording, arterial_name)], limbs.loc[(loop.recording, venous_name)]
        rows.append({'recording': loop.recording, 'loop': loop.loop, 'whole_snr': loop.pattern_shift_snr,
                     'arterial_length_px': a.length_px, 'venous_length_px': v.length_px,
                     'arterial_on_ridge': a.on_ridge, 'venous_on_ridge': v.on_ridge,
                     'arterial_snr': a.pattern_shift_snr, 'venous_snr': v.pattern_shift_snr,
                     'arterial_speed': abs(a.pattern_shift_speed_px_per_frame),
                     'venous_speed': abs(v.pattern_shift_speed_px_per_frame),
                     'arterial_points_right_way': a.pattern_shift_speed_px_per_frame > 0,
                     'venous_points_right_way': v.pattern_shift_speed_px_per_frame < 0,
                     'arterial_resolved': bool(a.pattern_shift_resolved),
                     'venous_resolved': bool(v.pattern_shift_resolved)})
    return pd.DataFrame(rows)


def main() -> int:
    results = pd.read_csv(RESULTS)
    part1 = whole_against_limbs(pd.read_csv(LOOPS))
    nearer = (part1.whole - part1.venous).abs() < (part1.whole - part1.arterial).abs()
    faster = part1[part1.arterial / part1.venous >= CLEARLY_FASTER]
    print(f'1. Counted whole loops with both limbs estimated (score {MIN_LIMB_SNR:g} or more) and running opposite '
          f'ways: {len(part1)}')
    print(f'   whole loop nearer the venous limb in {int(nearer.sum())}; arterial / venous speed median '
          f'{np.median(part1.arterial / part1.venous):.2f} ({(part1.arterial / part1.venous).min():.2f}-'
          f'{(part1.arterial / part1.venous).max():.2f}); whole / mean of limbs median '
          f'{np.median(part1.whole / ((part1.arterial + part1.venous) / 2)):.2f}')
    print(f'   arterial limb at least {CLEARLY_FASTER:g} x the venous: {len(faster)} loops; the whole loop read '
          f'{100 * ((faster.whole / faster.venous).min() - 1):.1f}-{100 * ((faster.whole / faster.venous).max() - 1):.1f}% '
          f'above the venous limb and {100 * (1 - (faster.whole / faster.arterial).max()):.0f}-'
          f'{100 * (1 - (faster.whole / faster.arterial).min()):.0f}% below the arterial')

    part2 = limb_pairs(results)
    part2.to_csv(OUT, index=False, float_format='%.6g')
    n = len(part2)
    print(f'\n2. Counted whole loops, the arterial limb against the venous limb of the same loop: {n}')
    for name, column in (('fainter on the resting image', 'on_ridge'), ('scored lower', 'snr'),
                         ('shorter line', 'length_px')):
        k = int((part2[f'arterial_{column}'] < part2[f'venous_{column}']).sum())
        print(f'   arterial {name} in {k} of {n} (sign test p = {sign_test(k, n):.3f}); medians '
              f'{part2[f"arterial_{column}"].median():.2f} against {part2[f"venous_{column}"].median():.2f}')
    right = part2[part2.arterial_points_right_way & part2.venous_points_right_way]
    k = int((right.arterial_speed > right.venous_speed).sum())
    print(f'   both limbs pointing the way flow runs: {len(right)}; arterial faster in {k} '
          f'(p = {sign_test(k, len(right)):.3f}), '
          f'speed ratio median {np.median(right.arterial_speed / right.venous_speed):.2f}')
    print(f'   whole-loop score / arterial limb score: median {np.median(part2.whole_snr / part2.arterial_snr):.1f} '
          f'(quartiles {np.percentile(part2.whole_snr / part2.arterial_snr, 25):.1f}-'
          f'{np.percentile(part2.whole_snr / part2.arterial_snr, 75):.1f})')
    print(f'   resolved on their own: arterial {int(part2.arterial_resolved.sum())}, venous '
          f'{int(part2.venous_resolved.sum())}; arterial limbs scoring 5 to under 8: '
          f'{int(((part2.arterial_snr >= 5) & (part2.arterial_snr < 8)).sum())}')

    limbs = results[(results['kind'] == 'limb') & results['pattern_shift_resolved'].astype(bool)]
    counts = limbs['limb_check'].value_counts()
    arterial_recordings = set(limbs.loc[limbs['limb_check'] == 'arterial', 'recording'])
    loop_recordings = set(results.loc[(results['kind'] == 'loop') & results['pattern_shift_resolved'].astype(bool),
                                      'recording'])
    by_subject = results.groupby('subject')['recording'].unique()
    both = [s for s, names in by_subject.items() if len(names) == 2 and all(r in arterial_recordings for r in names)]
    print(f'\n   all {int((results["kind"] == "limb").sum())} limbs: resolved {len(limbs)} (arterial '
          f'{int(counts.get("arterial", 0))}, venous {int(counts.get("venous", 0))}); recordings with an arterial limb '
          f'resolved {len(arterial_recordings)} of {results["recording"].nunique()}, with a whole loop resolved '
          f'{len(loop_recordings)}; an arterial limb at both visits: {", ".join(both) or "none"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
