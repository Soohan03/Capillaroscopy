# A signal-to-noise cutoff of 6 (post hoc, 2026-11-06)

**Post hoc, after unblinding.** At a meeting on 2026-11-06 the PI asked whether the results would differ if a loop
counted from a signal-to-noise ratio of 6 instead of the protocol's 8. The protocol (`PROTOCOL.md`, fixed and
unblinded on 2026-10-29) sets 8 and lists 7 and 9 as its sensitivity analyses. This one was asked for after the
results were known, and the protocol's results stand as the primary ones.

## What was done

Nothing was placed again or moved. `capillary.aims --min-snr 6` takes the same 210 whole loops (the 200 placed blind
before unblinding, the 9 on aim 2's three added recordings, and ISMOKE FP19 Cefter's `loop3`, which no aim uses). For
each loop it computes the pooled pattern shift again from the space-time diagram saved when the loop was measured,
and its two limbs' shifts for the movement check, and judges them at 6. The movement check uses the same cutoff, so
at 6 a loop can also drop out: both limbs resolve, running opposite ways along the line. Everything else about
counting a loop is unchanged (a whole loop, the official rest, a stabilized video, the speed inside the range
searched from 1 px/frame, a line that does not cross itself), and so is each recording's value (the reference if it
counts, else the first backup that counts).

`compare.py` then compares the run at 6 with the protocol's own run and checks that the comparison is fair:

- `--min-snr 8`, the same recompute path, gives the protocol's six tables to float precision (largest relative
  difference 2e-12), and every run judged the same 210 loops. The scores recomputed from the diagrams equal the saved
  ones exactly.
- A loop that scores above the cutoff without counting must sit at 1 px/frame, the slowest speed searched; the script
  stops otherwise (none did).
- Aim 1's statistics are recomputed with the primary report's intervals (`analysis/primary_endpoint/report.py`) and
  checked against `capillary.aims`' own.
- Where there should be no flow, with the protocol's own filter: the coarse-filter analysis' synthetic loops without
  flow (`analysis/coarse_filter/synthetic_results.csv`) and the 200 blind loops' lines over the cuff occlusion
  (`Reports/coarse_filter/measurements.csv`), judged as `capillary.aims` judges a loop, at 5 to 9. Also whether the
  loops counted at rest run the same way after release, where they count there too.

## Results

| | Cutoff 8 (protocol) | Cutoff 6 |
|---|---|---|
| Whole loops counted (of 210) | 91 | 101 (11 gained, 1 lost) |
| Recordings the aims use with a value (of 72) | 42 | 45 |
| **Aim 1, pooled (primary):** participants (of 24) | 9 | 10 |
| mean, mm/s | 0.121 | 0.120 |
| typical error, mm/s | 0.076 | 0.074 |
| within-subject CV (95% CI) | 63% (43–121%) | 62% (43–113%) |
| CV on the log scale | 76% | 78% |
| SDC, mm/s | 0.211 | 0.205 |
| bias nicotine − control, mm/s (limits) | +0.043 (−0.169 to 0.255) | +0.051 (−0.155 to 0.256) |
| ICC(A,1) (95% CI) | 0.05 (−0.55 to 0.65) | 0.02 (−0.48 to 0.59) |
| **Aim 1, ESMOKE:** participants (of 14) | 7 | 8 |
| CV (95% CI) | 67% (43–147%) | 64% (43–131%) |
| ICC(A,1) | 0.01 (−0.67 to 0.71) | −0.01 (−0.55 to 0.63) |
| **Aim 1, ISMOKE:** participants (of 10) | 2 | 2 (unchanged) |
| **Aim 2, pooled:** participants (of 23) | 8 | 8 |
| change after − before, mm/s (95% CI), p | −0.070 (−0.137 to −0.003), 0.043 | the same |
| **Aim 2, ESMOKE** 5 of 13; **ISMOKE** 3 of 10 | −0.087, p 0.11; −0.042, p 0.30 | the same |

