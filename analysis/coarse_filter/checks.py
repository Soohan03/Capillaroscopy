"""PLAN.md's checks of the post-hoc rule: V1 synthetic loops, V2 the occlusion, V3 the direction after release.

python3 analysis/coarse_filter/checks.py real        (the 200 blind loops; about 10 minutes on 12 cores)
python3 analysis/coarse_filter/checks.py synthetic   (about 5 minutes on 14 cores)
python3 analysis/coarse_filter/checks.py summary     (prints the checks and whether the rule passes them)

`real` measures every whole loop placed blind (observer SJ, loop1-loop3) by `rule.measure` over the official
rest (its saved space-time diagram, as the app measured it), the occlusion and the after-release window (both
sampled from the stabilized video as the app samples a line), and checks that step 1 at rest judges every loop
as its saved data set. It writes Reports/coarse_filter/measurements.csv in the data folder (it holds resting
velocities; the summary prints none). `synthetic` writes synthetic_results.csv here.
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rule  # noqa: E402

from capillary import aims, datasets, inventory, stabilize  # noqa: E402
from capillary.spacetime import Centreline, SpaceTimeSampler  # noqa: E402
from capillary.video import iter_frames, probe_video  # noqa: E402

OBSERVER = 'SJ'
#: PROTOCOL.md: unblinded at 13:07. A line saved later (ISMOKE FP19 Cefter's loop3, 13:53) was not placed blind.
UNBLINDED = '2026-10-29T13:07:00'
WINDOWS = ('occlusion', 'after release')
#: PLAN.md's pass marks.
MAX_FALSE_FLOW = 0.05
MAX_MEDIAN_ERROR = 0.10
WITHIN_20 = 0.90
MIN_SAME_WAY = 0.80
MIN_LOOPS_V3 = 5
#: The recording that suggested the rule; every check is also reported without it.
SUGGESTED_BY = 'ISMOKE_FP04_Sföre_11-Nov-2020_08-58-47'


def data_folder() -> str:
    return aims.default_data_folder() or rule.REPOSITORY


def out_dir() -> str:
    path = os.path.join(data_folder(), 'Reports', 'coarse_filter')
    os.makedirs(path, exist_ok=True)
    return path


def blind_loops() -> pd.DataFrame:
    """The 200 whole loops placed blind: observer SJ, ranked loop1-loop3, over the official rest, saved before
    unblinding."""
    table = aims.collect(os.path.join(data_folder(), 'Statistics'))
    table = aims.loops(table[(table['observer'] == OBSERVER) & (table['created'] < UNBLINDED)])
    table = table[table['dataset'].map(aims.rank).between(1, aims.RANKED_LOOPS) & (table['phase'] == aims.REST)]
    if len(table) != 200:
        raise SystemExit(f'expected the 200 blind loops, found {len(table)}')
    table = table.reset_index(drop=True)
    table['crosses_itself'] = table['points'].map(aims._crosses_itself)
    return table


# ------------------------------------------------------------------------------------------- real loops

def recording_job(job) -> list:
    """Every loop of one recording: at rest from its saved diagram, in the occlusion and after release from the
    video, read once per window for all of its loops."""
    import cv2
    cv2.setNumThreads(1)
    name, loops_ = job
    folder = data_folder()
    statistics_dir = os.path.join(folder, 'Statistics')
    video = os.path.join(folder, aims.STABILIZED_FOLDER, f'{name}.avi')
    info = probe_video(video)
    phases = inventory.recording_phases(name, info.fps, info.frame_count)
    shifts = stabilize.read_shifts(video)
    rows = []
    lines = {d: Centreline.from_points(p) for d, p in loops_[['dataset', 'points']].itertuples(index=False)}
    for dataset, crossing in loops_[['dataset', 'crosses_itself']].itertuples(index=False):
        diagram = np.load(datasets.line_dataset_files(statistics_dir, name, dataset)['space_time'])
        rows.append({'recording': name, 'dataset': dataset, 'window': 'rest', 'crosses_itself': crossing,
                     'picture_ok': True, 'frames': diagram.shape[0], 'apex_px': lines[dataset].apex_arc_px(),
                     **rule.measure(diagram, lines[dataset].apex_arc_px())})
    for window in WINDOWS:
        if phases is None or window not in phases.windows:
            continue
        first, last = phases.windows[window]
        samplers = {d: SpaceTimeSampler(line) for d, line in lines.items()}
        diagrams = {d: [] for d in samplers}
        for frame in iter_frames(video, max_frames=last - first + 1, start=first):
            for d, sampler in samplers.items():
                diagrams[d].append(sampler.row(frame))
        for dataset, crossing in loops_[['dataset', 'crosses_itself']].itertuples(index=False):
            check = stabilize.check_picture(shifts, (info.height, info.width), samplers[dataset].bounds, first, last)
            diagram = np.asarray(diagrams[dataset], dtype=np.float32)
            rows.append({'recording': name, 'dataset': dataset, 'window': window, 'crosses_itself': crossing,
                         'picture_ok': check.off_picture == 0 and check.lost == 0, 'frames': diagram.shape[0],
                         'apex_px': lines[dataset].apex_arc_px(),
                         **rule.measure(diagram, lines[dataset].apex_arc_px())})
    return rows


def real() -> None:
    loops_ = blind_loops()
    jobs = [(name, group) for name, group in loops_.groupby('recording')]
    started = time.time()
    with ProcessPoolExecutor(max_workers=12) as pool:
        rows = [row for rows in pool.map(recording_job, jobs) for row in rows]
    t = pd.DataFrame(rows)
    rest = rule.judge(t[t['window'] == 'rest']).set_index(['recording', 'dataset'])
    saved = loops_.set_index(['recording', 'dataset'])['counted']
    differ = rest['s1_counts'].reindex(saved.index) != saved
    if differ.any():
        raise SystemExit(f'step 1 at rest judged {int(differ.sum())} loops unlike their saved data sets')
    path = os.path.join(out_dir(), 'measurements.csv')
    t.to_csv(path, index=False)
    print(f'{len(loops_)} loops, {len(t)} measurements in {time.time() - started:.0f} s; step 1 at rest matches the '
          f'saved data sets; written to {path}')


# ---------------------------------------------------------------------------------------------- synthetic

CONDITIONS = ('as measured', 'faint')
LINES = {'loop 200 px': (20.0, 220.0), 'loop 300 px': (20.0, 320.0)}
SPEEDS = (1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 16.0, 20.0, 25.0, 30.0)
NULL_CLIPS, FLOW_CLIPS, CLIP_FRAMES = 30, 3, 1590


def synthetic_job(job) -> list:
    condition, speed, seed = job
    import cv2
    cv2.setNumThreads(1)
    from capillary import simulate
    from capillary.spacetime import space_time_diagram
    contrast = 20.0 / 3 if condition == 'faint' else 20.0
    recording = simulate.simulate(simulate.hairpin(), CLIP_FRAMES, speed, contrast=contrast,
                                  seed=5000 + 100 * seed + int(10 * speed) + (50_000 if condition == 'faint' else 0))
    rows = []
    for line_name, (start, end) in LINES.items():
        line = recording.drawn_line(start, end, seed=seed)
        diagram = space_time_diagram(recording.frames, line)
        rows.append({'condition': condition, 'line': line_name, 'speed': speed, 'seed': seed, 'crosses_itself': False,
                     **rule.measure(diagram, line.apex_arc_px())})
    return rows


def synthetic() -> None:
    jobs = [(c, 0.0, s) for c in CONDITIONS for s in range(NULL_CLIPS)]
    jobs += [(c, v, s) for c in CONDITIONS for v in SPEEDS for s in range(FLOW_CLIPS)]
    started = time.time()
    with ProcessPoolExecutor(max_workers=14) as pool:
        rows = [row for rows in pool.map(synthetic_job, jobs) for row in rows]
    pd.DataFrame(rows).to_csv(os.path.join(HERE, 'synthetic_results.csv'), index=False)
    print(f'{len(jobs)} clips in {time.time() - started:.0f} s')


# ------------------------------------------------------------------------------------------------ summary

def v1(t: pd.DataFrame, floor: float) -> dict:
    j = rule.judge(t, floor)
    null, flow = j[j['speed'] == 0], j[j['speed'] > 0].copy()
    flow['error'] = flow[f's2_{floor:g}_speed'] / flow['speed'] - 1
    found = flow[flow['s2_counts']]
    out = {'null_line_clips': len(null), 'null_found_flow': int(null['counts'].sum()),
           'null_found_by_step2': int(null['s2_counts'].sum()),
           'flow_line_clips': len(flow), 'flow_step1': int(flow['s1_counts'].sum()),
           'flow_step2': len(found),
           'step2_median_error': float(found['error'].median()) if len(found) else None,
           'step2_within_20': float((found['error'].abs() <= 0.2).mean()) if len(found) else None}
    out['passes'] = out['null_found_flow'] <= MAX_FALSE_FLOW * out['null_line_clips'] and (
        not len(found) or (abs(out['step2_median_error']) <= MAX_MEDIAN_ERROR and out['step2_within_20'] >= WITHIN_20))
    out['judged_on_accuracy'] = bool(len(found))
    # the coarser filter on every flow clip it could see (from the floor up), whatever step 1 found: context
    seen = flow[flow['speed'] > floor]
    hit = seen[seen[f's2_{floor:g}_in_range'].astype(bool) & (seen[f's2_{floor:g}_snr'] >= rule.MIN_SNR)]
    out['coarse_alone_resolved'] = f'{len(hit)} of {len(seen)}'
    out['coarse_alone_median_error'] = float(hit['error'].median()) if len(hit) else None
    return out


def v2(t: pd.DataFrame, floor: float) -> dict:
    j = rule.judge(t[t['window'] == 'occlusion'], floor)
    checked = j[j['picture_ok']]
    out = {'lines': len(j), 'left_out_picture': int((~j['picture_ok']).sum()), 'checked': len(checked),
           'step1_false_flow': int(checked['s1_counts'].sum()), 'step2_added_false_flow': int(checked['s2_counts'].sum())}
    out['step2_rate'] = out['step2_added_false_flow'] / out['checked'] if out['checked'] else None
    out['passes'] = out['checked'] > 0 and out['step2_rate'] <= MAX_FALSE_FLOW
    return out


def v3(t: pd.DataFrame, floor: float) -> dict:
    rest = rule.judge(t[t['window'] == 'rest'], floor).set_index(['recording', 'dataset'])
    after = rule.judge(t[t['window'] == 'after release'], floor).set_index(['recording', 'dataset'])
    after = after[after['picture_ok'] & after['counts']]
    out = {}
    for step in (2, 1):
        keys = rest.index[rest['step'] == step].intersection(after.index)
        same = np.sign(rest.loc[keys, 'speed_px_per_frame']) == np.sign(after.loc[keys, 'speed_px_per_frame'])
        out[f'step{step}_at_rest'] = int((rest['step'] == step).sum())
        out[f'step{step}_counted_after_release'] = len(keys)
        out[f'step{step}_same_way'] = int(same.sum())
    n = out['step2_counted_after_release']
    out['judged'] = n >= MIN_LOOPS_V3
    out['passes'] = bool(out['judged'] and out['step2_same_way'] >= MIN_SAME_WAY * n)
    return out


def gains(t: pd.DataFrame, floor: float) -> dict:
    """How many loops, recordings and aim-1 participants the rule adds (counts only)."""
    rest = rule.judge(t[t['window'] == 'rest'], floor)
    by_recording = rest.assign(rank=rest['dataset'].map(aims.rank)).sort_values('rank').groupby('recording')
    protocol = by_recording['s1_counts'].any()
    either = by_recording['counts'].any()
    wanted = aims.aim1_recordings()
    out = {'loops_step1': int(rest['s1_counts'].sum()), 'loops_step2': int(rest['s2_counts'].sum()),
           'recordings_protocol': int(protocol.sum()), 'recordings_rule': int(either.sum())}
    for study, group in wanted.groupby('study'):
        def pairs(has):
            return int(sum(bool(has.get(inventory.nfc(a), False)) and bool(has.get(inventory.nfc(c), False))
                           for a, c in zip(group['active_recording'], group['control_recording'])))
        out[f'{study}_participants_protocol'] = pairs(protocol)
        out[f'{study}_participants_rule'] = pairs(either)
    return out


def summary() -> None:
    synthetic_t = pd.read_csv(os.path.join(HERE, 'synthetic_results.csv'))
    real_t = pd.read_csv(os.path.join(out_dir(), 'measurements.csv'))
    without = real_t[real_t['recording'] != SUGGESTED_BY]
    result = {}
    for floor in rule.FLOORS:
        result[f'from {floor:g} px/frame'] = {
            'V1 synthetic': v1(synthetic_t, floor),
            'V2 occlusion': v2(real_t, floor), 'V2 occlusion, without FP04 Sföre': v2(without, floor),
            'V3 after release': v3(real_t, floor), 'V3 after release, without FP04 Sföre': v3(without, floor),
            'gains': gains(real_t, floor)}
    with open(os.path.join(HERE, 'checks_summary.json'), 'w', encoding='utf-8') as handle:
        json.dump(result, handle, indent=1, ensure_ascii=False, default=float)
    print(json.dumps(result, indent=1, ensure_ascii=False, default=float))


if __name__ == '__main__':
    {'real': real, 'synthetic': synthetic, 'summary': summary}[sys.argv[1]]()
