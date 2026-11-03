"""What a whole-loop line reports when the loop's two limbs move at different speeds (2026-11-03)

python analysis/whole_loop_limbs/two_speeds.py [--summary]     (about a minute; --summary from the saved CSV)

`capillary.simulate` moves its cells at one speed all round the loop, so the whole-loop line had only
been tested where both limbs move alike. In a real loop the venous limb is usually wider and slower.
Here the space-time diagram of a whole-loop line is built directly: the arterial limb (positions 0..La
along the line) at va px/frame, the venous limb (La..La+Lv) at vv. Two models of the venous pattern:

- `compressed`: the cells keep their order round the loop, so the venous limb shows the arterial
  pattern compressed by vv / va (the same red-cell flux in both limbs). Each position s sees the
  pattern delayed by its transit time tau(s).
- `independent`: the venous limb shows a pattern of its own with the same statistics, moving at vv
  (the cells rearranged at the apex).

On top, roughly as in `capillary.simulate`:
- motion blur over the whole frame interval (`blur` 1), or none (`blur` 0);
- optical blur of 1.2 px along the line;
- a darkening of the whole line at the same moment (OU, tau 8 frames, plus 1.1 Hz), uneven along it;
- jitter along the line (OU, tau 4 frames, SD 0.3 px);
- white noise of SD `noise` grey levels.

Every clip is 60 s at 30 fps, as long as the official rest. It is measured as the app measures a whole
loop: the pattern shift of the whole line, and of each half split at the apex (as
`pattern_shift.loop_limbs` splits it).

Writes two_speeds.csv: one row per clip, with its conditions, the whole loop's speed and score, and
each limb's. --summary prints, per condition, the range of what the whole loop read against the
limbs' true speeds and their mean.
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
from capillary import pattern_shift  # noqa: E402
from capillary.simulate import _ou, _red_cells, _smooth_noise  # noqa: E402

OUT = os.path.join(HERE, 'two_speeds.csv')
FRAMES = 1800
SEEDS = (0, 1, 2)
#: The arterial limb's speed (px/frame, 0.12 mm/s at 30 fps and 1.329 um/px) and the venous limb's, as a
#: share of it. At half speed the venous limb moves 1.5 px/frame, inside the searched range.
ARTERIAL_SPEED = 3.0
RATIOS = (1.0, 0.75, 0.5)
#: Limb lengths along the line (arterial, venous), px. 80 + 80 is about the median whole loop (159 px).
LENGTHS = ((80, 80), (60, 100), (100, 60), (120, 40))
CONTRAST = 20.0
#: The same-moment darkening relative to the vessel's contrast, as `simulate.Disturbances` measured it.
SAME_MOMENT_SD = 0.38


def _pattern(rng, u: np.ndarray, blur: float) -> np.ndarray:
    """The cell pattern at pattern positions `u`, averaged over `blur` px of it (motion blur; none below 0.25)."""
    step = 0.25
    lo, hi = u.min() - blur - 5.0, u.max() + 5.0
    cells = _red_cells(rng, hi - lo, step)
    if blur < step:
        return np.interp(u, lo + np.arange(cells.size) * step, cells)
    cumulative = np.concatenate([[0.0], np.cumsum(cells) * step])
    edges = lo + np.arange(cumulative.size) * step
    return (np.interp(u, edges, cumulative) - np.interp(u - blur, edges, cumulative)) / blur


def diagram(arterial_px: int, venous_px: int, va: float, vv: float, model: str = 'compressed', blur: float = 1.0,
            noise: float = 6.0, venous_contrast: float = CONTRAST, seed: int = 0) -> np.ndarray:
    """The space-time diagram (frames x positions, float32) of a whole-loop line whose limbs move at va and vv."""
    rng = np.random.default_rng(seed)
    s = np.arange(0, arterial_px + venous_px + 1, 1.0)
    jitter = _ou(rng, FRAMES, 4.0, 0.3)
    t = np.arange(FRAMES, dtype=float)[:, None]
    seen = s[None, :] + jitter[:, None]                     # where each sample looks, with the picture's jitter
    if model == 'compressed':
        transit = np.where(seen <= arterial_px, seen / va, arterial_px / va + (seen - arterial_px) / vv)
        occupancy = _pattern(rng, va * (t - transit), blur * va)
    elif model == 'independent':
        arterial = _pattern(rng, va * t - seen, blur * va)
        venous = _pattern(rng, vv * t - (seen - arterial_px), blur * vv)
        occupancy = np.where(seen <= arterial_px, arterial, venous)
    else:
        raise ValueError(f'unknown model {model!r}')
    occupancy = gaussian_filter1d(occupancy, 1.2, axis=1, mode='nearest')
    same = (_ou(rng, FRAMES, 8.0, 0.8 * SAME_MOMENT_SD)
            + 0.6 * SAME_MOMENT_SD * np.sin(2 * np.pi * 1.1 * np.arange(FRAMES) / 30.0 + rng.uniform(0, 6.3)))
    uneven = 1 + 0.15 * _smooth_noise(rng, s.size, 15.0)
    strength = np.where(s <= arterial_px, CONTRAST, venous_contrast)
    dark = strength[None, :] * occupancy * (1 + same[:, None] * uneven[None, :])
    return (110.0 - dark + rng.normal(0, noise, dark.shape)).astype(np.float32)


def conditions() -> list:
    """Every clip: the limb lengths, speeds, model, blur, noise and venous contrast, times the seeds.

    All four length splits at noise 6 with motion blur; for 80 + 80 also noise 1.3 and 10, no motion blur,
    and a darker (wider) venous limb.
    """
    out = []
    for ratio in RATIOS:
        for model in ('compressed', 'independent'):
            for lengths in LENGTHS:
                out.append(dict(test='lengths', lengths=lengths, ratio=ratio, model=model, blur=1.0, noise=6.0,
                                venous_contrast=CONTRAST))
            for noise in (1.3, 10.0):
                out.append(dict(test='noise', lengths=(80, 80), ratio=ratio, model=model, blur=1.0, noise=noise,
                                venous_contrast=CONTRAST))
            out.append(dict(test='no motion blur', lengths=(80, 80), ratio=ratio, model=model, blur=0.0, noise=6.0,
                            venous_contrast=CONTRAST))
            out.append(dict(test='darker venous limb', lengths=(80, 80), ratio=ratio, model=model, blur=1.0,
                            noise=6.0, venous_contrast=1.5 * CONTRAST))
    return [dict(c, seed=seed) for c in out for seed in SEEDS]


def measure(condition: dict) -> dict:
    """One clip: the whole loop's pattern shift and each limb's, with the limbs' true speeds and their averages."""
    arterial_px, venous_px = condition['lengths']
    va = ARTERIAL_SPEED
    vv = va * condition['ratio']
    d = diagram(arterial_px, venous_px, va, vv, condition['model'], condition['blur'], condition['noise'],
                condition['venous_contrast'], condition['seed'])
    whole = pattern_shift.pattern_shift(d)
    arterial = pattern_shift.pattern_shift(d[:, :arterial_px + 1])
    venous = pattern_shift.pattern_shift(d[:, arterial_px:])
    length = arterial_px + venous_px
    return {'test': condition['test'], 'arterial_px': arterial_px, 'venous_px': venous_px, 'model': condition['model'],
            'motion_blur': condition['blur'], 'noise': condition['noise'],
            'venous_contrast': condition['venous_contrast'], 'seed': condition['seed'],
            'arterial_true': va, 'venous_true': vv, 'mean_of_limbs': (va + vv) / 2,
            'transit_mean': length / (arterial_px / va + venous_px / vv),
            'whole_speed': abs(whole.speed_px_per_frame), 'whole_snr': whole.snr, 'whole_resolved': whole.resolved,
            'arterial_speed': abs(arterial.speed_px_per_frame), 'arterial_snr': arterial.snr,
            'venous_speed': abs(venous.speed_px_per_frame), 'venous_snr': venous.snr}


