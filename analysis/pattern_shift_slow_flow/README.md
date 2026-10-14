# The pattern shift below 1 px/frame (2026-10-14)

The aim-1 feasibility check (`../aim1_feasibility/`) found much resting flow slower
than the pattern shift's slowest speed, 1 px/frame (0.04 mm/s). 18 limbs scored 8
or more at that edge, which is never reported. These scripts develop and test a
slow range for `capillary.pattern_shift`: flow down to 0.1 px/frame (0.004 mm/s),
compared over as many frames as the pattern takes to move 2–8 px. The method and
its reasons are in the module's docstring, and the whole story is in the DEVLOG
entry of 2026-10-14.

The slow range is not the default. It is asked for with
`pattern_shift(..., min_speed=pattern_shift.SLOW_MIN_SPEED)` or
`python -m capillary.cli ... --slow-flow`. The default (from 1 px/frame) gives
exactly the results it gave before.

## Variants compared

Every script measures the same diagrams with each variant (`VARIANTS` in
`validate_synthetic.py`):

| Variant | What it does |
| --- | --- |
| `before` | The method before: frame distances 1–8, speeds from 1 px/frame |
| `floor only` | The search simply continued below 1 px/frame, frame distances 1–8 |
| `all lags` | Every frame distance over which the pattern moves 2–8 px, summed (the first design tried) |
| `all lags, mean` | The same, the speed chosen by the frame distances' mean contrast below 1 px/frame |
| `stretched` | The design kept. A speed v is scored as 1 px/frame is, on a time axis stretched by 1/v: term j compares rows j / v frames apart where the pattern has moved j px. The speed found is refined with the frame distances held fixed. Rows compared beyond 8 frames are taken about their own mean |
| `stretched, uncentred` | The same without that last step |
| `stretched, 6-s blocks` | The same with blocks of 6 s instead of 3 s |

## Files

| File | What it is |
| --- | --- |
| `validate_synthetic.py` | 222 simulated 60-s clips: 11 speeds from 0.1 to 3 px/frame (4 clips each) and 30 clips without flow, under the disturbances as measured, strong and faint. Writes `synthetic_results.csv`, and `null_bands.csv` (the highest score of each clip without flow in each speed band) |
| `validate_real.py` | The 124 lines of the aim-1 check (109 limbs, 15 through tissue) at rest, from the diagrams `../aim1_feasibility/measure.py` saved, and in the occlusion, from 15 s after the cuff went up until 2 s before its release (sampled again from the videos). Whole window and each half. Writes `real_results.csv`, or with `--dir restabilized` `real_results_restabilized.csv` (the lines moved onto the re-stabilized videos, 2026-10-14) |
| `validate_wobble.py` | Synthetic clips with the cells standing still or flowing at 0.3 px/frame, while the whole picture moves along the line: sines, sawtooths, bows and steady drifts. Writes `wobble_results.csv` |
| `*_results.csv` | One row per clip or line, window and variant: the estimate (px/frame), its signal-to-noise ratio and 95% interval, whether it lay inside the searched range and whether it counts as resolved |

`out/` (not tracked) holds the occlusion diagrams, `<recording>__<line>__occlusion.npy`.

## Rerunning

From the repository. `validate_real.py` needs the aim-1 check's diagrams in
`../aim1_feasibility/out/` (its `measure.py` writes them), and for the occlusion
the stabilized videos in `StabilizedVideos/`. Since the videos were made again on
2026-10-14, the occlusion needs `--dir restabilized` (see below):

```
python analysis/pattern_shift_slow_flow/validate_synthetic.py    # about a minute on 14 cores
python analysis/pattern_shift_slow_flow/validate_real.py --dir restabilized   # about 1.5 minutes
python analysis/pattern_shift_slow_flow/validate_wobble.py       # about 30 s
```

Each prints its summary tables; `--summary` prints them again from the saved CSV
(`validate_real.py --summary` that of the first run, with `--dir restabilized` that of the
rerun).

## What was found

In short (the numbers are in the DEVLOG):

- **Synthetic recordings.** `stretched` resolved every clip from 0.15 to 1 px/frame,
  within 5% of the truth (median 1%). At 0.1 px/frame, the edge, it resolved 4 of 12.
  It resolved none of the 90 clips without flow (highest score 7.2), and from
  1 px/frame up it gave the same results as `before`. Summing all frame distances
  (`all lags`) read 4% off (median; up to 15%) and resolved 15 of the 90 clips without
  flow.
- **The recordings at rest.** It resolved 42 of the 109 limbs, against 24 before
  (17 of them below 1 px/frame), and no line through tissue.
  - Of the loops with both limbs resolved, 14 ran opposite ways and 4 the same way.
  - Where the aim-1 check's centre-line blocks qualified, it agreed with their
    direction every time (16 limbs), with a median ratio of 0.96.
- **Movement of the picture.** A single line cannot tell slow flow from the picture
  moving along it.
  - In `validate_wobble.py`, with the cells standing still, movements of 10–20 px
    over a few seconds that go one way slower than the other were read as flow in 2–4
    of 10 clips, and a steady drift always. Movements of 2 px were not.
  - On the recordings, FP03_Wföre's loops E and F move the same way in all four
    limbs at rest.
  - In the occlusion, 24 of 97 limbs gave a slow speed. Some come from such
    movements: FP13_Qföre's loop E bows sideways and back in both limbs. Some come
    from the uncovered edge of the stabilized frame crossing the line: FP13_Qföre G
    left. Some look like real residual flow: FP05_Qföre's loop B.
  - From 1 px/frame up these movements stayed below the threshold.
- **On the re-stabilized videos (2026-10-14, `--dir restabilized`,
  `real_results_restabilized.csv`).** The same lines were moved onto the videos made again
  by the new stabilizer, and FP01_W was added (`../aim1_feasibility/restabilized/`).
  - At rest, `stretched` resolved 41 of 115 limbs.
  - In the occlusion, it resolved 22 of 97. FP03_Qföre's occlusion is left out, since the
    stabilizer lost those frames, and FP01_W's comes in.
  - On the 91 limbs whose occlusion both runs measured: 23 before, 22 after. The one
    difference sat at the threshold (score 8.01 → 7.99).
  - So the slow "flow" in the occlusion is not the movement of the whole picture that the
    new stabilizer follows.

## The re-stabilized videos

The occlusion is sampled from `StabilizedVideos/`, which was made again on 2026-10-14. The
first run's lines (`../aim1_feasibility/lines.json`) do not fit the new videos. Run
`validate_real.py --dir restabilized` to use the lines moved onto them, from the aim-1
check's rerun. It writes `real_results_restabilized.csv` and `out/restabilized/`, and leaves
out the occlusion of any recording whose occlusion frames the stabilizer lost.
