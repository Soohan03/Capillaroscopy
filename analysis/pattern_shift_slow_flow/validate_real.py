"""Pattern shift below 1 px/frame on the recordings: the aim-1 lines at rest, and in occlusion as a null.

python analysis/pattern_shift_slow_flow/validate_real.py [--dir <folder>] [--summary]      (a few minutes)

Rest: the space-time diagrams that the aim-1 feasibility check saved over the official rest window
(../aim1_feasibility/out/, written by its measure.py): 109 limbs and 15 lines through tissue in 15
before-exposure recordings. Occlusion: the same lines, traced again from ../aim1_feasibility/lines.json,
sampled from 15 s after the cuff was inflated until 2 s before its release, when the blood should stand
still: a null on the same vessels. (Recordings without an official release time are left out of it.)
Each diagram is measured with the variants of validate_synthetic.VARIANTS, over the whole window and over
each half. Writes real_results.csv and out/<recording>__<line>__occlusion.npy (not tracked).

The occlusion is sampled from the videos in StabilizedVideos/, which were made again on 2026-10-14; the
first run's lines do not fit them. --dir restabilized works on the aim-1 check's rerun instead (its
results, rest diagrams and lines, moved onto the new videos): it writes real_results_restabilized.csv
and out/restabilized/.
"""
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
AIM1 = os.path.join(REPO, 'analysis', 'aim1_feasibility')
OUT = os.path.join(HERE, 'out')
sys.path.insert(0, REPO)
sys.path.insert(0, AIM1)
sys.path.insert(0, HERE)
import common  # noqa: E402  (the aim-1 check's paths: which run is worked on)
from validate_synthetic import VARIANTS, estimate  # noqa: E402

#: The occlusion is measured from this long after the cuff was inflated, when the flow has stopped.
SETTLE_S = 15.0
MM_PER_PIXEL = 0.001328903654


def file_safe(name):
    import re
    return re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_')


def first_run() -> bool:
    """Whether the aim-1 check's first run is worked on (no --dir)."""
    return os.path.samefile(common.FOLDER, AIM1)


def occlusion_folder() -> str:
    """Where the occlusion diagrams go: out/, or out/<folder> for another run of the aim-1 check."""
    return OUT if first_run() else os.path.join(OUT, os.path.basename(common.FOLDER))


def results_path() -> str:
    """real_results.csv, or real_results_<folder>.csv for another run of the aim-1 check."""
    suffix = '' if first_run() else f'_{os.path.basename(common.FOLDER)}'
    return os.path.join(HERE, f'real_results{suffix}.csv')


def lost_frames(stem, first, last):
    """How many frames from `first` to `last` the stabilizer lost (written black; `placed_by` in the shift file)."""
    from common import video_path
    shifts = pd.read_csv(os.path.splitext(video_path(stem))[0] + '___stabilization.csv', index_col='frame')
    if 'placed_by' not in shifts:                          # written before 2026-10-14, when no frame was lost
        return 0
    return int((shifts.loc[first:last, 'placed_by'] == 'lost').sum())


def occlusion_diagrams(stem):
    """The occlusion diagram of every line of `stem` (traced as the aim-1 check traced them).

    None without official times, or when the stabilizer lost frames of the window.
    """
    import json
    import measure                                         # the aim-1 check's tracing; its main() is not run
    from common import LINES, video_path
    from capillary import inventory
    from capillary.spacetime import SpaceTimeSampler
    from capillary.video import iter_frames, probe_video
    info = probe_video(video_path(stem))
    phases = inventory.recording_phases(stem, info.fps, info.frame_count)
    if phases is None or phases.release_s is None:
        return None
    first = math.ceil((phases.occlusion_s + SETTLE_S) * info.fps)
    last = math.ceil((phases.release_s - 2.0) * info.fps) - 1
    lost = lost_frames(stem, first, last)
    if lost:
        print(f'{stem}: occlusion left out, the stabilizer lost {lost} of its {last - first + 1} frames', flush=True)
        return None
    with open(LINES, encoding='utf-8') as handle:
        specs = json.load(handle)[stem]
    lines, _ = measure.traced_lines(stem, specs)
    samplers = {name: SpaceTimeSampler(line) for name, line in lines.items()}
    rows = {name: [] for name in lines}
    for frame in iter_frames(video_path(stem), start=first, max_frames=last - first + 1):
        for name, sampler in samplers.items():
            rows[name].append(sampler.row(frame))
    diagrams = {}
    for name in lines:
        diagrams[name] = np.asarray(rows[name], dtype=np.float32)
        np.save(os.path.join(occlusion_folder(), f'{stem}__{file_safe(name)}__occlusion.npy'), diagrams[name])
    return diagrams


