# A coarser filter for faster flow: post-hoc plan

Written on 2026-10-29 after unblinding (13:07), by the student with Claude Code, **without the PI**. It is
exploratory and does not change the protocol's analysis (`PROTOCOL.md`), which stays the primary result.
This file was committed before any of the checks below was run, so that the rule and the pass marks were
fixed before their results were seen.

## Why

On ISMOKE FP04 Sföre the student sees blood moving, but none of the three loops placed blind counts
(signal-to-noise 2.6–4.2). With the rows band-passed at σ 4 and 16 px instead of 1 and 4, all three gave
0.40–0.48 mm/s (signal-to-noise 6.3–7.1). In the occlusion none of them showed that speed, and after release
all three ran the same way, faster. A likely reason: at about 11 px/frame the fine detail that the default
filter keeps (wavelengths about 5–24 px at half power, peak about 10 px) is smeared within each frame, and
only coarser detail (long plasma gaps, clumps of cells) is left to follow. The default filter was chosen on
2026-10-11 on limbs with slow flow (about 0.1 mm/s, 2–3 px/frame). If faster flow is missed, the study's
counted loops (about 0.04–0.15 mm/s) would be biased towards slow capillaries.

**Seen before this plan was written:** the protocol's results (unblinded at 13:07), and on FP04 Sföre only
its three blind loops and a test line placed after unblinding (`loop4`, 14:04), measured at rest, in the
occlusion and after release with the rows differenced and band-passed at σ 1–4, 2–8, 4–16 and 8–32 px. There,
the σ 4–16 filter also turned the slow creep in the occlusion (1 px/frame by the default filter) into
"flow" at 0.05–0.07 mm/s, signal-to-noise 22–28. Nothing else was measured with another filter.

## The post-hoc rule

For each of the 200 whole loops placed blind (observer SJ, `loop1`–`loop3`, the official rest):

1. **Step 1, the protocol:** as measured and judged now. A loop that counts keeps its value.
2. **Step 2, the coarser filter**, only for a loop whose sole failure in step 1 is "not resolved" (signal-to-
   noise below 8, or the speed at the edge of the searched range): the pattern shift on the same saved
   space-time diagram, with the rows band-passed at **σ 4 and 16 px**, and speeds searched **from 5 px/frame
   (0.20 mm/s)** up; everything else as the app measures. It counts when the signal-to-noise is 8 or more,
   the speed lies inside the searched range (not at 5 px/frame, not at the top), and the two limbs, each
   measured the same way, are not both resolved with opposite signs.
   - Why from 5 px/frame: step 2 is there for flow too fast for the default filter. The default filter is
     validated on synthetic flow up to 8 px/frame and longer lines, and blur over 5 px or more begins to
     smear its finest detail. Below 5 px/frame a result from the coarser filter is more likely the broad
     changes it lets through (FP04's creep in the occlusion) than flow the default filter missed.
3. Each recording's value as the protocol fixes it: the reference (`loop1`) if it counts by either step,
   else the first backup that counts.

**Sensitivity:** step 2 searching from 3 and from 8 px/frame.

## The checks, and when the rule passes

Only counts, directions and accuracy on synthetic flow; no resting velocity of the study's loops.

- **V1, synthetic loops** (`capillary.simulate`, the hairpin; lines of 200 and 300 px drawn as a person
  would; 53-s clips, about the rest; disturbances as measured, and faint (a third of the cells' contrast);
  the shutter open the whole frame). No flow: 30 clips per condition. Flow at 1, 2, 3, 5, 8, 12, 16, 20, 25 and
  30 px/frame: 3 clips each.
  - Passes when the rule (step 1 or 2) finds flow in at most 5% of the no-flow line clips (6 of 120), and
    where step 2 finds the flow, its median error is within ±10% and 90% of its results within ±20%.
  - The 2026-10-11 checks resolved 12–40 px/frame on 300-px synthetic lines with the default filter, so the
    simulator may not reproduce the loss of fine detail: then V1 tests step 2's accuracy and false alarms,
    not the reason for it. Reported either way.
- **V2, the occlusion** (blood held still by the cuff at 200 mmHg): each of the 200 lines over the
  official occlusion, judged by the same rule. Lines that leave the picture or meet lost frames
  (`stabilize.check_picture`) are left out and counted. A loop that counts there is a false alarm.
  - Passes when step 2 adds false alarms in at most 5% of the lines checked. Step 1's own rate is
    reported beside it.
- **V3, after release:** the same lines over the official after-release window, by the same rule. For
  each loop counted at rest by step 2 and after release by either step: whether the flow runs the same
  way along the line.
  - Passes when at least 80% run the same way (not judged with fewer than 5 such loops). Step 1's loops
    are reported beside them.
- Each check is also reported without FP04 Sföre, which suggested the rule.

## Then

Aim 1 per study with the post-hoc rule (from 5 px/frame; 3 and 8 as sensitivity), with the protocol's
statistics, beside the protocol's results. Computed and reported whatever the checks show, marked with
whether the rule passed them. In the thesis it can only be an exploratory, post-hoc analysis that the PI
had not agreed to beforehand.
