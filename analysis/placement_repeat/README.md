# Reproducibility of the placement (2026-11-05)

`PROTOCOL.md` plans it: on another day the observer places 10 recordings, drawn at random, again from
scratch, blind, under a second observer code, and the two placements are compared. `PLAN.md` fixes the
pool, the draw and the comparison; it was committed before the draw.

## What was found (2026-11-05)

The 10 drawn recordings (2 ESMOKE, 8 ISMOKE) were placed again as SJ-R, blind, at 17:25–17:35: 21 whole
loops, against 23 in the first placement. Before the comparison, `progress` flagged SA8EY's `loop2` and
`loop3` as lying on one capillary. The observer confirmed an accidental second save, 6 s after `loop2`, so
`loop3` was moved to the repeat folder's `.trash/`; no third loop qualified. The observer recognized none of
the codes.

| Comparison (PLAN.md) | Result |
| --- | --- |
| 1. The same reference capillary | 9 of 10 recordings (95% CI 55–100%) |
| 2. Its velocity, where it counts in both | 3 pairs: 0.082 / 0.085, 0.075 / 0.080, 0.083 / 0.087 mm/s; CV 1% (95% CI 1–8%); the repeat 0.004 mm/s higher (limits 0.001 to 0.007) |
| 2. Whether it counts | the same in all 9: in both 3, in neither 6 |
| 3. The recording's value | in both 4, in neither 6; 3 of the 4 from the same capillary; CV 66% (95% CI 38–247%), log scale 55%, ICC(A,1) 0.02 (−0.93 to 0.89) |
| Also: the mean of the counted loops | 4 pairs, CV 67% (95% CI 38–249%) |
| Also: the repeat's loops on a capillary of the first placement | 18 of 21 (on its loop1 9, loop2 8, loop3 1) |

- **The value's 66% comes from one recording,** ESMOKE FP07 Wföre (EPJXZ). Neither placement's reference
  counted (signal-to-noise 3.8 both times). The first placement's value came from its `loop3` (0.284 mm/s),
  the repeat's from its `loop2` (0.086 mm/s): two capillaries that the other placement did not place. The
  other three values agree within 0.005 mm/s.
- **On the same capillary the placements agree.** Of the 18 loops of the repeat that lie on one of the first
  placement's, the same ones count (5 in both, 13 in neither). The 5 counted in both read 0.047–0.102 mm/s,
  each within 0.005 mm/s of its first reading; two backups agree to the third decimal. The three references
  read 3–7% higher in the repeat, too few to tell a tendency from chance.
- **The losses reproduce.** Every loop that scored 8 or more without counting sat at the slowest speed
  searched (1 px/frame), on the same capillaries in both placements (782X8, M5LN3, 48JBX, both of LK9EV's;
  RAHFG's `loop2` reached 8.0 there in the repeat only). So the recordings without a value come from the
  method, not from where the lines were placed.
- **The one other reference:** ISMOKE FP08 Sefter (M5LN3). The repeat's `loop1` and `loop2` lie on the first
  placement's `loop2` and `loop3`; the first placement's `loop1` was not placed again. No value either time.

**What it means for aim 1.** On the same video, the observer chose the same reference in 9 of 10 recordings
and, where it counted, measured it within 0.005 mm/s (3–7%). So the observer and the line explain little of aim 1's inter-day CV (63%):
most of it comes from what differs between days (the field, the capillaries, the flow). Where a value comes
from a backup, which backup is chosen can move it several-fold (EPJXZ, 3.3 times), as loops of one recording
differ. These rest on 3–5 velocity pairs, from ten recordings, one observer and one week.

## Steps

```bash
python3 analysis/placement_repeat/repeat.py draw            # once: draws 10 of 70 and makes the repeat's data folder
python3 analysis/placement_repeat/repeat.py switch repeat   # app closed: the app opens on that folder, observer SJ-R, blind
#   ... place the 10 recordings in the app as PROTOCOL.md says ...
python3 analysis/placement_repeat/repeat.py progress        # codes and loop names, no result
python3 analysis/placement_repeat/repeat.py switch main     # app closed: back to the main data folder, observer SJ
python3 analysis/placement_repeat/repeat.py compare         # PLAN.md's comparison; tables here
```

The repeat's data folder is `capillaroscopy_placement_repeat/` beside the repository (`--folder` for
another). Its `StabilizedVideos/` holds links to the drawn videos in the main data folder, so it takes no
space, and its `Statistics/` holds the repeat's data sets. Back it up with the main `Statistics/`: the
repeat cannot be placed blind a second time either. Don't open it while the repeat is under way: the
links carry the recordings' names.

## Files

| File | What it is |
| --- | --- |
| `PLAN.md` | The plan, fixed before the draw |
| `repeat.py` | The draw, the settings switch, the progress check and the comparison |
| `recordings.csv`, `loops.csv`, `summary.csv` | Written by `compare`: one row per drawn recording, per loop of either placement, and per comparison |
