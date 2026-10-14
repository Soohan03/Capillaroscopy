"""Pattern shift below 1 px/frame, on synthetic recordings with a known speed.

python analysis/pattern_shift_slow_flow/validate_synthetic.py [--summary]     (about 2 minutes on 14 cores)

Simulated loop (capillary.simulate), the arterial limb's 120-px line drawn as a person would click it,
60-s clips (the official rest is 52-77 s). Conditions as in ../pattern_shift_bandpass/: the disturbances as
measured, strong, and faint (a third of the cells' contrast), the shutter open for the whole frame interval.
No flow: 30 clips per condition. Each clip is measured with every variant of VARIANTS (see there). For the
clips without flow the best score in each speed band is kept as well, to see where noise scores highest.
Writes synthetic_results.csv and null_bands.csv and prints the summary tables.
"""
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)

#: How each variant measures. 'package' calls capillary.pattern_shift.pattern_shift with the arguments given;
#: 'all lags' is the first design tried and set aside (`all_lags_estimate`).
VARIANTS = {
    # the method before: frame distances 1-8, speeds from 1 px/frame
    'before': ('package', dict(min_speed=1.0)),
    # the search simply continued below 1 px/frame, frame distances 1-8
    'floor only': ('all lags', dict(longest_lag=8)),
    # every frame distance over which the pattern moves 2-8 px, scored by their sum
    'all lags': ('all lags', dict(longest_lag=89)),
    # the same, the speed chosen by the frame distances' mean contrast below 1 px/frame
    'all lags, mean': ('all lags', dict(longest_lag=89, by_mean=True)),
    # the time axis stretched: term j compares rows j / speed frames apart, where the pattern moved j px; the speed
    # found refined with those frame distances held fixed. Rows compared beyond 8 frames centred, or not
    'stretched, uncentred': ('package', dict(min_speed=0.1, centred=False)),
    'stretched': ('package', dict(min_speed=0.1)),
    'stretched, 6-s blocks': ('package', dict(min_speed=0.1, block_frames=180)),
}
SPEEDS = (0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0)
CONDITIONS = ('as measured', 'strong', 'faint')
BANDS = ((0.1, 0.2), (0.2, 0.3), (0.3, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, np.inf))
FRAMES, NULL_SEEDS, SEEDS = 1800, 30, 4
MIN_SPEED, MAX_LAG = 0.1, 8


def condition(name):
    from capillary import simulate
    if name == 'strong':
        return simulate.Disturbances.strong(), 20.0
    return simulate.Disturbances(), (20.0 / 3 if name == 'faint' else 20.0)


def _all_lags_statistic(sums, lags, max_shift, speeds, by_mean):
    """The design set aside: below 1 px/frame every frame distance k up to MAX_LAG / speed (fading out over one
    frame) counts at k x speed px, as frame distances 1-8 do from 1 px/frame. Returns the score of every speed,
    and what chooses the speed: the score, or with `by_mean` below 1 px/frame the weighted mean of the frame
    distances' contrasts (scaled to equal the score at 1 px/frame)."""
    from scipy.interpolate import CubicSpline
    from capillary import pattern_shift as ps
    z = ps._contrasts(sums, max_shift)
    d = np.arange(max_shift + 1)
    speed, sign = np.abs(speeds), np.sign(speeds)
    total, squares, weights = np.zeros(speeds.size), np.zeros(speeds.size), np.zeros(speeds.size)
    for i, k in enumerate(lags):
        if not np.all(np.isfinite(z[i])):
            continue
        span = np.clip(MAX_LAG / np.minimum(speed, 1.0) + 1.0 - k, 0.0, 1.0)
        w = ps._lag_weight(k * speed, max_shift) * span
        used = w > 0
        total[used] += w[used] * sign[used] * CubicSpline(d, z[i])(k * speed[used])
        squares[used] += w[used] ** 2
        weights[used] += w[used]
    with np.errstate(invalid='ignore', divide='ignore'):
        score = np.where(squares > 0, total / np.sqrt(squares), np.nan)
        if not by_mean:
            return score, score
        one = np.isclose(speed, 1.0) & (squares > 0)
        scale = float(np.median(weights[one] / np.sqrt(squares[one])))
        return score, np.where(speed < 1.0 - 1e-9, scale * total / weights, score)


