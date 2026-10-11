"""Pattern shift with differenced rows (before 2026-10-11) against band-passed rows, on the recordings.

python analysis/pattern_shift_bandpass/validate_real.py      (a few minutes)

The lines of analysis/resting_flow_feasibility/lines.json (limbs snapped to the vessel as measure.py does;
tissue lines as placed), on the videos stabilized by capillary.stabilize. Windows from the official
times: rest, its two halves, occlusion, after release. Writes real_results.csv and prints the summary.
"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
FEASIBILITY = os.path.join(REPO, 'analysis', 'resting_flow_feasibility')
sys.path.insert(0, REPO)
sys.path.insert(0, FEASIBILITY)
sys.path.insert(0, HERE)
from validate_synthetic import FILTERS  # noqa: E402

MM = 0.001328903654


def run(stem):
    import cv2
    cv2.setNumThreads(2)
    import measure                                        # snap(), windows(), LINES; main() is not run
    from capillary.pattern_shift import pattern_shift
    from capillary.spacetime import Centreline, SpaceTimeSampler
    from capillary.stabilize import enhance
    from capillary.video import iter_frames, probe_video
    path = os.path.join(REPO, 'StabilizedVideos', f'{stem}.avi')
    info = probe_video(path)
    spans = measure.windows(stem, info.fps, info.frame_count)
    a, b = spans['rest']
    total = None
    for frame in iter_frames(path, start=a, max_frames=b - a):
        total = frame.astype(np.float64) if total is None else total + frame
    vessel = cv2.GaussianBlur(-enhance((total / (b - a)).astype(np.float32)), (0, 0), 1.5)
    samplers = {}
    for name, spec in measure.LINES[stem].items():
        points = spec['points'] if spec['kind'] == 'tissue' else measure.snap(spec['points'], vessel)
        samplers[name] = (spec['kind'], SpaceTimeSampler(Centreline.from_points(points)))
    diagrams = {name: [] for name in samplers}
    for frame in iter_frames(path):
        for name, (_, sampler) in samplers.items():
            diagrams[name].append(sampler.row(frame))
    rows = []
    for name, (kind, sampler) in samplers.items():
        diagram = np.asarray(diagrams[name], dtype=np.float32)
        for window, (start, stop) in spans.items():
            for filter_name, band in FILTERS.items():
                e = pattern_shift(diagram[start:stop], bandpass_px=band)
                to_mm_s = info.fps * MM
                rows.append({'recording': stem, 'line': name, 'kind': kind, 'length_px': sampler.n_positions,
                             'window': window, 'filter': filter_name, 'speed_px_per_frame': e.speed_px_per_frame,
                             'mm_s': e.speed_px_per_frame * to_mm_s, 'ci_low_mm_s': e.ci95[0] * to_mm_s,
                             'ci_high_mm_s': e.ci95[1] * to_mm_s, 'snr': e.snr, 'in_range': e.in_range,
                             'resolved': e.resolved, 'blocks': e.blocks})
    return rows


def summarize(t):
    pd.set_option('display.width', 250)
    pd.set_option('display.max_columns', 40)
    pd.set_option('display.max_rows', 400)
    tissue = t[t.kind == 'tissue']
    print('\nTissue lines (no flow expected), all windows: highest signal-to-noise, in range and overall; resolved')
    print(tissue.groupby('filter').agg(lines=('line', 'nunique'), estimates=('snr', 'size'),
                                       max_in_range=('snr', lambda s: s[tissue.loc[s.index, 'in_range']].max()),
                                       max_all=('snr', 'max'), resolved=('resolved', 'sum'))
          .reindex(FILTERS.keys()).round(1).to_string())
    limbs = t[t.kind == 'limb']
    print('\nLimbs resolved, per window')
    print(limbs.groupby(['filter', 'window']).resolved.sum().unstack('window')
          .reindex(FILTERS.keys()).to_string())
    rest = limbs[limbs.window == 'rest']
    resolved_any = rest[rest.resolved][['recording', 'line']].drop_duplicates()
    print('\nLimbs resolved at rest by any filter: mm/s (signal-to-noise)')
    for _, (stem, line) in resolved_any.iterrows():
        cells = []
        for f in FILTERS:
            r = rest[(rest.recording == stem) & (rest.line == line) & (rest['filter'] == f)].iloc[0]
            cells.append(f"{f}: {r.mm_s:+.3f} ({r.snr:.1f}{'' if r.resolved else ', no'})")
        print(f'  {stem[:13]} {line}: ' + '; '.join(cells))
    halves = limbs[limbs.window.isin(['rest 1st half', 'rest 2nd half'])]
    both = halves.groupby(['filter', 'recording', 'line']).filter(lambda g: g.resolved.all() and len(g) == 2)
    print('\nBoth halves of the rest resolved: the two estimates (mm/s)')
    for (f, stem, line), g in both.groupby(['filter', 'recording', 'line']):
        first = g[g.window == 'rest 1st half'].iloc[0]
        second = g[g.window == 'rest 2nd half'].iloc[0]
        print(f'  {f:11} {stem[:13]} {line:24} {first.mm_s:+.3f} / {second.mm_s:+.3f} '
              f'(difference {100 * (second.mm_s / first.mm_s - 1):+.0f}%)')


def main():
    with open(os.path.join(FEASIBILITY, 'lines.json'), encoding='utf-8') as handle:
        stems = [s for s in json.load(handle) if os.path.exists(os.path.join(REPO, 'StabilizedVideos', f'{s}.avi'))]
    started = time.time()
    with ProcessPoolExecutor(max_workers=len(stems)) as pool:
        rows = [row for rows in pool.map(run, stems) for row in rows]
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(HERE, 'real_results.csv'), index=False)
    print(f'{len(stems)} recordings, {t.line.nunique()} lines in {time.time() - started:.0f} s')
    summarize(t)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--summary':
        summarize(pd.read_csv(os.path.join(HERE, 'real_results.csv')))
    else:
        main()
