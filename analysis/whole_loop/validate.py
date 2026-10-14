"""Whole-loop lines against single limbs: are more loops measured, and is it flow? (2026-10-14)

python analysis/whole_loop/validate.py [--summary]      (about two minutes; --summary from the saved CSVs)

Reads the aim-1 check's rerun on the re-stabilized videos
(../aim1_feasibility/restabilized/results.csv), where measure.py measured every
loop with two limbs both as those limbs and as one whole-loop line (kind
`loop`: up the first limb, over the apex, down the second). At rest, per loop:

- measured by the whole-loop line, or by either limb, at each level of
  summarize.py (`resolved` is the app's rule);
- the whole loop's score against its better limb's;
- where both were measured, the whole loop's speed against its limbs', and
  whether the flow's direction names the same arterial limb;
- where only the whole loop was measured, the limbs' best speeds (reported
  even when unresolved) against the whole loop's: the same flow seen too
  weakly by the shorter lines, or flow beyond their reach;
- per participant, a loop measured at both visits.

In the occlusion (from 15 s after the cuff went up until 2 s before its
release, as ../pattern_shift_slow_flow/validate_real.py): the whole-loop lines
sampled again from the videos, a null where flow nearly stops. Recordings
without a release time, or whose occlusion frames the stabilizer lost, are left
out. Writes loops.csv and occlusion.csv.
"""
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
AIM1 = os.path.join(REPO, 'analysis', 'aim1_feasibility')
SLOW_FLOW = os.path.join(REPO, 'analysis', 'pattern_shift_slow_flow')
sys.path.insert(0, REPO)
sys.path.insert(0, AIM1)
sys.path.insert(0, SLOW_FLOW)
import common  # noqa: E402
from summarize import LEVELS, SLOW, mark_levels  # noqa: E402

RUN = 'restabilized'
LEVELS_ALL = LEVELS + (SLOW,)
#: The occlusion is measured from this long after the cuff was inflated, as in validate_real.py.
SETTLE_S = 15.0


def loop_table(results: pd.DataFrame) -> pd.DataFrame:
    """One row per whole loop with its two limbs' results beside it (`results` marked by `mark_levels`)."""
    by_line = results.set_index(['recording', 'line'])
    rows = []
    for loop in results[results['kind'] == 'loop'].itertuples(index=False):
        limbs = [by_line.loc[(loop.recording, name)] for name in (loop.first_limb, loop.second_limb)]
        row = {'recording': loop.recording, 'subject': loop.subject, 'role': loop.role, 'loop': loop.loop,
               'length_px': loop.length_px, 'limb_lengths_px': f'{limbs[0].length_px:.0f}/{limbs[1].length_px:.0f}',
               'snr': loop.pattern_shift_snr, 'best_limb_snr': max(limb.pattern_shift_snr for limb in limbs),
               'speed_px_per_frame': loop.pattern_shift_speed_px_per_frame,
               'limb_speeds_px_per_frame': [limb.pattern_shift_speed_px_per_frame for limb in limbs],
               'limb_snrs': [limb.pattern_shift_snr for limb in limbs],
               'first_half_snr': loop.pattern_shift_first_half_snr,
               'second_half_snr': loop.pattern_shift_second_half_snr,
               'ci_clear': loop.pattern_shift_ci95_low_mm_s * loop.pattern_shift_ci95_high_mm_s > 0,
               'arterial_limb': loop.arterial_limb}
        for level in LEVELS_ALL:
            row[f'whole_{level}_mm_s'] = getattr(loop, f'{level}_mm_s')
            row[f'contradicted_{level}'] = getattr(loop, f'{level}_contradicted')
            row[f'limbs_{level}_mm_s'] = [limb[f'{level}_mm_s'] for limb in limbs]
            row[f'limbs_{level}'] = sum(np.isfinite(limb[f'{level}_mm_s']) for limb in limbs)
        # the arterial limb by the limbs' own directions (app's rule): towards the apex is arterial
        checks = {limb.name[1]: limb['resolved_check'] for limb in limbs}
        arterial = [name for name, check in checks.items() if check == 'arterial']
        venous = [name for name, check in checks.items() if check == 'venous']
        others = {loop.first_limb: loop.second_limb, loop.second_limb: loop.first_limb}
        named = set(arterial) | {others[name] for name in venous}
        row['limbs_arterial_limb'] = named.pop() if len(named) == 1 else ('disagree' if named else '')
        rows.append(row)
    return pd.DataFrame(rows)


