# The numbers of the statistics report (2026-11-03)

"Statistics for Aims 1 and 2" (a Claude Docs document, https://claude.ai/artifact/C719bwNfWzSPfh7mEVidvp)
explains what each statistic of `PROTOCOL.md` computes and why, worked through on the study's own
values. `report_numbers.py` prints every number it quotes, step by step, from the functions the
protocol's analysis uses (`capillary.aims`, `capillary.agreement`).

The per-participant values are not in the repository. Give the script either:

- `capillary.aims`' tables, on the computer that holds the data:

  ```bash
  python analysis/statistics_report/report_numbers.py \
      --aim1 Reports/aims/aim1_pairs.csv --aim2 Reports/aims/aim2_values.csv --observer SJ
  ```

- or the report page's tables, which name only study and participant (its aim 1 participants table
  and `aim2_pairs.json`; the report of 2026-11-03 was computed from these).

## What it prints

- **Aim 1**, pooled and per study: each pair; the typical error with its chi-square interval; the CV
  and log CV; the smallest detectable change; Bland–Altman (bias, limits, their intervals, the
  slope, the limits as ratios); the paired t-test of the bias; and the two-way ANOVA behind
  ICC(A,1) and ICC(C,1).
- **Aim 2**, per study and pooled: each participant's change; the paired t-test step by step; the
  same on the log scale; the Wilcoxon signed-rank test with its ranks, W+ and the exact p counted
  over all sign patterns; the Hodges–Lehmann estimate; the sign test; and Spearman's correlation of
  the change with the value before.
- **Tables that do not depend on the values:**
  - the Wilcoxon test's smallest possible p by number of pairs;
  - Wilson intervals for the yields reported on 2026-10-29;
  - how wide the intervals get with more participants;
  - the smallest fall aim 2 could detect with 80% power, at the observed spread.

Run on 2026-11-03 against the report page's tables, every aim 1 and aim 2 figure equals what
`capillary.aims` reported on 2026-10-29 (DEVLOG, PROTOCOL.md).
