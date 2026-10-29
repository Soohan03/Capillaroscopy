# Measurement and analysis protocol

Fixed on 2026-10-29, before the first line of the study was placed. The student and the PI
agreed on the method (velocity round the whole capillary, in the resting flow), on the
quality control (signal-to-noise above 8) and on one reference capillary per video to begin
with. Two ranked backups were added for when the reference fails the quality control. The
details below were written down the same day.

Any change made after the results were first seen is listed under "Changes after
unblinding", with its reason.

## Recordings

- The recordings the aims use, as `capillary.inventory` chooses them
  (`metadata/derived/recordings.csv`), each the last attempt with 30 s of rest: the recording
  before exposure (före) of both visits for aim 1, and the recordings before and after exposure
  (efter) of the nicotine visit for aim 2. 72 recordings: ESMOKE 41, ISMOKE 31.
  - Until aim 2 was corrected (2026-10-29, "Changes after unblinding") the list held 90: före and
    efter of both visits (ESMOKE 54, ISMOKE 36). All 90 were placed blind.
- All stabilized with `capillary.stabilize` (translation only), on 2026-10-14 and 2026-10-29.
- Measured within the official rest: from 2 s after the video starts to 2 s before the cuff
  goes on (official times in `metadata/`).

## Choosing the capillaries (blind)

- **Blind placement** in the app:
  - the list shows only these recordings, under codes, in the order of the codes;
  - a line's result (velocity, signal-to-noise) is hidden;
  - the range is fixed to the official rest.
  - The observer does not know the participant, the visit, the exposure, or whether a
    recording comes before or after it.
- **Candidates:** loops that lie wholly within the dashed outline (the part of the frame that
  every rest frame shows), whose two limbs and apex can be followed on a still rest frame,
  and whose limbs do not merge with or cross another vessel.
  - A twisted loop whose limbs cross each other does not qualify either. Its line would cross
    itself: the crossing is sampled twice, and the split at the apex that checks each limb on
    its own becomes unreliable. A loop that twists without crossing qualifies; the two sides of
    its line stay about 5 px apart except at the apex, since the line reads 2 px to each side.
    (Clarified on 2026-10-29 during placement, before unblinding. `--progress` flags such lines,
    and the analysis does not count them: the next loop in the ranking takes their place.)
- **Ranking:** the observer plays the rest and ranks the candidates of the whole field before
  placing any line. First comes the loop where blood can be seen moving most clearly (plasma
  gaps, clusters of cells); between equally clear loops, the longer one.
- **Up to three loops per recording,** placed in the order of the ranking and named as the app
  suggests:
  - `loop1` is the reference capillary;
  - `loop2` and `loop3` are its backups.
  - Fewer when fewer qualify; none when none does.
- **The line:** "Whole loop", from the base of one limb, over the apex, to the base of the
  other. A point goes at each bend (about every 15 px), on the middle of the vessel. Either
  limb may come first.
- **Observer code:** every line carries the observer's initials.

## Measuring

The app's measurement, unchanged since 2026-10-14:

- the space-time diagram along the line over the official rest;
- the pattern shift pooled over the rest:
  - rows band-passed along the line (σ 1 and 4 px);
  - shifts over 1–8 frames;
  - speeds from 1 px/frame (the slow range is not used);
- velocity = shift × 30 frames/s × 0.001329 mm/px. Its sign only tells which end of the line
  lies on the arterial limb, so its size is used.
- A line that comes within 3 px of the stabilized frame's black edge in any frame of the rest
  is refused (`stabilize.check_picture`).

## Quality control: when a loop counts

A loop counts when all of these hold (`capillary.aims`):

- **signal-to-noise 8 or more,** with the speed within the measurable range (the app's
  "resolved"). The scores are continuous, so this is the same as "above 8";
- **no movement:** its two limbs did not move opposite ways along the line (that would be the
  picture moving, not flow);
- measured within the official rest, on a stabilized video.

## Each recording's value

- **Primary:**
  - the reference capillary's velocity, if it counts;
  - otherwise the first backup that counts, in the order of the ranking;
  - otherwise no value (missing, not zero).
- **Secondary:** the mean of all its loops that count.

## Aim 1: inter-day reproducibility

For each study, the participants with a value in both before-exposure recordings:

- within-subject CV: the typical error (SD of the differences / √2) over the mean of all
  values; also on the log scale;
- smallest detectable change: 2.77 × the typical error;
- Bland–Altman, active minus control visit: the bias and the 95% limits of agreement;
- ICC(A,1) (two-way, absolute agreement, single measurement) with its 95% interval.

## Aim 2: response to nicotine

As agreed with the PI about a month before unblinding (written here on 2026-10-29, after
unblinding: see "Changes after unblinding"). The participants with a value before and after
exposure on the nicotine visit, W in ESMOKE and S in ISMOKE; the control visit (Q, C) is not
used:

