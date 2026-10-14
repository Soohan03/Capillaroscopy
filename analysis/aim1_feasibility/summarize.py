"""Aim 1's feasibility from results.csv: what each recording and each participant gives at rest.

python analysis/aim1_feasibility/summarize.py [--dir <folder>]

Lists the recordings aim 1 uses (`capillary.inventory`) of every participant
with at least one measured recording, measured or not. --dir works on another
run of the check (common.py). A limb's velocity is counted at three levels, and
a fourth where results.csv has the slow range:

- `resolved`: the app's rule, the pooled pattern shift resolved (signal-to-noise
  ratio 8 or more).
- `robust`: resolved, at least `EDGE_PX_PER_FRAME`, and a 95% interval clear of
  zero. Near the slowest speed reported (1 px/frame) slow drift pulls the
  band-passed estimate (DEVLOG 2026-10-11), and an interval across zero means
  the blocks disagree on the direction, which the limb check rests on. Set
  before any result was seen, from the method's validation.
- `combined` (exploratory, set after the first results were seen): robust, or
  else the centre-line method's 3-s blocks, when at least `CL_MIN_RESOLVED` of
  them are resolved and at least `CL_MIN_ONE_WAY` of those run the same way;
  the velocity is then their median. Many limbs scored high at the pattern
  shift's slowest speed, and the centre-line method measures slower flow.
- `slow` (measured since 2026-10-14): the pooled pattern shift with its slow
  range, from 0.1 px/frame (`min_speed=SLOW_MIN_SPEED`, keys `slow_...`),
  resolved. It is not the app's rule: below 1 px/frame a line cannot tell flow
  from the picture moving along it (CLAUDE.md, Known issues).

The check (arterial or venous) comes from the direction of the velocity along a
line drawn from the base to the apex (`limb_from_direction`). A loop with both
limbs measured must show one of each, since the blood goes up one limb and down
the other: `loops_both` counts such loops and `loops_opposite` those that do.

Where results.csv has whole loops (kind `loop`, measure.py since 2026-10-14),
they are counted on their own at every level: `whole_loops` per recording,
`whole_<level>` of them measured, and per participant
`whole_<level>_both_visits`, a whole loop measured at both visits. A whole loop
is not counted at a level where both its limbs are measured and run the same
way (`<level>_contradicted`): that is the picture moving, not flow.

Writes summary_recordings.csv and summary_participants.csv (every level) into
the run's folder and prints compact Markdown tables.
"""
import os
import sys

import numpy as np
import pandas as pd

import common
from common import MM_PER_PIXEL, aim1_recordings
from capillary.pattern_shift import limb_from_direction

#: Resolved speeds below this (px/frame) may be drift rather than flow: at 1-1.5 px/frame band-passed
#: rows read 3-19% high on synthetic recordings and recordings without flow scored highest (2026-10-11).
EDGE_PX_PER_FRAME = 1.5
#: Exploratory: the centre-line blocks count when at least this share is resolved. Without flow the benchmark
#: resolves 7-11% of blocks under strong jitter (CLAUDE.md, centre-line limits).
CL_MIN_RESOLVED = 0.25
#: ... and at least this share of the resolved blocks runs the same way (jitter splits them both ways).
CL_MIN_ONE_WAY = 0.9
LEVELS = ('resolved', 'robust', 'combined')
#: The slow range's level, counted where results.csv has the slow range.
SLOW = 'slow'


def levels_of(table: pd.DataFrame) -> tuple:
    """The levels `table` (results, or a summary of them) is counted at: `LEVELS`, and `SLOW` where it has it."""
    return LEVELS + ((SLOW,) if 'slow_pattern_shift_resolved' in table or SLOW in table else ())