def all_lags_estimate(diagram, longest_lag, by_mean=False, block_frames=90):
    """`pattern_shift` with the design set aside (`_all_lags_statistic`), searched from MIN_SPEED."""
    from capillary import pattern_shift as ps
    n_blocks = diagram.shape[0] // block_frames
    max_shift = (diagram.shape[1] - 1) // 2
    lags = np.arange(1, min(max(MAX_LAG, min(longest_lag, int(np.ceil(MAX_LAG / MIN_SPEED)))), block_frames - 1) + 1)
    per_block = np.stack([ps._block_sums(diagram[j * block_frames:(j + 1) * block_frames], lags, max_shift)
                          for j in range(n_blocks)])
    speeds = ps._speed_grid(MIN_SPEED, max_shift)

    def best(sums):
        score, statistic = _all_lags_statistic(sums, lags, max_shift, speeds, by_mean)
        speed, _, in_range = ps._best(statistic, speeds)
        return speed, float(score[int(np.nanargmax(statistic))]), in_range

    pooled = per_block.sum(axis=0)
    speed, snr, in_range = best(pooled)
    ci = (float('nan'), float('nan'))
    if n_blocks >= 3 and np.isfinite(speed):
        others = np.array([best(pooled - per_block[j])[0] for j in range(n_blocks)])
        if np.all(np.isfinite(others)):
            se = np.sqrt((n_blocks - 1) / n_blocks * np.sum((others - others.mean()) ** 2))
            ci = (speed - 1.96 * se, speed + 1.96 * se)
    return ps.ShiftEstimate(speed, snr, ci, n_blocks, in_range)


def estimate(diagram, variant):
    from capillary.pattern_shift import pattern_shift
    kind, kwargs = VARIANTS[variant]
    return pattern_shift(diagram, **kwargs) if kind == 'package' else all_lags_estimate(diagram, **kwargs)