- the change, after minus before: the mean with its 95% confidence interval and a paired
  t-test, with the Wilcoxon signed-rank test as a check;
- the same on the log scale (the ratio after / before, as a geometric mean).
- For each study, and pooled over both as a separate analysis, since the nicotine comes from
  an e-cigarette in ESMOKE and from heated tobacco in ISMOKE. The pooled analysis takes the
  two studies' participants as different people.
- Skin temperature as a covariate, if DynCap has it (it is not in our data as of 2026-10-29).

## Sensitivity analyses

- The reference capillary only, without backups.
- The mean of all loops that count.
- Signal-to-noise thresholds of 7 and 9.

## Blinding

- No result is looked at until all 90 recordings have their lines. After aim 2's correction
  (below), aim 2 is not computed again until the three recordings it gained have theirs.
- Progress is checked with `python3 -m capillary.aims --progress`. It shows the codes, the
  names of each recording's loops and what to fix (a loop placed twice, a missing
  reference), never a velocity or a score. Problems found this way are fixed before
  unblinding.
- While the app is in blind placement, `capillary.aims` does not show results without
  `--unblind`.

## Reproducibility of the placement (later)

On another day, the observer places 10 recordings, drawn at random, again from scratch, under
a second observer code (for example `SJ-R`), also blind. Compared:

- whether the same reference capillary is chosen;
- its velocity;
- the recording's value.

## Fixed before unblinding

Found with `--progress` once every recording had been placed, and fixed without a result
being looked at:

- **29 lines on 13 recordings had been saved without the whole-loop role** (11:58–12:12).
  Returning to a recording seen before restored the role of its try-out line (none), and every
  new line kept it. They had been placed as this protocol asks, round whole loops over the
  official rest in the order of the ranking. They were re-saved as whole loops (`set1` →
  `loop1`, …) from their own points and space-time diagrams
  (`analysis/primary_endpoint/relabel_whole_loops.py`); the 3-s blocks and every number of the
  pooled pattern shift came out exactly as saved. Nothing was placed again. Since then the app
  saves every line as a whole loop during blind placement.
- **A recording skipped by mistake** (ISMOKE FP19 Sföre) was placed, still blind, at 12:37.
- **Not used:** two try-out lines placed while trying the app, before blind placement was switched
  on (09:56 and 09:59, measured over the whole video, on ESMOKE FP01 Qefter_försök2 and FP01
  Qföre). Their results could be seen. The study's loops on both recordings were placed blind
  later, on other capillaries (no overlap with the try-out lines). They are not whole loops, so
  the analysis does not read them.
- **No line possible:** ESMOKE FP03 Wefter. Its picture moved more than the frame is high during
  the rest, so no line stays in the picture over the whole rest. It counts as missing.

## Unblinding

On 2026-10-29 at 13:07, after 200 whole loops had been placed on 89 of the 90 recordings
(10:13–12:37). Results: `analysis/primary_endpoint/` and its report.

## Added after unblinding

These describe the results further; none changes a value or a statistic fixed above.

- 95% intervals for the typical error and the CV (chi-square, n − 1 degrees of freedom), for the
  limits of agreement (Bland & Altman 1999), the Bland–Altman slope, and the limits as ratios.
- The signal-to-noise threshold swept from 4 to 14, beside the protocol's 7 and 9.
- The quality of the lines (shape, clearance, the two halves of the rest, the two limbs, loops of
  one recording) and where each recording's value comes from.
- Exploratory: the second visit against the first, by date.
- Exploratory, post hoc, not agreed with the PI beforehand: a coarser filter for flow too fast for the
  default one (`analysis/coarse_filter/`). Its rule and pass marks were written down and committed
  (`PLAN.md`) before its checks were run; the values above stay the primary result.

## Changes after unblinding

- **Aim 2 corrected to what had been agreed** (2026-10-29, afternoon).
  - About a month before unblinding, the student and the PI agreed that aim 2 looks at each
    participant's recordings before and after exposure on the nicotine visit, when both exist:
    per study, and pooled as a separate analysis, without the control visit.
  - This protocol, written on the day of placement, recorded an older plan by mistake: the
    participants with a value in all four recordings, and the change on the active visit minus
    that on the control visit.
  - The correction came after aim 2 by the old text had been computed at unblinding and looked
    at: ESMOKE 5 of 13 participants, the difference in change −0.097 mm/s (95% CI −0.175 to
    −0.019); ISMOKE none. Those tables are kept in `Reports/aims/aim2_as_first_written/`.
  - Aim 2 gains ISMOKE FP02 and FP08, who have a complete S visit but not a complete C visit
    (no ESMOKE participant has a complete W visit without being in aim 2 already). Their three
    recordings without lines (FP02 Sföre and Sefter, FP08 Sefter) are placed in blind placement,
    under codes, by the same rules, before aim 2 is computed again.
  - The recordings after exposure on the control visit are no longer used; their lines stay on
    disk.
