# Reproducibility of the placement: plan

Written on 2026-11-05 by the student with Claude Code, a week after the first placement. This file was
committed before the recordings were drawn and before any line of the repeat was placed, so that the draw
and the comparison were fixed before their results could be seen.

`PROTOCOL.md` ("Reproducibility of the placement (later)") fixed on 2026-10-29, before unblinding: on
another day the observer places 10 recordings, drawn at random, again from scratch, under a second
observer code (for example `SJ-R`), also blind, and three things are compared: whether the same reference
capillary is chosen, its velocity, and the recording's value. This plan fixes what the protocol left open:
the recordings drawn from, the draw, how the repeat is kept blind, and how each comparison is computed.

## Why

Aim 1's inter-day CV (63% pooled) holds everything that differs between two recordings of one person on two
days: the flow itself, the field the camera shows, the capillary chosen and where its line lies. Placing the
same recordings again on another day measures the last two alone. A placement CV close to aim 1's would mean
that the choice and placement of the capillary account for most of the between-day variation.

## What has been seen before this plan

- The protocol's results since unblinding (2026-10-29 13:07). The report page and the tables name each
  value's study, participant and visit, never the codes the app lists recordings under during blind
  placement.
- The first placement's lines of one recording: ISMOKE FP04 Sföre, whose three blind loops were measured
  with other filters for the coarse filter and given a test line (`loop4`, since trashed) on 2026-10-29,
  after unblinding. It is left out of the pool. The later analyses (`analysis/whole_loop_limbs/`,
  `analysis/fore_efter_fields/`) used the lines of the aim-1 check or mean images, not the blind lines.

## The pool and the draw

- **The pool: the 72 recordings the aims use** (`capillary.inventory`; `metadata/derived/recordings.csv`),
  without two:
  - ESMOKE FP03 Wefter, on which no line is possible (`PROTOCOL.md`);
  - ISMOKE FP04 Sföre (above).
  - 70 recordings, every one with a reference capillary (`loop1`) in the first placement.
- **The draw:** the pool sorted by name (Unicode NFC), 10 drawn without replacement by numpy's default
  generator with **seed 20261105** (the date of this plan): `numpy.random.default_rng(20261105).choice(70,
  size=10, replace=False)`. Drawn once, by `repeat.py draw`; it is not repeated with another seed.

## Keeping the repeat blind

- **Its own data folder** (`capillaroscopy_placement_repeat/`, beside the repository):
  - `StabilizedVideos/` holds links to the 10 drawn videos and their stabilization files, so blind
    placement lists only them, under their codes (the same codes as in the first placement);
  - `Statistics/` starts empty, so no line of the first placement is drawn on the video, and the names
    `loop1`–`loop3` are free.
- `repeat.py draw` prints only the codes, and the folder's `placement_repeat.json` keeps the seed and the
  codes, not the names. The observer does not look into the folder.
- The app is pointed at the folder with observer **SJ-R** and blind placement on (`repeat.py switch
  repeat`), and back afterwards (`repeat.py switch main`). Progress is checked with `repeat.py progress`
  (codes and loop names only).
- The observer does not look at the first placement's lines while the repeat is under way.
- If, while placing, the observer recognizes a recording and remembers where its lines lay, they write
  down its code before placing it. It is placed as the others and reported as recognized.

## Placing

As `PROTOCOL.md` fixes it (candidates, ranking of the whole field before any line, up to three whole loops
named `loop1`–`loop3`, the official rest), from scratch, without the first placement's notes.

## The comparisons

**The first placement:** observer SJ's whole loops `loop1`–`loop3` on the drawn recordings, saved in blind
placement on 2026-10-29, as `capillary.aims` reads them. **The repeat:** observer SJ-R's, in the repeat's
data folder, read the same way. A loop counts as `capillary.aims` judges it (signal-to-noise 8 or more,
no movement, the official rest, a stabilized video).

**Two lines lie on the same capillary** when at least half of either line lies within 5 px of the other
(the rule of `capillary.placement`: `MATCH_PX`, `MIN_LINE_OVERLAP`, `line_overlap`). Both lines are on the
same stabilized video, so their coordinates are the same.

1. **The same reference capillary:** of the drawn recordings where both placements placed a `loop1`, in
   how many the two `loop1` lie on the same capillary; with its exact (Clopper–Pearson) 95% interval.
2. **Its velocity:** where the reference is the same capillary and counts in both placements, the two
   velocities (the pooled pattern shift's size, mm/s). Also how often it counts in both, in one, in neither.
3. **The recording's value** (`PROTOCOL.md`: the reference if it counts, else the first backup that counts):
   how many recordings have a value in both, in one, in neither; and, for those with both, whether the two
   values come from the same capillary.

For 2 and 3, with the values of both placements, as aim 1's statistics (`capillary.aims.reproducibility`):
the typical error (SD of the differences / √2) and the CV (typical error over the mean of all values), each
with its 95% interval (chi-square, n − 1 degrees of freedom, as `analysis/primary_endpoint/report.py`), the
CV on the log scale, the smallest detectable change, Bland–Altman as the repeat minus the first placement,
and ICC(A,1).

**Also reported, descriptive:** the same statistics for the mean of the counted loops (the protocol's
secondary value); and how many of the repeat's loops lie on a capillary of the first placement, and on
which rank.

## Reading the result

There are no pass marks. The placement CV of the recording's value (3) is set beside aim 1's inter-day CV;
the share of recordings with the same reference (1) says how far the ranking rule picks the same capillary
from the same video. About 60% of the recordings had a value in the first placement, so 3 will rest on
roughly five or six pairs and 2 on fewer: their intervals will be wide, and they are reported as they come.

## Limits

- One observer, ten recordings, one week apart. The observer placed these recordings once before and may
  remember some of them.
- The repeat sees the same video and frames, so it leaves out the field and the flow, which aim 1 includes.
