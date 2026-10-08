"""Benchmark: the velocity estimators on synthetic recordings with a known speed.

    python3 -m capillary.benchmark --out benchmark            (about 10 minutes)
    python3 -m capillary.benchmark --out benchmark --quick    (a minute; fewer cases)

Every case renders a capillary loop (`capillary.simulate`) with red cells
moving along it at a known speed, under one of three levels of disturbance,
and measures it twice, the way the app would:

- **two boxes**, 12 px, 30 px apart along the arterial limb, through the
  report arithmetic of the Analyze page (`capillary.velocity.analyze_trace`,
  windows of 201-301 frames, sliding by one frame);
- **centre line**, a 120-px line along the same limb drawn the way a person
  clicks it (a point every 15 px, up to 1 px off the centre), through
  `capillary.spacetime` (3-s blocks every 0.5 s);
- **pattern shift**, the same line's diagram through `capillary.pattern_shift`,
  one estimate pooled over the whole clip.

For each case it records the median velocity against the truth, how many
estimates were resolved, how many pointed the wrong way and, for the boxes,
how many windows found a delay of zero. Writes ``benchmark_cases.csv`` (one
row per case and method) and ``benchmark_summary.md`` (medians over seeds).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Optional, Sequence

import numpy as np
import pandas as pd

from . import simulate
from .intensity import extract_traces
from .pattern_shift import pattern_shift
from .spacetime import analyze_space_time, resolvable_speeds, space_time_diagram
from .velocity import analyze_trace

FPS = 30.0
MM_PER_PIXEL = 0.001328903654           # the app's default calibration
LINE = (20.0, 140.0)                    # arc positions along the loop (px): the arterial limb
BOXES = (50.0, 30.0)                    # upstream box at 50 px along the loop, the other 30 px further
SPEEDS = (0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 8.0, 12.0, 16.0, 25.0)
CONDITIONS = {
    'clean': simulate.Disturbances.clean(),
    'as measured': simulate.Disturbances(),
    'strong': simulate.Disturbances.strong(),
}


def _stats(values: np.ndarray, truth: float) -> dict:
    finite = values[np.isfinite(values)]
    median = float(np.median(finite)) if finite.size else float('nan')
    out = {
        'estimates': int(values.size),
        'resolved_fraction': finite.size / values.size if values.size else float('nan'),
        'median_mm_s': median,
        'iqr_mm_s': float(np.subtract(*np.percentile(finite, [75, 25]))) if finite.size else float('nan'),
    }
    if truth > 0:
        out['error_pct'] = 100 * (median / truth - 1) if finite.size else float('nan')
        out['wrong_sign_fraction'] = float(np.mean(finite < 0)) if finite.size else float('nan')
    else:
        out['error_pct'] = float('nan')
        out['wrong_sign_fraction'] = float('nan')
    return out


def run_case(condition: str, speed: float, seed: int, n_frames: int) -> list[dict]:
    recording = simulate.simulate(simulate.hairpin(), n_frames, speed, disturbances=CONDITIONS[condition],
                                  seed=seed)
    truth = recording.true_velocity_mm_s(MM_PER_PIXEL)
    common = {'condition': condition, 'speed_px_per_frame': speed, 'true_mm_s': truth, 'seed': seed}
    rows = []

    box1, box2 = recording.boxes(*BOXES)
    trace = extract_traces(recording.frames, box1, box2, fps=FPS)
    started = time.perf_counter()
    report = analyze_trace(trace, MM_PER_PIXEL, smooth_frames=None)
    lags = report.filter(regex=r'^lag_').to_numpy(dtype=float)
    lags = lags[np.isfinite(lags)]
    rows.append({**common, 'method': 'two boxes', **_stats(report['velocity'].to_numpy(dtype=float), truth),
                 'zero_lag_fraction': float(np.mean(lags == 0)) if lags.size else float('nan'),
                 'median_snr': float('nan'), 'seconds': time.perf_counter() - started})

    line = recording.drawn_line(*LINE, seed=seed)
    started = time.perf_counter()
    diagram = space_time_diagram(recording.frames, line)
    blocks = analyze_space_time(diagram, FPS, MM_PER_PIXEL)
    rows.append({**common, 'method': 'centre line', **_stats(blocks['velocity_mm_s'].to_numpy(dtype=float), truth),
                 'zero_lag_fraction': float('nan'), 'median_snr': float(np.nanmedian(blocks['snr'])),
                 'seconds': time.perf_counter() - started})

    started = time.perf_counter()
    pooled = pattern_shift(diagram)
    velocity = pooled.velocity_mm_s(FPS, MM_PER_PIXEL) if pooled.resolved else float('nan')
    rows.append({**common, 'method': 'pattern shift', **_stats(np.array([velocity]), truth),
                 'zero_lag_fraction': float('nan'), 'median_snr': pooled.snr,
                 'seconds': time.perf_counter() - started})
    return rows


def summarize(cases: pd.DataFrame) -> str:
    """A markdown table: per condition, speed and method, medians over the seeds."""
    slowest, fastest = resolvable_speeds(LINE[1] - LINE[0], FPS, MM_PER_PIXEL)
    lines = [
        f'Synthetic capillary loop, {FPS:g} fps, {MM_PER_PIXEL * 1000:.4g} um/px. Two boxes: 12 px, '
        f'{BOXES[1]:g} px apart. Centre line: {LINE[1] - LINE[0]:g} px, measurable '
        f'{slowest:.3f}-{fastest:.3f} mm/s. Medians over {cases["seed"].nunique()} seeds.',
        '',
        '| condition | speed (px/frame) | true (mm/s) | method | median (mm/s) | error | resolved | wrong sign '
        '| zero lag |',
        '|---|---:|---:|---|---:|---:|---:|---:|---:|',
    ]
    grouped = cases.groupby(['condition', 'speed_px_per_frame', 'method'], sort=False)
    for (condition, speed, method), group in grouped:
        def pct(column):
            value = group[column].median()
            return '' if not np.isfinite(value) else f'{100 * value:.0f}%'
        error = group['error_pct'].median()
        median = group['median_mm_s'].median()
        lines.append(
            f'| {condition} | {speed:g} | {group["true_mm_s"].iloc[0]:.3f} | {method} | '
            f'{"–" if not np.isfinite(median) else f"{median:.3f}"} | '
            f'{"" if not np.isfinite(error) else f"{error:+.1f}%"} | {pct("resolved_fraction")} | '
            f'{pct("wrong_sign_fraction")} | {pct("zero_lag_fraction")} |')
    return '\n'.join(lines) + '\n'


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m capillary.benchmark', description=__doc__.split('\n\n')[0])
    parser.add_argument('--out', default='benchmark', help='folder for the results (created if missing)')
    parser.add_argument('--quick', action='store_true', help='one seed, 10-s clips, fewer speeds')
    parser.add_argument('--seeds', type=int, default=3)
    parser.add_argument('--frames', type=int, default=900, help='frames per clip (default 900 = 30 s)')
    args = parser.parse_args(argv)

    speeds = (0.0, 0.5, 2.0, 6.0, 12.0, 25.0) if args.quick else SPEEDS
    seeds = 1 if args.quick else args.seeds
    n_frames = 300 if args.quick else args.frames
    os.makedirs(args.out, exist_ok=True)
    rows = []
    total = len(CONDITIONS) * len(speeds) * seeds
    done = 0
    for condition in CONDITIONS:
        for speed in speeds:
            for seed in range(seeds):
                rows += run_case(condition, speed, seed, n_frames)
                done += 1
                print(f'\r{done}/{total} cases', end='', file=sys.stderr, flush=True)
    print(file=sys.stderr)
    cases = pd.DataFrame(rows)
    cases.to_csv(os.path.join(args.out, 'benchmark_cases.csv'), index=False)
    summary = summarize(cases)
    with open(os.path.join(args.out, 'benchmark_summary.md'), 'w', encoding='utf-8') as handle:
        handle.write(summary)
    print(summary)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
