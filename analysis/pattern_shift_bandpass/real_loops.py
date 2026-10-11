"""Is there fast flow the limb lines miss? Lines round whole loops on the recordings.

python analysis/pattern_shift_bandpass/real_loops.py      (under a minute)

Each loop of ../resting_flow_feasibility/lines.json with both limbs drawn is joined into one line: up the
right limb from its base, over a point above the middle of the two limbs' tops (the apex), down the left
limb; then snapped to the vessel's ridge (within 6 px, as measure.py snaps limbs with 4 px). On a 300-px
simulated loop this reaches 0.48-1.6 mm/s (validate_long_line.py). Positive speed = up the right limb.
Pattern shift at rest and after release, differenced and band-passed rows. Writes loops_results.csv and,
to check the lines, out/<recording>_loops.png.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
FEASIBILITY = os.path.join(REPO, 'analysis', 'resting_flow_feasibility')
sys.path.insert(0, REPO)
sys.path.insert(0, FEASIBILITY)

MM = 0.001328903654
FILTERS = {'difference': None, 'band 1-4': (1.0, 4.0)}
LOOPS = {  # recording: (loop, right limb, left limb)
    'FP01_Qföre_22-Oct-2019_08-16-35': [('tall loop', 'tall loop, right limb', 'tall loop, left limb')],
    'FP01_Qefter_försök2_22-Oct-2019_09-50-15': [('loop A', 'loop A, right limb', 'loop A, left limb'),
                                                 ('loop B', 'loop B, right limb', 'loop B, left limb')],
    'FP01_Wefter_14-Oct-2019_10-13-03': [('right loop', 'right loop, inner limb', 'right loop, outer limb')],
    'FP03_Qefter_försök2_15-Oct-2019_11-06-33': [('loop P', 'loop P, right limb', 'loop P, left limb'),
                                                 ('loop Q', 'loop Q, right limb', 'loop Q, left limb')],
    'FP03_Qföre_15-Oct-2019_09-15-49': [('curly loop', 'curly loop, right limb', 'curly loop, left limb')],
}


def loop_points(right, left):
    right = sorted(right, key=lambda p: -p[1])            # base to top
    left = sorted(left, key=lambda p: p[1])               # top to base
    (xr, yr), (xl, yl) = right[-1], left[0]
    apex = ((xr + xl) / 2, min(yr, yl) - abs(xr - xl) / 2)
    return right + [apex] + left


def run(stem, loops, lines):
    import cv2
    import measure
    from capillary.pattern_shift import pattern_shift
    from capillary.spacetime import Centreline, SpaceTimeSampler
    from capillary.stabilize import enhance
    from capillary.video import iter_frames, probe_video
    path = os.path.join(REPO, 'StabilizedVideos', f'{stem}.avi')
    info = probe_video(path)
    spans = {k: v for k, v in measure.windows(stem, info.fps, info.frame_count).items()
             if k in ('rest', 'after release')}
    a, b = spans['rest']
    total = None
    for frame in iter_frames(path, start=a, max_frames=b - a):
        total = frame.astype(np.float64) if total is None else total + frame
    mean = (total / (b - a)).astype(np.float32)
    vessel = cv2.GaussianBlur(-enhance(mean), (0, 0), 1.5)
    centrelines = {name: Centreline.from_points(measure.snap(loop_points(lines[right]['points'],
                                                                         lines[left]['points']), vessel, search=6))
                   for name, right, left in loops}
    image = -enhance(mean)
    lo, hi = np.percentile(image[40:-40, 40:-40], [1, 99.7])
    image = cv2.cvtColor(np.clip((image - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    for name, line in centrelines.items():
        p = (2 * line.sample_positions(1.0)[0]).astype(np.int32)
        cv2.polylines(image, [p], False, (0, 0, 255), 1)
        cv2.circle(image, tuple(int(v) for v in p[0]), 4, (0, 255, 0), -1)          # start: the right limb's base
        cv2.putText(image, name, tuple(int(v) for v in p[len(p) // 2] + [6, -6]), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 200, 255), 1)
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    cv2.imwrite(os.path.join(HERE, 'out', f'{stem}_loops.png'), image)
    samplers = {name: SpaceTimeSampler(line) for name, line in centrelines.items()}
    rows = []
    for window, (start, stop) in spans.items():
        diagrams = {name: [] for name in samplers}
        for frame in iter_frames(path, start=start, max_frames=stop - start):
            for name, sampler in samplers.items():
                diagrams[name].append(sampler.row(frame))
        for name, sampler in samplers.items():
            diagram = np.asarray(diagrams[name], dtype=np.float32)
            for filter_name, band in FILTERS.items():
                e = pattern_shift(diagram, bandpass_px=band)
                rows.append({'recording': stem, 'loop': name, 'length_px': sampler.n_positions, 'window': window,
                             'filter': filter_name, 'speed_px_per_frame': e.speed_px_per_frame,
                             'mm_s': e.speed_px_per_frame * info.fps * MM, 'snr': e.snr, 'in_range': e.in_range,
                             'resolved': e.resolved})
    return rows


def main():
    with open(os.path.join(FEASIBILITY, 'lines.json'), encoding='utf-8') as handle:
        all_lines = json.load(handle)
    rows = []
    for stem, loops in LOOPS.items():
        if os.path.exists(os.path.join(REPO, 'StabilizedVideos', f'{stem}.avi')):
            rows += run(stem, loops, all_lines[stem])
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(HERE, 'loops_results.csv'), index=False)
    t['recording'] = t.recording.str.slice(0, 13)
    t['result'] = t.apply(lambda r: f"{r.mm_s:+.3f} mm/s ({r.snr:.1f}{', edge' if not r.in_range else ''}"
                                    f"{', resolved' if r.resolved else ''})", axis=1)
    pd.set_option('display.width', 200)
    print(t.pivot_table(index=['recording', 'loop', 'length_px', 'window'], columns='filter', values='result',
                        aggfunc='first').to_string())


if __name__ == '__main__':
    main()
