# The primary endpoint (2026-10-29)

Aim 1 — the inter-day reproducibility of resting red-cell velocity — from the
whole loops placed blind on 2026-10-29 by the protocol (`PROTOCOL.md`), with the
quality of the lines and what the signal-to-noise threshold removes. The whole
story is in the DEVLOG entry of 2026-10-29.

## Files

- `relabel_whole_loops.py` — the fix made before unblinding: 29 lines on 13
  recordings had been saved without the whole-loop role. It re-saved them as
  whole loops from their own points and space-time diagrams with the app's
  `regenerate_line_report`, checked that the 3-s blocks and the pooled pattern
  shift came out exactly as saved, and moved the old files to `.trash`. It
  stops if the lines it finds are not those 29, so it is a record now, not a
  tool to run again.
- `report.py` — the report's numbers. It reads the data sets through
  `capillary.aims` (the protocol's analysis) and adds:
  - each line's quality (shape, clearance inside the dashed outline, the two
    halves of the rest, the two limbs) and each recording's stabilization;
  - every loop's pattern shift and its limbs', computed once from the saved
    space-time diagrams (cached in `estimates.csv`) and judged at thresholds
    from 4 to 14. At 8 the script stops unless this gives every loop's saved
    result exactly; at 7 and 9 it gives what `capillary.aims --min-snr` gives;
  - aim 1 per study for the protocol's analysis and its sensitivity analyses,
    with 95% intervals for the typical error and CV (chi-square), the limits of
    agreement and the Bland–Altman slope, and the limits as ratios;
  - exploratory: the second visit against the first.
- `dashboard/index.html` — the report's page. It reads only the tables
  `report.py` writes and draws every number from them.

## Rerun

```bash
python3 analysis/primary_endpoint/report.py [--data <data folder>] [--observer SJ]
```

about 40 s the first time, seconds after that. It writes into
`Reports/primary_endpoint/` of the data folder:

- `loops.csv`, `recordings.csv`, `pairs.csv`, `aim1.csv`,
  `threshold_sweep.csv`: the tables with the recordings' names, for checking;
- `dashboard/*.json`: the report's tables, naming only study, participant and
  visit. No recording name, date or blind code is in them, so that a later blind
  placement of the same recordings (the protocol's reproducibility check) stays
  blind.

The report is the Dashboard artifact https://claude.ai/artifact/QJj6SkQsuMToHa3NkAEtAZ
(private until shared). To refresh it, ask Claude Code to upload the new
`dashboard/*.json` files to it and point its sources at them, and, if the page
changed, to write `dashboard/index.html` as its page.

## Results (2026-10-29, observer SJ)

- **Lines:** 200 whole loops on 89 of the 90 recordings (ESMOKE FP03 Wefter can
  take none), 1–3 per recording. 91 count.
- **Why the rest do not:** 69 scored below signal-to-noise 8, a median of 3.4
  (no moving pattern; only 14 lie between 6 and 8); 36 scored high (median 35)
  but sat at the slowest speed the protocol searches, 1 px/frame (0.040 mm/s);
  4 cross themselves; none had limbs moving opposite ways.
- **Recordings with a value:** 54 of 90 (45 from the reference, 9 from a backup).
- **Aim 1, both studies pooled (the primary result).** `PROTOCOL.md` was corrected on 2026-10-29
  to the pooling the study progress report states, after the per-study results below had been
  seen. 9 of 24
  participants with both visits. Mean 0.121 mm/s, typical error 0.076 mm/s, within-subject CV
  63% (95% CI 43–121%), on the log scale 76%, smallest detectable change 0.211 mm/s, bias
  active − control +0.043 mm/s (−0.040 to 0.126), limits −0.169 to 0.255 mm/s, ICC(A,1) 0.05
  (−0.55 to 0.65). Sensitivity: thresholds 7 and 9 give the same; the mean of the counted loops
  CV 62%, ICC(A,1) 0.11; the reference alone 4 participants. The report page shows the studies
  only, until it is regenerated.
- **Aim 1, ESMOKE:** 7 of 14 participants with both visits. Mean 0.130 mm/s,
  typical error 0.086 mm/s, within-subject CV 67% (95% CI 43–147%), on the log
  scale 88%, smallest detectable change 0.239 mm/s, bias active − control
  +0.050 mm/s (−0.063 to 0.163), limits −0.189 to 0.289 mm/s, ICC(A,1) 0.01
  (−0.67 to 0.71). Whether the differences grow with the mean cannot be told
  (slope of the differences on the means 0.98, 95% CI −1.01 to 2.96).
- **Aim 1, ISMOKE:** 2 of 10 participants with both visits; too few for an
  estimate (CV 38%, interval 17–1228%).
- **Sensitivity:** thresholds 7 and 9 keep the same participants and numbers
  (from 6.5 to 9 nothing changes); the mean of the counted loops gives ESMOKE
  CV 65%, ICC(A,1) 0.07; the reference alone leaves 3 ESMOKE and 1 ISMOKE
  participants.
- **The search floor:** if the 36 loops at 1 px/frame counted, 14 more
  recordings would have a value and aim 1 would gain 1 ESMOKE and 3 ISMOKE
  participants. Below 1 px/frame a line cannot tell slow flow from slow
  movement of the picture (CLAUDE.md, Known issues), so measuring them is a
  methods decision for the PI, to be taken before their velocities are seen.
- **Ranking:** 51% of references counted, 40% of first and 46% of second
  backups: ranking by the clearest visible flow picked a measurable loop little
  more often than its backups.
- **Within a recording:** in the 31 recordings with two or more counted loops,
  the loops differ by a median CV of 23% (fastest over slowest 1.4×, up to
  2.4×); the two halves of the rest differ by a median 22% of their mean.
- **Exploratory:** no order effect (second − first visit −0.010 mm/s,
  −0.133 to 0.113, in ESMOKE).
