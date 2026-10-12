# Aim 1: can resting CBV be measured on the arterial limb at both visits? (2026-10-12)

Aim 1 compares resting CBV between the two before-exposure (före) recordings of each
participant. The PI wants it from the arterial limb only. This check asks, for the
ESMOKE participants whose före recordings were on the desktop: how many limbs per
recording show measurable flow at rest, how many of those are arterial, and in how
many participants does each visit give an arterial limb. What was found is in the
DEVLOG entry of 2026-10-12.

## Recordings

The 16 före recordings of the 8 ESMOKE participants with both visits on the desktop
(FP01, FP03, FP05, FP06, FP07, FP09, FP12, FP13), stabilized by `capillary.stabilize`.
FP01_W (`FP01_W_14-Oct-2019_08-36-26`) is left out because the stabilizer cannot follow
its drift of about 200 px (DEVLOG 2026-10-08). That leaves 15.

## How the lines were placed

- **Who:** Claude Code (the AI assistant), by eye, not the study's observer. It worked
  from the resting image only. The lines were checked and corrected before any of them was
  measured, and none was changed after the results were seen.
  - FP01_Qföre and FP03_Qföre are the exception. Their lines come from the earlier
    feasibility check (`../resting_flow_feasibility/lines.json`, placed 2026-10-08, also
    before any velocity was seen). They are reversed here to run from base to apex.
  - An early test run measured these two before the others were placed; their lines
    were not changed afterwards.
- **The image:** the mean of the official rest window (2 s after the start to 2 s before
  the occlusion), band-passed with a difference of Gaussians (σ 1 and 8 px), vessels
  bright (`rest_image.py`, `zoom.py`). σ 2 and 15 px, as the stabilizer uses, merged the
  two limbs of narrow loops.
- **Which loops:** every capillary loop whose two limbs could be told apart and followed
  from the apex down for at least about 40 px. Loops whose limbs cross at once (figure-of-eight),
  rings, single bands, and loops washed out at the edge of the frame were left out. In
  every recording the apexes point up (towards the nail), which each loop's U-turn
  confirms.
- **Each limb** is given by two or three points from its base to the apex (`lines.json`,
  `kind: limb`). A limb is followed down only as far as it stays apart from the other
  limb: where the limbs cross or merge, the line ends above.
- **Tracing** (`measure.py`, `trace_loop`):
  - Each point is moved to the brightest pixel within 3 px.
  - Consecutive points are joined by the cheapest path along the vessel's ridge (a pixel
    costs 1 + 40 (1 − v)², with v the image scaled to 0–1 around the line).
  - The two limbs of a loop are kept 5 px apart except within 8 px of the apex. Without
    this, the line of a thin limb jumped to the brighter, wider limb beside it.
  - The path is smoothed over 5 px. `on_ridge` in the results is the mean of v along the
    line.
- **One tissue line per recording** runs through tissue between loops, as a control
  (`kind: tissue`, used as placed).
- **Close-up checks** (scratch scripts): each loop at 3–4 times with its traced lines and
  a 10-px grid. Three rounds of corrections were made from them: lines ended above
  crossings, one more point on a thin limb beside a wide one, and four loops dropped.

## How each line is measured (`measure.py`)

Over the official rest window, as a centre-line data set of the app keeps it
(`gui.tasks.summarize_line`):

- the pattern shift pooled over the rest and over each half
  (`capillary.pattern_shift.summarize`); resolved means a signal-to-noise ratio of 8 or
  more;
- the limb that the direction of the pooled flow shows (`limb_from_direction`): flow
  towards the apex is the arterial limb, flow away from it the venous limb, and an
  unresolved line is unknown;
- the centre-line method's 3-s blocks: the share resolved, their median and quartiles,
  and the share running along the line.

## When a limb counts as measured (`summarize.py`)

Three levels, from the app's rule to an exploratory combination:

1. **Resolved:** the pooled pattern shift reaches a signal-to-noise ratio of 8 (the app's
   rule).
2. **Robust:** resolved, and also at least 1.5 px/frame (0.06 mm/s), with a 95% interval
   clear of zero. Set before any result was seen, from the method's validation:
   - near its slowest speed (1 px/frame), slow drift pulls the band-passed estimate
     (DEVLOG 2026-10-11);
   - an interval across zero means the blocks disagree on the direction, which the limb
     check rests on.
3. **Combined (exploratory):** robust, or else the centre-line method's blocks, when at
   least 25% of them are resolved and at least 90% of those run the same way. The velocity
   is then their median. Without flow, the benchmark resolves 7–11% of blocks under strong
   jitter.
   - This level was added after the first results. Many limbs scored high at the pattern
     shift's slowest speed (0.04 mm/s), and their space-time pictures showed streaks slower
     than that, which the centre-line method measures.
   - It needs confirming on recordings it was not made on.

In every loop with both limbs measured, the two must run opposite ways, one towards the
apex and one away from it. `summarize.py` counts the loops that do. Drift of the image
moves both limbs the same way.

## Files

| File | What it is |
| --- | --- |
| `lines.json` | The lines, per recording, in the coordinates of the stabilized video: limbs (`loop`, `points` from base to apex) and the tissue line |
| `results.csv` | One row per line: length, `on_ridge`, the `pattern_shift_...` keys, `limb_check`, the centre-line blocks (`centre_line_...`), and the traced points |
| `summary_recordings.csv` | Per recording and level: limbs measured, arterial, venous, loops with both limbs and those running opposite ways, the velocities, the tissue line's score |
| `summary_participants.csv` | Per participant, visit and level: limbs and arterial limbs measured; whether both visits give an arterial limb, or any limb |
| `common.py` | Paths, the recordings aim 1 uses (`capillary.inventory`), the rest window, the band-pass |
| `rest_image.py`, `zoom.py` | The resting image with a grid, and zoomed parts of it, to place points |
| `measure.py` | Traces and measures the lines (`--trace-only` only traces and draws them) |
| `summarize.py` | The two summaries, printed as Markdown tables |

`out/` (not tracked) holds the resting images, the lines drawn on them
(`<recording>_lines.png`, an arrowhead at the apex end) and each line's space-time
diagram (`<recording>__<line>.npy`).

## Rerunning

From the repository, with the stabilized videos in `StabilizedVideos/` (the lines belong
to their coordinates):

```
python analysis/aim1_feasibility/rest_image.py <recording> ...   # about 10 s each
python analysis/aim1_feasibility/measure.py <recording> ...      # about a minute each
python analysis/aim1_feasibility/summarize.py
```
