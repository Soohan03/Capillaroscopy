"""Measure the lines of lines.json over the official rest window, as a centre-line data set would.

python analysis/aim1_feasibility/measure.py [--trace-only] <recording> [<recording> ...]

With --trace-only the lines are traced and drawn, nothing is measured: the
lines are checked and corrected this way before any velocity is seen.

A limb is given by points placed by eye on the resting image, from the limb's
base to its apex (`points`: at least those two, with points between them where
the limb bends). Its centre line follows the vessel's ridge from point to point
(`trace`): the cheapest path through the resting image, where bright (vessel)
pixels cost least. Lines through tissue are used as placed. Each line is
measured over the official rest window with what a centre-line data set keeps
(`gui.tasks.summarize_line`): the pattern shift pooled over the rest and over
each half (`capillary.pattern_shift.summarize`), the limb the direction of the
pooled flow shows (`limb_from_direction`), and the 3-s blocks of the
centre-line method (share resolved, median and quartiles, and the share running along the
line). Needs out/<recording>_rest_mean.npy (rest_image.py).

Writes out/<recording>_lines.png (the lines on the resting image, an arrowhead
at the apex end) and out/<recording>__<line>.npy (each space-time diagram), and
replaces the recording's rows in results.csv.
"""
import json
import os
import re
import sys

import cv2
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

from common import LINES, MM_PER_PIXEL, OUT, RESULTS, rest_window, to_uint8, vessel_image, video_path
from capillary import inventory, pattern_shift
from capillary.spacetime import Centreline, SpaceTimeSampler, analyze_space_time, space_time_summary
from capillary.video import iter_frames

#: A step through a pixel costs 1 + TRACE_PENALTY * (1 - v)^2, where v is the resting image scaled to 0-1
#: around the line (vessels near 1), so the traced path keeps to the bright ridge of the vessel.
TRACE_PENALTY = 40.0
#: The path is searched within this margin (px) around the two points it joins; the image is scaled
#: between the 5th and 99.5th percentile of that part, so an uncovered frame edge elsewhere does not matter.
TRACE_MARGIN_PX = 12
SCALE_PERCENTILES = (5, 99.5)
#: Each placed point is first moved to the brightest pixel within this radius (px), onto the vessel's ridge.
POINT_SNAP_PX = 3
#: The two limbs of a loop are traced apart: a limb's path costs this much more per pixel within
#: KEEP_APART_PX of the other limb's line, except within APEX_SHARED_PX of the apex, where the limbs meet.
#: 5 px keeps the second line out of a wide venous limb (12-15 px) whose ridge the first line follows,
#: while the limbs of narrow loops, 8-12 px apart, stay apart on their own ridges.
APART_COST = 200.0
KEEP_APART_PX = 5
APEX_SHARED_PX = 8
#: The traced path is smoothed over this many pixels, then a point is kept every POINT_SPACING_PX.
SMOOTH_PX = 5
POINT_SPACING_PX = 6
COLOURS = [(0, 0, 255), (255, 80, 0), (0, 200, 0), (0, 200, 255), (255, 0, 255), (255, 255, 0),
           (120, 120, 255), (0, 140, 255), (200, 200, 200), (80, 255, 160)]


def ridge_map(mean: np.ndarray) -> np.ndarray:
    """The resting image the lines are traced on: band-passed, vessels bright, slightly smoothed."""
    return cv2.GaussianBlur(vessel_image(mean), (0, 0), 1.0)


def _box(image: np.ndarray, points) -> tuple:
    """The part of `image` around `points` (x, y), `TRACE_MARGIN_PX` wide: x0, x1, y0, y1."""
    points = np.asarray(points, dtype=float)
    x0 = max(0, int(np.floor(points[:, 0].min())) - TRACE_MARGIN_PX)
    x1 = min(image.shape[1], int(np.ceil(points[:, 0].max())) + TRACE_MARGIN_PX + 1)
    y0 = max(0, int(np.floor(points[:, 1].min())) - TRACE_MARGIN_PX)
    y1 = min(image.shape[0], int(np.ceil(points[:, 1].max())) + TRACE_MARGIN_PX + 1)
    return x0, x1, y0, y1


