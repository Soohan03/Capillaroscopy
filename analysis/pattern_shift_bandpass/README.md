# Band-passed rows for the pattern-shift estimator (2026-10-11)

Before 2026-10-11, `capillary.pattern_shift` compared rows of the space-time
diagram after differencing them along the line, which weights the finest scale
(1–2 px) most. On the recordings that scale is mostly noise, and motion blur
erases it first. These scripts compare the differenced rows with band-passed
rows (a difference of Gaussians along the line) on synthetic recordings with a
known speed and on the lines of the resting-flow feasibility check. The band
chosen, σ 1 and 4 px, became the default. Why, and the numbers, are in the
DEVLOG entry of 2026-10-11.

## Files

| File | What it is |
| --- | --- |
| `validate_synthetic.py` | Six filters (differenced rows; band-passes 1–4, 1–6, 1–8, 1.5–6 and 2–8 px) on 234 simulated 30-s clips: 12 speeds from 0.5 to 30 px/frame, three levels of disturbance, the shutter open for the whole or half the frame interval, and 30 clips without flow per level. Writes `synthetic_results.csv` |
| `validate_real.py` | The same six filters on the 35 lines of `../resting_flow_feasibility/lines.json` (29 limbs, 6 lines through tissue), at rest, in each half of the rest, in occlusion and after release, using the official times. Writes `real_results.csv` |
| `validate_long_line.py` | Faster flow (12–40 px/frame) on the arterial limb's 120-px line against a 300-px line round the simulated loop, 60-s clips, differenced against band-passed (1–4 px) rows. Writes `long_line_results.csv` |
| `real_loops.py` | Lines round 7 whole loops of the recordings (both limbs of `lines.json` joined over the apex), at rest and after release: is there faster flow the limb lines miss? Writes `loops_results.csv` and `out/<recording>_loops.png` (not tracked) to check the lines |
| `*_results.csv` | One row per clip or line, window and filter: the estimate, its signal-to-noise ratio and (except for the loops) 95% interval, whether it lay in the searched range and whether it counts as resolved |

## Rerunning

From the repository, with the videos stabilized by `capillary.stabilize` in
`StabilizedVideos/` (the lines belong to those videos' coordinates):

```
python analysis/pattern_shift_bandpass/validate_synthetic.py     # about 30 s on 14 cores
python analysis/pattern_shift_bandpass/validate_real.py          # about 30 s
python analysis/pattern_shift_bandpass/validate_long_line.py     # about 10 s
python analysis/pattern_shift_bandpass/real_loops.py             # under a minute
```

Each script prints its summary tables; `--summary` prints them again from the
saved CSV without recomputing. The band is passed to `pattern_shift` as
`bandpass_px`; `None` gives the differenced rows.
