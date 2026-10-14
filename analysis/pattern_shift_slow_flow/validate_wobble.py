"""Movement of the picture along the line, without flow: does the pattern shift read it as flow?

python analysis/pattern_shift_slow_flow/validate_wobble.py [--summary]      (about 30 s on 14 cores)

During the occlusion the blood stands still, and the stopped cells are a strong still pattern on the vessel. If the
picture then moves along the line (residual movement after stabilization, the finger shifting under the cuff), that
pattern moves with it. Movement that goes one way slowly and comes back fast leaves a net direction. These clips
render the simulated loop (capillary.simulate, disturbances as measured) with the cells standing still or flowing
slowly, and then move the whole picture along the arterial limb:

- none;
- a sine (symmetric) of 2 or 10 px amplitude, period 3 s;
- a sawtooth of 2, 10 or 20 px: out over 2.5 s, back in 0.5 s (out at 0.03, 0.13 or 0.27 px/frame);
- bows of 15 px every 15 s: out and back within 4 s, out faster than back, like FP13_Qföre's limbs in occlusion;
- a steady drift of 0.05 or 0.3 px/frame (90 or 540 px in the minute, which a stabilized video would not show:
  the bound on what drift can do).

Each clip is measured by the method before (from 1 px/frame) and with the slow range. Writes wobble_results.csv.
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
sys.path.insert(0, HERE)
from validate_synthetic import FRAMES, estimate  # noqa: E402

VARIANTS = ('before', 'stretched')
SHAPES = {'none': ('none', 0.0), 'sine 2 px': ('sine', 2.0), 'sine 10 px': ('sine', 10.0),
          'sawtooth 2 px': ('sawtooth', 2.0), 'sawtooth 10 px': ('sawtooth', 10.0),
          'sawtooth 20 px': ('sawtooth', 20.0), 'bows of 15 px': ('bows', 15.0), 'drift 0.05': ('drift', 0.05),
          'drift 0.3': ('drift', 0.3)}
SPEEDS = (0.0, 0.3)
SEEDS = 10
PERIOD_S, RETURN_S, FPS = 3.0, 0.5, 30.0


def displacement(shape, size, n):
    """The picture's displacement along the limb in each frame (px)."""
    t = np.arange(n) / FPS
    if shape == 'none':
        return np.zeros(n)
    if shape == 'sine':
        return size * np.sin(2 * np.pi * t / PERIOD_S)
    if shape == 'drift':
        return size * np.arange(n)
    if shape == 'bows':
        # out and back over 4 s (smoothly, out faster than back), every 15 s
        phase = t % 15.0
        bow = np.where(phase < 4.0, np.sin(np.pi * (phase / 4.0) ** 0.6), 0.0)
        return size * bow
    phase = (t % PERIOD_S) / PERIOD_S
    out_share = (PERIOD_S - RETURN_S) / PERIOD_S
    return size * np.where(phase < out_share, phase / out_share, (1 - phase) / (1 - out_share))


def case(job):
    shape_name, speed, seed = job
    import cv2
    cv2.setNumThreads(1)
    from capillary import simulate
    from capillary.spacetime import space_time_diagram
    recording = simulate.simulate(simulate.hairpin(), FRAMES, speed, seed=5000 + 100 * seed + int(100 * speed))
    line = recording.drawn_line(20.0, 140.0, seed=seed)
    # the limb's direction, from its base to the apex: the picture moves along it
    (x0, y0), (x1, y1) = line.points[0], line.points[-1]
    along = np.array([x1 - x0, y1 - y0]) / np.hypot(x1 - x0, y1 - y0)
    shift = displacement(*SHAPES[shape_name], FRAMES)
    frames = recording.frames
    if np.any(shift):
        height, width = frames.shape[1:]
        moved = np.empty_like(frames)
        for i, frame in enumerate(frames):
            dx, dy = shift[i] * along
            matrix = np.float32([[1, 0, dx], [0, 1, dy]])
            moved[i] = cv2.warpAffine(frame, matrix, (width, height), flags=cv2.INTER_LINEAR,
                                      borderMode=cv2.BORDER_REFLECT)
        frames = moved
    diagram = space_time_diagram(frames, line)
    rows = []
    for variant in VARIANTS:
        e = estimate(diagram, variant)
        rows.append({'shape': shape_name, 'speed': speed, 'seed': seed, 'variant': variant,
                     'estimate': e.speed_px_per_frame, 'snr': e.snr, 'in_range': e.in_range, 'resolved': e.resolved,
                     'ci_low': e.ci95[0], 'ci_high': e.ci95[1]})
    return rows


def summarize(t):
    pd.set_option('display.width', 250)
    for speed in sorted(t.speed.unique()):
        part = t[t.speed == speed].copy()
        print(f'\nCells {"standing still" if speed == 0 else f"flowing at {speed:g} px/frame"} ({SEEDS} clips each): '
              'resolved / median estimate (px/frame) / highest signal-to-noise')
        grid = part.groupby(['shape', 'variant']).agg(
            resolved=('resolved', 'sum'), median=('estimate', lambda s: s[part.loc[s.index, 'resolved']].median()),
            max_snr=('snr', 'max'))
        cells = grid.apply(lambda r: f"{int(r.resolved)} {r['median']:+.2f} {r.max_snr:.1f}", axis=1).unstack('variant')
        print(cells.reindex(list(SHAPES)).to_string())


def main():
    jobs = [(shape, speed, seed) for shape in SHAPES for speed in SPEEDS for seed in range(SEEDS)]
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=14) as pool:
        table = pd.DataFrame([row for rows in pool.map(case, jobs) for row in rows])
    table.to_csv(os.path.join(HERE, 'wobble_results.csv'), index=False)
    print(f'{len(jobs)} clips in {time.perf_counter() - started:.0f} s')
    summarize(table)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--summary':
        summarize(pd.read_csv(os.path.join(HERE, 'wobble_results.csv')))
    else:
        main()