def _scaled(part: np.ndarray) -> np.ndarray:
    low, high = np.percentile(part, SCALE_PERCENTILES)
    return np.clip((part - low) / max(high - low, 1e-6), 0.0, 1.0)


def _cheapest_path(ridge: np.ndarray, start, end, avoid=None) -> np.ndarray:
    """The cheapest 8-connected pixel path from `start` to `end` (x, y) along the ridge, as (n, 2) x, y.

    `avoid`, if given, is a mask of pixels that cost `APART_COST` more.
    """
    (sx, sy), (ex, ey) = (int(round(v)) for v in start), (int(round(v)) for v in end)
    x0, x1, y0, y1 = _box(ridge, [(sx, sy), (ex, ey)])
    sub = 1.0 + TRACE_PENALTY * (1.0 - _scaled(ridge[y0:y1, x0:x1])) ** 2
    if avoid is not None:
        sub = sub + APART_COST * avoid[y0:y1, x0:x1]
    height, width = sub.shape
    index = np.arange(height * width).reshape(height, width)
    sources, targets, weights = [], [], []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        left, right = max(0, -dx), width - max(0, dx)
        a = index[:height - dy, left:right]
        b = index[dy:, left + dx:right + dx]
        sources.append(a.ravel())
        targets.append(b.ravel())
        weights.append((0.5 * (sub.ravel()[a.ravel()] + sub.ravel()[b.ravel()]) * np.hypot(dy, dx)))
    graph = coo_matrix((np.concatenate(weights), (np.concatenate(sources), np.concatenate(targets))),
                       shape=(height * width, height * width)).tocsr()
    first, last = index[sy - y0, sx - x0], index[ey - y0, ex - x0]
    _, predecessors = dijkstra(graph, directed=False, indices=first, return_predecessors=True)
    path = [last]
    while path[-1] != first:
        path.append(predecessors[path[-1]])
    path = np.asarray(path[::-1])
    return np.column_stack([path % width + x0, path // width + y0]).astype(float)


def _onto_ridge(point, ridge: np.ndarray) -> tuple:
    """The brightest pixel of `ridge` within `POINT_SNAP_PX` of `point` (x, y)."""
    x, y = (int(round(v)) for v in point)
    x0, x1 = max(0, x - POINT_SNAP_PX), min(ridge.shape[1], x + POINT_SNAP_PX + 1)
    y0, y1 = max(0, y - POINT_SNAP_PX), min(ridge.shape[0], y + POINT_SNAP_PX + 1)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    patch = np.where((xx - x) ** 2 + (yy - y) ** 2 <= POINT_SNAP_PX ** 2, ridge[y0:y1, x0:x1], -np.inf)
    row, column = np.unravel_index(int(np.argmax(patch)), patch.shape)
    return float(x0 + column), float(y0 + row)


def trace(points, ridge: np.ndarray, avoid=None) -> tuple:
    """The centre line along the vessel through `points` (base to apex), and its mean ridge value (0-1).

    Each point is moved onto the ridge (`_onto_ridge`) and consecutive points
    are joined by the cheapest path along it (`_cheapest_path`, keeping off
    the pixels of `avoid`); the joined path is smoothed over `SMOOTH_PX` pixels
    (its ends stay) and a point is kept every `POINT_SPACING_PX`. The ridge
    value is the image along the line, scaled to 0-1 around the whole line.
    """
    points = [_onto_ridge(point, ridge) for point in points]
    path = [np.asarray(points[0], dtype=float)[None, :]]
    for start, end in zip(points[:-1], points[1:]):
        path.append(_cheapest_path(ridge, start, end, avoid)[1:])
    path = np.vstack(path)
    half = SMOOTH_PX // 2
    padded = np.pad(path, ((half, half), (0, 0)), mode='edge')
    kernel = np.ones(SMOOTH_PX) / SMOOTH_PX
    smooth = np.column_stack([np.convolve(padded[:, i], kernel, 'valid') for i in (0, 1)])
    keep = list(range(0, len(smooth), POINT_SPACING_PX))
    if keep[-1] != len(smooth) - 1:
        keep.append(len(smooth) - 1)
    x0, x1, y0, y1 = _box(ridge, smooth)
    scaled = _scaled(ridge[y0:y1, x0:x1]).astype(np.float32)
    on_ridge = cv2.remap(scaled, (smooth[:, 0:1] - x0).astype(np.float32), (smooth[:, 1:2] - y0).astype(np.float32),
                         cv2.INTER_LINEAR).ravel()
    return smooth[keep].tolist(), float(on_ridge.mean())


def _apart_from(points, shape) -> np.ndarray:
    """Pixels within `KEEP_APART_PX` of the line through `points`, except within `APEX_SHARED_PX` of its apex."""
    mask = np.zeros(shape, dtype=np.uint8)
    samples = Centreline.from_points(points).sample_positions(1.0)[0]
    cv2.polylines(mask, [np.round(samples).astype(np.int32)], False, 1, 2 * KEEP_APART_PX + 1)
    apex = np.round(samples[-1]).astype(int)
    cv2.circle(mask, (int(apex[0]), int(apex[1])), APEX_SHARED_PX, 0, -1)
    return mask.astype(np.float32)


def trace_loop(limbs: dict, ridge: np.ndarray) -> dict:
    """The centre lines of one loop's limbs ({name: placed points}), each kept off the other's line.

    Each limb is traced on its own first; then each is traced again keeping
    off the other's line (`_apart_from`), twice round, so the two limbs of a
    narrow loop cannot share one ridge. Returns {name: (points, ridge value)}.
    """
    traced = {name: trace(points, ridge) for name, points in limbs.items()}
    if len(limbs) == 2:
        for _ in range(2):
            for name in limbs:
                other = next(n for n in limbs if n != name)
                traced[name] = trace(limbs[name], ridge, _apart_from(traced[other][0], ridge.shape))
    return traced


def file_safe(name: str) -> str:
    return re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_')


def overlay(mean: np.ndarray, lines: dict, path: str, scale: int = 2) -> None:
    """The lines on the resting image, each with its name at the base and an arrowhead at its last point."""
    image = cv2.resize(to_uint8(vessel_image(mean)), None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    for (name, line), colour in zip(lines.items(), COLOURS * 3):
        samples = scale * line.sample_positions(1.0)[0]
        cv2.polylines(image, [samples.astype(np.int32)], False, colour, 1)
        if len(samples) > 8:
            cv2.arrowedLine(image, tuple(int(v) for v in samples[-8]), tuple(int(v) for v in samples[-1]), colour,
                            1, tipLength=0.6)
        cv2.putText(image, name, tuple(int(v) for v in samples[0] + [4, 12]), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                    colour, 1)
    cv2.imwrite(path, image)


def traced_lines(stem: str, specs: dict) -> tuple:
    """The centre lines of `specs` (a recording's entry in lines.json) and their mean ridge values; draws them."""
    mean = np.load(os.path.join(OUT, f'{stem}_rest_mean.npy'))
    ridge = ridge_map(mean)
    traced = {}
    loops = {spec['loop'] for spec in specs.values() if spec['kind'] == 'limb'}
    for loop in loops:
        traced.update(trace_loop({name: spec['points'] for name, spec in specs.items()
                                  if spec['kind'] == 'limb' and spec['loop'] == loop}, ridge))
    lines, on_ridge = {}, {}
    for name, spec in specs.items():
        points, on_ridge[name] = traced[name] if spec['kind'] == 'limb' else (spec['points'], float('nan'))
        lines[name] = Centreline.from_points(points)
    overlay(mean, lines, os.path.join(OUT, f'{stem}_lines.png'))
    outside = [name for name, line in lines.items() if not SpaceTimeSampler(line).inside(mean.shape)]
    if outside:
        raise ValueError(f'{stem}: lines leave the frame: {outside}')
    return lines, on_ridge


def measure(stem: str, specs: dict) -> pd.DataFrame:
    """One row per line of `specs` (a recording's entry in lines.json), measured over the rest window."""
    fps, (first, last) = rest_window(stem)
    lines, on_ridge = traced_lines(stem, specs)
    samplers = {name: SpaceTimeSampler(line) for name, line in lines.items()}

    rows = {name: [] for name in lines}
    for frame in iter_frames(video_path(stem), start=first, max_frames=last - first + 1):
        for name, sampler in samplers.items():
            rows[name].append(sampler.row(frame))

    recording = inventory.parse_name(stem)
    results = []
    for name, line in lines.items():
        spec = specs[name]
        diagram = np.asarray(rows[name], dtype=np.float32)
        np.save(os.path.join(OUT, f'{stem}__{file_safe(name)}.npy'), diagram)
        shift = pattern_shift.summarize(diagram, fps, MM_PER_PIXEL)
        blocks = space_time_summary(analyze_space_time(diagram, fps, MM_PER_PIXEL, first_frame=first))
        results.append({
            'recording': stem, 'study': recording.study, 'subject': recording.subject,
            'condition': recording.condition, 'role': inventory.ROLES[recording.condition],
            'line': name, 'loop': spec.get('loop', ''), 'kind': spec['kind'], 'apex_seen': spec.get('apex_seen', ''),
            'length_px': round(line.length_px, 1), 'on_ridge': round(on_ridge[name], 2),
            'rest_first_frame': first, 'rest_last_frame': last, 'rest_frames': diagram.shape[0],
            **shift,
            'limb_check': (pattern_shift.limb_from_direction(shift['pattern_shift_velocity_mm_s'])
                           if spec['kind'] == 'limb' else ''),
            'centre_line_blocks': blocks['blocks'], 'centre_line_resolved_fraction': blocks['resolved_fraction'],
            'centre_line_median_mm_s': blocks['median'], 'centre_line_q25_mm_s': blocks['q25'],
            'centre_line_q75_mm_s': blocks['q75'], 'centre_line_positive_fraction': blocks['positive_fraction'],
            'points': ';'.join(f'{x:.1f},{y:.1f}' for x, y in line.points),
        })
        row = results[-1]
        print(f"{name:16s} {spec['kind']:6s} {row['length_px']:5.0f} px (ridge {row['on_ridge']:.2f})"
              f" | {shift['pattern_shift_speed_px_per_frame'] * fps * MM_PER_PIXEL:+.3f} mm/s,"
              f" snr {shift['pattern_shift_snr']:5.1f} {'OK' if shift['pattern_shift_resolved'] else '--'}"
              f" | halves {shift['pattern_shift_first_half_snr']:5.1f} {shift['pattern_shift_second_half_snr']:5.1f}"
              f" | {row['limb_check'] or '-':8s} | blocks {blocks['resolved_fraction']:.0%}", flush=True)
    return pd.DataFrame(results)


def main(args) -> None:
    trace_only = '--trace-only' in args
    stems = [arg for arg in args if arg != '--trace-only']
    with open(LINES, encoding='utf-8') as handle:
        specs = json.load(handle)
    if trace_only:
        for stem in stems:
            lines, on_ridge = traced_lines(stem, specs[stem])
            print(f'== {stem}')
            for name, line in lines.items():
                print(f'{name:18s} {line.length_px:5.0f} px, ridge {on_ridge[name]:.2f}')
        return
    table = pd.read_csv(RESULTS) if os.path.exists(RESULTS) else pd.DataFrame()
    for stem in stems:
        print(f'== {stem}', flush=True)
        rows = measure(stem, specs[stem])
        if len(table):
            table = table[table['recording'] != stem]
        table = pd.concat([table, rows], ignore_index=True)
        table.to_csv(RESULTS, index=False)


if __name__ == '__main__':
    main(sys.argv[1:])
