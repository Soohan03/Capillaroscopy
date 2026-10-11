"""Faster flow on a longer line: the arterial limb's 120-px line against a 300-px line round the loop.

python analysis/pattern_shift_bandpass/validate_long_line.py      (under a minute on 14 cores)

Synthetic loop (capillary.simulate) with the measured disturbances, the shutter open for the whole frame
interval (the simulator's worst case), 60-s clips (about the rest window), 3 seeds per speed and 8 without
flow. The pattern moves at one speed all round the simulated loop; in a real loop the venous limb is
slower. Pattern shift with differenced rows (before 2026-10-11) and band-passed rows. Writes
long_line_results.csv and prints the summary.
"""
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)

FILTERS = {'difference': None, 'band 1-4': (1.0, 4.0)}
LINES = {'limb 120 px': (20.0, 140.0), 'loop 300 px': (20.0, 320.0)}
SPEEDS = (12.0, 16.0, 20.0, 25.0, 30.0, 40.0)


def case(job):
    speed, seed = job
    import cv2
    cv2.setNumThreads(1)
    from capillary import simulate
    from capillary.pattern_shift import pattern_shift
    from capillary.spacetime import space_time_diagram
    recording = simulate.simulate(simulate.hairpin(), 1800, speed, seed=2000 + 100 * seed + int(speed))
    rows = []
    for line_name, (start, end) in LINES.items():
        diagram = space_time_diagram(recording.frames, recording.drawn_line(start, end, seed=seed))
        for filter_name, band in FILTERS.items():
            e = pattern_shift(diagram, bandpass_px=band)
            rows.append({'line': line_name, 'filter': filter_name, 'speed': speed, 'seed': seed,
                         'estimate': e.speed_px_per_frame, 'snr': e.snr, 'resolved': e.resolved})
    return rows


def summarize(t):
    pd.set_option('display.width', 200)
    print('\nNo flow: highest signal-to-noise (8 clips), and how many were resolved')
    print(t[t.speed == 0].groupby(['line', 'filter']).agg(max_snr=('snr', 'max'), resolved=('resolved', 'sum'))
          .round(1).to_string())
    flow = t[t.speed > 0].copy()
    flow['error_pct'] = 100 * (flow.estimate / flow.speed - 1)
    grid = flow.groupby(['line', 'filter', 'speed']).agg(resolved=('resolved', 'sum'), error=('error_pct', 'median'),
                                                         snr=('snr', 'min'))
    print('\nResolved (of 3) / median error % / lowest signal-to-noise, per speed (px/frame; 25 = 1.0 mm/s)')
    print(grid.apply(lambda r: f'{int(r.resolved)} {r.error:+.1f} {r.snr:.0f}', axis=1).unstack('speed').to_string())


def main():
    jobs = [(0.0, s) for s in range(8)] + [(v, s) for v in SPEEDS for s in range(3)]
    started = time.time()
    with ProcessPoolExecutor(max_workers=14) as pool:
        rows = [row for rows in pool.map(case, jobs) for row in rows]
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(HERE, 'long_line_results.csv'), index=False)
    print(f'{len(jobs)} clips in {time.time() - started:.0f} s')
    summarize(t)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--summary':
        summarize(pd.read_csv(os.path.join(HERE, 'long_line_results.csv')))
    else:
        main()
