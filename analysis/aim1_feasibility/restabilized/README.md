# Aim 1's feasibility, again on the re-stabilized videos (2026-10-14)

The check of the folder above (`..`, 2026-10-12) measured resting flow on lines placed on
the videos as they were stabilized on 2026-10-11/12. On 2026-10-14 every video in
`StabilizedVideos/` was made again with the new stabilizer, which follows large movements
frame to frame and builds its references from the official rest (DEVLOG, both entries of
2026-10-14). This folder repeats the check on the new videos, with the same lines, plus
FP01_W, which the new stabilizer could stabilize for the first time. The pattern shift's
slow range is measured alongside the default. What was found is in the DEVLOG entry of
2026-10-14, "Aim 1's feasibility, again on the re-stabilized videos".

The first run's files stay as they were: they are the record of the old videos, which are
now in `.trash/` (one `2026-10-14_…_previous stabilized video` folder per recording).

## The lines

- **The 15 recordings of the first run:** every line of `../lines.json` moved by its
  recording's move (`move_lines.py`). The new stabilizer centres a video on its median
  shift over the official rest, so the picture moved by the same amount in every frame.
  - **The move:** the shift files record how far each frame was moved
    (`shift_x_px`, `shift_y_px`; what the raw frame shows at p, the stabilized frame shows at
    p + shift). A line moves by the median over the official rest of the new shift minus
    the old one (the old shift files are in `.trash/`).
  - **The moves:** 1.8–169 px (`moves.csv`).
    - Registering the old resting image onto the new one (phase correlation) gives the same
      move within 0.4 px in all 15 recordings.
    - In 10 recordings the stabilizer placed the rest frames differently relative to each
      other. Single frames are then off the median move by a median of 0.1–1.0 px (95th
      percentile up to 3.7 px, FP12_Wföre). In the other 5, every frame moved by exactly the
      same amount.
  - **Still on the vessel:** each moved line was traced on the new resting image and
    compared with its first-run trace, moved the same way (`line_check.csv`).
    - All 109 limbs lie within a mean 0.85 px of it. The ridge values are unchanged
      (median difference 0.00).
    - Four lines end 3–6 px from where they ended before: FP03_Qföre F, FP07_Wföre A right,
      FP09_Wföre B left and FP13_Qföre A right. Close-ups showed both traces on the same
      vessel; an end point had snapped to a neighbouring pixel.
    - No line was corrected.
- **FP01_W** (`FP01_W_14-Oct-2019_08-36-26`), added by the same rules as the first run
  (`../README.md`).
  - Placed by Claude Code from its resting image only, before anything was measured:
    loops A, C and E (6 limbs), and one line through tissue between A and B.
  - Loops B and D were left out. They are figure-of-eight loops whose limbs cross about
    30 px below the apex, short of the 40 px the rules ask for.
  - Its name has neither före nor efter (`metadata/README.md`). The inventory takes it as
    before exposure from the time of day.
  - Its official rest lasts 33.6 s, against 52–77 s in the other recordings, so less is
    pooled.

All lines were placed and checked before any of them was measured on the new videos. None
was changed afterwards.

## What is measured

As in the first run (`../measure.py`), over the official rest window. Since 2026-10-14
`measure.py` also measures the pattern shift with its slow range
(`min_speed=pattern_shift.SLOW_MIN_SPEED`, from 0.1 px/frame): the keys `slow_pattern_shift_...`
and `slow_limb_check`. `../summarize.py` counts it as a fourth level, `slow` (resolved).
It is not the app's rule: below 1 px/frame a line cannot tell flow from the picture moving
along it (CLAUDE.md, Known issues).

`compare_runs.py` sets the two runs side by side, line by line. The first run's slow range
comes from the slow-range validation
(`../../pattern_shift_slow_flow/real_results.csv`, variant `stretched`, at rest), which is
the same estimator on the first run's diagrams.

## What was found

(Since 2026-10-14 the rerun also measures whole loops: 23 of 53 at the app's rule,
against 14 by single limbs, and 5 participants with a loop at both visits instead
of 2; see `../../whole_loop/`. What follows is about the limbs.)