Thresholds 7 and 9 (the protocol's sensitivity analyses) count 95 and 88 loops and give the protocol's figures for
both aims.

- **The loops.** 15 of the 210 score from 6 up to 8: 11 of them count at 6, and 4 sit at 1 px/frame and count at
  neither. The loops below 8 score a median of 3.4 (no moving pattern). The loop lost at 6 is ISMOKE FP23 Cefter2
  `loop2` (score 10.9): at 6 both limbs resolve, opposite ways. No aim uses that recording.
- **The values.** 4 recordings change value, all used by the aims:
  - ESMOKE FP22 W före gains a value from its reference (`loop1`, score 6.3): 0.171 mm/s. With its Q före (0.049)
    the participant enters aim 1, a pair 3.5-fold apart. Its W efter has no value, so aim 2 is unchanged.
  - ISMOKE FP04 C före (`loop2`, 0.117) and FP20 C före (`loop1`, 0.060) gain a value, but their S före has none,
    so no aim 1 pair.
  - ESMOKE FP16 W efter's value moves from its backup (`loop2`, 0.116) to its reference (`loop1`, score 6.06,
    0.097); FP16 W före has no value, so no aim 2 pair.
- **The protocol's other values.** The mean of all counted loops: aim 1 pooled 9 → 10 participants, CV 62% → 64%,
  ICC(A,1) 0.11 → 0.09; aim 2 pooled −0.071 mm/s (p 0.039) at both. The reference only: aim 1 pooled 4 → 5
  participants, CV 47% → 61%, ICC(A,1) 0.23 → −0.24; aim 2 pooled 4 participants, −0.041 mm/s (p 0.16) at both.
- **Where there should be no flow.**

  | Cutoff | Synthetic, no flow: flow found (of 120) | Occlusion: flow found (of 163) | Loops counted at rest (of 200) | counted after release too | the same way |
  |---|---|---|---|---|---|
  | 5 | 2 | 16 | 107 | 60 | 60 |
  | 6 | 0 | 14 | 101 | 57 | 57 |
  | 7 | 0 | 12 | 95 | 49 | 49 |
  | 8 | 0 | 12 | 91 | 45 | 45 |
  | 9 | 0 | 10 | 88 | 40 | 40 |

  No synthetic loop without flow reaches 6 inside the range searched (the highest scores 5.4), so 6 is just clear of
  the synthetic noise and 5 is not. In the occlusion, 6 lets through 2 more of 163 lines than 8; some of that may be
  real flow under the cuff. Of the 11 loops gained, 1 of the 8 measured in the occlusion shows flow there (ESMOKE
  FP20 Q före `loop2`); after release 3 of 8 measured count, all 3 the same way as at rest (both of ESMOKE FP22 W
  före's, and ISMOKE FP20 C före `loop1`).
- **Reading.** Lowering the cutoff to 6 adds one participant to aim 1 and changes none of its conclusions: the
  pooled CV stays at 62–63% and the ICC near zero, with intervals as wide as before. Aim 2 does not change. The
  cutoff decides few loops. Most of those that do not count score far below 6 (no moving pattern) or score high at
  the slowest speed searched (the open PI decision on the search floor, CLAUDE.md, Known issues).

## Files

- `compare.py`: the comparison and the checks above; prints them and writes the report page's tables into
  `dashboard/` (recordings named by study, participant, visit and before/after only).
- `dashboard/`: `aim1.csv`, `aim2.csv`, `loops.csv`, `changed_loops.csv`, `changed_values.csv`, `aim1_pairs.csv`,
  `null_checks.csv`, `summary.csv`, and `index.html`, the report page's source.

## Rerun

From the repository on the desktop, where the data folder is (about a minute for each `--min-snr` run):

```bash
python3 -m capillary.aims --min-snr 6 --out Reports/aims/sensitivity_minsnr6
python3 -m capillary.aims --min-snr 6 --value mean --out Reports/aims/sensitivity_minsnr6_valuemean
python3 -m capillary.aims --min-snr 6 --value reference-only --out Reports/aims/sensitivity_minsnr6_valuereferenceonly
python3 -m capillary.aims --min-snr 8 --out Reports/aims/check_minsnr8_recomputed
python3 analysis/snr_threshold_6/compare.py
```

It also reads the protocol's runs in `Reports/aims/` (its own and the `sensitivity_*` folders,
`analysis/primary_endpoint/README.md`) and `Reports/coarse_filter/measurements.csv`, all in the data folder.

The report page is the Dashboard artifact https://claude.ai/artifact/BnybzKU5Z8vqfFG1xKY35g (private until shared).
Its tables are the CSV files above, uploaded to it; to refresh it, ask Claude Code to upload the new ones and point
its sources at them.
