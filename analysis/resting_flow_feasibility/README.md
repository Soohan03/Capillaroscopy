# Can resting CBV be measured? (started 2026-10-08)

A feasibility check for aim 1: in how many capillaries of the downloaded
ESMOKE recordings can the resting red-cell velocity be measured, and with
which method? Interrupted on the Mac (it overheated) and to be continued on the
desktop. What was found so far, and why, is in the DEVLOG entry of 2026-10-08
("Resting CBV: a first feasibility check").

## Files

| File | What it is |
| --- | --- |
| `lines.json` | The centre lines, per recording: limbs of capillary loops (`limb`) and control lines through tissue (`tissue`), as points in the coordinates of the **stabilized** video |
| `results.csv` | One row per line: the pattern-shift velocity at rest (and its first and second half), in occlusion and after release, with the 95% interval and signal-to-noise ratio; the centre-line method's share of resolved rest blocks and their median |
| `rest_image.py` | Writes `out/<recording>_rest_mean.npy` (mean of the rest window) and `out/<recording>_rest_grid.png` (band-passed, with a grid) to place lines on |
| `zoom.py` | A zoomed part of that image with a 10-px grid: `zoom.py <recording> x0 y0 x1 y1` |
| `measure.py` | Measures every line of a recording, writes `out/<recording>_lines.png` (the lines on the resting image) and replaces the recording's rows in `results.csv` |
| `validate_pattern_shift.py` | The synthetic validation of `capillary.pattern_shift` (138 clips, about 5 minutes) |

## How the lines were placed

On the resting image (the band-passed mean of the stabilized video between
2 s and 2 s before the official occlusion), points were placed by eye along
the middle of clearly visible capillary limbs. `measure.py` moves them onto
the vessel's ridge (within 4 px across the line) and smooths the result.
Tissue lines are used as placed. Lines were chosen from the image alone,
before any velocity was seen.

The coordinates belong to videos stabilized by `capillary.stabilize` at commit
`af1dce6` or later, the stabilizer that re-centres on the median position. A
video stabilized by other code has other coordinates.

## Continuing on the desktop

1. Copy the 9 raw recordings into `RecordedVideos/` (they were in
   `Video_inventory/` on the Mac, from DynCap), and stabilize them:
   `python3 -m capillary.stabilize RecordedVideos/<name>.avi --out StabilizedVideos/<name>.avi`
   (2–3 minutes each, at most 200 MB of memory).
2. For every recording in `lines.json`, run
   `python3 analysis/resting_flow_feasibility/rest_image.py <recording>`, then
   `python3 analysis/resting_flow_feasibility/measure.py <recording>`.
3. Still to do: FP03_Wföre (stabilized but not measured), and FP03_Qefter_försök2
   again (its rows in `results.csv` predate the estimator fix of 2026-10-08).
   FP01_W and FP03_Wefter need the stabilizer to follow large movements first
   (DEVLOG).