def occlusion(task):
    """The whole-loop lines of one recording over its occlusion: rows, and a note."""
    import json
    import cv2
    import measure
    from capillary import inventory, pattern_shift
    from capillary.spacetime import SpaceTimeSampler
    from capillary.video import iter_frames, probe_video
    cv2.setNumThreads(2)
    common.use(RUN)
    stem = task
    path = common.video_path(stem)
    info = probe_video(path)
    phases = inventory.recording_phases(stem, info.fps, info.frame_count)
    if phases is None or phases.release_s is None:
        return [], f'{stem}: left out, no official release time'
    first = math.ceil((phases.occlusion_s + SETTLE_S) * info.fps)
    last = math.ceil((phases.release_s - 2.0) * info.fps) - 1
    shifts = pd.read_csv(os.path.splitext(path)[0] + '___stabilization.csv', index_col='frame')
    lost = int((shifts.loc[first:last, 'placed_by'] == 'lost').sum())
    if lost:
        return [], f'{stem}: left out, the stabilizer lost {lost} of its {last - first + 1} occlusion frames'
    with open(common.LINES, encoding='utf-8') as handle:
        specs = json.load(handle)[stem]
    lines, on_ridge = measure.traced_lines(stem, specs)
    loops, _ = measure.whole_loops(specs, lines, on_ridge)
    if not loops:
        return [], f'{stem}: no loop with two limbs'
    samplers = {name: SpaceTimeSampler(line) for name, line in loops.items()}
    rows = {name: [] for name in loops}
    for frame in iter_frames(path, start=first, max_frames=last - first + 1):
        for name, sampler in samplers.items():
            rows[name].append(sampler.row(frame))
    out = []
    for name in loops:
        shift = pattern_shift.summarize(np.asarray(rows[name], dtype=np.float32), info.fps, common.MM_PER_PIXEL)
        out.append({'recording': stem, 'line': name, 'occlusion_first_frame': first, 'occlusion_last_frame': last,
                    'snr': shift['pattern_shift_snr'], 'resolved': bool(shift['pattern_shift_resolved']),
                    'speed_px_per_frame': shift['pattern_shift_speed_px_per_frame'],
                    'mm_s': shift['pattern_shift_velocity_mm_s']})
    return out, f'{stem}: {len(out)} loops'


def participants(loops: pd.DataFrame, level: str) -> tuple:
    """Participants with a loop measured at both visits: by whole loops, by limbs, and how many were compared."""
    flags = loops.assign(whole=loops[f'whole_{level}_mm_s'].notna(), limbs=loops[f'limbs_{level}'] > 0)
    visits = flags.groupby(['subject', 'role'])[['whole', 'limbs']].any().unstack('role')
    visits = visits.dropna()
    return (int((visits['whole'].sum(axis=1) == 2).sum()), int((visits['limbs'].sum(axis=1) == 2).sum()),
            len(visits))


