"""Batch entry point: analyse a video without opening the GUI.

    python -m capillary.cli StabilizedVideos/clip.mp4 \\
        --roi1 320,240 --roi2 320,300 --size 10x10 --out report.csv

Running the same measurement from a script is what makes a result reproducible:
the ROI coordinates, box size and calibration are all on the command line, so a
report can be regenerated months later without re-clicking on a canvas.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Optional, Sequence

import numpy as np

from .intensity import extract_traces_from_video
from .roi import ROI
from .velocity import DEFAULT_WINDOWS, analyze_trace
from .video import probe_video

DEFAULT_MM_PER_PIXEL = 0.001328903654


def read_mm_per_pixel(settings_path: str) -> Optional[float]:
    """Pull `mm_per_pixel` out of the app's settings.csv, if present."""
    if not settings_path or not os.path.isfile(settings_path):
        return None
    try:
        with open(settings_path, newline='') as handle:
            for row in csv.reader(handle):
                if len(row) >= 2 and row[0].strip() == 'mm_per_pixel':
                    return float(row[1])
    except (OSError, ValueError):
        return None
    return None


def parse_size(text: str) -> tuple[int, int]:
    """Parse ``"WxH"`` (or a single number for a square box)."""
    parts = str(text).lower().replace(',', 'x').split('x')
    try:
        numbers = [int(p) for p in parts if p.strip() != '']
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f'invalid box size {text!r}') from exc
    if len(numbers) == 1:
        return numbers[0], numbers[0]
    if len(numbers) == 2:
        return numbers[0], numbers[1]
    raise argparse.ArgumentTypeError(f'invalid box size {text!r}, expected "WxH"')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='python -m capillary.cli',
        description='Estimate capillary flow velocity from a video, headlessly.',
    )
    parser.add_argument('video', help='path to the (stabilised) video file')
    parser.add_argument(
        '--roi1', required=True,
        help='rectangle 1 as "x,y" or "x,y,w,h" (the downstream box in the GUI convention)',
    )
    parser.add_argument('--roi2', required=True, help='rectangle 2 as "x,y" or "x,y,w,h"')
    parser.add_argument(
        '--size', type=parse_size, default=(10, 10),
        help='default box size "WxH" for ROIs given as "x,y" (default: 10x10)',
    )
    parser.add_argument(
        '--mm-per-pixel', type=float, default=None,
        help='spatial calibration; defaults to the value in --settings',
    )
    parser.add_argument(
        '--settings', default='settings.csv',
        help='settings.csv to read mm_per_pixel from (default: settings.csv)',
    )
    parser.add_argument('--fps', type=float, default=None, help='override the video frame rate')
    parser.add_argument(
        '--windows', default=','.join(str(w) for w in DEFAULT_WINDOWS),
        help='comma-separated correlation window lengths in frames',
    )
    parser.add_argument(
        '--step', type=int, default=1, help='advance the window by this many frames (default: 1)',
    )
    parser.add_argument('--max-frames', type=int, default=None, help='analyse only the first N frames')
    parser.add_argument('--out', default=None, help='write the full per-frame report here (CSV)')
    parser.add_argument(
        '--summary-out', default=None,
        help='write the time/velocity/correlation summary here (CSV)',
    )
    parser.add_argument(
        '--positive-flow', choices=('a_to_b', 'b_to_a'), default='b_to_a',
        help='which direction counts as positive velocity (default: b_to_a, as in the GUI)',
    )
    parser.add_argument(
        '--legacy-lag', action='store_true',
        help='reproduce the pre-fix off-by-one lag, for comparison with old reports',
    )
    parser.add_argument('--quiet', action='store_true', help='suppress the summary on stdout')
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        roi_a = ROI.parse(args.roi1, *args.size)
        roi_b = ROI.parse(args.roi2, *args.size)
        windows = [int(w) for w in str(args.windows).split(',') if w.strip()]
    except ValueError as exc:
        parser.error(str(exc))

    mm_per_pixel = args.mm_per_pixel
    if mm_per_pixel is None:
        mm_per_pixel = read_mm_per_pixel(args.settings)
    if mm_per_pixel is None:
        mm_per_pixel = DEFAULT_MM_PER_PIXEL

    try:
        info = probe_video(args.video)
        trace = extract_traces_from_video(
            args.video, roi_a, roi_b, max_frames=args.max_frames, fps=args.fps
        )
        report = analyze_trace(
            trace,
            mm_per_pixel=mm_per_pixel,
            windows=windows,
            step=args.step,
            legacy_lag=args.legacy_lag,
            positive_flow=args.positive_flow,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1

    if args.out:
        report.to_csv(args.out)
    if args.summary_out:
        report.loc[:, ['time_s', 'velocity', 'correlation']].to_csv(args.summary_out)

    if not args.quiet:
        _print_summary(args.video, info, trace, report, mm_per_pixel)
    return 0


def _print_summary(path, info, trace, report, mm_per_pixel) -> None:
    velocity = report['velocity'].to_numpy(dtype=float)
    finite = velocity[np.isfinite(velocity)]
    correlation = report['correlation'].to_numpy(dtype=float)
    finite_correlation = correlation[np.isfinite(correlation)]

    print(f'{path}')
    print(f'  {info.width}x{info.height}, {trace.n_frames} frames @ {trace.fps:g} fps '
          f'({trace.duration_s:.1f} s)')
    print(f'  ROI separation : {trace.distance_px:.1f} px '
          f'({trace.distance_px * mm_per_pixel:.4f} mm)')
    print(f'  usable frames  : {trace.valid_count()}/{trace.n_frames}')
    print(f'  estimates      : {len(finite)}/{len(report)} windows resolved')
    if finite.size:
        print(f'  velocity       : median {np.median(finite):.3f} mm/s '
              f'(IQR {np.percentile(finite, 25):.3f} to {np.percentile(finite, 75):.3f})')
    if finite_correlation.size:
        print(f'  correlation    : median {np.median(finite_correlation):.2f}')


if __name__ == '__main__':
    raise SystemExit(main())