def mark_levels(results: pd.DataFrame) -> pd.DataFrame:
    """`results` with `<level>_mm_s` (NaN when not measured at that level) and `<level>_check` for each level."""
    results = results.copy()
    ps = results['pattern_shift_velocity_mm_s']
    resolved = results['pattern_shift_resolved'].astype(bool)
    fast_enough = results['pattern_shift_speed_px_per_frame'].abs() >= EDGE_PX_PER_FRAME
    one_sign = results['pattern_shift_ci95_low_mm_s'] * results['pattern_shift_ci95_high_mm_s'] > 0
    robust = resolved & fast_enough & one_sign
    positive = results['centre_line_positive_fraction']
    blocks = (results['centre_line_resolved_fraction'] >= CL_MIN_RESOLVED) & \
        (np.maximum(positive, 1 - positive) >= CL_MIN_ONE_WAY)
    results['resolved_mm_s'] = ps.where(resolved)
    results['robust_mm_s'] = ps.where(robust)
    results['combined_mm_s'] = ps.where(robust, results['centre_line_median_mm_s'].where(blocks))
    results['combined_method'] = np.where(robust, 'pattern shift', np.where(blocks, 'centre line', ''))
    if SLOW in levels_of(results):
        results['slow_mm_s'] = results['slow_pattern_shift_velocity_mm_s'].where(
            results['slow_pattern_shift_resolved'].astype(bool))
    for level in levels_of(results):
        results[f'{level}_check'] = [limb_from_direction(v) if kind == 'limb' else ''
                                     for v, kind in zip(results[f'{level}_mm_s'], results['kind'])]
    if (results['kind'] == 'loop').any():
        # A whole loop whose two limbs are both measured and run the same way (both towards the apex, or both
        # away) shows the picture moving, not flow: blood goes up one limb and down the other. It is not counted.
        by_line = results.set_index(['recording', 'line'])
        for level in levels_of(results):
            speeds = by_line[f'{level}_mm_s']
            contradicted = []
            for row in results.itertuples(index=False):
                limbs = ([speeds.get((row.recording, row.first_limb), np.nan),
                          speeds.get((row.recording, row.second_limb), np.nan)] if row.kind == 'loop' else [np.nan, np.nan])
                contradicted.append(bool(np.isfinite(limbs).all() and np.sign(limbs[0]) == np.sign(limbs[1])))
            results[f'{level}_contradicted'] = contradicted
            results.loc[results[f'{level}_contradicted'], f'{level}_mm_s'] = np.nan
    return results


def _speeds(part: pd.DataFrame, column: str) -> str:
    return ', '.join(f'{abs(v):.3f}' for v in part[column])


def per_recording(results: pd.DataFrame, wanted: pd.DataFrame) -> pd.DataFrame:
    rows = []
    has_whole = bool((results['kind'] == 'loop').any())
    for item in wanted.itertuples(index=False):
        part = results[results['recording'] == item.name]
        limbs = part[part['kind'] == 'limb']
        tissue = part[part['kind'] == 'tissue']
        row = {'study': item.study, 'subject': item.subject, 'role': item.role, 'recording': item.name,
               'measured': bool(len(part)), 'limbs': len(limbs), 'loops': limbs['loop'].nunique(),
               'tissue_max_snr': tissue['pattern_shift_snr'].max() if len(tissue) else np.nan}
        if SLOW in levels_of(results):
            row['tissue_max_slow_snr'] = tissue['slow_pattern_shift_snr'].max() if len(tissue) else np.nan
        for level in levels_of(results):
            measured = limbs[limbs[f'{level}_mm_s'].notna()]
            arterial = measured[measured[f'{level}_check'] == 'arterial']
            venous = measured[measured[f'{level}_check'] == 'venous']
            pairs = [loop for _, loop in measured.groupby('loop') if len(loop) == 2]
            row.update({
                level: len(measured), f'{level}_arterial': len(arterial), f'{level}_venous': len(venous),
                f'{level}_loops_both': len(pairs),
                f'{level}_loops_opposite': sum(set(loop[f'{level}_check']) == {'arterial', 'venous'} for loop in pairs),
                f'{level}_arterial_mm_s': _speeds(arterial, f'{level}_mm_s'),
                f'{level}_venous_mm_s': _speeds(venous, f'{level}_mm_s'),
                f'{level}_arterial_mean_mm_s': arterial[f'{level}_mm_s'].abs().mean() if len(arterial) else np.nan,
            })
        if has_whole:
            whole = part[part['kind'] == 'loop']
            row['whole_loops'] = len(whole)
            for level in levels_of(results):
                counted = whole[whole[f'{level}_mm_s'].notna()]
                row.update({f'whole_{level}': len(counted), f'whole_{level}_mm_s': _speeds(counted, f'{level}_mm_s'),
                            f'whole_{level}_mean_mm_s': counted[f'{level}_mm_s'].abs().mean() if len(counted) else np.nan})
        rows.append(row)
    return pd.DataFrame(rows)