def measure_recording(stem, folder=AIM1):
    import cv2
    cv2.setNumThreads(2)
    common.use(folder)
    lines = pd.read_csv(common.RESULTS)
    lines = lines[(lines.recording == stem) & lines.kind.isin(['limb', 'tissue'])]   # not the whole loops
    windows = {'rest': {name: np.load(os.path.join(common.OUT, f'{stem}__{file_safe(name)}.npy'))
                        for name in lines.line}}
    occlusion = occlusion_diagrams(stem)
    if occlusion is not None:
        windows['occlusion'] = occlusion
    out = []
    for window, diagrams in windows.items():
        for line in lines.itertuples(index=False):
            diagram = diagrams[line.line].astype(float)
            middle = diagram.shape[0] // 2
            for variant in VARIANTS:
                whole = estimate(diagram, variant)
                halves = [estimate(part, variant) for part in (diagram[:middle], diagram[middle:])]
                out.append({'recording': stem, 'subject': line.subject, 'condition': line.condition,
                            'line': line.line, 'loop': line.loop, 'kind': line.kind, 'length_px': line.length_px,
                            'on_ridge': line.on_ridge, 'window': window, 'frames': diagram.shape[0],
                            'variant': variant, 'speed': whole.speed_px_per_frame, 'snr': whole.snr,
                            'ci_low': whole.ci95[0], 'ci_high': whole.ci95[1], 'in_range': whole.in_range,
                            'resolved': whole.resolved, 'blocks': whole.blocks,
                            'first_half_speed': halves[0].speed_px_per_frame, 'first_half_snr': halves[0].snr,
                            'first_half_resolved': halves[0].resolved,
                            'second_half_speed': halves[1].speed_px_per_frame, 'second_half_snr': halves[1].snr,
                            'second_half_resolved': halves[1].resolved,
                            'centre_line_resolved_fraction': line.centre_line_resolved_fraction,
                            'centre_line_positive_fraction': line.centre_line_positive_fraction,
                            'centre_line_median_mm_s': line.centre_line_median_mm_s})
    print(f'{stem}: {len(lines)} lines, windows {", ".join(windows)}', flush=True)
    return out


def summarize(t):
    pd.set_option('display.width', 250)
    pd.set_option('display.max_columns', 40)
    pd.set_option('display.max_rows', 400)
    order = [v for v in VARIANTS if v in set(t.variant)]
    t = t.copy()
    t['mm_s'] = t.speed * 30.0 * MM_PER_PIXEL
    t['clear'] = t.resolved & ((t.ci_low > 0) | (t.ci_high < 0))
    t['slow'] = t.speed.abs() < 1.0
    for window in ('rest', 'occlusion'):
        part = t[t.window == window]
        if part.empty:
            continue
        print(f'\n== {window}: lines resolved (of {part[part.variant == order[0]].shape[0]}), highest score where '
              f'not resolved')
        grid = part.groupby(['variant', 'kind']).agg(
            lines=('resolved', 'size'), resolved=('resolved', 'sum'), interval_clear=('clear', 'sum'),
            below_1=('slow', lambda s: int((s & part.loc[s.index, 'resolved']).sum())),
            max_snr=('snr', 'max'))
        print(grid.unstack('kind').reindex(order).to_string())
    rest = t[(t.window == 'rest') & (t.kind == 'limb')]
    print('\n== rest, loops with both limbs resolved: opposite ways / same way')
    for variant in order:
        part = rest[(rest.variant == variant) & rest.resolved]
        both = part.groupby(['recording', 'loop']).filter(lambda g: len(g) == 2)
        signs = both.groupby(['recording', 'loop']).speed.apply(lambda s: np.sign(s).prod())
        print(f'  {variant:32s} {int((signs < 0).sum())} / {int((signs > 0).sum())}')
    print(f'\n== rest, participants with both visits (of {int((rest.groupby("subject").condition.nunique() == 2).sum())}): '
          'a limb measured at both visits; one towards the apex (arterial) at both')
    for variant in order:
        part = rest[rest.variant == variant]
        towards_apex = (part.speed > 0) & part.resolved
        per_visit = part.assign(towards_apex=towards_apex).groupby(['subject', 'condition']).agg(
            any_limb=('resolved', 'any'), arterial=('towards_apex', 'any'))
        visits = per_visit.groupby('subject').agg(visits=('any_limb', 'size'), any_both=('any_limb', 'all'),
                                                  arterial_both=('arterial', 'all'))
        visits = visits[visits.visits == 2]
        print(f'  {variant:32s} any limb {int(visits.any_both.sum())}, arterial {int(visits.arterial_both.sum())} '
              f'({", ".join(visits.index[visits.any_both])})')
    combined = rest[(rest.centre_line_resolved_fraction >= 0.25)
                    & (np.maximum(rest.centre_line_positive_fraction, 1 - rest.centre_line_positive_fraction) >= 0.9)]
    print('\n== rest, limbs whose centre-line blocks qualified in the aim-1 check (25% resolved, 90% one way): '
          'the pattern shift against the blocks\' median (mm/s)')
    for variant in order:
        part = combined[combined.variant == variant]
        agree = part[part.resolved]
        same = np.sign(agree.mm_s) == np.sign(agree.centre_line_median_mm_s)
        ratio = (agree.mm_s / agree.centre_line_median_mm_s)
        print(f'  {variant:32s} resolved {len(agree)} of {len(part)}, same direction {int(same.sum())}, '
              f'ratio median {ratio.median():.2f} (IQR {ratio.quantile(0.25):.2f}-{ratio.quantile(0.75):.2f})')
    print('\n== rest, resolved limbs: both halves resolved, and their speeds within 25% of each other')
    for variant in order:
        part = rest[(rest.variant == variant) & rest.resolved]
        halves = part.first_half_resolved & part.second_half_resolved
        close = halves & ((part.first_half_speed / part.second_half_speed - 1).abs() <= 0.25)
        print(f'  {variant:32s} {int(halves.sum())} of {len(part)} both halves, {int(close.sum())} within 25%')


def main():
    os.makedirs(occlusion_folder(), exist_ok=True)
    stems = sorted(pd.read_csv(common.RESULTS).recording.unique())
    started = time.time()
    with ProcessPoolExecutor(max_workers=8) as pool:
        rows = [row for rows in pool.map(partial(measure_recording, folder=common.FOLDER), stems) for row in rows]
    table = pd.DataFrame(rows)
    table.to_csv(results_path(), index=False)
    print(f'{len(stems)} recordings in {time.time() - started:.0f} s')
    summarize(table)


if __name__ == '__main__':
    args = common.run_args(sys.argv[1:])
    if args and args[0] == '--summary':
        summarize(pd.read_csv(results_path()))
    else:
        main()
