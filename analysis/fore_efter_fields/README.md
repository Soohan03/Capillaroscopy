# Do före and efter show the same capillaries? (2026-11-03)

Aim 2 compares each participant's recording before exposure (före) with the one after it (efter) on
the nicotine visit. If the camera was placed anew between them, each change compares different
capillaries, so the loop-to-loop spread enters every change. This was first checked as a scratch
script on 2026-10-23 and is saved here. The whole story is in the DEVLOG entry of 2026-11-03.

## What was found (the Mac's copies, 2026-11-03)

`same_field.py` compares the band-passed mean images of the official rest. The central half of one
image is searched in the other by normalized cross-correlation, and the pictures are written to
`out/` to look at.

| Pair | Score |
| --- | --- |
| The two halves of one rest, the same field (6 sharp recordings) | 0.97–0.99 |
| Före and efter of one visit: FP01 Q, FP03 Q | 0.32, 0.28 |
| Före of two different participants (2 pairs) | 0.20–0.26 |

- **No loop could be recognized in both images** of FP01's Q visit, FP03's Q visit or FP03's W visit
  (looked at on 2026-10-23). An image match scores före against efter no higher than two different
  participants.
- So the camera was most likely placed anew after the exposure. Aim 2's changes then compare
  different capillaries, and part of each change is the difference between capillaries.
- **Two of the Mac's copies are unreliable:** FP01_W and FP03_Wefter were stabilized on 2026-10-08,
  before the stabilizer could follow large movements. Their two halves match only 0.68 and 0.81, so
  their mean images are smeared. FP03 W was judged by eye only, and FP01 W not at all.

## What it means for aim 2

- Each before→after change contains the difference between capillaries as well as any change in
  flow. Within one recording, loops differ by a median 23% (DEVLOG 2026-10-29). Between the two
  days of aim 1, with different fields, the CV is 63%.
- The report page already lists "the capillary may differ" among the caveats of aim 2. This check
  says it is the usual case, not an exception, at least in the visits checked.

## Limits and what to do next

- Three visits of two ESMOKE participants, on old copies of the videos.
- **Run it on the desktop,** where all 72 recordings the aims use are stabilized with the current
  stabilizer: `python analysis/fore_efter_fields/same_field.py` checks every visit whose two
  recordings are in `StabilizedVideos/`. Then look at the pictures in `out/`.
- Where a visit did keep its field, the same loops could be followed before and after. That would
  be a new analysis, decided before its results are seen.

## Files

| File | What it is |
| --- | --- |
| `same_field.py` | The comparison; writes `scores.csv` and the pictures in `out/` (not tracked); `--summary` prints the table from `scores.csv` |
| `scores.csv` | One row per pair: its kind (`halves`, `same visit`, `different people`), the two recordings, the score and the shift |

## Rerun

```bash
python analysis/fore_efter_fields/same_field.py [--videos <folder>]     # seconds per recording
```