def per_participant(recordings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (study, subject), part in recordings.groupby(['study', 'subject'], sort=False):
        row = {'study': study, 'subject': subject}
        visits = {role: part[part['role'] == role] for role in ('active', 'control')}
        measured = {role: len(visit) == 1 and bool(visit['measured'].iloc[0]) for role, visit in visits.items()}
        row['both_measured'] = all(measured.values())
        for level in levels_of(recordings):
            for role, visit in visits.items():
                for key in ('', '_arterial', '_arterial_mean_mm_s'):
                    row[f'{role}_{level}{key}'] = visit[f'{level}{key}'].iloc[0] if measured[role] else np.nan
            row[f'{level}_arterial_both_visits'] = row['both_measured'] and min(
                row[f'active_{level}_arterial'], row[f'control_{level}_arterial']) >= 1
            row[f'{level}_any_both_visits'] = row['both_measured'] and min(
                row[f'active_{level}'], row[f'control_{level}']) >= 1
        if 'whole_loops' in recordings:
            for level in levels_of(recordings):
                for role, visit in visits.items():
                    for key in ('', '_mean_mm_s'):
                        row[f'{role}_whole_{level}{key}'] = visit[f'whole_{level}{key}'].iloc[0] if measured[role] else np.nan
                row[f'whole_{level}_both_visits'] = row['both_measured'] and min(
                    row[f'active_whole_{level}'], row[f'control_whole_{level}']) >= 1
        rows.append(row)
    table = pd.DataFrame(rows)
    counts = [f'{role}_{level}{key}' for role in ('active', 'control') for level in levels_of(recordings)
              for key in ('', '_arterial')]
    if 'whole_loops' in recordings:
        counts += [f'{role}_whole_{level}' for role in ('active', 'control') for level in levels_of(recordings)]
    return table.astype({column: 'Int64' for column in counts})


def markdown(table: pd.DataFrame) -> str:
    """`table` as a Markdown table (numbers to 3 decimals, NaN blank)."""
    def cell(value):
        if value is pd.NA:
            return ''
        if isinstance(value, (bool, np.bool_)):
            return 'yes' if value else 'no'
        if isinstance(value, (float, np.floating)):
            return '' if np.isnan(value) else f'{value:.3f}'
        return str(value)
    lines = ['| ' + ' | '.join(table.columns) + ' |', '| ' + ' | '.join('---' for _ in table.columns) + ' |']
    lines += ['| ' + ' | '.join(cell(v) for v in row) + ' |' for row in table.itertuples(index=False)]
    return '\n'.join(lines)


def compact(recordings: pd.DataFrame, participants: pd.DataFrame) -> tuple:
    """The two summaries shortened for printing: counts as arterial/venous of measured, per level."""
    shown = pd.DataFrame({
        'Participant': recordings['subject'], 'Visit': recordings['role'],
        'Recording': recordings['recording'].str.replace(r'_\d\d-\w{3}-\d{4}_.*$', '', regex=True),
        'Limbs (loops)': [f'{n} ({m})' if measured else 'not measured' for n, m, measured
                          in zip(recordings['limbs'], recordings['loops'], recordings['measured'])]})
    levels = levels_of(recordings)
    for level in levels:
        shown[f'{level.capitalize()}: art/ven'] = [
            f'{a}/{v}' if measured else '' for a, v, measured
            in zip(recordings[f'{level}_arterial'], recordings[f'{level}_venous'], recordings['measured'])]
    shown['Loops both (opposite)'] = [f'{b} ({o})' if measured else '' for b, o, measured in zip(
        recordings['combined_loops_both'], recordings['combined_loops_opposite'], recordings['measured'])]
    shown['Arterial, combined (mm/s)'] = recordings['combined_arterial_mm_s']
    shown['Tissue score'] = recordings['tissue_max_snr']
    if SLOW in levels:
        shown['Tissue score, slow'] = recordings['tissue_max_slow_snr']
    if 'whole_loops' in recordings:
        shown['Whole loops: resolved of all'] = [f'{k} of {n}' if measured else '' for k, n, measured in zip(
            recordings['whole_resolved'], recordings['whole_loops'], recordings['measured'])]
        shown['Whole loops (mm/s)'] = recordings['whole_resolved_mm_s']
    people = pd.DataFrame({'Participant': participants['subject'],
                           'Both visits measured': participants['both_measured']})
    for level in levels:
        people[f'{level.capitalize()}: arterial W / Q'] = [
            f'{a} / {c}' if both else '' for a, c, both in zip(
                participants[f'active_{level}_arterial'].astype(object),
                participants[f'control_{level}_arterial'].astype(object), participants['both_measured'])]
        people[f'{level.capitalize()}: both'] = participants[f'{level}_arterial_both_visits']
    people['Combined: any limb in both'] = participants['combined_any_both_visits']
    if SLOW in levels:
        people['Slow: any limb in both'] = participants['slow_any_both_visits']
    if 'whole_resolved_both_visits' in participants:
        people['Resolved: whole loop in both'] = participants['whole_resolved_both_visits']
    return shown, people


def main(args) -> None:
    common.run_args(args)
    results = mark_levels(pd.read_csv(common.RESULTS))
    wanted = aim1_recordings()
    measured = set(zip(results['study'], results['subject']))
    wanted = wanted[[key in measured for key in zip(wanted['study'], wanted['subject'])]]
    recordings = per_recording(results, wanted)
    participants = per_participant(recordings)
    recordings.to_csv(os.path.join(common.FOLDER, 'summary_recordings.csv'), index=False)
    participants.to_csv(os.path.join(common.FOLDER, 'summary_participants.csv'), index=False)
    shown, people = compact(recordings, participants)
    print(markdown(shown))
    print()
    print(markdown(people))
    print()
    limbs = results[results['kind'] == 'limb']
    tissue = results[results['kind'] == 'tissue']
    for level in levels_of(results):
        both = participants[participants['both_measured']]
        print(f"{level}: {int(limbs[f'{level}_mm_s'].notna().sum())} of {len(limbs)} limbs "
              f"({int((limbs[f'{level}_check'] == 'arterial').sum())} arterial, "
              f"{int((limbs[f'{level}_check'] == 'venous').sum())} venous) in "
              f"{int((recordings[level] > 0).sum())} of {int(recordings['measured'].sum())} recordings; loops with both "
              f"limbs: {int(recordings[f'{level}_loops_both'].sum())}, opposite: "
              f"{int(recordings[f'{level}_loops_opposite'].sum())}; participants with both visits measured: "
              f"{len(both)}, an arterial limb in both: {int(both[f'{level}_arterial_both_visits'].sum())}, any limb "
              f"in both: {int(both[f'{level}_any_both_visits'].sum())}")
    by_blocks = limbs[limbs['combined_method'] == 'centre line']
    print(f"combined by the centre-line blocks: {len(by_blocks)} limbs, "
          f"{by_blocks['combined_mm_s'].abs().min():.3f}-{by_blocks['combined_mm_s'].abs().max():.3f} mm/s")
    print(f"tissue lines: pattern shift resolved {int(tissue['pattern_shift_resolved'].sum())} of {len(tissue)} "
          f"(highest score {tissue['pattern_shift_snr'].max():.1f}); centre-line blocks resolved at most "
          f"{tissue['centre_line_resolved_fraction'].max():.0%}")
    edge = limbs[~limbs['pattern_shift_resolved'].astype(bool) & (limbs['pattern_shift_snr'] >= 8)]
    print(f"unresolved limbs scoring 8 or more at the pattern shift's slowest speed "
          f"({MM_PER_PIXEL * 30:.3f} mm/s at 30 fps): {len(edge)} in {edge['recording'].nunique()} recordings")
    if SLOW in levels_of(results):
        slow = limbs[limbs['slow_mm_s'].notna()]
        clear = slow['slow_pattern_shift_ci95_low_mm_s'] * slow['slow_pattern_shift_ci95_high_mm_s'] > 0
        below = slow['slow_pattern_shift_speed_px_per_frame'].abs() < 1
        print(f"slow range: {len(slow)} limbs resolved, {int(clear.sum())} with a 95% interval clear of zero, "
              f"{int(below.sum())} below 1 px/frame ({slow['slow_mm_s'].abs().min():.3f}-"
              f"{slow['slow_mm_s'].abs().max():.3f} mm/s); tissue lines resolved "
              f"{int(tissue['slow_pattern_shift_resolved'].astype(bool).sum())} of {len(tissue)} (highest score "
              f"{tissue['slow_pattern_shift_snr'].max():.1f})")
    whole = results[results['kind'] == 'loop']
    if len(whole):
        both = participants[participants['both_measured']]
        for level in levels_of(results):
            speeds = whole[f'{level}_mm_s'].dropna().abs()
            print(f"whole loops, {level}: {len(speeds)} of {len(whole)} loops in "
                  f"{int((recordings[f'whole_{level}'] > 0).sum())} of {int(recordings['measured'].sum())} recordings "
                  f"({speeds.min():.3f}-{speeds.max():.3f} mm/s; {int(whole[f'{level}_contradicted'].sum())} not "
                  f"counted, their limbs running the same way); participants with a whole loop at both visits: "
                  f"{int(both[f'whole_{level}_both_visits'].sum())} of {len(both)}")


if __name__ == '__main__':
    main(sys.argv[1:])
