# Reproducibility of the placement (2026-11-05)

`PROTOCOL.md` plans it: on another day the observer places 10 recordings, drawn at random, again from
scratch, blind, under a second observer code, and the two placements are compared. `PLAN.md` fixes the
pool, the draw and the comparison; it was committed before the draw.

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
