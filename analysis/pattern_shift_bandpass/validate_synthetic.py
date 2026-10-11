"""Pattern shift with differenced rows (before 2026-10-11) against band-passed rows, on synthetic recordings.

python analysis/pattern_shift_bandpass/validate_synthetic.py      (about 2 minutes on 14 cores)

Simulated loop (capillary.simulate), the arterial limb's 120-px line drawn as a person would click it, 30-s
clips. Conditions: the disturbances as measured, strong, and faint (a third of the cells' contrast); the
shutter open for the whole frame interval (exposure 1.0, the simulator's default) or for half of it at the
faster speeds. No flow: 30 clips per condition. Writes synthetic_results.csv and prints the summary tables.
"""
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)

FILTERS = {'difference': None, 'band 1-4': (1.0, 4.0), 'band 1-6': (1.0, 6.0), 'band 1-8': (1.0, 8.0),
           'band 1.5-6': (1.5, 6.0), 'band 2-8': (2.0, 8.0)}
SPEEDS = (0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0, 12.0, 16.0, 20.0, 25.0, 30.0)
HALF_EXPOSURE_SPEEDS = (8.0, 12.0, 16.0, 20.0, 25.0, 30.0)
NULL_SEEDS, SEEDS = 30, 3


def condition(name, exposure):
    from capillary import simulate
    if name == 'strong':
        return simulate.Disturbances(same_moment_sd=0.6, same_moment_unevenness=0.4, jitter_px=1.0,
                                     exposure=exposure), 20.0
    return simulate.Disturbances(exposure=exposure), (20.0 / 3 if name == 'faint' else 20.0)


def case(job):
    name, exposure, speed, seed = job
    import cv2
    cv2.setNumThreads(1)
    from capillary import simulate
    from capillary.pattern_shift import pattern_shift
    from capillary.spacetime import space_time_diagram
    disturbances, contrast = condition(name, exposure)
    recording = simulate.simulate(simulate.hairpin(), 900, speed, seed=1000 + 100 * seed + int(10 * speed),
                                  contrast=contrast, disturbances=disturbances)
    diagram = space_time_diagram(recording.frames, recording.drawn_line(20.0, 140.0, seed=seed))
    rows = []
    for filter_name, band in FILTERS.items():
        e = pattern_shift(diagram, bandpass_px=band)
        rows.append({'condition': name, 'exposure': exposure, 'speed': speed, 'seed': seed, 'filter': filter_name,
                     'estimate': e.speed_px_per_frame, 'snr': e.snr, 'ci_low': e.ci95[0], 'ci_high': e.ci95[1],
                     'in_range': e.in_range, 'resolved': e.resolved})
    return rows


def summarize(table):
    pd.set_option('display.width', 250)
    pd.set_option('display.max_columns', 40)
    pd.set_option('display.max_rows', 400)
    null = table[table.speed == 0]
    print('\nNo flow: highest signal-to-noise (30 clips per condition), and how many were resolved')
    print(null.groupby(['filter', 'condition']).agg(max_snr=('snr', 'max'), resolved=('resolved', 'sum'))
          .unstack('condition').round(1).to_string())
    flow = table[table.speed > 0].copy()
    flow['error_pct'] = 100 * (flow.estimate / flow.speed - 1)
    flow['covered'] = (flow.ci_low <= flow.speed) & (flow.speed <= flow.ci_high)
    for exposure in sorted(flow.exposure.unique(), reverse=True):
        part = flow[flow.exposure == exposure]
        print(f'\nShutter open {exposure:g} of the frame interval: resolved (of {SEEDS}) / median error % / '
              f'lowest signal-to-noise, per speed (px/frame)')
        for cname in ('as measured', 'strong', 'faint'):
            sub = part[part.condition == cname]
            if sub.empty:
                continue
            print(f'  {cname}')
            grid = sub.groupby(['filter', 'speed']).agg(
                resolved=('resolved', 'sum'), error=('error_pct', 'median'), snr=('snr', 'min'))
            cells = grid.apply(lambda r: f"{int(r.resolved)} {r.error:+.1f} {r.snr:.0f}", axis=1).unstack('speed')
            print(cells.reindex(FILTERS.keys()).to_string())
    resolved = flow[flow.resolved & (flow.exposure == 1.0)]
    print('\nResolved estimates (shutter 1.0): median and worst |error| %, and truth inside the 95% interval')
    print(resolved.groupby('filter').agg(median_abs_error=('error_pct', lambda s: s.abs().median()),
                                         worst_abs_error=('error_pct', lambda s: s.abs().max()),
                                         covered=('covered', 'mean'), n=('covered', 'size'))
          .reindex(FILTERS.keys()).round(2).to_string())


def main():
    jobs = [(c, 1.0, 0.0, s) for c in ('as measured', 'strong', 'faint') for s in range(NULL_SEEDS)]
    jobs += [(c, 1.0, v, s) for c in ('as measured', 'strong', 'faint') for v in SPEEDS for s in range(SEEDS)]
    jobs += [(c, 0.5, v, s) for c in ('as measured', 'faint') for v in HALF_EXPOSURE_SPEEDS for s in range(SEEDS)]
    started = time.time()
    with ProcessPoolExecutor(max_workers=14) as pool:
        rows = [row for rows in pool.map(case, jobs) for row in rows]
    table = pd.DataFrame(rows)
    table.to_csv(os.path.join(HERE, 'synthetic_results.csv'), index=False)
    print(f'{len(jobs)} clips in {time.time() - started:.0f} s')
    summarize(table)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--summary':
        summarize(pd.read_csv(os.path.join(HERE, 'synthetic_results.csv')))
    else:
        main()