def summary(table: pd.DataFrame) -> str:
    """Per condition (seeds and, where both ran, models and noise levels together): what the whole loop read."""
    lines = ['whole loop against its limbs (px/frame; arterial limb at 3.0)', '']
    groups = [('equal lengths 80 + 80, both models, noise 1.3 / 6 / 10',
               (table.arterial_px == 80) & (table.venous_px == 80) & (table.motion_blur == 1)
               & (table.venous_contrast == CONTRAST))]
    groups += [(f'arterial {a} + venous {v} px, both models, noise 6',
                (table.arterial_px == a) & (table.venous_px == v) & (table.noise == 6) & (table.motion_blur == 1)
                & (table.venous_contrast == CONTRAST)) for a, v in LENGTHS if (a, v) != (80, 80)]
    groups += [('80 + 80 without motion blur, both models', table.test == 'no motion blur'),
               ('80 + 80, venous limb 1.5 times as dark, both models', table.test == 'darker venous limb')]
    for title, mask in groups:
        lines.append(title)
        for ratio, part in table[mask].groupby(table.venous_true / table.arterial_true, sort=False):
            lines.append(f'  venous at {ratio:.2f} x arterial ({part.venous_true.iloc[0]:.2f}): whole loop '
                         f'{part.whole_speed.min():.2f}-{part.whole_speed.max():.2f} (mean of limbs '
                         f'{part.mean_of_limbs.iloc[0]:.2f}; {len(part)} clips, {int(part.whole_resolved.sum())} resolved)')
        lines.append('')
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--summary', action='store_true', help='print the summary of the saved two_speeds.csv')
    args = parser.parse_args()
    if not args.summary:
        rows = []
        for number, condition in enumerate(conditions(), 1):
            rows.append(measure(condition))
            if number % 24 == 0:
                print(f'{number} clips', flush=True)
        pd.DataFrame(rows).to_csv(OUT, index=False, float_format='%.6g')
    print(summary(pd.read_csv(OUT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
