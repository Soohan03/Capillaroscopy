"""Batch entry point: measure a line on a video without opening the GUI.

    python -m capillary.cli StabilizedVideos/clip.avi \\
        --line "372,110;352,160;338,205" --out blocks.csv

``--line`` gives the centre line (`capillary.spacetime`, the Centre line
page). Running the same measurement from a script is what makes a result
reproducible: the line, frames and calibration are all on the command line
(and in a data set's provenance file), so a result can be regenerated months
later without re-clicking on a canvas.

As in the app, a line on a stabilized video (one with a shift file) is refused
when it leaves the picture in a frame read (`capillary.stabilize.check_picture`).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Optional, Sequence

import numpy as np

from . import pattern_shift, spacetime, stabilize
from .video import iter_frames, probe_video

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


def parse_line(text: str) -> spacetime.Centreline:
    """Parse ``"x1,y1;x2,y2;..."`` (points may also be separated by spaces) into a centre line."""
    points = []
    for part in str(text).replace(';', ' ').split():
        try:
            x, y = (float(v) for v in part.split(','))
        except ValueError as exc:
            raise ValueError(f'invalid point {part!r} in --line; expected "x,y"') from exc
        points.append((x, y))
    return spacetime.Centreline.from_points(points)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='python -m capillary.cli',
        description='Estimate capillary flow velocity along a line on a video, headlessly.',
    )
    parser.add_argument('video', help='path to the (stabilised) video file')
    parser.add_argument(
        '--line', required=True,
        help='centre line as "x1,y1;x2,y2;..." in video pixels, from where the blood comes from',
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
    parser.add_argument('--start', type=int, default=0, help='first frame to analyse (default: 0)')
    parser.add_argument('--max-frames', type=int, default=None, help='analyse at most N frames')
    parser.add_argument('--out', default=None, help='write the table of 3-s blocks here (CSV)')
    parser.add_argument(
        '--summary-out', default=None,
        help='write the time/velocity summary here (CSV)',
    )
    parser.add_argument(
        '--slow-flow', action='store_true',
        help='let the pattern shift search below 1 px/frame (from 0.1); movement of the picture along the line '
             'can look like slow flow there',
    )
    parser.add_argument('--quiet', action='store_true', help='suppress the summary on stdout')
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    mm_per_pixel = args.mm_per_pixel
    if mm_per_pixel is None:
        mm_per_pixel = read_mm_per_pixel(args.settings)
    if mm_per_pixel is None:
        mm_per_pixel = DEFAULT_MM_PER_PIXEL
    try:
        line = parse_line(args.line)
    except ValueError as exc:
        parser.error(str(exc))
    return _measure_line(args, line, mm_per_pixel)


def _picture_problem(video: str, line: spacetime.Centreline, info, start: int,
                     max_frames: Optional[int]) -> Optional[str]:
    """Why `line` cannot be measured over the frames read from a stabilized `video`, or None
    (`capillary.stabilize.check_picture`; a video without a shift file is not checked)."""
    shifts = stabilize.read_shifts(video)
    if shifts is None:
        return None
    last = info.frame_count - 1 if max_frames is None else min(info.frame_count, start + max_frames) - 1
    check = stabilize.check_picture(shifts, (info.height, info.width), spacetime.SpaceTimeSampler(line).bounds,
                                    start, last)
    return check.problem()


def _measure_line(args, line: spacetime.Centreline, mm_per_pixel: float) -> int:
    try:
        info = probe_video(args.video)
        fps = args.fps or info.fps
        problem = _picture_problem(args.video, line, info, args.start, args.max_frames)
        if problem is not None:
            print(f'error: {problem}', file=sys.stderr)
            return 1
        diagram = spacetime.space_time_diagram(iter_frames(args.video, max_frames=args.max_frames, start=args.start),
                                               line)
        blocks = spacetime.analyze_space_time(diagram, fps, mm_per_pixel, first_frame=args.start)
        pooled = pattern_shift.summarize(diagram, fps, mm_per_pixel, min_speed=(
            pattern_shift.SLOW_MIN_SPEED if args.slow_flow else pattern_shift.MIN_SPEED))
    except (FileNotFoundError, ValueError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    if args.out:
        blocks.to_csv(args.out)
    if args.summary_out:
        blocks.loc[:, ['time_s', 'velocity_mm_s']].to_csv(args.summary_out)
    if not args.quiet:
        summary = spacetime.space_time_summary(blocks)
        slowest, fastest = spacetime.resolvable_speeds(line.length_px, fps, mm_per_pixel)
        print(f'{args.video}')
        print(f'  {info.width}x{info.height}, {diagram.shape[0]} frames from {args.start} @ {fps:g} fps '
              f'({diagram.shape[0] / fps:.1f} s)')
        print(f'  centre line    : {len(line.points)} points, {line.length_px:.1f} px '
              f'({line.length_px * mm_per_pixel:.4f} mm), measurable {slowest:.4f} to {fastest:.3f} mm/s')
        print(f'  estimates      : {summary["resolved"]}/{summary["blocks"]} blocks resolved')
        if summary['resolved']:
            print(f'  velocity       : median {summary["median"]:.4f} mm/s '
                  f'(IQR {summary["q25"]:.4f} to {summary["q75"]:.4f}), '
                  f'median signal-to-noise {summary["median_snr"]:.0f}')
        to_mm_s = fps * mm_per_pixel
        speed = pooled['pattern_shift_speed_px_per_frame']
        if np.isfinite(speed):
            low, high = pooled['pattern_shift_ci95_low_mm_s'], pooled['pattern_shift_ci95_high_mm_s']
            interval = f', 95% CI {low:.4f} to {high:.4f}' if np.isfinite(low) else ''
            print(f'  pattern shift  : {speed * to_mm_s:.4f} mm/s{interval}, signal-to-noise '
                  f'{pooled["pattern_shift_snr"]:.1f}, pooled over {pooled["pattern_shift_blocks"]} blocks - '
                  f'{"resolved" if pooled["pattern_shift_resolved"] else "not resolved"}')
            halves = ('first_half', 'second_half')
            if np.isfinite(pooled['pattern_shift_first_half_snr']):
                print('  halves         : ' + ' / '.join(
                    f'{pooled[f"pattern_shift_{half}_mm_s"]:.4f}' if np.isfinite(pooled[f'pattern_shift_{half}_mm_s'])
                    else 'not resolved' for half in halves) + ' mm/s')
        else:
            print('  pattern shift  : no estimate (the line or the range is too short)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
