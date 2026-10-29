# Measurement and analysis protocol

Fixed on 2026-10-29, before the first line of the study was placed. The student and the PI
agreed on the method (velocity round the whole capillary, in the resting flow), on the
quality control (signal-to-noise above 8) and on one reference capillary per video to begin
with. Two ranked backups were added for when the reference fails the quality control. The
details below were written down the same day.

Any change made after the results were first seen is listed under "Changes after
unblinding", with its reason.

## Recordings

- The 90 recordings the aims use, as `capillary.inventory` chooses them
  (`metadata/derived/recordings.csv`): for each participant and visit, the recording before
  exposure (före) and after it (efter), each the last attempt with 30 s of rest. ESMOKE 54,
  ISMOKE 36.
- All stabilized with `capillary.stabilize` (translation only), on 2026-10-14 and 2026-10-29.
- Measured within the official rest: from 2 s after the video starts to 2 s before the cuff
  goes on (official times in `metadata/`).

## Choosing the capillaries (blind)

- **Blind placement** in the app:
  - the list shows only these 90 recordings, under codes, in the order of the codes;
  - a line's result (velocity, signal-to-noise) is hidden;
  - the range is fixed to the official rest.
  - The observer does not know the participant, the visit, the exposure, or whether a
    recording comes before or after it.
- **Candidates:** loops that lie wholly within the dashed outline (the part of the frame that
  every rest frame shows), whose two limbs and apex can be followed on a still rest frame,
  and whose limbs do not merge with or cross another vessel.
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

## Aim 2: response to exposure

For each study, the participants with a value in all four recordings:

- each visit's change, after minus before;
- the difference in change, active minus control: the mean with its 95% confidence interval
  and a paired t-test, with the Wilcoxon signed-rank test as a check;
- the same on the log scale (the ratio after / before).
- Skin temperature as a covariate, if DynCap has it (it is not in our data as of 2026-10-29).

## Sensitivity analyses

- The reference capillary only, without backups.
- The mean of all loops that count.
- Signal-to-noise thresholds of 7 and 9.

## Blinding

- No result is looked at until all 90 recordings have their lines.
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

## Changes after unblinding

None yet.