def report(loops: pd.DataFrame, null: pd.DataFrame) -> None:
    pd.set_option('display.width', 220)
    n = len(loops)
    print(f'{n} loops with two limbs in {loops.recording.nunique()} recordings; whole-loop lines '
          f'{loops.length_px.min():.0f}-{loops.length_px.max():.0f} px (median {loops.length_px.median():.0f})\n')
    rows = []
    for level in LEVELS_ALL:
        whole = loops[f'whole_{level}_mm_s'].notna()
        limbs = loops[f'limbs_{level}'] > 0
        by_whole, by_limbs, compared = participants(loops, level)
        rows.append({'level': level, 'whole loop': int(whole.sum()), 'either limb': int(limbs.sum()),
                     'both ways': int((whole & limbs).sum()), 'whole only': int((whole & ~limbs).sum()),
                     'limbs only': int((~whole & limbs).sum()),
                     'not counted, limbs the same way': int(loops[f'contradicted_{level}'].sum()),
                     'participants, whole loop at both visits': f'{by_whole} of {compared}',
                     'participants, a limb at both visits': f'{by_limbs} of {compared}'})
    print('Loops measured at rest, by the whole-loop line and by its limbs')
    print(pd.DataFrame(rows).to_string(index=False))

    ratio = loops.snr / loops.best_limb_snr
    print(f'\nScore of the whole loop / its better limb: median {ratio.median():.2f}, quartiles '
          f'{ratio.quantile(0.25):.2f}-{ratio.quantile(0.75):.2f}, lower in {int((ratio < 1).sum())} of {n}')

    measured = loops[loops.whole_resolved_mm_s.notna()]
    print(f'Whole loops measured (app\'s rule): {len(measured)}, {measured.whole_resolved_mm_s.abs().min():.3f}-'
          f'{measured.whole_resolved_mm_s.abs().max():.3f} mm/s (median {measured.whole_resolved_mm_s.abs().median():.3f}); '
          f'95% interval clear of zero {int(measured.ci_clear.sum())}; both halves scoring 8 or more '
          f'{int(((measured.first_half_snr >= 8) & (measured.second_half_snr >= 8)).sum())}')

    both = measured[measured.limbs_resolved > 0]
    limb_mean = both.limbs_resolved_mm_s.apply(lambda v: np.nanmean(np.abs(v)))
    speed_ratio = both.whole_resolved_mm_s.abs() / limb_mean
    same = (both.arterial_limb == both.limbs_arterial_limb).sum()
    print(f'\nBoth measured ({len(both)} loops): whole loop / mean of its measured limbs, median {speed_ratio.median():.2f} '
          f'(range {speed_ratio.min():.2f}-{speed_ratio.max():.2f}); the same arterial limb named in {int(same)} of '
          f'{int((both.limbs_arterial_limb != "").sum())} where the limbs name one')

    named = both[both.limbs_arterial_limb != '']
    if (named.arterial_limb != named.limbs_arterial_limb).any():
        print(named[named.arterial_limb != named.limbs_arterial_limb][
            ['recording', 'loop', 'arterial_limb', 'limbs_arterial_limb', 'limbs_resolved_mm_s']].to_string(index=False))

    # Each limb's line runs from its base to the apex: flow round the loop runs along the first limb's line and
    # against the second's, so the second limb's speed is compared with its sign turned.
    only = measured[measured.limbs_resolved == 0]
    seen = []
    for row in only.itertuples(index=False):
        for side, speed, snr in zip((1, -1), row.limb_speeds_px_per_frame, row.limb_snrs):
            seen.append({'loop': f'{row.recording[:10]} {row.loop}', 'limb': 'first' if side == 1 else 'second',
                         'whole_px_per_frame': row.speed_px_per_frame, 'limb_px_per_frame': side * speed,
                         'limb_snr': snr})
    seen = pd.DataFrame(seen)
    seen['same_way'] = np.sign(seen.limb_px_per_frame) == np.sign(seen.whole_px_per_frame)
    seen['same_flow'] = seen.same_way & ((seen.limb_px_per_frame / seen.whole_px_per_frame - 1).abs() <= 0.25)
    loops_seen = seen.groupby('loop').same_flow.any()
    print(f'Whole loop only ({len(only)} loops, {len(seen)} limbs): the limb\'s best speed (unresolved), taken round '
          f'the loop, runs the same way as the whole loop\'s in {int(seen.same_way.sum())} limbs and lies within 25% '
          f'of it in {int(seen.same_flow.sum())}, at least one limb in {int(loops_seen.sum())} of {len(loops_seen)} '
          f'loops; limb scores median {seen.limb_snr.median():.1f} (range {seen.limb_snr.min():.1f}-'
          f'{seen.limb_snr.max():.1f})')
    print(seen.round(2).to_string(index=False))

    if null is not None and len(null):
        rest = loops.set_index(['recording', 'loop'])
        null = null.assign(loop=null.line.str.replace(', whole loop', '', regex=False))
        at_rest = [np.isfinite(rest.loc[(r, lp), 'whole_resolved_mm_s']) for r, lp in zip(null.recording, null.loop)]
        null = null.assign(measured_at_rest=at_rest)
        print(f'\nOcclusion (the null): {int(null.resolved.sum())} of {len(null)} whole loops resolved '
              f'(highest score {null.snr.max():.1f}, median {null.snr.median():.1f}); of the '
              f'{int(null.measured_at_rest.sum())} loops measured at rest: {int(null[null.measured_at_rest].resolved.sum())} '
              f'(scores median {null[null.measured_at_rest].snr.median():.1f})')
        print(null[null.resolved].round(3).to_string(index=False))


def main(args) -> None:
    common.use(RUN)
    results = mark_levels(pd.read_csv(common.RESULTS))
    if not (results['kind'] == 'loop').any():
        raise SystemExit('no whole loops in the results: run measure.py --dir restabilized first')
    if '--summary' in args:
        loops = pd.read_pickle(os.path.join(HERE, 'out', 'loops.pkl'))
        null = pd.read_csv(os.path.join(HERE, 'occlusion.csv'))
        report(loops, null)
        return
    loops = loop_table(results)
    stems = sorted(loops.recording.unique())
    with ProcessPoolExecutor(max_workers=8) as pool:
        done = list(pool.map(occlusion, stems))
    for _, note in done:
        print(note)
    null = pd.DataFrame([row for rows, _ in done for row in rows])
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    loops.to_pickle(os.path.join(HERE, 'out', 'loops.pkl'))
    flat = loops.copy()
    for column in [c for c in flat.columns if flat[c].map(lambda v: isinstance(v, list)).any()]:
        flat[column] = flat[column].map(lambda v: ';'.join(f'{x:.4g}' for x in v))
    flat.to_csv(os.path.join(HERE, 'loops.csv'), index=False)
    null.to_csv(os.path.join(HERE, 'occlusion.csv'), index=False)
    print()
    report(loops, null)


if __name__ == '__main__':
    main(sys.argv[1:])