def score_curve(diagram, variant):
    """The pooled score of every speed, as the variant computes it before choosing the best."""
    from capillary import pattern_shift as ps
    kind, kwargs = VARIANTS[variant]
    block_frames = kwargs.get('block_frames', 90)
    max_shift = (diagram.shape[1] - 1) // 2
    min_speed = kwargs.get('min_speed', MIN_SPEED)
    if kind == 'package':
        longest = MAX_LAG if min_speed >= 1.0 else int(np.ceil(MAX_LAG / min_speed)) + 1
    else:
        longest = max(MAX_LAG, min(kwargs['longest_lag'], int(np.ceil(MAX_LAG / min_speed))))
    lags = np.arange(1, min(longest, block_frames - 1) + 1)
    centre_beyond = MAX_LAG if kind == 'package' and kwargs.get('centred', True) else None
    pooled = sum(ps._block_sums(diagram[j * block_frames:(j + 1) * block_frames], lags, max_shift,
                                centre_beyond=centre_beyond)
                 for j in range(diagram.shape[0] // block_frames))
    speeds = ps._speed_grid(min_speed, max_shift)
    if kind == 'package':
        return speeds, ps._speed_scores(pooled, lags, max_shift, speeds)
    return speeds, _all_lags_statistic(pooled, lags, max_shift, speeds, kwargs.get('by_mean', False))[0]


def case(job):
    name, speed, seed = job
    import cv2
    cv2.setNumThreads(1)
    from capillary import simulate
    from capillary.spacetime import space_time_diagram
    disturbances, contrast = condition(name)
    recording = simulate.simulate(simulate.hairpin(), FRAMES, speed, seed=2000 + 100 * seed + int(100 * speed),
                                  contrast=contrast, disturbances=disturbances)
    diagram = space_time_diagram(recording.frames, recording.drawn_line(20.0, 140.0, seed=seed))
    rows, bands = [], []
    for variant in VARIANTS:
        started = time.perf_counter()
        e = estimate(diagram, variant)
        rows.append({'condition': name, 'speed': speed, 'seed': seed, 'variant': variant,
                     'estimate': e.speed_px_per_frame, 'snr': e.snr, 'ci_low': e.ci95[0], 'ci_high': e.ci95[1],
                     'in_range': e.in_range, 'resolved': e.resolved, 'seconds': time.perf_counter() - started})
        if speed == 0:
            speeds, scores = score_curve(diagram, variant)
            for lo, hi in BANDS:
                inside = (np.abs(speeds) >= lo) & (np.abs(speeds) < hi)
                if inside.any():
                    bands.append({'condition': name, 'seed': seed, 'variant': variant, 'band': f'{lo:g}-{hi:g}',
                                  'max_score': float(np.nanmax(scores[inside]))})
    return rows, bands


def summarize(table, bands):
    pd.set_option('display.width', 250)
    pd.set_option('display.max_columns', 40)
    pd.set_option('display.max_rows', 400)
    order = [v for v in VARIANTS if v in set(table.variant)]
    null = table[table.speed == 0]
    print(f'\nNo flow ({NULL_SEEDS} clips per condition): highest signal-to-noise of the estimate, and how many were '
          f'resolved')
    print(null.groupby(['variant', 'condition']).agg(max_snr=('snr', 'max'), resolved=('resolved', 'sum'))
          .unstack('condition').reindex(order).round(1).to_string())
    if bands is not None and len(bands):
        print('\nNo flow: highest score in each speed band (px/frame), all conditions')
        grid = bands.groupby(['variant', 'band']).max_score.max().unstack('band')
        print(grid.reindex(order)[[f'{lo:g}-{hi:g}' for lo, hi in BANDS]].round(1).to_string())
    flow = table[table.speed > 0].copy()
    flow['error_pct'] = 100 * (flow.estimate / flow.speed - 1)
    flow['covered'] = (flow.ci_low <= flow.speed) & (flow.speed <= flow.ci_high)
    print(f'\nResolved (of {SEEDS}) / median error % / lowest signal-to-noise, per speed (px/frame)')
    for cname in CONDITIONS:
        sub = flow[flow.condition == cname]
        print(f'  {cname}')
        grid = sub.groupby(['variant', 'speed']).agg(resolved=('resolved', 'sum'), error=('error_pct', 'median'),
                                                     snr=('snr', 'min'))
        cells = grid.apply(lambda r: f"{int(r.resolved)} {r.error:+.1f} {r.snr:.0f}", axis=1).unstack('speed')
        print(cells.reindex(order).to_string())
    resolved = flow[flow.resolved]
    for label, part in (('below 1 px/frame', resolved[resolved.speed < 1.0]),
                        ('from 1 px/frame', resolved[resolved.speed >= 1.0])):
        print(f'\nResolved estimates {label}: median and worst |error| %, truth inside the 95% interval')
        print(part.groupby('variant').agg(median_abs_error=('error_pct', lambda s: s.abs().median()),
                                          worst_abs_error=('error_pct', lambda s: s.abs().max()),
                                          covered=('covered', 'mean'), n=('covered', 'size'))
              .reindex(order).round(2).to_string())
    print('\nSeconds per estimate (median)')
    print(table.groupby('variant').seconds.median().reindex(order).round(2).to_string())


def main():
    jobs = [(c, 0.0, s) for c in CONDITIONS for s in range(NULL_SEEDS)]
    jobs += [(c, v, s) for c in CONDITIONS for v in SPEEDS for s in range(SEEDS)]
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=14) as pool:
        results = list(pool.map(case, jobs))
    table = pd.DataFrame([row for rows, _ in results for row in rows])
    bands = pd.DataFrame([band for _, bands in results for band in bands])
    table.to_csv(os.path.join(HERE, 'synthetic_results.csv'), index=False)
    bands.to_csv(os.path.join(HERE, 'null_bands.csv'), index=False)
    print(f'{len(jobs)} clips in {time.perf_counter() - started:.0f} s')
    summarize(table, bands)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--summary':
        summarize(pd.read_csv(os.path.join(HERE, 'synthetic_results.csv')),
                  pd.read_csv(os.path.join(HERE, 'null_bands.csv')))
    else:
        main()