- **The results barely changed.**
  - Of the 109 limbs measured in both runs, the default rule resolved 22 in both. It
    resolved two only in the first run (FP01_Qföre's "2" loop, score 8.3 → 7.3; FP13_Qföre F
    right, 8.1 → 6.5) and one only in the rerun (FP09_Qföre A right, 6.9 → 8.7).
  - The velocities of the 22 agree within 0.005 mm/s (rerun/first 0.96–1.07, median 1.00),
    all in the same direction.
- **The scores move by about 5% between two equally good placements of a line.**
  - The scores changed by a median of 5% (90th percentile 18%). They changed as much where
    the stabilizer placed the rest frames exactly as before (only the whole picture moved)
    as where it placed them differently.
  - So the change comes from the line's sub-pixel position and the interpolation, not from
    the better registration.
  - A limb scoring within about 1.5 of the threshold of 8 can fall on either side of it.
- **The better registration at rest did not add limbs.** The stabilizer's match at rest rose
  in FP12_Qföre (0.42 → 0.82), FP12_Wföre (0.42 → 0.87) and FP09_Qföre (0.48 → 0.75).
  FP09_Qföre gained the one limb above, and FP12 gained nothing.
- **The slow range:** 41 of 115 limbs (first run 42 of 109).
  - From 1 px/frame (0.04 mm/s), all 22 limbs measured in both runs agree within 10%.
  - Below it, 10 of 18 agree within 10% and 16 within 25%. Two changed much despite high
    scores (16–20): FP06_Qföre E right went from 0.015 to 0.025 mm/s and FP09_Wföre B left
    from 0.009 to 0.023 mm/s.
  - So below 1 px/frame the speed itself, not only whether flow is there, depends on a
    sub-pixel change of the line.
- **FP01_W gives nothing.** No limb is resolved at any level. The best are E left (score 7.3)
  and E right (5.6), and its tissue line scored 2.0.
- **No tissue line shows flow** (16 lines, highest score 4.5, at the default and the slow
  range).

### Per participant

Eight participants now have both visits measured. For each rule, the number with a limb
measured at both visits:

| Rule | Arterial limb, rerun (of 8) | Any limb, rerun (of 8) | First run (of 7): arterial / any |
| --- | --- | --- | --- |
| Resolved (the app's rule) | 1 (FP06) | 2 | 1 / 2 |
| Robust | 0 | 2 | 0 / 2 |
| Combined (exploratory) | 2 (FP09, FP13) | 5 | 1 / 4 |
| Slow range | 3 (FP06, FP09, FP13) | 4 | 2 / 3 |

FP09 joins the combined and slow rows through the one limb that crossed the threshold. The
first run's conclusion stands: resting CBV from an arterial limb at both visits is
available in at most 3 of 8 participants, whichever rule is used.

## Files

| File | What it is |
| --- | --- |
| `move_lines.py` | Moves the first run's lines onto the new videos and checks them; writes `moves.csv`, `line_check.csv` and `lines.json` (keeping FP01_W's lines) |
| `moves.csv` | Per recording: the move from the shift files and from the images, how far single rest frames lie from it, the stabilizer's median match at rest before and after |
| `line_check.csv` | Per line: length, the mean and largest distance from its first-run trace, ridge value before and after |
| `lines.json` | The lines on the re-stabilized videos: the 15 recordings moved, FP01_W placed (`source`) |
| `results.csv` | One row per line, as `../results.csv`, plus the slow range; since 2026-10-14 also one row per whole loop (kind `loop`, `../../whole_loop/`), the other rows unchanged |
| `summary_recordings.csv`, `summary_participants.csv` | As in the first run, with the `slow` level |
| `compare_runs.py`, `compare_runs.csv` | The two runs line by line: scores and velocities at every level |

`out/` (not tracked) holds the resting images, the lines drawn on them and each line's
space-time diagram, as in the first run.

## Rerunning

From the repository, with the re-stabilized videos in `StabilizedVideos/`. `move_lines.py`
also needs the old shift files in `.trash/` and the first run's resting images in `../out/`.

```
python analysis/aim1_feasibility/rest_image.py --dir restabilized <recording> ...   # about 10 s each
python analysis/aim1_feasibility/restabilized/move_lines.py                         # about a minute
python analysis/aim1_feasibility/measure.py --dir restabilized --jobs 8 <recording> ...   # 162 s for all 16, with whole loops
python analysis/aim1_feasibility/summarize.py --dir restabilized
python analysis/aim1_feasibility/restabilized/compare_runs.py
```
