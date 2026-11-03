# Whole loops and their two limbs (2026-11-03)

Two questions that came up while preparing the supervisor meeting of 2026-10-23, run first as
scratch checks and saved here so they can be rerun:

1. A whole-loop line pools both limbs into one speed. Which speed does it report when the arterial
   and venous limbs move at different speeds? (`two_speeds.py`, synthetic space-time diagrams)
2. Why does an arterial limb on its own reach the threshold so rarely? (`real_limbs.py`, the
   aim-1 check's lines on 16 before-exposure ESMOKE recordings)

The whole story is in the DEVLOG entry of 2026-11-03.

## The whole loop follows the stronger limb; it does not average them

Synthetic whole-loop lines, the arterial limb at 3 px/frame (0.12 mm/s), 60 s, both models of the
venous pattern (`compressed`: the arterial pattern compressed, as the same flux in a slower limb;
`independent`: a pattern of its own), three seeds each. Speeds in px/frame:

| Line | Venous limb | Whole loop reads | Mean of the two limbs |
| --- | --- | --- | --- |
| 80 + 80 px (noise 1.3, 6 and 10) | same speed (3.00) | 2.95–2.98 | 3.00 |
| | 25% slower (2.25) | 2.34–2.61 | 2.62 |
| | half the speed (1.50) | 1.51–1.56 | 2.25 |
| venous limb longer, 60 + 100 px | 25% slower | 2.29–2.36 | 2.62 |
| | half the speed | 1.51–1.53 | 2.25 |
| arterial limb longer, 100 + 60 px | 25% slower | 2.73–2.86 | 2.62 |
| | half the speed | 1.54–2.96 (either limb) | 2.25 |
| arterial limb longer, 120 + 40 px | 25% slower | 2.88–2.92 | 2.62 |
| | half the speed | 2.94–2.97 | 2.25 |
| 80 + 80 px without motion blur | 25% slower | 2.33–2.67 | 2.62 |
| | half the speed | 1.50–1.55 | 2.25 |
| 80 + 80 px, venous limb 1.5 times as dark | 25% slower | 2.27–2.33 | 2.62 |
| | half the speed | 1.49–1.53 | 2.25 |

- **With equal limbs the slower limb wins.** At a twofold difference the whole loop reports the
  slower limb's speed; at 25% it lies between the slower limb and the mean.
- **A longer or darker limb pulls it towards itself.** With the arterial half three times as long as
  the venous, it reads the arterial speed.
- **Not motion blur.** Without it the results are the same. The likely cause: a slower pattern stays
  inside its own half of the line for more frames, so it adds more matching pairs to the pooled
  comparison. This is not proven.
- The noise level (1.3 to 10 grey levels) made no difference, and every clip was resolved.

**On the recordings** (part 1 of `real_limbs.py`). In 11 counted whole loops where each limb had
its own best speed (score 5 or more, resolved or not) and the limbs ran opposite ways:

- the whole loop lay nearer the venous limb in 7;
- the arterial limb ran a median 1.10 times as fast as the venous (0.75–1.53);
- in the 5 whose arterial limb was at least 1.2 times as fast, the whole loop read 0.5–12% above the
  venous limb's speed and 9–31% below the arterial's.

## Why the arterial limb alone resolves so rarely

Part 2: the 23 counted whole loops, whose direction names the arterial limb, each loop's two limbs
side by side.

- **Half the line, much less signal.** This is the main reason. The whole loop scored a median 2.7
  times its arterial limb alone (quartiles 2.0–3.4). Arterial limbs scored a median 6.0, under the
  threshold of 8, and 5 more scored 5 to under 8.
- **The arterial limb is the weaker limb.** It was the fainter of the two on the resting image in 17
  of 23 loops (sign test p = 0.035; `on_ridge` median 0.56 against 0.64). It scored lower in 16 of
  23 (p = 0.09). Its line was not shorter (9 of 23), and it ran faster in 13 of 22 (median 1.10
  times, p = 0.52).
- **Resolved on their own:** 9 arterial and 9 venous limbs of these 23 loops. Across all 115 limbs,
  9 arterial and 14 venous.
- **Per recording and participant:** an arterial limb resolved in 8 of 16 recordings, a whole loop
  in 13. Only FP06 had an arterial limb at both visits.

## What it means for the study

- The protocol's resting CBV, a whole loop's velocity, is the velocity of the loop's dominant limb.
  In these loops that is usually the venous one. It is not an arterial CBV, and the methods should
  say so.
- One loop carries the same red-cell flux through both limbs. An exposure that changes the flow
  changes both limbs' velocities by the same factor if their widths do not change. So relative
  comparisons (the CV, the ICC, the ratio after / before) suffer less than absolute values do. A
  loop whose dominant limb differs from one recording to the next adds noise.

## Limits

- The synthetic diagrams are cleaner than real loops: every clip resolved, at scores far above the
  real ones.
- Two simple models of the venous pattern. In a wider venous limb cells may also spread across the
  lumen, which neither model draws.
- Parts 1 and 2 use the aim-1 check's lines, placed by Claude Code during method development, not
  the study's blind lines. The study's 200 blind loops (on the desktop) save each limb's pattern
  shift when it resolves (`pattern_shift_start_limb_…`, `pattern_shift_end_limb_…`), so part 1
  could be repeated on the loops whose two limbs both resolved.

## Files

| File | What it is |
| --- | --- |
| `two_speeds.py` | The synthetic check; writes `two_speeds.csv`, `--summary` prints the table above from it |
| `two_speeds.csv` | One row per clip (144): conditions, the limbs' true speeds, the whole loop's and each half's speed and score |
| `real_limbs.py` | Parts 1 and 2 on the recordings; writes `real_limbs.csv` and prints the numbers above |
| `real_limbs.csv` | The 23 loops of part 2, the arterial and venous limb side by side |

## Rerun

```bash
python analysis/whole_loop_limbs/two_speeds.py     # about 25 s
python analysis/whole_loop_limbs/real_limbs.py     # seconds
```

The scratch runs of 2026-10-23, quoted in that day's briefing, used the same model. Its 80 + 80 rows
are the ones above; for the other lengths it ran fewer noise levels.
