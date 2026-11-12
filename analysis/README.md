# The analyses

Each folder is one analysis: its scripts, the result tables that could be
tracked, and a README with what was done, what was found and how to rerun it.
The whole story of each is in the `DEVLOG.md` entry of its date.

They fall into three groups. Only the first is the study's planned analysis.

## 1. The protocol's results

Planned in `PROTOCOL.md`, on the whole loops the observer placed blind on
2026-10-29: 200 before unblinding, and 9 more on the three recordings that
aim 2's correction added.

| Folder | Date | What it is |
| --- | --- | --- |
| `primary_endpoint/` | 2026-10-29 | Aim 1 (inter-day reproducibility, the primary endpoint) and aim 2 (the change after nicotine), with the protocol's sensitivity analyses, the quality of every line and what the signal-to-noise threshold removes. Its README has the results |
| `statistics_report/` | 2026-11-03 | Prints every statistic of both aims step by step, from the functions the protocol's analysis uses, so that each reported number can be followed by hand |
| `placement_repeat/` | 2026-11-05 | The protocol's "Reproducibility of the placement": 10 recordings, drawn at random, placed again blind by the same observer. `PLAN.md` was committed before the draw |

## 2. Post hoc analyses of the study's loops

Made after unblinding. The protocol's results stay the primary ones, and each
README says so.

| Folder | Date | What it is |
| --- | --- | --- |
| `coarse_filter/` | 2026-10-29 | Exploratory, not agreed with the PI beforehand: loops the protocol does not resolve, measured again with a coarser filter for faster flow. `PLAN.md`, with the rule and its pass marks, was committed before the checks were run |
| `snr_threshold_6/` | 2026-11-06 | Asked for by the PI: both aims with a loop counting from a signal-to-noise ratio of 6 instead of 8 |

## 3. Method development and checks

How the measurement came to be what the protocol fixes, and what it means.
None of these uses the study's blind lines. Where they use lines, these were
placed on the resting image during development, before any of their velocities
was seen. Each README says who placed them and how; in the aim-1 check it was
Claude Code, not the study's observer.

| Folder | Date | What it is |
| --- | --- | --- |
| `resting_flow_feasibility/` | 2026-10-08 | A first check of whether resting velocity can be measured at all in these videos, and the synthetic validation of the pattern shift. It was interrupted; `aim1_feasibility/` is the larger check that followed |
| `pattern_shift_bandpass/` | 2026-10-11 | Band-passed against differenced rows for the pattern shift, on synthetic and real lines. The band chosen (σ 1 and 4 px) is the estimator's default |
| `aim1_feasibility/` | 2026-10-12 | Can resting velocity be measured on the arterial limb at both visits? 15 before-exposure recordings of 8 ESMOKE participants. `restabilized/` repeats it on the videos of the final stabilizer (2026-10-14). Too few single limbs could be measured |
| `pattern_shift_slow_flow/` | 2026-10-14 | A slow range for the pattern shift, below 1 px/frame, developed and tested. It is not the default: one line cannot tell slow flow from the picture moving along it |
| `whole_loop/` | 2026-10-14 | One line round the whole loop against a line on each limb. It measured more loops, which is why the protocol measures whole loops |
| `whole_loop_limbs/` | 2026-11-03 | Which speed a whole loop reports when its two limbs differ (the dominant limb's, usually the venous one), and why an arterial limb alone rarely reaches the threshold |
| `fore_efter_fields/` | 2026-11-03 | Whether the recordings before and after exposure show the same capillaries. In the three visits checked, no loop could be recognized in both |

## Rerunning

- **What needs the recordings.** The videos and the data sets made on them are
  in the data folder, which is not part of the repository. Scripts that read
  them say so in their README. The tracked tables are their results.
- **What runs anywhere.** The synthetic checks need only the repository:
  `pattern_shift_bandpass/validate_synthetic.py` and `validate_long_line.py`,
  `pattern_shift_slow_flow/validate_synthetic.py` and `validate_wobble.py`,
  `resting_flow_feasibility/validate_pattern_shift.py`,
  `whole_loop_limbs/two_speeds.py` and `coarse_filter/checks.py synthetic`.
- **Shared code.** `aim1_feasibility/` holds the tracing and measuring that
  `pattern_shift_slow_flow/`, `whole_loop/` and `whole_loop_limbs/` reuse, and
  `resting_flow_feasibility/` the lines `pattern_shift_bandpass/` measures.
  `primary_endpoint/report.py` is imported by `coarse_filter/` and
  `snr_threshold_6/` for aim 1's statistics.
- **Versions.** The scripts run against the current `capillary` package. The
  early checks were first run on earlier versions of the estimator and the
  stabilizer; their READMEs and the DEVLOG say which.
