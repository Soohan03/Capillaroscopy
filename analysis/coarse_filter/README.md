# A coarser filter for faster flow (post hoc)

**Exploratory, post hoc, not agreed with the PI.** The protocol's analysis (`PROTOCOL.md`,
`analysis/primary_endpoint/`) stays the primary result. The rule and its pass marks were written in `PLAN.md`
and committed (0b15b9c, 2026-10-29 14:38) before any check was run; what had been seen before is listed there.

## The rule in short

A loop that does not count by the protocol only because it was not resolved is measured again on its saved
space-time diagram, with the rows band-passed at σ 4 and 16 px (the protocol: 1 and 4) and speeds searched from
5 px/frame (0.20 mm/s) up. It counts with the same quality control (signal-to-noise 8 or more, speed inside the
searched range, limbs not opposite). A recording's value is the protocol's: the reference if it counts by either
step, else the first backup that counts. Sensitivity: step 2 from 3 and from 8 px/frame.

## Rerun

```
python3 analysis/coarse_filter/checks.py real        # the 200 blind loops at rest, in the occlusion, after release (~1.5 min)
python3 analysis/coarse_filter/checks.py synthetic   # synthetic loops (~0.5 min)
python3 analysis/coarse_filter/checks.py summary     # the checks against PLAN.md's pass marks -> checks_summary.json
python3 analysis/coarse_filter/aim1.py               # aim 1 with the rule, beside the protocol -> aim1.csv
```

`rule.py` holds the measurement and the rule. `checks.py real` stops unless step 1 at rest judges every loop as
its saved data set does (it did). Tables with recording names and velocities go to `Reports/coarse_filter/`
in the data folder (`measurements.csv`, `loops.csv`, `pairs.csv`).

The 200 loops are those saved before unblinding (13:07). ISMOKE FP19 Cefter's `loop3` was saved at 13:53, after
unblinding; it is left out here and is not in the primary report either.

## The checks (from 5 px/frame): all three pass

| Check | Pass mark | Result |
|---|---|---|
| V1 synthetic, no flow | rule finds flow in ≤ 6 of 120 line clips | **0 of 120** (also from 3 and 8) |
| V1 synthetic, accuracy of step 2 | median error ≤ ±10%, 90% within ±20% | not judged: step 2 recovered no clip that step 1 missed |
| V2 occlusion | step 2 adds false flow in ≤ 5% of lines | **0 of 163** (from 3: 1 of 163; from 8: 0) |
| V3 after release | ≥ 80% of step 2's loops the same way | **6 of 6** (from 3: 11 of 11; from 8: 5 of 5) |

- **V1:** the simulator mostly does not reproduce the loss of fine detail (as PLAN.md expected from 2026-10-11).
  Step 1 resolved 110 of the 120 flow line clips. It missed 4 at 1 px/frame (the edge of its range, below step 2's)
  and the faint 200-px line at 25–30 px/frame (6 clips, signal-to-noise 5.7–7.6), which step 2 missed too (4.1–7.9).
  So V1 shows that step 2 adds no false flow, not why it is needed. On its own, the coarser filter resolved 54 of
  the 72 flow clips above 5 px/frame, with median errors of −0.3% to −4.3% per speed (−1.6% overall).
- **V2:** 185 of the 200 lines have an official occlusion (6 recordings have no release time, so the occlusion
  window isn't known). 22 left the picture in the occlusion and were left out, so 163 were checked. **The protocol's
  own measurement found "flow" in 12 of the 163 (7%)** during the occlusion: residual flow, or something else that
  passes the quality control. Step 2 added none.
- **V3:** the protocol's own loops: 51 of 51 counted after release ran the same way.
- **Without FP04 Sföre** (the recording that suggested the rule) every result is the same. FP04 Sföre itself gains
  nothing: with the coarser filter its loops reach signal-to-noise 6.3–7.1, below 8.

## Aim 1 with the rule

| | Protocol | Rule (from 5) | from 3 | from 8 |
|---|---|---|---|---|
| Loops counted (of 200) | 91 | 105 (14 by step 2) | 111 | 102 |
| Recordings with a value (of 90) | 54 | 60 | 63 | 60 |
| ESMOKE participants (of 14) | 7 | 9 | 9 | 9 |
| ESMOKE mean, mm/s | 0.130 | 0.176 | 0.176 | 0.184 |
| ESMOKE CV (95% CI) | 67% (43–147) | 69% (47–132) | 69% | 76% |
| ESMOKE CV, log scale | 88% | 107% | 107% | 120% |
| ESMOKE SDC, mm/s | 0.239 | 0.336 | 0.336 | 0.387 |
| ESMOKE ICC(A,1) (95% CI) | 0.01 (−0.67 to 0.71) | 0.31 (−0.39 to 0.79) | 0.31 | 0.19 |
| ISMOKE participants (of 10) | 2 | 3 | 4 | 3 |

- Of the protocol's 54 values, 51 stay as they were. In 3, the reference, now counted by step 2, takes the place
  of a backup. On ESMOKE FP05 Wföre, its loop1 (step 2) and loop2 (step 1) agree, 0.315 and 0.316 mm/s.
  6 recordings gain a value.
- **Step 2 finds faster loops:** median 0.38 mm/s (0.21–0.53) against 0.08 mm/s (0.04–0.32) for the protocol's 91.
  So the protocol's measurement counts mainly slow capillaries; the faster ones lie nearer the 0.3–1 mm/s of the
  literature.
- **The reproducibility does not improve.** In 3 of the 9 ESMOKE pairs one visit's value comes from step 1 and the
  other's from step 2, a slow capillary against a fast one (ratios 0.30, 2.30 and 8.40). Which capillary
  counts on each day dominates the difference between the days. The ICC rises because the participants spread
  further apart, but its interval still includes 0.
- ISMOKE stays too small to judge.

## What it means

The coarser step looks like a valid measurement: no false flow in the synthetic loops or in the occlusion, and
the same direction after release. It shows that the protocol misses faster resting flow, which is worth reporting
as a limitation of the method. But adding those capillaries gives two more ESMOKE participants without making
resting CBV more reproducible between days. The main source of variance is the capillary chosen, not the number
of recordings with a value. This is for the PI to weigh; in the thesis it can only be an exploratory, post-hoc
analysis.
