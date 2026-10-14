# Whole-loop lines (2026-10-14)

One line along a whole capillary loop (up one limb, over the apex and down the
other) measures resting flow in many more loops than a line on each limb. On the
53 loops of the aim-1 rerun with both limbs traced, the app's rule measured 23
whole loops, against 14 loops by either limb. 5 of 7 participants got a loop at
both visits instead of 2. The whole story is in the DEVLOG entry of 2026-10-14.

## The line

- **Joined, not placed.** `../aim1_feasibility/measure.py` (`whole_loops`) joins the
  traced lines of a loop's two limbs. The line runs up the first limb (as listed in
  `lines.json`) from its base to the apex, then down the second limb to its base.
  Nothing more is placed by hand.
- **One velocity per loop.** Flow runs one way round a loop. Positive means flow
  from the first limb's base to the second's, so the first limb is arterial
  (`arterial_limb`).
- **In `results.csv`:** kind `loop`, line `<loop>, whole loop`, with `first_limb`,
  `second_limb` and `arterial_limb`. The limbs and tissue lines are measured as
  before, unchanged.
- **Counted by `../aim1_feasibility/summarize.py`** at each level, in the columns
  `whole_<level>` and `whole_<level>_both_visits`.
  - A whole loop is not counted at a level where both its limbs are measured and
    run the same way, both towards the apex or both away.
  - Blood goes up one limb and down the other, so that is the picture moving.
  - On these recordings it removed one loop at the app's rule (FP06_Qföre H) and four
    in the slow range.

## Why it measures more

- **More of the pattern.** A whole-loop line is about twice as long as a limb (72–357 px,
  median 159), so it pools more of the moving pattern. Its score is a median 1.6 times
  its better limb's (quartiles 1.16–1.91).
- **The same flow, seen too weakly by the limbs.** 12 loops were measured only as whole
  loops. Their limbs' best speeds (unresolved, scores 2.5–15, median 5.1), taken round
  the loop, ran the same way as the whole loop's in 23 of 24 limbs, and lay within 25%
  of it in 15.
- **Not flow beyond the limbs' reach.** The limbs' own best speeds show that they saw
  the same flow (at least one limb within 25% in 10 of the 12 loops). The longer line
  adds signal, not range.

## What was found

Loops measured at rest, of the 53 with two limbs:

| Level | Whole loop | Either limb | Participants with a loop at both visits (of 7): whole loop / limbs |
| --- | --- | --- | --- |
| Resolved (the app's rule) | 23 | 14 | 5 / 2 |
| Robust | 17 | 10 | 5 / 1 |
| Combined (exploratory) | 28 | 17 | 6 / 3 |
| Slow range | 33 | 22 | 6 / 4 |

Seven participants have loops with two limbs at both visits. FP12_Qföre has none, so
FP12 cannot have a whole loop at its control visit.

- **Where loop and limbs were both measured** (11 loops): the whole loop's speed is a
  median 0.94 of its limbs' mean (range 0.64–1.03). The same arterial limb is named in
  11 of 11.
- **The whole loops measured** (app's rule): 0.048–0.33 mm/s, median 0.092. The 95%
  interval is clear of zero in 20 of 23, and both halves of the rest score 8 or more in 16.
- **The occlusion as a null** (from 15 s after the cuff went up until 2 s before its
  release, as in the slow-range validation):
  - none of the 21 loops measured at rest shows flow, their scores falling to a median 4.0;
  - over all 46 loops, 3 show flow: FP05_Wföre A and C and FP07_Wföre D, at 0.05–0.08
    mm/s, none of them measured at rest;
  - at the same rule, single limbs show flow under the cuff in 2 of 97.

## Limits

- **One speed per loop.** The arterial and venous limbs' speeds are pooled, so the
  limbs are not told apart by speed. The flow's direction still names the arterial limb.
- **Not yet tested on unseen recordings.** This was found on the 16 recordings the
  method was developed on. The 6 ESMOKE participants not yet measured are its first test.
- **Some loops have no whole-loop line.** Loops with only one limb traced have none
  (FP12_Qföre's two, among others). Figure-of-eight loops are still left out by the
  placement rules.

## Files

| File | What it is |
| --- | --- |
| `validate.py` | The comparison at rest and the occlusion null; `--summary` prints it again from the saved files |
| `loops.csv` | One row per loop: the whole loop's score and velocity at each level, its limbs' beside it, and whether the limbs contradict it |
| `occlusion.csv` | The whole loops over the occlusion: score, speed and whether resolved |

`out/` (not tracked) keeps `loops.pkl`, the same table with its list columns, for
`--summary`.

## Rerunning

From the repository, with the re-stabilized videos in `StabilizedVideos/`:

```
python analysis/aim1_feasibility/measure.py --dir restabilized --jobs 8 <recording> ...   # 162 s for all 16
python analysis/aim1_feasibility/summarize.py --dir restabilized
python analysis/whole_loop/validate.py
```
