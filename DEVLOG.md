# Development Log

Diary of all changes made to the capillaroscopy analysis tool. Every session
that changes code gets a dated entry: what branch, what changed, why, and how
it was verified. Newest entries first.

---

## 2026-10-29 — Where the two corrections come from

**Branch:** `docs/agreement-sources`, from `main` at de14ab3 (PR #29 merged). No code changed.

The user said where the two corrections of the protocol come from:
- **Aim 1's pooling:** the study progress report, written before unblinding (shared here on 2026-10-07), states
  that aim 1 is pooled over both studies.
- **Aim 2's correction** (the nicotine visit only, per study and pooled): a verbal agreement between the user and
  the PI about a month before unblinding, with no written record. The notes Claude Code took of the progress
  report on 2026-10-07 give aim 2 as the difference in change, active minus control, with the studies analysed
  separately: the older plan PROTOCOL.md first recorded.

PROTOCOL.md now cites the report for aim 1 and says aim 2's agreement was verbal, both in the aims' sections and
in "Changes after unblinding". CLAUDE.md and the primary endpoint's README say the same. The change log's last
point on aim 2 (the control visit's recordings are no longer used) had ended up under aim 1's entry when that was
added; it is back under aim 2.

**Verified.** Documentation only: `git diff` checked; nothing the code or tests read was touched.

---

## 2026-10-29 — Aim 1 pooled over both studies

**Branch:** `feature/aim1-pooled`, from `main` at a69db38 (PR #28 merged).

**Why.** The user noticed that PROTOCOL.md was missing a statement: aim 1's result is pooled over ESMOKE and
ISMOKE, as agreed with the PI long before unblinding. The protocol said "for each study". Like aim 2's this
afternoon, the correction comes after unblinding: the per-study results (ESMOKE 7 of 14 participants, CV 67%,
ICC(A,1) 0.01; ISMOKE 2 of 10) had been computed and looked at. They stay in the reports, beside the pooled result.
No document in the repository records the pooling. The notes Claude Code took of the progress report
(2026-10-07) say "studies analysed separately", under aim 2; the report itself was not checked.

**What changed.**
- `capillary/aims.py`: `aim1` adds a pooled row (`POOLED`, 'ESMOKE + ISMOKE') after each observer's studies, as
  `aim2` does. The printed report shows it first, as "pooled: the primary result".
- `analysis/primary_endpoint/report.py`: `aim1_table` and `aim1.csv` include the pooled row, with the report's
  intervals. The report page's charts still show the studies only; the page has not been regenerated.
- PROTOCOL.md: aim 1's section and a "Changes after unblinding" entry with the pooled result. CLAUDE.md,
  README.md and the primary endpoint's README: the same.

**Results** (the same values as at unblinding, observer SJ):

| | Participants | CV (95% CI) | Log CV | SDC, mm/s | Bias active − control, mm/s | ICC(A,1) (95% CI) |
|---|---|---|---|---|---|---|
| Pooled | 9 of 24 | 63% (43–121) | 76% | 0.211 | +0.043 (−0.040 to 0.126) | 0.05 (−0.55 to 0.65) |
| ESMOKE | 7 of 14 | 67% (43–147) | 88% | 0.239 | +0.050 (−0.063 to 0.163) | 0.01 (−0.67 to 0.71) |
| ISMOKE | 2 of 10 | 38% (17–1228) | 44% | 0.097 | +0.019 | 0.18 |

Sensitivity, pooled: thresholds 7 and 9 give the same; the mean of the counted loops CV 62%, ICC(A,1) 0.11; the
reference alone leaves 4 participants (CV 47%).

**Verified.** `python3 -m pytest`: 319 passed. One new test checks the pooled row: the CV and ICC(A,1) of ESMOKE's
three pairs and an ISMOKE pair, against `agreement.icc`, and that the report prints it first. `capillary.aims` and
its four sensitivity runs were rerun. Their per-study aim 1 rows equal those of 13:07, compared file by file.

---

## 2026-10-29 — Aim 2 corrected to the nicotine visit

**Branch:** `feature/aim2-nicotine-visits`, from `feature/reference-capillary` at d44b8ea (not merged yet).

**Why.** The user asked whether to run aim 2. It had already run at unblinding (13:07), by PROTOCOL.md's text:
participants with a value in all four recordings, and the change on the active visit minus that on the control
visit. The user then said that this was not what had been agreed. About a month before unblinding, the student and
the PI agreed that aim 2 looks only at the nicotine visit (W in ESMOKE, S in ISMOKE), per participant with both its
recordings before and after exposure. The analysis is per study, and pooled over both as a separate analysis, since
the nicotine comes from an e-cigarette in one study and from heated tobacco in the other. The control visit is not
used. PROTOCOL.md had recorded the older plan by mistake.

On the way the user doubted, then confirmed, which letters carry nicotine: W and S do, Q and C (sham) don't, as
the code had them. The labels came from the progress report shared on 2026-10-07.

**Seen before the correction.** Aim 2 by the old text: ESMOKE 5 of 13 participants, difference in change
−0.097 mm/s (95% CI −0.175 to −0.019), t-test p 0.026, Wilcoxon p 0.0625 (all 5 the same way); ISMOKE none. Its
tables, and the sensitivity runs', were copied to `Reports/aims/aim2_as_first_written/` before anything was rerun.
PROTOCOL.md's new "Changes after unblinding" entry says this.

**What changed.**
- `capillary/inventory.py`: aim 2 needs the före and efter of the active visit only (`participants`), and only
  those recordings are marked as aim 2's (`mark_use`). Aim 2 now has 13 ESMOKE participants (the same 13) and 10
  ISMOKE (8 + FP02 and FP08, who have a complete S visit but no complete C visit; FP02 is "check" for its odd
  2 Nov names). The aims use 72 recordings instead of 90: the 21 control-visit efter recordings drop out, and 3
  join (ISMOKE FP02 Sföre and Sefter, FP08 Sefter). `metadata/derived/` regenerated.
- `capillary/aims.py`: `AIM2_RECORDINGS` holds the two nicotine-visit recordings. `response(before, after)` gives
  the change (mean, 95% interval, paired t-test, Wilcoxon) and the ratio after / before (geometric mean, interval,
  t-test on the logs). `aim2` adds a pooled row, `POOLED` ('ESMOKE + ISMOKE'), after the studies. The printed
  report says so.
- `analysis/primary_endpoint/report.py` and its dashboard: aim 2's funnel now counts participants with a value
  before and after nicotine (wording only; the published report has not been regenerated).
- PROTOCOL.md: the recordings, aim 2 (now "response to nicotine"), the blinding note and the change entry.
  CLAUDE.md, README.md and metadata/README.md: aim 2 and the counts.

**Blinding of the three new recordings.** They are stabilized but have no lines. The user places them in blind
placement (reference + two backups, same rules), and aim 2 is not computed again until then. So nothing of the new
aim 2 has been looked at. `capillary.aims --progress` lists 4 codes without lines: these 3 and ESMOKE FP03 Wefter,
where no line is possible.

**Verified.** `python3 -m pytest`: 318 passed. The aim 2 tests were rewritten: the change and ratio against scipy,
the per-study and pooled rows, the inventory's 13 + 10 participants. The inventory tests now expect 72 recordings
and the control-visit efter unused, and the blind list's test has the same change. `--progress` runs.

**Afterwards: the three recordings placed, aim 2 computed.**
- The user placed the three recordings in blind placement at 18:58–19:04 (confirmed by the user; `settings.csv`
  was rewritten at 19:04:34, when blind placement was switched off), three whole loops each. `--progress` found
  nothing to fix.
- None of the nine counted:
  - FP02 Sefter's three (signal-to-noise 31–42), FP02 Sföre loop1 (17.6) and FP08 Sefter loop2 (19.9) lay at the
    slowest speed searched;
  - the other four scored 2.7–7.1.
- Aim 2 (19:05, `capillary.aims` and the four sensitivity runs):

  | | Pairs | Change after − before, mm/s (95% CI) | t-test / Wilcoxon p | Ratio after/before |
  |---|---|---|---|---|
  | ESMOKE | 5 of 13 | −0.087 (−0.204 to 0.030) | 0.109 / 0.062 | 0.52 (0.23–1.15) |
  | ISMOKE | 3 of 10 | −0.042 (−0.175 to 0.090) | 0.303 / 0.500 | 0.60 (0.12–3.11) |
  | Pooled | 8 of 23 | −0.070 (−0.137 to −0.003) | 0.043 / 0.023 | 0.55 (0.33–0.91) |

- 7 of 8 decreased. The sensitivity runs agree: signal-to-noise 7 and 9 give the same; the mean of the counted
  loops gives pooled −0.071 (−0.137 to −0.005); the reference alone leaves 1 ESMOKE pair.
- Aim 1 and its sensitivity tables came out identical to those of 13:07 (compared file by file).

---

## 2026-10-29 — Post hoc: a coarser filter for faster flow

**Branch:** `feature/reference-capillary`. Commits: 0b15b9c (the plan, 14:38, before any check), then the scripts
and results.

**Why.** On ISMOKE FP04 Sföre the user saw blood moving, but none of its three blind loops counted
(signal-to-noise 2.6–4.2). A test line placed after unblinding (`loop4`, 14:04, since moved to the trash by the
user) was measured over the whole video, so the occlusion's slow creep dominated it. Over the rest alone it gave
0.146 mm/s, signal-to-noise 10.7.

With the rows band-passed at σ 4–16 px instead of 1–4, the three blind loops gave 0.40–0.48 mm/s
(signal-to-noise 6.3–7.1). They showed no such speed in the occlusion and ran the same way, faster, after
release. The likely reason: at about 11 px/frame the fine detail the default filter keeps is smeared within each
frame. The user, unable to reach the PI, asked to run the check as a post-hoc analysis.

**How it was kept honest.** `analysis/coarse_filter/PLAN.md` fixed the rule, the checks and their pass marks, and
listed what had been seen. It was committed before anything was run; PROTOCOL.md's "Added after unblinding" points
to it.
- The rule: step 2 is only for loops not resolved by the protocol. It uses σ 4–16, with speeds searched from
  5 px/frame (0.20 mm/s), so that the creep the coarser filter turns into "flow" in the occlusion falls at the
  edge of the searched range. The quality control is the same.
- Sensitivity: step 2 from 3 and from 8 px/frame.
- Only the loops saved before unblinding. ISMOKE FP19 Cefter's `loop3` was saved at 13:53, after unblinding, and
  is left out; it is not counted in the protocol's analysis either.

**Results** (`analysis/coarse_filter/README.md`). The rule passes all three checks:
- synthetic no-flow: 0 of 120 line clips;
- the occlusion: step 2 added no false flow in 163 lines (the protocol's own measurement found "flow" in 12);
- after release: 6 of 6 loops ran the same way.

The simulator does not reproduce the loss of fine detail, so V1 tests false alarms only. FP04 Sföre itself gains
nothing (6.3–7.1 < 8).

Aim 1, ESMOKE:
- 9 participants instead of 7;
- CV 69% (47–132) instead of 67%; log CV 107% instead of 88%;
- ICC 0.31 (−0.39 to 0.79) instead of 0.01.

ISMOKE: 3 participants instead of 2. Step 2's 14 loops run at a median 0.38 mm/s, against 0.08 for the protocol's
91: the protocol counts mainly slow capillaries. The rule adds data without making CBV more reproducible: 3 of the
9 ESMOKE pairs set a slow capillary against a fast one.

**Files:** `analysis/coarse_filter/` (`PLAN.md`, `rule.py`, `checks.py`, `aim1.py`, `README.md`,
`synthetic_results.csv`, `checks_summary.json`, `aim1.csv`); tables with names in `Reports/coarse_filter/` (not in
the repository).

**Verified:**
- `checks.py real` stops unless step 1 at rest judges all 200 loops as their saved data sets do; it did.
- `aim1.py`'s protocol rows equal the primary report (ESMOKE 7, CV 66.6%, ICC 0.007).
- No code of the app changed.

---

## 2026-10-29 — The recordings aim 1 uses are marked in the list

**Branch:** `feature/reference-capillary` (after the entry below).

The user, about to write the report, asked to see in the app which recordings aim 1 uses.

- **The chip:** each of them gets an **Aim 1** chip in the recording list, first among its chips, in the
  accent colour. These are the 48 recordings: each aim-1 participant's before-exposure recording of
  both visits, 28 ESMOKE and 20 ISMOKE.
- **The filter:** typing "aim 1" in the list's filter lists only them.
- **Where the list comes from:** `gui.blind.aim1_recordings`, from the same `used_for` of
  `capillary.inventory` that `capillary.aims.aim1_recordings` reads. The set is checked to be the
  same as the analysis's.
  - `gui.blind` now reads the inventory once (`_uses`) for both lists.
- **Hidden during blind placement** (`gui.blind.shows_aim1`): aim 1 uses only recordings before
  exposure, so the chip would tell those from the ones after it, which the protocol hides from the
  observer.
- Also this session: the baseline recordings listed per study with their values for the user
  (`Reports/primary_endpoint/baseline_recordings.csv`, not in the repository). Asked whether the
  highest-SNR loop should replace the reference, it was checked and not adopted:
  - it gives the same 54 recordings and the same 7 + 2 participants;
  - it picks another loop in 13 of 54 recordings;
  - SNR falls with velocity among counted loops (Spearman ρ −0.46), so it would favour slow loops
    (ESMOKE mean 0.122 instead of 0.130 mm/s);
  - it would be a rule chosen after unblinding.

**Verified:** `python3 -m pytest`, 318 passed (a new test for the marks and for hiding them).

---

## 2026-10-29 — The protocol, the study's lines placed blind, and the primary endpoint

**Branch:** `feature/reference-capillary`. Commits 6fd617d, 282387f, db39c70 and c195221 (the
protocol and `capillary.aims`), then b05f071 (the app's role fix), e53462b (the relabel script),
9290c56 (the report, PROTOCOL.md, README.md) and 37505cb (this entry, CLAUDE.md).

### The protocol (`PROTOCOL.md`, 09:51, before the first study line)

The user and the PI agreed: velocity round the whole capillary in the resting flow;
signal-to-noise as the quality control, above 8 accepted as measurable; one "reference"
capillary per video to begin with. The user added two ranked backups for when the reference
fails. PROTOCOL.md fixes the details: the 90 recordings, candidates and ranking (the clearest
moving blood first, then the longer loop), up to three loops named in ranking order (`loop1` the
reference), each recording's value (the reference if it counts, else the first backup that
counts, else missing; secondary: the mean of the counted loops), aim 1 and aim 2's statistics,
the sensitivity analyses (reference only, mean, thresholds 7 and 9), blinding, and a later
check of the placement's reproducibility (10 random recordings placed again under a second
observer code).

**FP23's four recordings** were stabilized the same morning (2.8–3.2 min each, match over the
rest 0.80–0.89, no frame lost, 74–89% of the frame usable at rest), so all 90 recordings were
ready. ISMOKE FP22 C was left raw on purpose: the aims do not use it (its S visit has no
official times).

### `capillary.aims` for the protocol (commits 6fd617d–c195221)

- `capillary/blinding.py`: the codes, moved out of `gui/blind.py` so the command line shows the
  same ones.
- `--progress`: how far blind placement got, by code. Each recording's data set names and what
  to fix (no `loop1`, a gap, more than three loops, not a whole loop, not over the rest, two
  loops on one capillary, a line crossing itself), never a velocity, a score or a count of
  loops that count. While the app is in blind placement the results stay hidden unless
  `--unblind` is passed.
- Each recording's value by the reference rule (`value_mm_s`, `value_from`), the reference alone
  and the mean of the counted loops; `--value` picks which aim 1 uses.
- Aim 2: each visit's change after minus before, the difference active minus control (mean,
  95% CI, paired t-test, Wilcoxon) and the same as ratios on the log scale.
- `--min-snr`: the loops judged at another threshold from their saved space-time diagrams
  (`recount`; `pattern_shift.loop_limbs` took a `min_snr`).
- Twisted loops: a line that crosses itself is not a candidate (the crossing is sampled twice
  and the split at the apex fails). Asked during placement whether points may cross, the rule
  was written into the protocol before unblinding; `--progress` flags such lines and the
  analysis skips them, so the next loop in the ranking takes their place. 4 of the 200 lines,
  all backups.

### Placement (10:13–12:37)

The user placed 200 whole loops on 89 recordings with blind placement on, a median of 32 s
apart. The app lagged once mid-session (no traceback in the task output or the log) and was
restarted.

`--progress` afterwards found what the protocol asks to fix before unblinding:

- **29 lines on 13 recordings saved without the whole-loop role** (11:58–12:12, the last 13
  codes in the list). Their names were `set1`, `set2`… instead of `loop1`…, so the analysis would
  have skipped them. They had whole-loop shape (both ends near each other, the apex in the
  middle), lay over the official rest and were placed in ranking order.
  - Cause: `LinePage.restore_state` gives a recording seen before the role its line had then,
    and a recording not seen before keeps the last role. The first of the 13 (FP01
    Qefter_försök2) had a try-out line with no role from 09:56; returning to it restored that
    role, and every new line kept it.
  - Fix, chosen by the user over placing them again:
    `analysis/primary_endpoint/relabel_whole_loops.py` re-saved each line as a whole loop
    (`set1` → `loop1`… in the order placed; on FP01 Qefter_försök2 `set2` → `loop1`) from its own
    points, frames and space-time diagram with the app's `regenerate_line_report`. It checks that
    the 3-s blocks and every summary number except the role's come out exactly as saved, then
    moves the old files to `.trash/2026-10-29_12-43-28_lines re-saved as whole loops`. The
    provenance keeps `relabelled` (from, when, why, software).
  - Its first two runs stopped on bugs of the script before anything was moved: the 3-s blocks
    were not copied for the regenerator to read, and a velocity saved as `null` (unresolved) was
    compared with the fresh NaN. The two half-written `loop1` files each left on FP01
    Qefter_försök2 were removed by hand (checked byte for byte to be copies of `set2`).
  - App fix (`gui/blind.py` `ROLE`, `LinePage.keep_blind_role`): during blind placement every
    line is a whole loop. The other role buttons are disabled, and a remembered role gives way,
    with the suggested name. Tested on a stand-in page without a window (the user was placing
    in the app).
- **LK9EV (ISMOKE FP19 Sföre) had no lines.** Its picture was fine (85% of the frame usable,
  match 0.93); the user had skipped it and placed it blind at 12:37 (`loop1`, `loop2`).
- **E8FYS (ESMOKE FP03 Wefter) has no line.** No place shows the picture in every rest frame
  (it moved more than the frame is high), so every line is refused; missing.
- **Two try-out lines** from before blind placement (09:56 on FP01 Qefter_försök2, 09:59 on FP01
  Qföre), measured over the whole video with results visible. The blind loops on both
  recordings lie on other capillaries (no overlap). Not whole loops, so not read; left in place.

### Unblinding (13:07) and the results

The user confirmed that placement was final. `python3 -m capillary.aims --unblind --observer SJ`:

- **Loops:** 91 of 200 count. 69 scored below 8 (a median of 3.4, no moving pattern; only 14
  between 6 and 8). 36 scored high (median 35, 9.7–83.5) but their speed sat at the slowest
  searched, 1 px/frame (0.040 mm/s; `in_range` false). 4 cross themselves. None had limbs
  moving opposite ways.
- **Recordings:** 54 of 90 have a value, 45 from the reference and 9 from a backup (loop2 7,
  loop3 2). ESMOKE 36 of 54, ISMOKE 18 of 36.
- **Aim 1, ESMOKE** (7 of 14 participants with both visits, 3 with one, 4 with neither):
  - mean 0.130 mm/s (control 0.105, active 0.154);
  - typical error 0.086 mm/s (95% CI 0.056–0.190), CV 67% (43–147%), log-scale CV 88% (50–300%);
  - smallest detectable change 0.239 mm/s (184% of the mean);
  - bias active − control +0.050 mm/s (−0.063 to 0.163), limits −0.189 to 0.289;
  - ICC(A,1) 0.01 (−0.67 to 0.71);
  - slope of the differences on the means 0.98 (−1.01 to 2.96): with 7 participants a
    proportional bias can be neither shown nor excluded; as ratios, active / control ×1.37 with
    limits ×0.24 to ×7.8.
- **Aim 1, ISMOKE:** 2 of 10 participants with both visits (6 with one): CV 38% (17–1228%),
  ICC(A,1) 0.18 (−3.3 to 1.0). Not interpretable.
- **Sensitivity analyses:**
  - thresholds 7 and 9 give the same participants and statistics; the sweep changes nothing
    from 6.5 to 9, and ESMOKE drops to 5 participants at 9.5;
  - the mean of the counted loops: ESMOKE CV 65%, ICC(A,1) 0.07; ISMOKE CV 42%;
  - the reference alone: 3 ESMOKE and 1 ISMOKE participants.
- **The search floor:** if the 36 loops at 1 px/frame counted, 14 more recordings would have a
  value, and aim 1 would gain 1 ESMOKE and 3 ISMOKE participants (8 and 5). Below 1 px/frame one
  line cannot tell slow flow from slow movement of the picture (Known issues), which is why the
  protocol does not search there. Whether to measure them is for the PI, before their velocities
  are seen.
- **The lines:**
  - median length 0.33 mm (IQR 0.25–0.43), 22 points about 12 px apart;
  - the closest line kept 1.1 px inside the dashed outline;
  - counted loops: median 0.080 mm/s (0.040–0.316), 2.0 px/frame (at most 7.9, inside the
    validated range), median signal-to-noise 21.8, median 95% interval ±17%.
- **The ranking** by visible flow: 51% of references counted, 40% of first and 46% of second
  backups.
- **Within a recording** (31 with two or more counted loops): between-loop CV a median 23%,
  fastest over slowest 1.4× (up to 2.4×). The two halves of the rest differ by a median 22% of
  their mean (63 loops).
- **Exploratory, visit order:** second − first visit −0.010 mm/s (−0.133 to 0.113) in ESMOKE,
  so the active visit's higher mean is not an order effect.
- Aim 2 has values in all four recordings for 5 of 13 ESMOKE and 0 of 8 ISMOKE participants
  (not analysed further here).

### The report (`analysis/primary_endpoint/`)

- `report.py`: it computes every loop's pattern shift and its limbs' once from the saved
  diagrams (cached) and judges them at thresholds from 4 to 14. It stops unless at 8 this
  reproduces every saved result. Then aim 1 for the protocol and its sensitivity analyses,
  through `capillary.aims` and `capillary.agreement`, with the added intervals listed in
  PROTOCOL.md, and the line quality.
- It writes tables with the recordings' names for checking, plus the report's data, which names
  only study, participant and visit. No blind code is shown next to a name, so the later blind
  re-placement stays blind.
- The report is a Dashboard artifact (https://claude.ai/artifact/QJj6SkQsuMToHa3NkAEtAZ), drawn
  by `dashboard/index.html` from those tables. Four tabs:
  - **primary endpoint:** per-study figures, both visits per participant, Bland–Altman, the
    sensitivity analyses as interval plots, every participant, visit order;
  - **signal-to-noise:** the attrition funnel, every loop's score by rank, why loops fail,
    where values come from, the threshold sweep, the loops near the threshold;
  - **line quality;**
  - **methods.**
- PROTOCOL.md records the fixes before unblinding, the unblinding and the additions after it
  (none changes a value).

**Verified:**
- The report's numbers equal `capillary.aims --unblind`, and at 7 and 9 the sweep's loops and
  recordings equal `--min-snr 7` (95, 55) and `--min-snr 9` (88, 54).
- `python3 -m pytest`: 317 passed.

---

## 2026-10-14 — 30 more ISMOKE recordings stabilized

**Branch:** `fix/line-picture-edge`. No code changed; this entry and CLAUDE.md's data notes.

The user copied more ISMOKE recordings into `RecordedVideos/` and asked for some of the newest to
be stabilized. Some came from a second OneDrive zip (`OneDrive_2_2026-10-14.zip`, 12 videos of
FP19, FP20 and FP21) that was still being extracted.

**How:**
- The app's own job (`gui.tasks.stabilize`) ran from a scratch script, 7 videos at a time, the
  aims' recordings first.
- A video started only once fully written. For a video of the zip, its file had the size the zip
  lists; for one copied earlier, its size had held and it had not changed for a minute.
- Unfinished output went to `StabilizedVideos/.partial_batch/`, removed afterwards.
- 30 videos in 18.8 min (a median 3.25 min each). None failed.
- Left as before: the two raw FP09 efter recordings, which the aims do not use.

**Results:**
- **The 26 recordings the aims use** (FP08 Cföre and Sföre, and the four of each of FP09, FP15,
  FP16, FP19, FP20 and FP21):
  - no frame lost in any rest;
  - median match over the official rest 0.79 (0.58–0.93; FP09_Cföre 0.58 and FP16_Cföre 0.63
    lowest);
  - the picture moved 15–217 px during the rest (median 70).
- **Where lines can go** (`stabilize.picture_area` over the rest): a median 82% of the frame
  (49–94%), less than on the 60 recordings checked in the previous entry (a median 92%). Below
  75% on 8:
  - FP08_Sföre 49% (it moved 217 px);
  - FP16_Cföre 62%, and FP16_Sföre, FP19_Cefter and FP20_Sefter 64% each;
  - FP21_Sföre2 70%, and FP09_Cföre and FP16_Sefter 72%.
- **Outside the rest:**
  - FP21_Cföre: 1189 of its 1698 occlusion frames were carried along the path from their
    neighbours. The picture changes under the cuff (match 0.30 there). Its rest is placed by the
    references throughout (match 0.82).
  - FP21_Sefter lost 90 frames and FP20_Sefter 17, all in the occlusion. FP19_Sföre lost 5,
    outside the rest.
- **Not used by the aims:**
  - FP08_Sefter, FP10_Sföre and FP11_Cföre. FP11_Cföre has no official rest and lost 453 frames.
  - FP18_Sföre, 11900 frames (6.6 min). Its picture could mostly not be followed: 9421 frames
    were lost.
- **Now:** 103 stabilized videos. All 54 ESMOKE recordings the aims use and 32 of the 36 ISMOKE
  ones. Missing: ISMOKE FP23's four (Sföre and Sefter of 02-Dec-2020, Cföre and Cefter2 of
  09-Dec-2020), in neither `RecordedVideos/` nor the zip.

**Also this session (scratch, nothing in the repository):** asked to place lines on one recording
and give its velocities, Claude Code placed whole loops on ISMOKE_FP02_Sföre_02-Nov-2020. That
recording is not used by the aims, so the study's recordings stay blind for the user's own
placement.
- Three loops had both limbs and the apex visible on the rest's mean image. They were traced along
  the vessel (as in `analysis/aim1_feasibility/measure.py`) and measured over the official rest
  with `gui.tasks.measure_line_dataset`.
- Results: 0.044, 0.083 and 0.051 mm/s (signal-to-noise 79.6, 34.9 and 8.5), a mean of
  0.059 mm/s.
- Four more loops were seen but not placed: two narrow ones whose limbs merge into one band, one
  at the frame's edge, and one too faint.

## 2026-10-14 — Lines must stay in the picture: the stabilizer's black strip

**Branch:** `fix/line-picture-edge`, from `feature/blind-whole-loop` at `98bcf76` (the note on the
first ISMOKE recordings, not yet on `main`, so this branch's pull request carries it too). Commit
`d0e0778` (code, tests, README, CLAUDE.md, this entry).

The user asked what limits the tool now and then to "fix the edge bug". This was an open item
from the slow-range work: where the picture moved, the stabilizer moves the frame back and leaves
a black strip along its edge, and nothing kept a line off it. `SpaceTimeSampler.inside` only
checked that a line lies within the frame, the page used only that, and the measurement checked
nothing. A line that reaches the strip sees the strip's edge move along the line as the picture
moves: a strong pattern that reads as flow.

**In short:**
- A line on a stabilized video is measured only if its samples keep 3 px clear of the black strip
  in every frame of the range, and no frame of the range was lost. The Centre line page, the
  measurement job and the batch CLI refuse other lines and say why. The page outlines where every
  frame of the range has picture.
- On the aim-1 rerun's lines, 6 of 184 reach the strip at rest, all on FP03_Wföre. They are the
  example the slow range's "movement of the picture" rested on: on the stretches of rest they keep
  clear of the strip, their slow flow is gone. The app's own measurement (from 1 px/frame) was not
  affected on these lines, so the aim-1, whole-loop and `capillary.aims` numbers stand.
- On recordings that moved a lot at rest, lines must stay in the middle of the frame, and on
  FP03_Wefter no line can be measured over its whole rest.

### What changed

- **`capillary/stabilize.py`** (a new section, and a paragraph in the module docstring):
  - `read_shifts(video)`: a stabilized video's `___stabilization.csv`, indexed by frame; None
    when there is none (a raw recording); ValueError when it holds no shifts.
  - A frame moved by (dx, dy) shows the recorded picture from x = dx to dx + width - 1 and from
    y = dy to dy + height - 1. `picture_area(shifts, shape, first, last)`: the part of the frame
    that every placed frame of the range shows, `EDGE_MARGIN_PX` inside each frame's strip.
  - `check_picture(shifts, shape, box, first, last)` gives a `PictureCheck`:
    - the frames in which the samples' bounding box reaches a frame's strip or leaves the frame,
      and the frames the stabilizer lost (written black) with where they lie;
    - the clearance (how far the samples keep from the area's edge, negative when they reach
      over it) and the side they come nearest;
    - `problem()`, the sentence the user sees:
      - lost frames: set the range to frames the stabilizer placed;
      - a line that reaches the strip: move it at least so many px away from that edge;
      - when no part of the frame shows the picture in every frame of the range, or the line is
        larger than that part, it says so instead;
    - `record()`, kept with a data set: the rule, the area and the clearance.
  - `EDGE_MARGIN_PX = 3` (below).
- **`capillary/spacetime.py`:** `SpaceTimeSampler.bounds`, the rectangle that holds every sample
  (the line and 2 px to either side); `inside` uses it.
- **`gui/tasks.py`:** `picture_check`; `measure_line_dataset` refuses a line that fails it before
  reading any frame (ValueError with the sentence), and saves `picture` (the check's record, or
  null for a video without a shift file) in the provenance.
- **`capillary/cli.py`:** for a video with a shift file, a `--line` that fails the check over the
  frames to be read is refused (`error: …`, exit code 1).
- **`gui/line_page.py`:**
  - The open video's shift file is read once each time a recording is shown.
  - `_line_problem` adds the check over the current range, so a failing line blocks Measure and
    the preview, and its sentence shows under the button and in the preview panel (also during
    blind placement).
  - A dashed outline shows where the line's middle may go: the area every frame of the range
    shows, less the 2 px the line samples to either side. It is light grey, and orange while the
    line reaches beyond it. It is not drawn without a shift file or when no area is left.
  - `on_range_change` redraws the outline and the message when the range changes.
  - The Centre line section's help text explains the outline.
- **`gui/measure_page.py`:** the hook `on_range_change`, called when the user changes the range.
- **`gui/theme.py`:** the outline's two colours.
- **Tests** (6 new, 306 in all):
  - `test_stabilize`:
    - the shift file read back by frame, None without one, a file without shifts refused;
    - the area of a range worked out by hand, with lost frames and the sentences;
    - the margin against the stabilizer's own move (below).
  - `test_spacetime`: the bounds.
  - `test_line_tasks`: a synthetic stabilized video with a shift file whose picture moves for 10
    frames is refused over a range holding them; a range without them is measured and its area
    and clearance saved. A video without a shift file saves `picture` as null.
  - `test_pipeline`: the CLI refuses the line over a range holding such frames and measures it
    over a range without them.
- **Docs:** README (the Centre line page, *How a recording is stabilized*, the slow range, the
  batch command), CLAUDE.md (the Centre line reminder, Stabilization, Known issues).

### The margin

The stabilizer moves each frame with bicubic interpolation (`shift_frame`), which blends the
black outside the recorded frame into the pixels beside the strip. The line is then read between
pixels (bilinear).

- The test moves a textured frame by known sub-pixel amounts with `shift_frame` and compares each
  line's samples with those of the same move of a larger texture, which has no strip. Lines
  10 px from the left and right edges are tested, one between pixels, under 83 moves from -12 to
  +12 px. Wherever the check passes, the samples are identical (difference below 0.01). Without
  the margin, frames whose blend reaches the line pass.
- A finer scan (scratch `margin_check.py`, moves in steps of 0.01 px):
  - Left side: lines whose samples start at 8.0–8.8 px are blended from a move of 7.02 px on. A
    margin of 2 px refuses them from 6.01–6.81 px on, a margin of 1 px only from 7.01–7.81 px.
  - Right side: samples ending at 151.0 px are blended from a move of -7.02 px. Samples ending
    between pixels (151.3–151.8 px) are blended from -6.02 px, because the bilinear read takes
    the next pixel. A margin of 2 px refuses them from -5.20 to -5.70 px on, a margin of 1 px from
    -6.20 px.
  - So 2 px is just enough on both sides, with as little as 0.3 px to spare, and 1 px is not.
    `EDGE_MARGIN_PX` is 3, which always leaves at least a pixel.

### On the recordings

Scratch scripts `real_edge_check.py`, `slow_vs_strip.py`, `fp03_clean.py` and `rest_areas.py` use
the lines of `analysis/aim1_feasibility/restabilized/results.csv` (limbs, whole loops and tissue
lines, as measured) and the videos in `StabilizedVideos/`.

- **At rest** (each recording's rest frames, as measured): 6 of 184 lines in 16 recordings reach
  the strip. All are on FP03_Wföre, which swings 185 px up and down with breathing: both limbs of
  loops E and F, and the two whole loops.
  - They reach it in 82–258 of the 2040 rest frames.
  - In 74–225 of those frames the line reads the strip itself (grey level 0). In the other
    frames its darkest sample is 34–39.
  - The other lines keep a median 99 px from the strip (the nearest 2.0 px).
- **In the occlusion** (official times, 2 s margins): 22 of 164 lines reach the strip, among them
  7 whole loops (FP03_Wföre A, B, E and F, FP05_Wföre L1, FP13_Qföre G, FP03_Qföre's curly loop).
  FP03_Qföre's 8 lines also hold lost frames (1612 of its 1764 occlusion frames).
- **The app's measurement** (pattern shift from 1 px/frame) was not affected on these lines.
  None of the 23 limbs it resolved at rest nor the 23 whole loops it counted reach the strip. The
  3 loops resolved in the whole-loop analysis's occlusion null (FP05_Wföre A and C, FP07_Wföre D)
  keep clear of it too. The aim-1 feasibility, whole-loop and `capillary.aims` numbers stand.
- **The slow range** (the slow-range validation's chosen variant, `stretched`, on the re-stabilized
  videos):
  - At rest, 4 of its 41 resolved limbs reach the strip: the four limbs of FP03_Wföre's loops E
    and F.
  - In the occlusion, 6 of its 22 resolved limbs reach it: FP03_Wföre A right, E left and right,
    F left and right, and FP13_Qföre G left.
- **FP03_Wföre's loops E and F were the strip.** This was CLAUDE.md's example of the picture
  moving: four limbs "moving" the same way at rest. Each line was measured over the stretches of
  rest that keep clear of the strip (at least 3 s each), against stretches of the same length
  that hold strip frames. Signal-to-noise and speed:
  - E left: whole rest 68.5 at -0.74 px/frame. Clear stretches 3.3 and 3.6 (2.0–8.9 s and
    9.3–50.8 s). Stretches with the strip 29.1 and 62.7, at -0.67 and -0.81 px/frame.
  - F left: 35.5 over the whole rest; clear 7.4, 3.0 and 4.8; with the strip 22–28.
  - F right: 23.0; clear 2.3–3.5; with the strip 20–25.
  - E right: 45.3 at -0.78 px/frame. Clear 10.4 and 9.4, but at -1.25 and -1.79 px/frame: a flow
    of its own that the strip had swamped.
  - F whole loop: 20.6 at -0.76 px/frame over the whole rest; 12.0 at -4.04 px/frame (0.16 mm/s)
    over 2.0–53.8 s, which it keeps clear of.
  - So the slow "flow" at -0.4 to -0.8 px/frame was the strip moving along the lines. The other
    16 limbs that seemed to flow in the occlusion are not explained by it, and the slow range
    still needs a check that the picture held still.
- **How much of the frame a line can use over the rest** (`picture_area` over each aims
  recording's official rest, 60 recordings):
  - A median 92% of the frame (10th percentile 77%): at least 90% on 40 recordings, 75–90% on
    14, below 75% on 6.
  - The 6: FP03_Qföre 53%, FP03_Wföre 54%, FP06_Wföre 59%, FP06_Qefter_försök2 69%, FP07_Qföre 70%
    and FP03_Wefter 0%.
  - FP03_Wefter moved more than 250 px up and down during its rest (the area every frame shows
    would run from y = 291.5 to 241.9). No line on it can be measured over its whole rest, which
    blind placement requires. A line in its middle reaches the strip in only 125 of its 2121 rest
    frames.

### How it was verified

- **Tests:** 306 pass. flake8's error selection is clean on the whole repository, and the touched
  files have the same 7 warnings as on `origin/main`, all in code not changed here.
- **The window** (scratch `gui_edge.py`, under WSLg on a scratch data folder with links to three
  videos and their shift files; no window took focus):
  - FP03_Wföre, E left over the rest: refused ("In 258 of the range's 2040 frames … Move it at
    least 50 px away from the bottom edge. The dashed outline shows …"). The outline was orange,
    Measure disabled, and the preview panel gave the same sentence.
  - The range set to frames 60–266 (2.0–8.9 s, which E left keeps clear of): no blocker, and the
    outline back to grey. So a change of range updates both.
  - Loop A as a whole loop over the rest: measured and saved; its provenance has `picture` with
    the area (30.4, 86.3)–(606.8, 374.5) and a clearance of 13.7 px.
  - Blind placement, FP03_Wefter (listed as E8FYS): the range was its official rest, and a line in
    the middle was refused ("… No part of the frame shows the picture in every frame of this
    range: it moved too far."), with no outline.
  - FP13_Qföre G left: clear over the rest. Over the occlusion it was refused (106 of 1734 frames;
    move it 13 px away from the left edge).
  - No Tk errors. The screenshots show the outline round the picture, grey or orange.

### Still open

- **Measuring only the frames in which a line lies in the picture** would recover lines near the
  edge, and FP03_Wefter (a line in its middle is clear in 94% of its rest). It was not built:
  which frames count is a methods decision for the PI, and the diagram, the blocks and the
  reports would need to carry the frames left out.
- The occlusion's slow "flow" in 16 limbs that keep clear of the strip still needs a check that
  the picture held still near the line.

## 2026-10-14 — The 28 new ESMOKE recordings stabilized

**Branch:** `feature/blind-whole-loop`. No code changed; this entry and CLAUDE.md's data notes.

The user copied the remaining ESMOKE recordings into `RecordedVideos/` from OneDrive, and asked
for the new ones to be stabilized: 28 raw videos of FP15–FP22. Each came with a Windows
`:Zone.Identifier` file beside it, which the app ignores.

**How:**
- The app's own job (`gui.tasks.stabilize`, the stabilizer as re-made on 2026-10-14) ran from a
  scratch script, 7 videos at a time, the aims' recordings first.
- The unfinished output went to `StabilizedVideos/.partial_batch/`, since the app empties
  `.partial/` when it starts. The folder was removed afterwards.
- It took 14.5 min: about 3.5 min per video, 0.5 min for the two short clips.

**Results:** all 28 videos were written with their shift files and provenance; none failed.
- **The 24 the aims use** (FP15, FP16, FP18, FP20, FP21 and FP22, four each):
  - median match over the official rest 0.69–0.94, and no frame lost in any rest;
  - the picture moved 8–84 px during the rest (FP16_Wefter most).
- **FP21_Qföre** jumps 103 px at 74.9 s, 13 s after the cuff went on (62.2 s). One frame is lost
  at 77.1 s, and 6 frames were carried from their neighbours. Its rest (11 px of movement, match
  0.88) is unaffected.
- **FP21_Wefter** has a median match of 0.47 over the whole recording (0.74 at rest), and 11
  frames were carried from their neighbours.
- **Not used by the aims:**
  - FP17_Qföre and FP17_Qefter_försök2 (FP17's W före has no official times);
  - FP17_Wföre and FP19_Wföre, clips of 26 and 24 s without official times.
- `FP21Wföre_20-Nov-2019_09-08-03` lacks the underscore after FP21, as in the official times. The
  inventory reads it.
- **On the desktop after this batch:** 61 stabilized videos, among them all 54 ESMOKE recordings
  the aims use. The two raw FP09 efter recordings, which the aims do not use, are still
  unstabilized.

**The first ISMOKE recordings, the same evening.** While the batch ran, the user began
extracting a second zip into `RecordedVideos/`: 12 ISMOKE videos of FP02, FP04 and FP07.
- **How:** a scratch script stabilized each video, with the same job, once its file had the size
  the zip lists and had stopped changing.
- **Result:** all 12 stabilized, none failed. Median match over the rest 0.66–0.94 (FP07_Cefter
  lowest), and no frame lost anywhere.
- **The aims use 6 of them:** FP04's two före recordings (aim 1), and FP07's four.
  - FP02 is used by neither aim: its S was recorded on two days, one of them together with C.
  - FP04_Sefter's rest is only 2 s.
- **Now:** 73 stabilized videos; 60 of the 90 recordings the aims use (ISMOKE 6 of 36).

## 2026-10-14 — Whole loops and blind placement in the app; the aims from the saved data sets

**Branch:** `feature/blind-whole-loop`, from `main` at `ec877bc` (PR #22, whole-loop lines in the
analysis, merged). Commit `3726237` (code, tests, README, CLAUDE.md, this entry).

The user decided to place the study's lines by hand ("as much manually as possible") and asked
whether the PI's idea, a mean over the capillaries visible in a video, is feasible. A check in the
session's scratchpad (below) found that it is, as the mean of the loops that can be measured. The
user then asked for the three pieces this needs:
1. blind placement, so that nothing but the anatomy decides where a line goes;
2. whole-loop lines on the Centre line page;
3. a script that turns the saved lines into one value per visit and computes aim 1's statistics.

**In short:**
- **Centre line page:** "The line follows" now offers any stretch, an arterial limb or a **whole
  loop** (base of one limb, over the apex, base of the other). A whole loop's result says which end
  lies on the arterial limb, and each limb is measured on its own as a check against movement. The
  recording's saved lines are drawn dashed, so that no loop is drawn twice.
- **Blind placement** (header button): only the aims' recordings are listed, under codes. The
  preview and every result are hidden, measuring uses the official rest, and Two boxes, Results
  and Validation are closed.
- **`python3 -m capillary.aims`:** one resting velocity per recording (the mean of its counted
  whole loops), then aim 1 per study: CV, smallest detectable change, Bland–Altman, ICC(A,1).
- **On real data** the app's measurement reproduces the analysis scripts' whole loops exactly, and
  the script reproduces the scratch check's per-visit means and statistics.

### Is a mean over the visible capillaries feasible? (the scratch check)

On the aim-1 rerun (`analysis/aim1_feasibility/restabilized/`, 16 recordings of 8 ESMOKE
participants, lines placed by Claude Code), at the app's rule. One value per capillary: the whole
loop where it is counted, else its measured limbs; a loop whose limbs ran the same way was left out.
- **Visible (traced) capillaries:** 62, about 4 per recording (1–8).
- **Measurable at rest:** 26 (42%). The other 36 show no moving pattern. It cannot be told whether
  their blood moves, so they cannot enter the mean, and counting them as 0 would be a guess.
- **Per visit:** 1–3 measurable capillaries (median 2). 13 of 16 visits have a mean, and 5 of 8
  participants have one at both visits. Requiring at least 2 per visit leaves 2–3 of 8 participants.
- **Spread:** within a recording the fastest capillary is 1.1–3.4 times the slowest (median 2.0; SD
  of the logs 0.46). With about 2 capillaries per visit, which ones are measurable alone moves a
  visit's mean by roughly 40% from day to day.
- **Agreement:** in the 5 participants the day-to-day CV was about 26% (typical error / mean) and
  ICC(A,1) 0.12–0.20. Five participants are too few to estimate either.
- **The W visit:** its mean was higher than the Q visit's in all 5 (1.4–2.8 times), though both
  recordings are before exposure. That happens by chance 1 time in 16; it needs a look in the full
  data.
- **The combined rule** (centre-line blocks for slow limbs) gives 7 of 8 participants, but its very
  slow block values raise the CV on the log scale to 118%.
- **Told the user:** feasible as the mean of the measurable loops, not of all visible ones. Keep the
  measuring automatic: at rest most loops' streaks are too faint to read by eye in a 3-s piece,
  while the pattern shift pools the whole minute. Fix with the PI, before measuring, which
  capillaries count, the mean with its count, and blinding.

### What changed

- **`capillary/spacetime.py`:** `Centreline.apex_arc_px()` is the apex's distance along a line
  drawn round a loop: the point farthest from both ends (the largest of the smaller of its two
  distances), searched in the middle 80% of the line.
  - Four rules were compared on the 53 loops, against where the two traced limbs met (scratch
    `apex_check.py`), as median / 90th percentile / largest error in px:
    - farthest from both ends: 1.3 / 6.7 / 17.5;
    - farthest from the bases' midpoint: 1.5 / 5.7 / 25.2;
    - farthest from the chord between the bases: 2.3 / 12.9 / 24.7;
    - half the line's length: 3.0 / 14.5 / 34.9.
- **`capillary/pattern_shift.py`:**
  - `WHOLE_LOOP` ('whole loop'), the role of such a line.
  - `loop_from_direction`: 'start' when the pooled flow runs along the line (the limb where the
    line starts is arterial), 'end' against it, 'unknown' when not resolved.
  - `loop_limbs`: the pattern shift of the diagram's positions up to the apex and from it, each on
    its own and pooled over the range, as velocities along the line.
    - Flow round the loop reads the same sign in both limbs. The picture moving along the loop's
      axis reads opposite signs.
    - So both limbs resolved with opposite signs give `loop_movement`. A limb shorter than 24 px
      is not measured.
- **`gui/tasks.py`:**
  - `summarize_line` takes the apex. For a whole loop it adds `arterial_end`, the limbs'
    `pattern_shift_start_limb_...` and `pattern_shift_end_limb_...`, and `loop_movement`.
  - `measure_line_dataset` and `regenerate_line_report` (from the provenance's points) pass the
    apex, and the provenance's description of the roles names the whole loop.
  - `Caper.py`'s report title and `capillary/datasets.py`'s docstring know the whole loop too.
- **`gui/line_page.py`:**
  - "The line follows" (three radio buttons) replaces the Arterial limb checkbox. Each role has its
    own hints and end labels: start and end on a whole loop, set outwards since a loop's bases lie
    side by side.
  - The result says which end lies on the arterial limb, and warns when the limbs moved opposite
    ways. A negative velocity no longer counts as a warning on a whole loop.
  - The suggested data set name follows the role: set1, limb1 or loop1 (`suggest_name`).
  - The lines of the recording's saved data sets are drawn dashed in light blue with their names,
    read once per recording and list of data sets.
  - During blind placement the preview is neither computed nor shown: a note takes its place.
- **`gui/measure_page.py`:**
  - The recording's code is used in the title, messages and job titles.
  - During blind placement, the range is set to the official rest when a recording opens, and
    measuring is refused unless the range is exactly the rest (`rest_window`). The last result is
    hidden, the saved message has no velocity, and the name hint does not show the file name.
- **`gui/blind.py`** (new):
  - `code(stem)`: the recording's name, NFC-normalized, hashed (SHA-256) into 5 characters from
    an alphabet without 0/O and 1/I. The same on every computer and every day. A code two names
    share gets -2, -3 (`codes`).
  - `aim_recordings()`: the recordings `capillary.inventory` assigns to the aims.
  - `listed()`: those recordings, in the order of their codes. Every recording is listed when the
    official times cannot be read.
- **`gui/app.py`:**
  - The header button "Blind placement", yellow while on. Switching it on or off asks first (off
    in red), and the state is kept in settings.csv as `blind_placement`.
  - `display_name` gives the code during blind placement. The list, the window title and the
    stabilization messages use it.
  - Two boxes, Results and Validation are greyed out and refused (also by Ctrl + 2/3/4), with a
    message in the status bar.
  - Switching it on sets the open recording's range to the rest at once.
- **`gui/library_view.py`:** the list shows display names and filters by them. During blind
  placement the context menu's Two boxes, Results, Show in folder and Move to trash are disabled.
- **`gui/results_page.py`:** cards state a whole loop's arterial end and warn of movement.
- **`gui/theme.py`:** the saved lines' colour, the yellow "on" header button, and a dim colour
  for disabled tabs.
- **`capillary/aims.py`** (new), `python3 -m capillary.aims [--data] [--observer] [--out]`:
  - `collect` reads every centre-line provenance.
  - `loops` counts a whole loop when it lies within the official rest (`phase` 'rest'), is
    resolved, shows no `loop_movement` and was measured on a stabilized video. Otherwise
    `why_not` gives the reason.
  - Loops of one recording that lie on top of each other are listed (half of the shorter within
    6 px of the other): one capillary probably drawn twice. They are not removed; that is the
    observer's call.
  - `per_recording`: the mean of the counted loops' speeds (the velocity's size), with the
    numbers of loops placed and counted.
  - `aim1_recordings` takes each participant's before-exposure recordings from the inventory, and
    `aim1_pairs` and `aim1` give per observer and study:
    - the participants with a mean at both visits and at one only;
    - the typical error (SD of the differences / sqrt 2), the CV (typical error / grand mean) and
      the CV on the log scale;
    - the smallest detectable change, 2.77 × the typical error;
    - Bland–Altman bias and limits (`agreement.bland_altman`), and ICC(A,1) with its 95% interval
      (`agreement.icc`).
  - The tables go to `Reports/aims/`. The data folder comes from settings.csv unless `--data` is
    given.
- **Tests** (13 new, 300 in all):
  - `test_spacetime`: the apex on the simulated hairpin and on a loop with uneven limbs.
  - `test_pattern_shift`: a whole loop names its arterial end and measures each limb at the true
    speed, both ways round. Limbs moving opposite ways are movement, while a still limb or one too
    short is not.
  - `test_line_tasks`: a whole loop measured, saved and regenerated as the page does it.
  - `test_blind`: codes stable and the same for NFD names, collisions told apart, the listing and
    its order, and the inventory's choice.
  - `test_aims`: which loops count and why not, duplicates, the per-recording mean, aim 1 against
    hand computation, and the command's tables and summary.
- **Docs:** README (Centre line, blind placement, the whole loop, `capillary.aims`, code table) and
  CLAUDE.md.

### How it was verified

- **Tests and lint:** 300 tests pass. flake8 is clean on CI's selection, and the touched files add
  no warnings (the remaining ones are in code unchanged from `main`).
- **The app's measurement on real data** (scratch `e2e_loops.py`):
  - `gui.tasks.measure_line_dataset`, with role whole loop and the official rest from
    `inventory.recording_phases`, measured the 53 whole loops of the aim-1 rerun (points as
    `measure.py` joins them) into a scratch data folder.
  - The rest frames are the same for all 53, and both resolve the same 24 loops. Velocities and
    scores are identical.
  - The arterial end agrees with `measure.py`'s arterial limb in 24 of 24.
  - The apex split marks one loop as movement, FP06_Qföre_försök2 H (limbs −0.047 and +0.049 mm/s
    along the line). It is the same loop the separately traced limbs marked.
- **`capillary.aims` on those data sets:**
  - 23 loops counted (29 not resolved, 1 movement); 13 of 15 recordings with loops have a mean,
    from 1–3 loops (median 2).
  - ESMOKE aim 1: 5 of 14 participants with a mean at both visits, 3 at one only. Mean
    0.118 mm/s (W 0.151, Q 0.085).
  - Typical error 0.031 mm/s, CV 26% (log scale 26%), smallest detectable change 0.086 mm/s.
  - Bland–Altman bias 0.066 mm/s (95% CI 0.011 to 0.120), limits −0.020 to 0.152. ICC(A,1) 0.12
    (−0.15 to 0.73).
  - These are the scratch check's numbers.
- **The window** (scripted under WSLg, on a scratch data folder with links to the 16 videos; no
  window took focus):
  - Without blind placement: the list, the saved lines (6 of FP13_Wföre) and the name loop1
    suggested for a whole loop.
  - Blind placement on: 16 recordings by code, the code in the panel and the window title, the
    three pages greyed out, and Results refused with its message. The range was set to the rest at
    once, and the preview was hidden.
  - A whole loop was measured and saved (role whole loop, phase rest, frames 60–1622) with no
    result shown, and a seventh dashed line appeared. Measuring the whole video was refused.
  - Blind placement off: names, the result and the preview came back. There were no Tk errors.
  - Screenshots were checked: the start and end labels lie apart, and the options fit the panel.

### Still open

- **Snap-to-vessel** (tracing along the vessel's ridge as the line is clicked) was proposed as an
  optional fourth piece and not built.
- **Aim 2's statistics:** `recordings.csv` already has every recording's mean.
- **The protocol to agree with the PI before placing:**
  - which loops count (for example every loop whose two limbs and apex show in the resting image,
    chosen before measuring);
  - the mean with its count;
  - at least one loop per visit;
  - what to do with flagged duplicates.

## 2026-10-14 — Whole-loop lines: resting flow measured in more loops

**Branch:** `analysis/whole-loop`, from `main` at `0984a7f` (PR #21, the aim-1 rerun, merged).
Commit `9498265` (scripts, results, READMEs, this entry, CLAUDE.md).

The user asked whether the program could be changed to give better readings. A test in the
session's scratchpad suggested measuring along the whole capillary loop instead of one limb at
a time, and the user asked for it in the analysis scripts. The app is not changed.

**In short:** at the app's own rule (a pattern-shift score of 8 or more):
- one line up one limb, over the apex and down the other measures 23 of 53 loops, against
  14 by their single limbs;
- 5 of 8 participants get a loop at both visits, against 2 of 8 by single limbs.

### Why it should help

- **More of the pattern.** Limb lines are short (36–172 px), and the pattern shift's score
  grows with the pattern it can pool. Flow runs one way round a loop, up the arterial limb and
  down the venous limb. A line round the loop therefore follows one moving pattern for about
  twice the length.
- **Movement partly cancels.** If the picture moves along the limbs, it moves the pattern
  forward along one half of the line and backward along the other.

### What changed

- **`analysis/aim1_feasibility/measure.py`:**
  - `whole_loops` joins the traced lines of each loop's two limbs: up the first limb as listed
    in `lines.json`, then down the second. Nothing more is placed by hand.
  - Each whole loop is measured with the limbs and written as kind `loop`, line
    `<loop>, whole loop`, with the columns `first_limb`, `second_limb`, `arterial_limb` and
    `slow_arterial_limb`.
  - A positive velocity runs from the first limb's base to the second's, which names the first
    limb arterial (`arterial_limb`).
  - The limbs and tissue lines are measured as before.
- **`analysis/aim1_feasibility/summarize.py`:**
  - Whole loops are counted on their own at every level: per recording `whole_loops`,
    `whole_<level>` with the speeds; per participant `whole_<level>_both_visits`.
  - **The movement rule:** a whole loop is not counted at a level where both its limbs are
    measured and run the same way, both towards the apex or both away (`<level>_contradicted`).
    Blood goes up one limb and down the other, so that is the picture moving. The aim-1 check
    already used it to judge loops.
- **`analysis/whole_loop/`** (new): `validate.py` compares each whole loop with its limbs at
  rest and samples the whole loops again over the occlusion as a null. With `README.md`,
  `loops.csv` and `occlusion.csv`.
- **`analysis/pattern_shift_slow_flow/validate_real.py`** now reads only limbs and tissue
  lines. With whole loops in the results, its occlusion part would have failed on them.
- **The rerun's results** (`analysis/aim1_feasibility/restabilized/`): `results.csv` gained 53
  whole-loop rows, and the two summaries gained whole-loop columns.
- **The READMEs** of `aim1_feasibility/` and `restabilized/` mention the whole loops.

### Results

All on the 16 before-exposure recordings of the rerun. The 53 loops with both limbs traced are
in 15 of them (FP12_Qföre has none). The whole-loop lines are 72–357 px long (median 159).

| Level | Whole loops measured (of 53) | The same loops by either limb |
| --- | --- | --- |
| Resolved (the app's rule) | 23 | 14 |
| Robust | 17 | 10 |
| Combined (exploratory) | 28 | 17 |
| Slow range | 33 | 22 |

**Per participant**, a value at both visits:
- **Whole loops, app's rule:** 5 of 8. This is as many as the exploratory combined rule gives
  on all 115 limbs; the app's rule on all limbs gives 2 of 8.
- **Same loops only:** on the 7 participants with two-limb loops at both visits, whole loops give
  5 and their limbs 2.
- **Other levels (whole loops / those loops' limbs):** robust 5 / 1, combined 6 / 3, slow range 6 / 4.

**Checks:**
- **The score** of a whole loop is a median 1.6 times its better limb's (quartiles
  1.16–1.91). It is lower in 8 of 53.
- **Loop and limbs both measured** (11 loops): the whole loop's speed is a median 0.94 of its
  measured limbs' mean (range 0.64–1.03). The flow's direction names the same arterial limb in
  11 of 11.
- **Measured only as a whole loop** (12 loops): the limbs had seen the same flow too weakly.
  Their best speeds (unresolved, scores 2.5–15, median 5.1), taken round the loop, ran the same
  way as the whole loop's in 23 of 24 limbs. They lay within 25% of it in 15, and at least one
  limb did in 10 of the 12 loops.
- **So the gain is signal, not range.**
  - **A correction to what the user was told:** earlier in the session, I said about half of the
    newly measured loops flowed faster than their limbs could follow. That used the reach of
    the centre-line block method (about 0.045 × line length px/frame), not the pattern shift's.
    The limbs' own best speeds show they saw the same flow.
- **The movement rule** removed one loop at the app's rule: FP06_Qföre H. Both its limbs read
  flow away from the apex (−0.046 and −0.048 mm/s), and the whole loop had followed the stronger
  half. In the slow range it removed 4.
- **The whole loops measured** (app's rule): 0.048–0.33 mm/s, median 0.092. The 95% interval is
  clear of zero in 20 of 23, and both halves of the rest score 8 or more in 16.
- **The occlusion as a null** (from 15 s after the cuff went up until 2 s before release; FP03_Qföre
  lost, FP07_Qföre and FP09_Wföre without a release time):
  - none of the 21 whole loops measured at rest shows flow (scores median 4.0);
  - over all 46, three do: FP05_Wföre A and C and FP07_Wföre D, at 0.05–0.08 mm/s, none of them
    measured at rest;
  - single limbs show flow under the cuff in 2 of 97 at the same rule.

### What it means

- **For aim 1:** whole loops at the app's validated rule give as many participants a value at
  both visits as the exploratory combined rule on limbs, without the combined rule.
  - They cost the speed per limb: the arterial and venous speeds are pooled into one.
  - They keep the arterial limb, named by the direction.
- **Fix before the new recordings:** the line geometry and the movement rule should be set before
  the 6 ESMOKE participants not yet measured, which are then their first test.
- **The app** cannot draw such a line as one yet with its limb workflow. A whole-loop mode on the
  Centre line page is the next part, if the user places lines in the app.

### Verification

- **First run reproduced:** after re-measuring the rerun, its 131 limb and tissue rows are
  identical to before, and the first run's summaries are rewritten byte for byte.
- **Other scripts reproduced:** `restabilized/compare_runs.csv` and
  `pattern_shift_slow_flow/real_results_restabilized.csv` come out identical to the committed
  files.
- **The scratch test reproduced:** `whole_loop/validate.py` gives the same numbers as the
  scratchpad test (24 whole loops before the movement rule, 3 of 46 in the occlusion).
- **Tests and lint:** `python -m pytest` 287 passed. flake8 is clean on the CI selection for the
  whole repository, and in full on `analysis/aim1_feasibility/`,
  `analysis/pattern_shift_slow_flow/` and `analysis/whole_loop/`.

---

## 2026-10-14 — Aim 1's feasibility, again on the re-stabilized videos

**Branch:** `analysis/aim1-restabilized`, from `main` at `213f0c3` (PR #20, the re-stabilization,
merged). Commit `b2685a9` (scripts, results, READMEs, this entry, CLAUDE.md).

The user asked to rerun the aim-1 check of 2026-10-12 on the videos the new stabilizer made.
The check's numbers came from the old videos, and they are what goes to the supervisors.
- The check's lines were moved onto the new videos, and FP01_W was added.
- The slow range of the pattern shift was measured alongside the default.
- Everything is in `analysis/aim1_feasibility/restabilized/` (with a README). The first run's
  files stay as they were, as the record of the old videos (now in `.trash/`).

**In short:** the re-stabilization changed almost nothing at rest. The first run's
conclusion stands: resting CBV from an arterial limb at both visits is available in at most
3 of 8 participants, whichever rule is used.

### Why rerun

- The new stabilizer centres each video on its official rest, so every picture moved
  (1.8–169 px in these recordings) and the old lines no longer fit.
- It also builds its references from the rest. The match at rest rose in most recordings
  whose references moved there (FP12_Wföre 0.42 → 0.87, FP12_Qföre 0.42 → 0.82, FP09_Qföre
  0.48 → 0.75). Would better-aligned rest frames give more measurable limbs?
- FP01_W could be stabilized for the first time, so FP01 could have both visits.

### How

**The scripts can work on a second run** (`analysis/aim1_feasibility/`):
- `common.py` gained `use(folder)` and `run_args(args)`. A script works on the first run's
  folder (lines, results, `out/`) unless given `--dir <folder>`. `rest_image.py`, `zoom.py`,
  `measure.py` and `summarize.py` take it.
- `measure.py` also measures the pattern shift with its slow range
  (`min_speed=SLOW_MIN_SPEED`). Its results are the keys `slow_pattern_shift_...` and
  `slow_limb_check`.
- `measure.py --jobs N` measures N recordings at once. All 16 took 84 s with 8.
- `summarize.py` counts a fourth level, `slow` (resolved by the slow range), where the
  results have it. It also reports each recording's tissue line's slow score.
- Without `--dir` the scripts work as before. `summarize.py` rewrote the first run's two
  summary files byte for byte.

**Moving the lines** (`restabilized/move_lines.py`):
- **The move:** the stabilizer's shift files record how far each frame was moved (what the
  raw frame shows at p, the stabilized frame shows at p + shift). A point of the old video
  therefore lies at p + (new shift − old shift) in the new one. Each recording's lines were
  moved by the median of that difference over the official rest. The old shift files are in
  `.trash/`; they were written on 2026-10-11, before the lines were placed.
- **The moves:** 1.8–169 px (`moves.csv`).
  - **Check:** registering the old resting image onto the new one (`cv2.phaseCorrelate` on
    the band-passed images, its sign checked on a synthetic shift) gives the same move
    within 0.4 px in all 15 recordings.
  - In 5 recordings every rest frame moved by exactly the same amount.
  - In the other 10 the stabilizer placed the rest frames differently relative to each
    other: single frames lie a median 0.1–1.0 px off the median move (95th percentile up to
    3.7 px, FP12_Wföre).
- **Still on the vessel?** Each moved line was traced on the new resting image and compared
  with its first-run trace, moved the same way (`line_check.csv`).
  - All 109 limbs lie within a mean 0.85 px of it, and the ridge values are unchanged
    (median difference 0.00).
  - Four lines end 3–6 px from where they ended before: FP03_Qföre F, FP07_Wföre A right,
    FP09_Wföre B left and FP13_Qföre A right. Close-ups with both traces drawn showed them on
    the same vessel; an end point had snapped to a neighbouring pixel.
  - No line was corrected.

**FP01_W** (`FP01_W_14-Oct-2019_08-36-26`):
- Placed by Claude Code (the AI assistant) by the first run's rules, from its resting image
  only and before anything was measured. Close-ups at 4–6× were used to place the points, and
  the traced lines were checked on a close-up sheet.
- Loops A, C and E (6 limbs, 40–68 px), and a 110-px line through tissue between A and B.
- Loops B and D were left out. They are figure-of-eight loops whose limbs cross about 30 px
  below the apex, short of the rules' 40 px.
- Its official rest is 33.6 s, against 52–77 s in the other 15 recordings. Its name has
  neither före nor efter (`metadata/README.md`).

**Measured:** every line over the official rest (`measure.py --dir restabilized --jobs 8`),
then `summarize.py --dir restabilized` and `restabilized/compare_runs.py`.
- `compare_runs.py` sets the two runs side by side, line by line, at every level.
- The first run's slow range is the slow-range validation's `stretched` variant at rest
  (`pattern_shift_slow_flow/real_results.csv`). It is the same estimator
  (`pattern_shift(min_speed=0.1)`) on the first run's diagrams.

**The slow-range validation on the moved lines** (`validate_real.py --dir restabilized`):
- The script sampled its occlusion from `StabilizedVideos/` along the first run's lines,
  which no longer fit. It now takes `--dir`, and writes `real_results_restabilized.csv` and
  `out/restabilized/`.
- It now leaves out the occlusion of a recording whose occlusion frames the stabilizer lost
  (`placed_by` 'lost' in the shift file). All 1374 of FP03_Qföre's are lost (the 500-px jump
  when the cuff goes on), and the first try failed on its blank diagrams.
- Its "(of 7)" participants is now counted.

### Results

**At rest, the 109 limbs measured in both runs:**

| Level | First run | Rerun | Both | First only | Rerun only |
| --- | --- | --- | --- | --- | --- |
| Resolved (the app's rule) | 24 | 23 | 22 | 2 | 1 |
| Robust | 16 | 17 | 16 | 0 | 1 |
| Combined (exploratory) | 30 | 30 | 29 | 1 | 1 |
| Slow range | 42 | 41 | 40 | 2 | 1 |

- **Velocities of limbs counted in both runs:** the same direction every time.
  - Resolved, robust and combined: rerun/first 0.93–1.09 (median 1.00), at most 0.005 mm/s
    apart.
- **The three limbs that changed** all lay near the threshold, and moved both ways:
  - FP01_Qföre's "2" loop: score 8.3 → 7.3;
  - FP13_Qföre F right: 8.1 → 6.5;
  - FP09_Qföre A right: 6.9 → 8.7. It is the only limb gained, in the recording whose match at
    rest rose most after FP12's.
- **FP12_Qföre and FP12_Wföre** (match at rest 0.42 → 0.82 and 0.87) gained nothing.
- **The scores move by about 5% between two equally good placements of a line.**
  - The scores changed by a median 5% (90th percentile 18%). They changed as much in the 5
    recordings whose rest frames moved as a whole (33 limbs) as in the 10 whose frames were
    placed differently (76 limbs).
  - So the change comes from the line's sub-pixel position and the interpolation, not from
    the registration.
  - For limbs scoring 5–12, the change reached 1.4 (90th percentile). A limb within about
    1.5 of the threshold of 8 can fall on either side of it.
- **The slow range's speed below 1 px/frame is less repeatable.**
  - From 1 px/frame (0.04 mm/s), all 22 limbs measured in both runs agree within 10%.
  - Below it, 10 of 18 agree within 10% and 16 within 25%.
  - Two changed much despite high scores (16–20): FP06_Qföre E right 0.015 → 0.025 mm/s and
    FP09_Wföre B left 0.009 → 0.023 mm/s. This fits the earlier finding that real slow flow
    is often not a steady translation (the slow-range entry below).
- **FP01_W:** no limb resolved at any level. The best were E left (score 7.3) and E right
  (5.6); its tissue line scored 2.0.
- **Tissue lines:** none resolved at any level (16 lines, highest score 4.5).
- **Loops with both limbs counted:**
  - resolved: 8 (7 opposite);
  - combined: 11 (all opposite);
  - slow range: 17 (13 opposite, 4 the same way).

**Per participant** (8 now have both visits measured; first run 7):

| Rule | Arterial limb at both visits | Any limb at both visits | First run: arterial / any |
| --- | --- | --- | --- |
| Resolved | 1 (FP06) | 2 | 1 / 2 |
| Robust | 0 | 2 | 0 / 2 |
| Combined | 2 (FP09, FP13) | 5 | 1 / 4 |
| Slow range | 3 (FP06, FP09, FP13) | 4 | 2 / 3 |

FP09 enters the combined and slow rows through FP09_Qföre A right, the one limb that crossed
the threshold.

**The occlusion** (the slow-range validation, `stretched`):
- On the 91 limbs both runs measured there, the slow range found slow "flow" in 23 before and
  22 after. The one difference sat at the threshold (score 8.01 → 7.99).
- Over all occlusion windows of the rerun: 22 of 97 limbs (FP03_Qföre out, FP01_W in).
- So the slow speeds under the cuff do not come from the movement of the whole picture,
  which the new stabilizer follows. They are local movement (FP13_Qföre's loop E bows),
  the frame's uncovered edge, or real residual flow; the user and the PI think blood probably
  still moves under the cuff.

### What it means

- **For aim 1:** the re-stabilization does not change the feasibility picture, and FP01's
  W visit adds no limb.
  - The questions for the supervisors stay as they were: arterial-only or any limb, and which
    rule. Arterial at both visits is available in 0–3 of 8 participants; any limb in 2–5.
- **Line placement matters near the threshold.** A sub-pixel change of a line moves a limb's
  score by about 5%. In the real analysis, the observer's placement will decide limbs scoring
  about 6.5–9.5.
  - The rule must be fixed beforehand.
  - The scores should be reported, not only resolved or not.
  - A sensitivity analysis (for example a threshold of 7 or 9) would show how much the
    results lean on it.
- **The slow range** gives about as many limbs as before. Below 1 px/frame its speed can
  change by a factor of 2 with the line.
  - What it needs before it can be used is unchanged: a local check that the picture held
    still near the line. The global re-stabilization did not reduce the slow "flow" in the
    occlusion.

### Verification

- `python -m pytest`: 287 passed.
- flake8: the CI selection (E9, F63, F7, F82) on the whole repository is clean. The full check
  (`--max-line-length=127`) on `analysis/aim1_feasibility/` and
  `analysis/pattern_shift_slow_flow/` is clean too.
- The first run is reproduced:
  - `summarize.py` without `--dir` rewrote `summary_recordings.csv` and
    `summary_participants.csv` byte for byte;
  - `validate_real.py --summary` prints the first run's tables as before;
  - `compare_runs.py` finds the first run's 24 / 16 / 30 / 42 limbs.
- The moves were checked by the image registration (within 0.4 px), and the moved lines by
  their distance to the old traces and by close-ups.
- Only analysis scripts changed; the app and the `capillary` package did not.

### Files

- Changed: `analysis/aim1_feasibility/` `common.py`, `measure.py`, `rest_image.py`,
  `summarize.py`, `zoom.py` and `README.md` (the rerun, `--dir`, where the old videos are);
  `analysis/pattern_shift_slow_flow/validate_real.py` and `README.md`.
- New: `analysis/aim1_feasibility/restabilized/`:
  - `README.md`, `move_lines.py`, `compare_runs.py`;
  - `lines.json`, `moves.csv`, `line_check.csv`, `results.csv`, the two summaries and
    `compare_runs.csv`.
- New: `analysis/pattern_shift_slow_flow/real_results_restabilized.csv`.
- Not tracked: `restabilized/out/` (resting images, lines drawn, diagrams) and
  `pattern_shift_slow_flow/out/restabilized/` (occlusion diagrams).
- The scratch scripts used to place and check FP01_W's lines (`sheet.py`, `checksheet.py`,
  `addlines.py`, `place.sh`) are in the session scratchpad, adapted from those of 2026-10-12.

---

## 2026-10-14 — Every stabilized video re-made with the new stabilizer

**Branch:** `fix/stabilizer-large-movements` (no code changed; this entry only).

The user asked to re-stabilize the 31 videos in `StabilizedVideos/` that the earlier
stabilizer had made, knowing their picture would move. All 33 are now made by the
stabilizer of the entry below. The 31 provenance files record commit `94b756d`, which has
the same stabilizer code as `f3bd7a1`. All are clean.

### How

- Each video went through the app's own stabilize job (`gui.tasks.stabilize`), 14 at a time,
  from its raw recording in `RecordedVideos/`. Each took 3–9 minutes.
- The job moved each previous video, with its shift file and provenance, to `.trash/`, one
  dated folder per recording: 31 folders, `2026-10-14_10-19-14_… previous stabilized video` to
  `2026-10-14_10-28-23_…`. Nothing was deleted.
- The new shift file of every recording was compared with its old one in `.trash/`, per
  official phase. Scratch scripts in the session scratchpad: `restabilize_all.py` and
  `compare_restab.py`.

### Results

- **The centring moved.** The new videos are centred on the median shift over the official
  rest, not on the references' frame. So the picture moved, by the same amount in every
  frame:
  - 1.8–169 px (median 25 px; over 50 px in 9 recordings);
  - the largest are FP05_Wföre 169 px, FP03_Qföre 114 px and FP07_Qföre 93 px.
- **Where the references' frame stayed the same** (13 recordings), the shifts relative to each
  other are unchanged: at most 0.14 px apart at rest, and so are the matches.
- **Where the references moved into the rest** (18 recordings, from frames as late as 5530):
  - **Rest:** the match rose in 16. The largest gains were FP12_Wföre 0.42 → 0.87,
    FP12_Qföre 0.42 → 0.82, FP12_Wefter 0.50 → 0.83, FP12_Qefter 0.44 → 0.77 and FP09_Qföre
    0.48 → 0.75.
    - FP07_Qföre fell, 0.76 → 0.61, and FP07_Wefter is unchanged (0.91 → 0.90).
    - Old and new placements agree within a median 0.1–0.9 px (relative to each other). The
      largest single differences are in FP12_Wföre (up to 10 px), whose old match of 0.42 at
      rest suggests the old placement was the wrong one.
  - **Occlusion:** the match fell where the old references lay there:
    - FP06_Qföre 0.75 → 0.36;
    - FP09_Qföre 0.85 → 0.53;
    - the four FP12 recordings about 0.85 → 0.50;
    - FP06_Qefter 0.91 → 0.66.

    The frames are still placed where they were (median 0.2–0.9 px apart, at most 6 px in
    FP12_Wföre). So the lower number reflects references built in the rest, which look less
    like the occlusion. It does not mean the frames are misplaced.
  - **After release:** the match mostly rose (FP12_Wföre 0.39 → 0.83). It fell in FP05_Wföre
    (0.81 → 0.66) and FP06_Qföre (0.85 → 0.62).
- **Frames not placed by the references:** a few were carried from neighbours (FP02_Wföre 5,
  FP07_Qföre 3, FP03_Qefter 2, FP05_Wefter 1). Only FP03_Qföre lost frames: 3193, everything
  after the cuff, as in the entry below.
- **Four recordings have a rest window but no occlusion window:** FP06_Wefter, FP07_Qefter,
  FP07_Qföre and FP09_Wföre. So only their rest was compared.

### What no longer fits

- **The lines of the aim-1 check** (`analysis/aim1_feasibility/lines.json`) and of the
  slow-range validation (`analysis/pattern_shift_slow_flow/`) were placed on the old videos.
  On the new ones they are off by the recording's centring change.
  - Their saved results and diagrams stay a valid record of the old videos.
  - To rerun either check, the lines must be shifted (the median shift difference at rest,
    from the two shift files) or placed again.
- **Data sets:** the only one on a re-stabilized video is `set1` of FP01_Wefter 10-13-03, the
  two-box set already known to be unreliable (Known issues). The FP01_Qefter 09-46-17 sets are
  on a recording that is not in `StabilizedVideos/`.
- `Validation/reading1` was drawn from video that had never been stabilized and is not affected.

---

## 2026-10-14 — The stabilizer follows large movements frame to frame

**Branch:** `fix/stabilizer-large-movements`, from `main` at `99aa56c` (PR #18, the pattern
shift's slow range, merged by the user).

**Commits:**

- `f3bd7a1` — the stabilizer and this entry
- a follow-up noting the commit and the two recordings stabilized with it

**Stabilized into `StabilizedVideos/`** with `f3bd7a1` (clean tree, recorded in the provenance),
two at once in about 8 minutes:

- **FP01_W_14-Oct-2019_08-36-26:** the references around frame 1046. Median match 0.80;
  4 frames from neighbours; 307 lost (the dark end, from about 141 s).
- **FP03_Wefter_21-Oct-2019_10-21-58:** the references around frame 675. Median match 0.71;
  53 frames from neighbours; none lost.

The results are the same as the scratch runs below. `StabilizedVideos/` now holds 33 videos: all
the aims use among the 35 raw ESMOKE recordings, plus FP02_Wföre and FP04's two.

The user chose the stabilizer as the next task. On the slow range's occlusion results (the entry
below), the user said the blood probably still moves under the cuff, which the PI had thought
likely when looking at the videos.

### What failed, and why

The registration of 2026-10-08 failed on three recordings: FP01_W, FP03_Wefter, and FP03_Qföre
after the cuff. To see why, every frame of five raw recordings was registered onto the frame
before it (scratch script).

- **FP01_W** drifts slowly and smoothly for 140 s; neighbouring frames match at 0.85–0.9.
  - Then the picture goes dark (mean grey 70 → 9), and its last ~8 s are noise.
  - The references were built around the sharpest frame of the whole recording, at 141 s, in
    that darkening end, about 200 px from where the picture spends the recording. So no frame was
    found (match 0.08).
  - The occlusion (38 s) and release (102 s) lie in the good part.
- **FP03_Wefter** makes excursions of 100–200 px at rest. Neighbouring frames still match
  (lowest 0.45, steps up to 49 px), but the search against the references, led by the previous
  frame's position, lost them.
- **FP03_Qföre** moves about 500 px sideways and 300 px down within ~10 s of the cuff going on,
  and stays there.
  - From then on the camera sees a part of the finger that shares almost nothing with the resting
    picture.
  - No translation brings it back into the same 640 × 480 frame. Its rest was always fine.
  - Its stabilized video had been centred on the median of all frames, which lay in the
    post-cuff view, so its rest sat far off-centre.
- **FP07_Qföre** (stabilized, 9 frames at the search limit) makes one excursion of about 400 px
  at 135 s, after the rest.

### The new procedure (`capillary/stabilize.py`; the module docstring has the details)

1. **First reading: follow the movement.**
   - Every frame is registered onto the frame before it, with the same coarse and fine search,
     giving a path of the picture.
   - A frame that matches the one before it below `STEP_MIN_MATCH` = 0.3, or only at the edge of
     the search, breaks the path, and a new stretch begins.
   - The sharpness and mean grey of every frame are kept.
2. **The references' centre** is the sharpest frame among those that:
   - lie within `REFERENCE_RADIUS_PX` = 40 px of the median position along the path, so as much
     of the recording as possible overlaps the references;
   - have a usual mean grey (within `BRIGHTNESS_FACTOR` = 1.5);
   - lie on the stretch of path that holds most of them;
   - come from the official rest when the recording has official times (`rest_window`, via
     `capillary.inventory`), since resting velocity is measured there.

   The references are built from it and its 24 neighbours as before (a second, short reading).
3. **Third reading: register onto the references** as before. The fine search is now led by
   where the frame should be: the frame before's position plus the step between them along the
   path. Before any frame has been placed, it is led by the position along the path relative to
   the references' centre.
   - A frame is placed by the references (`placed_by` 'references') when it matches them at
     least `MIN_MATCH` = 0.3, the two references agree within `MAX_DISAGREEMENT_PX` = 2 px, and
     the match lies inside the search.
4. **Frames the references miss** are carried along the path from the placed frames before and
   after them on their stretch, the path's own drift spread evenly between the two (`bridge`;
   'neighbours').
   - A stretch with no placed frame is 'lost': no shift, written black.
5. **Re-centring** is on the median shift over the official rest (else all frames), so the
   picture sits where it is during the rest.
6. **Writing** is unchanged. The video is now read four times.

**The shift file** gains `placed_by`, `step_x_px`, `step_y_px`, `step_match` and `mean_grey`.
The summary counts the frames placed from neighbours and those lost. The command line prints
them, and the provenance describes the new steps.

### Results on seven recordings

All were stabilized into a scratch folder with the new code. Seven ran at once in about
17 minutes (the frame-to-frame reading adds a third to the time).

Per official phase: how the frames were placed, and the median match with the references.
"Old" is the video in `StabilizedVideos/`, stabilized with the code of 2026-10-08.

| Recording | Phase | Old: match | New: by references / neighbours / lost | New: match |
| --- | --- | ---: | --- | ---: |
| FP01_W | rest | (failed, 0.08 overall) | 1008 / 0 / 0 | 0.85 |
| FP01_W | occlusion | | 1821 / 0 / 0 | 0.77 |
| FP01_W | after release | | 1088 / 4 / 247 (the dark end) | 0.83 |
| FP03_Wefter | rest | (failed, 0.24) | 2068 / 53 / 0 | 0.74 |
| FP03_Wefter | occlusion and later (no release time) | | 3801 / 0 / 0 | 0.69 |
| FP03_Qföre | rest | 0.68 | 1695 / 0 / 0 | 0.68 |
| FP03_Qföre | occlusion | 0.14 (wrong) | 152 / 0 / 1612 | 0.12 |
| FP03_Qföre | after release | 0.11 (wrong) | 0 / 0 / 1401 | 0.10 |
| FP07_Qföre | rest | 0.76 | 1689 / 0 / 0 | 0.61 |
| FP07_Qföre | occlusion and later | 0.75 | 3406 / 3 / 0 | 0.65 |
| FP01_Qföre | rest / occlusion / after release | 0.88 / 0.70 / 0.74 | all by references | 0.88 / 0.70 / 0.74 |
| FP03_Wföre | rest / occlusion / after release | 0.60 / 0.66 / 0.59 | all by references | 0.68 / 0.57 / 0.55 |
| FP12_Wföre | rest / occlusion / after release | 0.42 / 0.80 / 0.39 | all by references | 0.87 / 0.50 / 0.83 |

**New against old shifts** (a constant offset removed; the largest coordinate per frame):

- **FP01_Qföre:** identical (at most 0.02 px).
- **FP03_Qföre at rest:** identical (at most 0.13 px).
- **FP03_Wföre:** median 0.3–0.5 px; 14 of 2040 rest frames differ by more than 1 px.
- **FP07_Qföre at rest:** median 0.54 px, at most 1.34.
- **FP12_Wföre at rest:** median 0.85 px, at most 10 px (the old registration's weak rest).
- The references' centre moved into the rest wherever the old one lay elsewhere: FP03_Wföre
  (frame 3002 → 91), FP12_Wföre, FP07_Qföre. The match is highest near where the references
  come from, so the rest gained and later phases lost a little.

**Movement left in the output** (scratch script). Each output frame, its central two thirds, was
registered onto the frame before it; the table gives the steps over 1 px.

| Recording | Old | New |
| --- | --- | --- |
| FP12_Wföre at rest | 515 | 0 |
| FP03_Qföre at rest | 870 (its rest sat off-centre, mostly black) | 105 |
| FP03_Wföre at rest | 157 | 85 |
| FP03_Wföre, occlusion and after release | 333 and 283 | 474 and 380 |
| FP07_Qföre at rest | 12 | 5 |

The running sum of these steps drifts by tens of pixels even on FP01_Qföre, so it is not a
measure of anything and is not reported.

**Mean images** (band-passed, scratch script), where alignment shows directly:

- The raw resting means of FP01_W and FP03_Wefter are a smear with no capillaries. The new
  stabilized means show sharp loops, at rest and, for FP01_W, through the occlusion.
- FP12_Wföre at rest, FP07_Qföre at rest and FP03_Wföre in the occlusion are equally sharp old
  and new.

### What it means

- **FP01_W and FP03_Wefter can now be measured.** FP01's active visit enters aim 1 (both före
  recordings), and FP03_Wefter aim 2.
- **FP03_Qföre's occlusion and release are lost,** not misplaced. A separate stabilization of
  the post-cuff view, in its own frame, would be possible but is not needed by the aims.
- **Re-stabilizing the other 29 videos** would improve the rest where the old references lay
  elsewhere (FP12_Wföre most).
  - It would move their picture by the change of centring.
  - Lines placed on the old videos would then no longer fit: `analysis/aim1_feasibility/
    lines.json`, the slow-range validation's occlusion lines, and any data sets.
  - So that is for the user to decide.

### Changes

- **`capillary/stabilize.py`:**
  - new `rest_window`, `path_stretches`, `path_positions`, `choose_reference` and `bridge`;
  - `stabilize_video` reads four times;
  - new constants `STEP_MIN_MATCH`, `MIN_MATCH`, `MAX_DISAGREEMENT_PX`, `REFERENCE_RADIUS_PX`,
    `BRIGHTNESS_FACTOR`;
  - the summary counts frames placed from neighbours and lost (NaN-safe);
  - the command line prints them;
  - the provenance and docstring describe the new steps.
- **`tests/test_stabilize.py`** (6 new, 287 tests in all):
  - a 100-px drift where the coarse search reaches 40 px, with the sharpest frame at the far
    end;
  - dark frames at the end, which are lost and written black;
  - a jump to a view that does not overlap, which is lost;
  - the bridging arithmetic, the path's stretches and positions, and the choice of the
    references' centre.

  The shift file's column test was updated.
- **`CLAUDE.md`:** the stabilizer notes; "Large movements" under Known issues.

### Verification

- `python -m pytest`: 287 passed. The stabilizer's old tests are unchanged apart from the
  columns: the shifts still undo synthetic moves within 0.15 px, memory does not grow with
  length, and no frame is silently wrong.
- flake8: clean on the changed files at the CI's settings.
- The seven recordings above, three ways: the stabilizer's own numbers, the movement left in
  the output, and the mean images, looked at.
- **Scratch scripts** (session scratchpad, not in the repository):
  - the frame-to-frame registration of raw recordings and its plot;
  - the batch stabilization;
  - the evaluation;
  - the mean images.

---

## 2026-10-14 — The pattern shift below 1 px/frame: a slow range, validated, and not the default

**Branch:** `feature/pattern-shift-slow-flow`, from `main` at `d292ef7` (PR #17 merged).

**Commits:**

- `9e3a4be` — the slow range with its tests, validation and this entry
- a follow-up noting the commit here

The user asked to continue. I proposed three tasks:

- slow flow with the pattern shift;
- the stabilizer for large movements;
- the line-placement comparison on the pooled resting velocity.

The user chose the first.

### The question

The aim-1 check (2026-10-12) found much resting flow slower than the pattern shift's slowest
speed, 1 px/frame (0.04 mm/s at 30 fps and 1.33 µm/px).

- 18 limbs scored 8 or more at that edge, which is never reported.
- The exploratory "combined" rule measured slower limbs from the centre-line method's 3-s blocks
  instead.

The aim: measure slower flow with the pattern shift itself, with the same signal-to-noise ratio
and jackknife interval, first on synthetic recordings, then on the aim-1 lines.

Below 1 px/frame the pattern moves less than 2 px over frame distances 1–8. That is too little to
compare: close to zero shift the backward correlation subtracted holds part of the peak's own tail
(`MIN_SHIFT_PX`). So slower flow has to be compared over more frames.

### Designs tried, in order

Synthetic recordings throughout (`analysis/pattern_shift_slow_flow/validate_synthetic.py`):

- the simulated loop's arterial limb, a 120-px line, 60-s clips (the official rest is 52–77 s);
- 11 speeds from 0.1 to 3 px/frame, 4 clips each, and 30 clips without flow;
- the disturbances as measured, strong, and faint (a third of the contrast);
- 222 clips.

The final numbers of every design kept in the script are in its table below. The steps between
come from versions of the code that no longer exist; their numbers are from this session's runs.

1. **The search simply continued below 1 px/frame** (frame distances 1–8, `floor only`).
   - It read 39–53% high at 0.3 px/frame: at shifts of a few pixels the tail of the peak
     dominates.
   - 10 of 90 clips without flow were resolved.
2. **Every frame distance over which the pattern moves 2–8 px** (`all lags`): up to 80 frames
   at 0.1 px/frame, each read at frame distance × speed as the method does from 1 px/frame up.
   - It read 2–11% low at 0.3–0.7 px/frame. The score (sum ÷ √n) grows with the number of frame
     distances, and that number grows as 1/speed, so the score leans towards slower speeds.
   - Choosing the speed by the frame distances' mean contrast instead (`all lags, mean`)
     removed most of that (median error 3.8%).
   - Neither fixed the false positives: 15 and 11 of the 90 clips without flow were resolved,
     with scores up to 12.5 (the method from 1 px/frame: 6.2). Below 1 px/frame, neighbouring
     frame distances are read at nearly the same shift and share their noise, so √n overstates
     the signal-to-noise ratio.
3. **A stretched time axis.** A speed v is scored exactly as 1 px/frame is, on a time axis
   stretched by 1/v (`_stretched_scores`).
   - Term j = 1..8 compares rows j / v frames apart (between the two nearest frame distances,
     linearly), where the pattern has moved j px.
   - Every slow speed is then scored from the same number of terms at the same shifts as
     1 px/frame, and the false positives went: no clip without flow resolved, highest score 7.2.
   - But the estimates snapped to speeds where several stretched frame distances are whole
     frames (0.500 and 0.750 px/frame exactly).
   - And they leaned towards faster speeds, because the longer frame distances correlate less
     (fewer row pairs in a 3-s block): +20% at 0.1 px/frame in a first test.
4. **Two steps.** The stretched score finds the flow and is its signal-to-noise ratio. The speed
   is then refined with the frame distances held fixed (`_slow_lags`: the whole frames nearest to
   j / v), each read at frame distance × speed, so nothing changes with the speed but the shift
   read.
   - A first version reported the refining score as the signal-to-noise ratio. Searching again
     with other frame distances fits the noise a second time: clips without flow reached 9.0. So
     the score stays the one that found the flow.
   - At 0.1 px/frame the estimates were still 7–12% high (median per condition), the frame
     distances (10–80) approaching the 90-frame block. Taking the rows compared beyond 8 frames
     about their own mean (`CENTRED`) removed it. Taking every frame distance's rows about their
     own mean had made no difference at 0.15–2 px/frame. Centring only beyond 8 frames leaves
     the method from 1 px/frame up bit-identical.
5. **On the recordings** (below), 12 limbs at rest and 10 in the occlusion stopped at exactly
   1.000 px/frame, where the slow range meets the faster one. The stretched score falls with
   longer frame distances, since real blood rearranges, while the faster range's fixed frame
   distances do not. So:
   - a speed found at that point is refined too;
   - the choice of frame distances is repeated from each refined speed until it stays the same
     (at most 5 rounds);
   - the refinement searches 0.1–1.5 px/frame on an even grid of 0.002 px/frame. Where the grid
     spacing changes, the parabolic interpolation is skipped, and one estimate had stopped
     there.

**Synthetic results** of the design kept (`stretched`):

| Variant | Resolved below 1 px/frame (of 84) | Median error | Worst error | Truth in 95% interval | Clips without flow resolved (of 90) | Highest score without flow |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| before (from 1 px/frame) | 0 | – | – | – | 0 | 6.2 |
| floor only | 80 | 46% | 331% | 16% | 10 | 12.2 |
| all lags | 84 | 5.9% | 19.5% | 57% | 15 | 12.5 |
| all lags, mean | 84 | 3.8% | 25.3% | 67% | 11 | 12.4 |
| stretched, uncentred | 84 | 1.2% | 16.2% | 67% | 0 | 7.2 |
| **stretched** | 76 | 1.0% | 6.6% | 72% | 0 | 7.2 |
| stretched, 6-s blocks | 76 | 1.0% | 5.1% | 80% | 0 | 7.5 |

- From 0.15 to 1 px/frame `stretched` resolved all 72 clips, within 4.6% of the truth (median
  1.0%). At 0.1 px/frame, the floor, it resolved 4 of 12; the others stopped at the edge.
- From 1 px/frame up all variants but `all lags` give the method's old results (median error
  0.56%, worst 3.2%).
- The interval holds the truth less often than 95% (72–75%). It covers the statistical scatter
  only, and from 1 px/frame up the figure is 65%.
- Blocks of 6 s were a little better below 1 px/frame. They would change the method from
  1 px/frame up and halve the blocks the jackknife leaves out, so blocks stay at 3 s.

### The recordings (`validate_real.py`)

- **At rest:** the 124 lines of the aim-1 check (109 limbs, 15 through tissue), from the
  diagrams its `measure.py` saved over the official rest.
- **In the occlusion:** the same lines, traced again from its `lines.json`, sampled from 15 s
  after the cuff went up until 2 s before its release, when the blood should stand still.
  - This covers 13 recordings: FP07_Qföre and FP09_Wföre have no release time.
- Each window is measured whole and in halves.

| | Before | Slow range (`stretched`) |
| --- | ---: | ---: |
| Limbs resolved at rest (of 109) | 24 | 42 (17 below 1 px/frame) |
| … with the interval clear of zero | 22 | 38 |
| Tissue lines resolved at rest (of 15) | 0 (highest 4.4) | 0 (highest 4.4) |
| Loops with both limbs resolved: opposite / same way | 7 / 1 | 14 / 4 |
| Participants with a limb at both visits (of 7) | 2 | 3 (FP06, FP07, FP13) |
| … with a limb towards the apex at both | 1 | 2 |
| Limbs whose aim-1 centre-line blocks qualified, resolved (of 21) | 8 | 16, all in the blocks' direction, median ratio 0.96 (IQR 0.72–1.06) |
| Limbs resolved in the occlusion (of 97) | 2 | 24 (21 below 1 px/frame) |
| Tissue lines resolved in the occlusion (of 13) | 0 | 0 (highest 5.6) |

The combined rule of the aim-1 check gave a limb at both visits in 4 participants, an arterial
one in 1.

**The 18 limbs newly resolved at rest:**

- **12 look like flow.** Their loop's other limb runs the opposite way, or the centre-line
  blocks agree on the direction, and their space-time pictures show streaks that way: FP06_Qföre
  D, E and K left; FP09_Wföre B; FP12_Qföre E left; FP13_Qföre D left and F left; FP13_Wföre D.
- **4 are drift:** FP03_Wföre's loops E and F, all four limbs towards the base at
  0.5–0.8 px/frame, with signal-to-noise ratios of 23–63. The aim-1 check had already called
  them drift. The method before saw them only at its edge.
- **2 are doubtful:** FP06_Qföre's loop I, both limbs towards the base.

**The occlusion:**

- Of the loops with both limbs resolved, 6 run opposite ways and 2 the same way (FP03_Wföre E
  and F).
- The space-time pictures (a scratch script) show three things:
  - **The picture moving.** In FP13_Qföre's loop E the streaks stand still but bow sideways and
    back in both limbs together (7–11 s). The pattern-shift estimates of the two limbs still came
    out opposite (−0.17 and +0.10 px/frame), so the loop rule does not catch it. FP01_Qföre's
    tall loop shows still streaks that meander.
  - **The stabilized frame's uncovered edge** crossing the line in FP13_Qföre G left (the first
    6 s). `SpaceTimeSampler.inside` checks the frame's bounds, not where the moved frame left
    no picture.
  - **Real movement:** FP05_Qföre's loop B shows streaks moving towards the apex at
    0.4–0.8 px/frame under the cuff.
- So the occlusion is not a clean null below 1 px/frame, and not all of what moves there is
  blood.

**Where each frame distance's contrast peaks** (a scratch script) tells whether the pattern
moves steadily:

- A steady movement peaks further away the more frames apart the rows are: synthetic
  0.3 px/frame at 0.25–0.31 px/frame over frame distances 12–64; FP12_Qföre E left at
  0.31–0.38 over 12–64; FP13_Wföre D at 0.7–1.1 over 3–32 (all but one frame distance).
- At short frame distances every slow pattern peaks at about 3 px, since it has moved less
  than the peak is wide. Only the longer frame distances show the speed.
- In FP06_Qföre's loop E, FP09_Wföre B left and the occlusion cases the peak stays at a fixed
  2–4 px over frame distances 3–24.
  - That is what movement below a pixel (the correlation's own slope), small jumps, or
    stop-and-go flow advancing a few pixels per heartbeat would give.
  - The speed reported there depends on how long the pattern stays recognisable, not only on
    how fast it moves.

### Movement of the picture (`validate_wobble.py`)

Synthetic clips with the cells standing still or flowing at 0.3 px/frame, while the whole picture
moves along the limb (10 clips each):

| Movement of the picture | Still cells: resolved before / slow range | Highest score, slow range | Flow at 0.3 px/frame: median estimate, slow range |
| --- | ---: | ---: | ---: |
| none | 0 / 0 | 5.0 | 0.30 |
| sine, 2 px | 0 / 0 | 6.3 | 0.25 |
| sine, 10 px | 0 / 2 | 12.4 | 0.83 |
| sawtooth, 2 px (out 2.5 s, back 0.5 s) | 0 / 0 | 5.7 | 0.32 |
| sawtooth, 10 px | 0 / 3 | 8.8 | 0.43 |
| sawtooth, 20 px | 0 / 4 | 13.2 | 0.58 |
| bows of 15 px, out faster than back, every 15 s | 0 / 4 | 10.7 | 0.29 |
| steady drift, 0.05 px/frame | 0 / 0 | 3.3 | 0.36 |
| steady drift, 0.3 px/frame | 0 / 10 | 17.7 | 0.60 |

- A single line cannot tell slow flow from the picture moving along it.
- Movements of a few pixels are harmless.
- Uneven movements of 10–20 px over a few seconds read as slow flow in 2–4 of 10 clips, and
  bias real slow flow.
- A steady drift is flow, as far as one line can tell.
- The method before resolved none of these. Its scores reached up to 9.5 at its edge, which it
  never reports. It was protected by its range, not by its design.

### What was decided

- **The slow range is in the package but not the default.** `MIN_SPEED` stays 1 px/frame, so
  the app, its data sets and the batch command measure exactly as before. Compared on 45
  diagrams (synthetic and from the aim-1 check), the largest difference from the code at
  `d292ef7` is 2 × 10⁻¹³.
- It is asked for with `pattern_shift(..., min_speed=SLOW_MIN_SPEED)` (also in `summarize` and
  `shift_time_course`) or `python -m capillary.cli ... --slow-flow`.
- The app does not offer it. Its results need a check that the picture held still near the
  line, for example the loop's other limb running the opposite way, and that check does not yet
  exist.

### Changes

- **`capillary/pattern_shift.py`**
  - Below 1 px/frame: `_stretched_scores` finds the flow; `_slow_lags` and `_fixed_lag_scores`
    refine the speed (`REFINE_TOP`, `REFINE_ROUNDS`); `_contrasts` normalizes each frame
    distance.
  - `_block_sums` takes the rows compared beyond `centre_beyond` frames about their own mean. It
    now sums the cross-spectra over the rows before one inverse transform per frame distance, and
    takes the energies from cumulative sums: the same numbers, faster.
  - The speed grid is 0.002 px/frame apart below 1 px/frame (`_speed_grid`). `_best` refines
    between any evenly spaced neighbours.
  - New constants `SLOW_MIN_SPEED`, `CENTRED`, `REFINE_TOP`, `REFINE_ROUNDS`,
    `SLOW_SPEED_STEP`. `min_speed` and `centred` are arguments of `pattern_shift`, and
    `min_speed` of `summarize` and `shift_time_course`.
  - The docstring has a section on the slow range.
- **`capillary/cli.py`:** `--slow-flow`.
- **`gui/tasks.py`:** a data set's provenance also records `centred_beyond_max_lag` and
  `slow_refine_top_px_per_frame`. With the default these change nothing in the measurement.
- **Tests (16 new, 281 in all):**
  - the centred correlation sums against a direct computation;
  - slow flow at 0.15, 0.3 and 0.6 px/frame within 4%, with the interval around the estimate;
  - slow flow the other way;
  - no snapping at 0.48, 0.52, 0.73 or 0.98 px/frame;
  - no flow in four clips;
  - flow below the slow range not reported;
  - faster flow unchanged by the slow range;
  - the batch command's `--slow-flow` leaving faster flow as it was.
- **`analysis/pattern_shift_slow_flow/`:** the three validation scripts, their results and a
  README.
- **`README.md`, `CLAUDE.md`:** the slow range; the movement of the picture under Known issues.

### Verification

- `python -m pytest`: 281 passed.
- The default against the code at `d292ef7`: identical to 2 × 10⁻¹³ on 45 diagrams.
- flake8: the CI's error selection is clean on the whole repository, and the full set on the
  changed files, except one warning in `tests/test_datasets.py` that was there before.
- The three validations were rerun on the final code. The tables above are from those runs.
- Looked at: space-time pictures of 21 limbs, at rest and in the occlusion. The per-frame-distance
  peaks of 14 lines and three synthetic clips were also checked.
- **Scratch scripts** (in the session's scratchpad, not in the repository):
  - the comparison with the old code;
  - the space-time pictures;
  - the per-frame-distance peaks.

### Open

- **A check that the picture held still near a line** would make the slow range usable. For
  example: the tissue beside the vessel measured the same way, or a local registration of the
  stabilized video around the line. Then decide whether the slow range becomes the default and
  whether it replaces the combined rule.
- **The stabilized frame's uncovered edge** can cross a line (FP13_Qföre in the occlusion). The
  line check should use the area every frame covers, from the shift file.
- **For the supervisors:**
  - much resting flow in these videos is slow, and often not a steady movement;
  - under the cuff some loops still move (FP05_Qföre B);
  - with the slow range a limb is measured at both visits in 3 of the 7 participants, an
    arterial one in 2.

---

## 2026-10-12 — Aim 1 feasibility: resting flow on the arterial limb in 15 before-exposure recordings

**Branch:** `analysis/aim1-feasibility`, from `main` at `17a2770` (after PR #16, the arterial limb on
the Centre line page, was merged).

**Commits:**

- `a0a95da` — this entry, with `analysis/aim1_feasibility/` and notes in `CLAUDE.md`
- a follow-up after the user renamed the video folder back (below): the notes and
  `.gitignore` corrected, the analysis reading `StabilizedVideos/` only

The user asked to continue where the last session left off.

- The user merged PR #16 (step 2 of the arterial-limb plan) on GitHub at the start of the session.
  `main` was fast-forwarded to `17a2770` and `feature/arterial-limb` deleted.
- 23 more recordings had arrived in `RecordedVideos/`. The user chose to stabilize them. As the next
  task the user chose aim 1's feasibility: for the participants now on the desktop, can an arterial
  limb's resting flow be measured in the före recordings of both visits?

### The recordings on the desktop

- **35 raw recordings** are in `RecordedVideos/`. The 23 new ones (FP05–FP13) came from
  `OneDrive_2_2026-10-11.zip` and `OneDrive_3_2026-10-11.zip`.
- **Each new one was checked** (scratch script, read only):
  - the name is in NFC and in the official times;
  - rawvideo, 640 × 480, 30 fps;
  - every frame reads and none is black;
  - every official occlusion and release falls inside the video at 30 fps.
- **`FP09_Wefter_23-Oct-2019_10-04-53` is not in the official times.** DynCap has no times for
  any FP09 W after-exposure recording, which is why FP09 is used for aim 1 only.
  - The file holds 2052 frames (68 s), probably an aborted attempt.
  - It was not stabilized.
- **FP09_Qefter** is in the official times but used by no aim, so it was not stabilized either.
- **Clean-up.** The 23 `:Zone.Identifier` files Windows had added were deleted. All were 143 bytes
  and pointed at the two OneDrive zips.
- **Coverage** (`python -m capillary.inventory --have RecordedVideos`):
  - 30 of the 90 recordings the aims use are here, all ESMOKE.
  - 8 ESMOKE participants have both före recordings: FP01, FP03, FP05, FP06, FP07, FP09, FP12
    and FP13.
  - No ISMOKE recording has arrived yet.

### Stabilized

The 21 new recordings the aims use were stabilized with the command line at commit `17a2770`:
`python -m capillary.stabilize RecordedVideos/<name>.avi --out StabilizedVideos/<name>.avi`. They
ran 11 at a time on 16 cores and took 9 minutes (213–349 s each).

| Recording | Used for | Moved (px) | Match at rest | In occlusion | After release | Notes |
| --- | --- | --- | ---: | ---: | ---: | --- |
| FP05_Qföre_försök4 | aims 1, 2 | 107.5 × 33.6 | 0.75 | 0.81 | 0.71 | |
| FP05_Wföre | aims 1, 2 | 87.7 × 192.2 | 0.71 | 0.62 | 0.81 | a 44-px jump after the rest |
| FP05_Wefter_försök2 | aim 2 | 204.7 × 128.9 | 0.67 | 0.59 | 0.62 | |
| FP06_Qföre_försök2 | aims 1, 2 | 35.5 × 12.6 | 0.66 | 0.75 | 0.84 | |
| FP06_Qefter_försök2 | aim 2 | 106.3 × 71.0 | 0.73 | 0.91 | 0.81 | |
| FP06_Wföre | aims 1, 2 | 92.8 × 138.5 | 0.82 | 0.72 | 0.63 | |
| FP06_Wefter | aim 2 | 70.4 × 88.8 | 0.73 | 0.44 | – | no release time |
| FP07_Qföre | aims 1, 2 | 292.0 × 320.9 | 0.76 | 0.75 | – | no release time; jumps of up to 294 px from 134 s on, 9 frames at the search limit |
| FP07_Qefter | aim 2 | 58.9 × 19.2 | 0.83 | 0.65 | – | no release time |
| FP07_Wföre | aims 1, 2 | 68.2 × 15.0 | 0.93 | 0.62 | 0.88 | |
| FP07_Wefter | aim 2 | 46.7 × 25.2 | 0.91 | 0.88 | 0.88 | references disagree by more than 1 px on 3 rest frames |
| FP09_Qföre | aim 1 | 43.1 × 29.4 | 0.48 | 0.85 | 0.48 | |
| FP09_Wföre | aim 1 | 7.0 × 12.0 | 0.83 | 0.75 | – | no release time |
| FP12_Qföre | aims 1, 2 | 10.4 × 19.8 | 0.42 | 0.90 | 0.55 | references disagree by more than 1 px on 78 rest frames (at most 3.0 px) |
| FP12_Qefter | aim 2 | 29.4 × 26.2 | 0.44 | 0.79 | 0.61 | |
| FP12_Wföre | aims 1, 2 | 12.4 × 45.0 | 0.42 | 0.80 | 0.39 | references disagree by more than 1 px on 147 rest frames (at most 6.7 px) |
| FP12_Wefter | aim 2 | 24.7 × 33.5 | 0.50 | 0.85 | 0.49 | |
| FP13_Qföre | aims 1, 2 | 145.3 × 79.0 | 0.94 | 0.90 | 0.87 | |
| FP13_Qefter | aim 2 | 28.0 × 9.7 | 0.94 | 0.91 | 0.96 | |
| FP13_Wföre_försök2 | aims 1, 2 | 27.4 × 117.8 | 0.91 | 0.90 | 0.90 | |
| FP13_Wefter | aim 2 | 33.4 × 107.4 | 0.87 | 0.87 | 0.83 | |

Match is the median normalized cross-correlation with the references, per phase as on 2026-10-11.
Without a release time, "in occlusion" runs to the end of the video.

- **At rest no frame is at the search limit.** FP07_Qföre's one large step at rest (21 px, at
  30 s) was followed: its match stays at 0.71 or more and its references agree within 0.3 px.
- **FP12's two före recordings are the weakest at rest:** match 0.42, and the two references
  disagree by more than 1 px on 78 and 147 frames. Their resting images are still sharp enough to
  place lines on, but the alignment at rest is less certain than in the others.
- **FP09_Qföre** matches only 0.48 at rest; its references agree.

### The folder renamed, and renamed back

At 18:22, after the stabilization, `StabilizedVideos/` was renamed to `ESMOKE_Videos/`. It held
the 31 stabilized videos (the 10 of 2026-10-11 and the 21 above), each with its shift file and
provenance.

- **The app could not see them.** `gui.settings.DataFolder.stabilized` is `StabilizedVideos/`,
  and `ensure()` creates it, empty, at the next start. The app would have listed the 31
  recordings as raw only and offered to stabilize them again.
- **Sorting by study is not needed:** ISMOKE names start with `ISMOKE_`, and the inventory sorts
  the recordings by name. Changing the app to read one folder per study would only buy tidier
  folders.
- **So the user renamed it back** the same evening. `StabilizedVideos/` again holds the 31 videos
  with their shift files. CLAUDE.md's data layout notes the episode.
- In between, the analysis below read the videos from either name, and `a0a95da` added
  `ESMOKE_Videos/` and `ISMOKE_Videos/` to `.gitignore`. The follow-up commit takes both out
  again.

### The feasibility check (`analysis/aim1_feasibility/`)

**The question.** Aim 1 compares resting CBV between the two före recordings of each participant,
and the PI wants it from the arterial limb only. Seven of the eight participants have both före
recordings measurable; FP01_W cannot be stabilized. How many of the seven give an arterial limb
with measurable resting flow at both visits?

**Lines** (the folder's README has the details):

- **What:** 109 limbs of 59 loops in the 15 recordings (2–16 limbs per recording, median 6), and
  one line through tissue in each as a control.
- **Who and from what:** placed by Claude Code by eye, not by the study's observer.
  - They were placed on the resting image: the mean of the official rest (52–77 s per
    recording), band-passed with σ 1 and 8 px.
  - No velocity had been seen at that point.
  - FP01_Qföre and FP03_Qföre reuse the lines of 2026-10-08.
- **Which loops:** those whose two limbs could be told apart and followed down from the apex.
  Loops whose limbs cross at once, rings, single bands and loops washed out at the frame's edge
  were left out.
- **Direction:** each limb runs from its base to the apex. In every recording the apexes point
  up, as each loop's U-turn shows.
- **Tracing:** each line follows the vessel's ridge from point to point (the cheapest path
  through the image), and the two limbs of a loop are kept 5 px apart except near the apex.
- **Checks before measuring:** gridded close-ups of every loop, in three rounds. Lines were
  ended above where the limbs cross or merge, a point was added on a thin limb beside a wide
  one, and four loops were dropped.
- **Measurement:** over the official rest window. Per line, the pattern shift pooled over the
  rest and its halves, as a centre-line data set keeps it, plus the centre-line method's 3-s
  blocks. About 7 minutes for the 124 lines.

**When a limb counts as measured**, at three levels (`summarize.py`):

1. **Resolved:** the pooled pattern shift reaches a signal-to-noise ratio of 8, the app's rule.
2. **Robust:** resolved, and also at least 1.5 px/frame (0.06 mm/s), with a 95% interval clear
   of zero. This rule was set before any result was seen:
   - near the slowest speed reported (1 px/frame), slow drift pulls the band-passed estimate
     (2026-10-11);
   - the limb check rests on the direction, which an interval across zero leaves open.
3. **Combined (exploratory):** robust, or else the centre-line blocks, when at least 25% of
   them are resolved and at least 90% of those run the same way. Without flow the benchmark
   resolves 7–11% of blocks under strong jitter. This level was added after the first results,
   for the reason below.

**Results** (art/ven: arterial and venous limbs measured; loops: those with both limbs measured at
the combined level, and in brackets how many of them run opposite ways):

| Participant | Visit | Recording | Limbs (loops) | Resolved: art/ven | Robust: art/ven | Combined: art/ven | Loops (opposite) | Arterial, combined (mm/s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FP01 | W | FP01_W | not measured (stabilizer fails) | | | | | |
| FP01 | Q | FP01_Qföre | 4 (3) | 1/2 | 1/1 | 1/1 | 1 (1) | 0.106 |
| FP03 | Q | FP03_Qföre | 6 (5) | 0/0 | 0/0 | 0/0 | 0 | |
| FP03 | W | FP03_Wföre | 10 (5) | 1/2 | 1/1 | 1/1 | 1 (1) | 0.080 |
| FP05 | W | FP05_Wföre | 8 (4) | 0/0 | 0/0 | 0/0 | 0 | |
| FP05 | Q | FP05_Qföre_försök4 | 4 (2) | 1/1 | 1/1 | 1/1 | 1 (1) | 0.139 |
| FP06 | W | FP06_Wföre | 7 (4) | 1/1 | 0/1 | 0/1 | 0 | |
| FP06 | Q | FP06_Qföre_försök2 | 16 (8) | 1/4 | 1/1 | 2/3 | 2 (2) | 0.068, 0.040 |
| FP07 | Q | FP07_Qföre | 6 (3) | 0/1 | 0/1 | 0/1 | 0 | |
| FP07 | W | FP07_Wföre | 12 (6) | 1/1 | 1/1 | 1/1 | 1 (1) | 0.140 |
| FP09 | W | FP09_Wföre | 6 (3) | 0/0 | 0/0 | 2/2 | 2 (2) | 0.009, 0.014 |
| FP09 | Q | FP09_Qföre | 2 (1) | 0/0 | 0/0 | 0/0 | 0 | |
| FP12 | Q | FP12_Qföre | 2 (2) | 0/0 | 0/0 | 0/1 | 0 | |
| FP12 | W | FP12_Wföre | 4 (2) | 0/0 | 0/0 | 0/1 | 0 | |
| FP13 | W | FP13_Wföre_försök2 | 12 (6) | 0/0 | 0/0 | 1/2 | 1 (1) | 0.038 |
| FP13 | Q | FP13_Qföre | 10 (5) | 3/3 | 2/2 | 3/3 | 3 (3) | 0.066, 0.087, 0.080 |

| Level | Limbs measured (of 109) | Arterial | Recordings with a limb (of 15) | Loops with both limbs (opposite) | Arterial limb at both visits (of 7) | Any limb at both visits (of 7) |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| Resolved | 24 | 9 | 8 | 8 (7) | 1 (FP06) | 2 |
| Robust | 16 | 7 | 8 | 6 (6) | 0 | 2 |
| Combined | 30 | 12 | 12 | 12 (12) | 1 (FP13) | 4 (FP06, FP07, FP12, FP13) |

- **No tissue line shows flow.** None of the 15 was resolved by the pattern shift (highest score
  4.4), and the centre-line method resolved none of their blocks.
- **Much resting flow is slower than the pattern shift's range.**
  - 18 limbs in 6 recordings scored 8 or more at its slowest speed (1 px/frame, 0.04 mm/s), which
    the method never reports.
  - Where the two limbs of such a loop moved opposite ways, the centre-line blocks resolved 25–80%
    of the rest, all one way: FP06_Qföre's loop D, FP09_Wföre's loop B, FP13_Wföre's loop D.
  - Where they moved the same way, the blocks resolved 0–5%: FP03_Wföre's loops E and F, all four
    limbs towards the base. That is drift of the image, not flow.
  - The combined level takes 14 limbs from the centre-line blocks, at 0.005–0.087 mm/s, in 6
    recordings. 8 of them were at the pattern shift's edge.
  - All 12 loops with both limbs measured at this level run opposite ways.
- **The space-time pictures** (10 s of 24 lines, scratch script) agree:
  - mirrored slanted streaks in FP13_Qföre's loop A, FP06_Qföre's loop D, and FP13_Wföre's loop A.
    The pattern shift missed the last on its 50-px lines (scores 7.2 and 4.7); the centre-line
    method resolved about 60% of its blocks.
  - Noise on FP03_Qföre's limbs and on FP03_Wföre's B left. The pattern shift resolved that limb
    at 10.2, but its interval spans zero, so it is not robust.
  - Faint texture moving the same way on both limbs of FP03_Wföre's loop E.
  - FP09_Wföre's limbs (0.005–0.02 mm/s) show slowly moving large features, close to standstill.
- **The one loop that broke the rule at the resolved level,** FP06_Qföre's loop H, has both limbs
  venous at 1.1–1.2 px/frame, near the slow edge.
  - Its right limb shows clear streaks towards the base: real venous flow.
  - The left limb's line lies off the ridge (0.25 of the ridge's brightness, against 0.5–0.8 on
    most lines). Its weak score (8.7) is probably the right limb's flow, picked up near the apex.
  - The robust rule drops both, as slower than 1.5 px/frame.
- **The velocities are low:** arterial limbs a median 0.074 mm/s (0.009–0.140), venous 0.067
  (0.005–0.101).
  - That is far below the 0.5–1 mm/s the project expected from the literature.
  - The limbs that can be measured are those whose plasma gaps show, probably the slower ones.
  - The frame rate and the pixel size are still unverified.
- **Measured limbs are longer:** a median of 98 px, against 70 px for the others.
- **Where nothing was measured:** FP03_Qföre, FP05_Wföre and FP09_Qföre give no limb at any
  level. Their space-time pictures are noise.

### What it means for aim 1

To discuss with the supervisors:

- **Resting CBV from the arterial limb only is feasible in at most 1 of these 7 participants.**
  Whether a visit gives an arterial limb depends on which few loops happen to show plasma gaps,
  and each recording gives 0–3 such loops.
- **Any limb, arterial or venous,** gives both visits in 2 participants with the pattern shift
  alone, and in 4 with the centre-line method added for slower flow.
- **The combined rule is exploratory.** If it is to be used, it should be fixed before the real
  analysis and checked on recordings it was not made on: the rest of ESMOKE, and ISMOKE.
- **The lines here are a lower bound on what can be found.**
  - They were placed on clearly visible loops only (2–16 limbs per recording).
  - An observer working in the app, with the video, may find more.
  - The study's observer should place the lines for the real analysis, blind to the visit.

### Verification

- `python -m pytest`: 265 passed; nothing in the package changed.
- **After the folder was renamed back,** all 15 recordings' videos and rest windows were found in
  `StabilizedVideos/` (scratch check). `summarize.py` gave the same numbers.
- flake8: the CI's error selection is clean on the whole repository, and the full set on
  `analysis/aim1_feasibility/`.
- **The measurement ran twice,** the second time with three more centre-line columns. All 30
  earlier columns of the 124 lines agreed exactly.
- **Controls:**
  - the tissue lines (none showed flow);
  - the direction rule in loops (12 of 12 at the combined level);
  - 24 space-time pictures looked at.
- **Scratch scripts** (in the session's scratchpad, not in the repository):
  - the read-only check of the raw recordings;
  - the parallel stabilization and its quality per phase;
  - the gridded close-ups for placing and checking lines;
  - the space-time pictures.

### Open

- **Decide with the supervisors:** arterial limb only, or any limb, for aim 1; and whether to
  combine the two methods, and by which rule.
- **Line placement by the study's observer** in the app, blind to the visit, then compared with
  these lines (`capillary/placement.py` should compare the pooled velocity at rest, not the
  blocks).
- **If the combined rule is kept,** the Centre line page should show it, since it now gives the
  pooled pattern shift as the headline.
- **More recordings:** 60 of the 90 the aims use are still to come, all of ISMOKE among them.
- **The stabilizer fix for large movements:** FP01's active visit (FP01_W) cannot be measured
  until then.
- **Still unverified:** the frame rate, the pixel size and the exposure time.

---

## 2026-10-11 — The arterial limb on the Centre line page: pattern shift, official phases, direction check

**Branch:** `feature/arterial-limb`, from `main` at `06700a0` (after PR #15, the band-pass of step 1,
was merged).

**Commits:**

- this entry, with the change and its tests

This is step 2 of the plan in the entry below: the user's PI wants resting CBV from the arterial limb
only. After step 1 the user said "Lets start". Step 2 puts the pattern shift on the Centre line page,
takes the rest from the official times, and checks whether a line lies on the arterial limb.

### How the arterial limb is recognized

- **Blood flows up the arterial limb to the apex and down the venous limb.** So the direction of
  flow along a limb tells which limb it is, once the apex end of the line is known.
- **The line runs from the limb's base to the apex.** That fixes the apex end independently of the
  flow. If the user marks the line as an arterial limb, the page labels its first point "base" and
  its last "apex", so a line drawn the wrong way shows at once. Flow along the line (positive) is
  then the arterial limb, and flow against it the venous limb.
- **The check uses the pattern shift pooled over the range.**
  - At rest single 3-s blocks rarely resolve.
  - A few resolved blocks give no reliable direction: with no flow but strong jitter, the benchmark
    resolves 7–11% of blocks.
  - Pooled scores without flow stayed at or below 5.4 (synthetic) and 3.6 (tissue lines). A
    resolved pooled estimate (8 or more) gives a reliable sign.
- **Outcomes:**
  - *arterial:* resolved and towards the apex;
  - *venous:* resolved and towards the base, so the venous limb, or a line drawn from the apex;
  - *unknown:* not resolved.

### The change

- **`capillary/inventory.py`: the official phases as frames.**
  - `recording_phases(name, fps, frame_count)` returns a `Phases`, with these windows:
    - the rest, from 2 s after the start to 2 s before the occlusion;
    - the occlusion, from 2 s after it to 2 s before the release;
    - after release, from 2 s after the release to 2 s before the end of the video.
  - The 2-s margins are `REST_MARGIN_S`, as in the inventory's rest and the earlier analyses.
  - Without a release time, only the rest is given.
  - If an official time lies after the end of the video, no window is given and a note says the
    times do not fit. This is the case of `FP01_Wefter_14-Oct-2019_10-07-49` (metadata/README).
  - Notes also flag a rest under 30 s and a missing release.
  - `Phases.phase_of(first, last, fps)` labels a range by the official times themselves (no
    margins): rest, occlusion, after release, several joined by " + ", or "occlusion or later"
    without a release time.
  - The times are read once per folder (`lru_cache`).
- **`capillary/pattern_shift.py`:**
  - `summarize(diagram, fps, mm_per_pixel)` returns what a data set keeps, all keys starting with
    `pattern_shift_`:
    - the pooled velocity (NaN unless resolved, as the blocks do, so nothing downstream averages
      unresolved values in) and the best speed (also when unresolved);
    - the signal-to-noise ratio, whether resolved, and the blocks pooled;
    - the 95% interval (NaN unless resolved);
    - each half of the range in time, pooled on its own, when a half holds at least
      `MIN_HALF_BLOCKS` (3) blocks.
  - Why the halves: the jackknife interval held the truth in only 63% of synthetic cases (step 1),
    and the halves were the stability check of the validation. They also measure within-recording
    repeatability, next to aim 1's between-day repeatability.
  - `limb_from_direction(velocity)` returns arterial, venous or unknown.
  - `ARTERIAL_LIMB = 'arterial limb'` is the role of such a line.
- **`gui/tasks.py`:**
  - `measure_line_dataset(..., role=None)` pools the pattern shift after the blocks
    (`summarize_line`).
  - The summary gains the `pattern_shift_...` keys, plus:
    - `line_role` ("arterial limb" or empty);
    - `limb_check` (arterial, venous or unknown, for an arterial limb);
    - `phase` (the range's official phase; empty without usable times).
  - The provenance gains `line.role` and the pattern-shift settings (`pattern_shift`).
  - `regenerate_line_report` recomputes all of it from the saved diagram and keeps the role. Older
    centre-line data sets get the pattern shift when their report is regenerated.
  - Two-box data sets get `phase` too (`range_phase`).
- **`Caper.generate_line_report`:**
  - the velocity plot draws the pooled velocity and its 95% interval across the range;
  - the title states the limb check;
  - the summary CSV in `Reports/` carries all the new columns.
- **Range section (`gui/measure_page.py`, both measure pages):**
  - "Official phases" with the occlusion and release times, and buttons Rest, Occlusion and After
    release that set the range. The buttons are disabled where a window is missing.
  - A note when the recording has no official times, or when they do not fit.
  - The range's detail names its phase ("rest", "rest + occlusion").
  - The timeline (`gui/transport.py`) marks the occlusion with an orange bar under the track. Its
    hover label adds the phase ("1:40.000 · frame 3000 · occlusion").
- **Centre line page (`gui/line_page.py`):**
  - **Option:** a checkbox "Arterial limb, from its base to the apex".
    - It stays on for further recordings.
    - It is kept with each recording's line, and restored with a data set's line.
    - The overlay labels base and apex; the hints ask for the base first.
  - **Pooled row:** a new row says the pooled method measures from 0.04 mm/s. Its tooltip gives
    the validated range.
  - **Result panel:**
    - the check, with an icon;
    - the pooled velocity as the headline (the blocks' median when the pooled one is not resolved);
    - the pattern shift's velocity, 95% interval, signal-to-noise ratio and halves;
    - the 3-s blocks as before;
    - notes when the range mixes phases, the halves run opposite ways, or few blocks were resolved.
    - When fewer than two blocks are resolved, the chart says the pooled velocity is above it.
  - **Preview:** when 4 s show no clear streaks, the message now says that Measure pools the whole
    range.
- **Results page:** a centre-line card shows:
  - the pooled velocity with its interval, signal-to-noise ratio and halves;
  - the blocks;
  - the limb check;
  - the phase, and the role in the description.
  - A data set without pattern shift says to regenerate its report.
- **`capillary/cli.py`** prints the halves after the pooled estimate.
- **Docs:** README (the page table, the pattern shift, a paragraph on the arterial limb), CLAUDE.md,
  the data set formats (`capillary/datasets.py` docstring).

### Verification

**Tests:** 265 pass (259 + 6 new):

- `test_the_official_phases_as_frames_of_a_video`: FP01_Qföre's windows (60–1988, 2109–3854,
  3975–5339 for 5400 frames), the phase labels, the macOS spelling.
- `test_phases_without_a_release_or_that_do_not_fit_the_video`: rest only; a 2-s rest
  (ISMOKE_FP04_Sefter); FP01_Wefter 10-07-49's times after the video's end; an unknown name.
- `test_a_data_set_keeps_the_pooled_speed_and_each_half`: flow slowing from 5 to 4 px/frame
  halfway; each half finds its own speed within 3%.
- `test_a_short_or_unresolved_range_keeps_no_velocity_it_cannot_support`.
- `test_the_direction_of_flow_tells_the_limbs_of_a_loop_apart`: on a simulated loop, a line from
  the base to the apex on the left limb reads arterial, on the right limb venous.
- `test_an_arterial_limb_is_checked_by_the_direction_of_its_flow` (through `measure_line_dataset`):
  - the role, check and phase in the provenance and the summary CSV;
  - the same line reversed reads venous;
  - regenerating keeps the check.
- Existing tests check that a line without a role saves `role: null` and no check, and that
  regenerating recomputes the pooled velocity.
- **Planted bugs:** with arterial and venous swapped, 2 tests fail; with the rest windows without
  margins, 2 tests fail.
- **flake8:** the CI's error selection is clean on the whole repository. The full set reports
  nothing on the lines this branch changed; older lines keep their earlier warnings.

**On the recordings** (scratch script, not in the repository; written to a scratch data folder).
All 35 feasibility lines were measured through `measure_line_dataset`:

- each snapped to the vessel as in step 1;
- each turned to run from its lower end (base) to its upper end (apex);
- each marked as an arterial limb;
- the range set to the official rest window.

Results:

- **The same 5 of 29 limbs resolved as in step 1.** Their pooled velocities agree with step 1's
  within 0.0004 mm/s (the sign turned with the line).
- **The check:** 2 arterial, 3 venous, 24 unknown. All 6 tissue lines were unknown.
- **Time:** about 3.5 s per line (median), reading a minute of video.

| Line | px | Pooled (mm/s) | 95% interval | Signal-to-noise | Halves | Check |
| --- | ---: | ---: | --- | ---: | --- | --- |
| FP01_Qföre, tall loop, right limb | 63 | +0.108 | 0.098–0.117 | 9.1 | – / +0.102 | arterial |
| FP01_Qföre, tall loop, left limb | 104 | −0.083 | −0.091 to −0.075 | 19.9 | −0.085 / −0.081 | venous |
| FP03_Qefter, loop P, right limb | 147 | +0.042 | 0.036–0.048 | 18.7 | +0.043 / +0.040 | arterial |
| FP03_Qefter, loop P, left limb | 122 | −0.058 | −0.083 to −0.032 | 15.8 | −0.067 / −0.051 | venous |
| FP03_Qefter, loop S | 120 | −0.051 | −0.059 to −0.044 | 10.8 | −0.055 / −0.054 | venous |

- **Both loops with clear flow show one limb up and the other down,** as a loop must.
- **The arterial limb is not always the faster one.**
  - In FP01_Qföre's tall loop it is (0.108 against 0.083 mm/s).
  - In loop P it is the slower (0.042 against 0.058). Its speed lies at 1.05 px/frame, near the
    slowest speed reported, where step 1 found that slow drift can pull the estimate.
- **Only 2 arterial resting velocities in 6 recordings.** At rest most limbs show no moving
  pattern (step 1).

**The window** (scripted under WSLg, no window taking focus, scratch data folder with links to the
videos):

- **FP01_Qföre:**
  - occlusion 1:08.300 and release 2:10.500 shown;
  - Rest set frames 60–1988, labelled "rest";
  - the arterial-limb hints and labels appeared.
- **The tall loop's right limb,** with the line as clicked (not snapped): 0.0986 mm/s
  (0.078–0.119, signal-to-noise 9.6), arterial.
  - The snapped line gave 0.108. The 8% difference comes from where the line lies across the
    limb.
- **The other limb:** venous, with the warning.
- **Results page:** the cards and the report plot (pooled line and interval band, title with the
  check) look right.
- **A recording without official times** (a renamed link): disabled buttons, with a note.
- **Two boxes page:** After release set frames 3975–5668.
- No Tk errors; the app shut down cleanly.
- Two fixes came from the screenshots:
  - The theme's minimum button width pushed "After release" out of the panel; the three buttons now
    share three equal columns with less padding.
  - The chart said "no value could be resolved" when only the blocks were unresolved.
- **The batch command** on the same arterial limb printed the same numbers.

### Open

- **Line placement** (Validation page, `capillary/placement.py`) compares the blocks' medians. At
  rest those are mostly unresolved, so it should compare the pooled velocity. The placement
  sensitivity seen above (8%) is what it should quantify.
- **A table across data sets** for the aims: recording, limb, pooled velocity and interval,
  halves, check, phase, observer.
- **Blinding:** the page shows velocities while the line is placed. For aim 1, decide with the
  supervisors whether the observer should be blind to the visit.
- **Step 3:** the arterial limb's speed from a line over the apex (a simulator with different
  speeds per limb).
- **The exposure time,** which the user is checking.
- **New recordings:** `RecordedVideos/` now holds 28 recordings, 16 more than when 10 were
  stabilized earlier today. They are not stabilized yet; the user will say when all have arrived.

## 2026-10-11 — Pattern shift on band-passed rows; no hidden fast flow at rest

**Branch:** `feature/pattern-shift-bandpass`, from `main` at `a6f9b4a`.

**Commits:**

- this entry, with the estimator change, its tests and `analysis/pattern_shift_bandpass/`

The user and their PI agreed on how resting CBV should be measured:

- on the arterial limb only, since the velocity changes towards the venous side;
- if that is not feasible, over a longer distance.

The user asked to work on measuring faster velocities. A look at what limits them came first. The
user then chose step 1 of three proposed steps, a more sensitive estimator. The user will check the
camera's exposure time, which decides how much fast flow is blurred.

### What limits faster velocities

- **Not the search.** Pattern shift (2026-10-08) searches up to half the line's length per frame:
  60 px/frame (2.4 mm/s) on a 120-px line.
- **Blur and line length.** The simulated loops had the shutter open for the whole frame interval
  (the simulator's default and its worst case).
  - A 120-px line on the arterial limb measured up to about 12 px/frame (0.48 mm/s).
  - A 300-px line round the loop measured 12–40 px/frame (0.48–1.6 mm/s) within about 1%
    (`validate_long_line.py`, below).
  - A longer line lets the pattern be followed over more frame distances (at 25 px/frame, six
    instead of one or two), with more positions overlapping.
- **The recordings hide no fast flow.**
  - All 35 lines of the feasibility check were scored at rest and after release, and so were
    lines round 7 whole loops (173–328 px).
  - Everything resolved was slow, 0.04–0.15 mm/s. Nothing faster appeared on any line, though
    the loop lines would reach 1.6 mm/s in simulation.
  - Most capillaries show no moving pattern at all, so at rest the limit is visibility rather
    than speed.
  - The capillaries that can be measured may be the slower ones, whose plasma gaps show. The
    thesis should state this selection.
- **Which limb is arterial.** In every loop with clear flow, blood goes up one limb towards the
  apex (arterial) and down the other. On FP01_Qföre's tall loop the arterial limb is the faster:
  −0.116 mm/s on a 64-px line, against +0.083 on the venous limb (differenced rows).
- **Space-time diagrams** (scratch plots):
  - FP01_Qföre's tall loop shows clear streaks.
  - FP03_Qföre's curly loop shows them only faintly. Coarse filters suggested 0.2–0.3 mm/s
    there; the loop line found nothing, so this is not confirmed.

### Why band-pass

Differencing a row along the line weights each spatial frequency k by (2 sin πk)², most at the
finest scale (2-px patterns). In the recordings that scale is mostly noise, and motion blur erases
it first.

A first comparison (scratch scripts, pattern shift's scores only) found the following:

- **On the recordings,** band-passed rows gave 2–3 times the signal-to-noise on limbs with flow
  (FP01_Qföre's left limb 11.4 → 21.2; FP03_Qefter's loop P 9.6 → 23.9). Lines through tissue
  stayed lower.
- **On the simulator,** the opposite: its cells are crisp 6-px blobs, sharper than the real
  pattern.

### The change (`capillary/pattern_shift.py`)

- **The filter.** `_prepared` band-passes each row along the line with a difference of Gaussians,
  σ 1 and 4 px (`BANDPASS_PX`, `scipy.ndimage.gaussian_filter1d`, reflected at the ends). The
  still structure and the same-moment change are removed first, as before.
  - It passes patterns of about 4–30 px, most strongly near 10 px (gain 0.78).
  - It passes almost nothing at 2 px or 200 px (0.007).
- **The old method stays available.** `bandpass_px=None` differences the rows as before
  (`_block_sums`, `pattern_shift`, `shift_time_course`), to reproduce earlier results.
- **Unchanged:** `MIN_SNR` (8), `MIN_SHIFT_PX` (2 px), `MIN_SPEED` (1 px/frame).
- **Docstrings:** how it works, the range, and the threshold's levels without flow.

### Choosing the band (`analysis/pattern_shift_bandpass/`)

Five bands were compared with the differenced rows: 1–4, 1–6 (the first candidate, from the
scratch comparison), 1–8, 1.5–6 and 2–8 px.

**Synthetic** (`validate_synthetic.py`). 234 clips of 30 s, with a 120-px line drawn on the
simulated arterial limb:

- 12 speeds from 0.5 to 30 px/frame;
- 3 conditions: as measured, strong, and faint (a third of the contrast);
- 3 seeds each;
- the shutter open the whole frame, and at 8–30 px/frame also half the frame;
- 30 clips without flow per condition.

Columns, for the 108 clips with flow and the shutter open the whole frame:

- **Resolved:** clips resolved, out of the 108.
- **Error of those:** median and worst error of the resolved clips.
- **At 1–1.5 px/frame:** median error at the two slowest speeds reported.
- **No flow:** the highest score inside the searched range, with the highest at its slow edge in
  brackets.

| Filter | Resolved | Error of those | At 1–1.5 px/frame | No flow |
| --- | ---: | --- | --- | --- |
| difference | 49 | 0.6% / 4.8% | −1.0 to 0.0% | 4.4 (4.4) |
| band 1–4 | 60 | 0.4% / 5.6% | 0.0 to +0.2% | 5.4 (7.3) |
| band 1–6 | 55 | 0.4% / 6.2% | +0.8 to +1.4% | 6.2 (9.7) |
| band 1–8 | 54 | 0.7% / 12.4% | +2.8 to +6.9% | 6.5 (8.2) |
| band 1.5–6 | 57 | 0.5% / 7.0% | +1.1 to +2.4% | 6.3 (10.5) |
| band 2–8 | 54 | 0.9% / 23.2% | +6.4 to +19.3% | 7.2 (7.6) |

The highest no-flow scores of the band-passes all lie at 1.0–1.5 px/frame, mostly in the strong
condition (three times the measured image jitter). Whole-image jitter moves the still background,
and a band-pass keeps more of it than differencing does. None reached 8 inside the searched range;
the edge itself is never reported.

**Real** (`validate_real.py`). The 35 feasibility lines (29 limbs, 6 through tissue) in 6
recordings, scored over five windows. Columns:

- **Tissue:** the highest score on the tissue lines, over 30 estimates.
- **Limbs resolved:** out of 29, at rest, in the rest's first and second halves, and after release.
  In occlusion, none for any filter.

| Filter | Tissue | Limbs resolved: rest, 1st half, 2nd half, after release |
| --- | ---: | --- |
| difference | 5.6 | 3, 0, 0, 1 |
| band 1–4 | 3.6 | 5, 4, 7, 1 |
| band 1–6 | 4.0 | 5, 5, 7, 4 |
| band 1–8 | 4.7 | 6, 5, 7, 5 |
| band 1.5–6 | 4.7 | 5, 5, 7, 5 |
| band 2–8 | 5.1 | 5, 5, 6, 5 |

**Band 1–4 was chosen, after the validation:**

- **It is the only band that keeps every limb resolved before,** namely FP01_Qföre's 64-px
  arterial limb: differenced 8.7, band 1–4 8.8, the wider bands 5.6–6.6. Arterial limbs are
  short, and they are what the PI asked for.
- **It did best on the synthetic recordings:** the most clips resolved, the smallest error at
  the slow end, and the lowest scores on tissue.
- **The wider bands' extra limbs after release are not faster flow.** All lie at 1.0–1.4
  px/frame (0.040–0.055 mm/s). That is the slow edge, where those bands read 3–19% high on
  synthetic recordings and where no-flow clips scored highest. Band 1–4 put the same limbs at the
  edge, which is not reported.
- **It was chosen on the same data it is validated on;** check it on new recordings.

### Results with the chosen band

**Synthetic, shutter open the whole frame.** Each cell gives the clips resolved (of 3) and the
median error. The two filters are each shown at the measured disturbances and at a third of the
contrast (faint).

| px/frame (mm/s) | Difference, as measured | Band 1–4, as measured | Difference, faint | Band 1–4, faint |
| --- | --- | --- | --- | --- |
| 1.0 (0.040) | 2, 0.0% | 1, 0.0% | 1, 0.0% | 1, 0.0% |
| 1.5 (0.060) | 3, −1.0% | 3, +0.1% | 3, −0.6% | 3, +0.2% |
| 2 (0.080) | 3, +0.2% | 3, +0.1% | 3, +0.3% | 3, +0.1% |
| 3 (0.120) | 3, −0.7% | 3, −0.5% | 3, −1.3% | 3, −0.5% |
| 5 (0.199) | 3, +0.2% | 3, −0.1% | 3, +0.2% | 3, 0.0% |
| 8 (0.319) | 3, +0.4% | 3, −0.4% | 3, +0.8% | 3, −0.4% |
| 12 (0.478) | 2, −3.6% | 3, −4.8% | 0 | 2, −3.9% |
| 16–25 (0.64–1.0) | 0 | 0 | 0 | 0 |
| 30 (1.20) | 0 | 2, −2.9% | 0 | 0 |

- **Faint pattern:** the lowest scores at 1.5–8 px/frame were 14–23 with band 1–4, against 10–18
  for differenced rows.
- **Shutter open half the frame:** both resolve 16 px/frame (band 1–4 in all six clips,
  differenced rows in five). At 20 px/frame, band 1–4 resolves two of six and differenced rows
  one.
- **Intervals:** the truth lay inside the 95% interval for 63% of resolved estimates (differenced
  rows: 69%). The intervals cover the scatter of the blocks only (docstring); systematic errors of
  0.5–5% are not in them.

**Long line** (`validate_long_line.py`). 60-s clips, shutter open the whole frame, 3 seeds; the
lowest score in brackets.

| px/frame (mm/s) | Limb 120 px: differenced | Limb: band 1–4 | Loop 300 px: differenced | Loop: band 1–4 |
| --- | --- | --- | --- | --- |
| 12 (0.48) | 2, −4.2% | 2, −3.6% | 3, −0.6% (35) | 3, −0.3% (36) |
| 16 (0.64) | 0 | 0 | 3, −0.1% (37) | 3, −0.2% (31) |
| 20 (0.80) | 0 | 0 | 3, −0.1% (29) | 3, −0.4% (27) |
| 25 (1.00) | 0 | 0 | 3, −0.8% (18) | 3, −1.1% (15) |
| 30 (1.20) | 0 | 2, −3.5% | 3, −1.7% (14) | 3, −1.2% (14) |
| 40 (1.59) | 0 | 0 | 3, +0.7% (9) | 3, −0.3% (12) |

- **No flow** (8 clips): at most 5.4 (limb, band 1–4) and 4.4 (loop, differenced); none resolved.
- **The simulated loop has one speed all round.** In a real loop the venous limb is slower.

**Real limbs at rest, band 1–4.** In mm/s, with the score in brackets and the differenced rows'
result after "differenced":

- **FP01_Qföre, tall loop, left limb (venous):** +0.084 (18.6); differenced +0.083 (11.4).
  Halves +0.086 and +0.081.
- **FP01_Qföre, tall loop, right limb (arterial, 64 px):** −0.107 (8.8); differenced −0.116 (8.7).
- **FP03_Qefter, loop P, left limb:** +0.058 (15.7); differenced +0.079 (9.6). Halves +0.067 and
  +0.051.
- **FP03_Qefter, loop P, right limb:** −0.042 (18.9); differenced −0.040, at the edge (9.4).
  Halves −0.043 and −0.040.
- **FP03_Qefter, loop S:** +0.051 (10.8); differenced +0.068 (6.2), unresolved. Halves +0.055
  and +0.054.

Notes:

- Three of the five lie at 1.05–1.45 px/frame, near the slowest speed reported.
- On loop P's left limb the two filters disagree, 0.058 against 0.079 mm/s.
  - Its halves differ by 24%, so the flow changes within the minute, and the two filters weight
    the blocks differently.
  - Which is closer is unresolved.

**Loops** (`real_loops.py`):

- **FP01_Qföre's tall loop:** +0.087 mm/s at rest (32.4; differenced 15.7) and +0.145 after
  release (9.5; differenced 4.8, unresolved). The faster flow after the cuff is now measured.
- **FP03_Qefter's loop P:** +0.044 at rest (43.6).
- **The others:** at the slow edge (1 px/frame, scores 8–23: slow flow or drift), or nothing
  (FP03_Qföre's curly loop).
- No loop showed faster flow.

**Benchmark** (`python -m capillary.benchmark`, before and after the change):

- The centre line and the two boxes are identical (216 rows).
- Pattern shift resolved 57 of the 99 cases with flow (56 before) and none without.
- Its errors stay within 1% at 2–8 px/frame, and are −3.1 to −3.6% at 12 (−2.8 to −3.6% before).
- Its scores are higher at 2–3 px/frame (25.7–39.6, against 14.9–31.2) and lower at 5–8
  (14.9–24.1, against 18.5–30.9).

### Tests

- **`test_the_correlation_sums_equal_a_direct_computation`:** now runs for both filters, through
  `_prepared`.
- **New, `test_rows_are_prepared_without_still_structure_and_band_passed`:**
  - a 10-px pattern passes (gain over 0.7);
  - 2-px and 200-px patterns do not;
  - still structure and the same-moment change vanish;
  - `None` differences.
- **`test_pooling_makes_a_faint_pattern_measurable`:** the pattern's contrast went from 1.3 to
  0.4. With band-passed rows, a single 3-s block resolved the old pattern (13.8). Differenced rows
  need about three times this contrast, even pooled.
- **`test_the_interval_holds_the_estimate_and_narrows_with_more_blocks`:** now uses the median
  width over 4 seeds.
  - With band-passed rows the intervals are 5–10 times narrower: 0.013–0.036 px/frame at
    4 px/frame.
  - They narrow less with more blocks: the median ratio of 90-s to 30-s width is 0.83, against
    0.61 for differenced rows, and one seed of eight came out wider.
- **Planted bug:** with the band-pass switched off, 2 tests fail.
- **Totals:** 259 tests pass (257 + 2).
- **flake8:** the CI's error selection is clean on the whole repository, and the full set is
  clean on the changed and new files.

### Open

- **Step 2:** pattern shift on the Centre line page for the arterial limb.
  - the rest window taken from the official times;
  - a direction check;
  - saved as "arterial limb".
- **Step 3:** the arterial limb's speed from a line that continues over the apex. This needs a
  simulator with different speeds in the two limbs.
- **The exposure time,** which the user is checking, decides how much fast flow is blurred.
- **The band on new recordings.** It was chosen and validated on the same 6 recordings. Check it
  on FP03_Wföre, FP04 and FP05 when lines are drawn there.
- **Near the slow edge** (1–1.5 px/frame), band-passed rows are pulled by slow drift; without
  flow, synthetic clips reached 5.4 there. The centre-line method measures that range better.
- **The centre-line method** also differences its rows ("whitening"). Band-passing may help it
  too; not done.
- **Intervals:** the truth lay inside them for 63% of synthetic estimates, so systematic errors
  dominate. Consider an interval that includes them before reporting intervals in the thesis.

---

## 2026-10-11 — The desktop's "stabilized" videos were raw; recordings copied in and stabilized

**Branch:** `docs/unstabilized-desktop-videos`, from `main` at `fc2fc7e`.

**Commits:**

- this entry, with corrections to `CLAUDE.md` and `metadata/README.md` (no code changed)

The user had worked on the Mac and asked to bring the desktop up to date.

- `main` was fast-forwarded from `bb597e2` to `fc2fc7e` (pull requests #9–#13), and the
  merged local branch `data/occlusion-times` was deleted.
- The 257 tests pass under WSL: Python 3.12.3, OpenCV 4.13.0, NumPy 2.4.6, SciPy 1.17.1
  (the Mac has OpenCV 5.0).
- No package was added; `image-registration` is no longer needed.

The user then said the videos in the desktop's `StabilizedVideos/` were probably not
stabilized.

### What the 8 videos were

The 8 files in `StabilizedVideos/` were copied in on 2026-06-11. The app calls every
video in that folder stabilized, and every desktop analysis of 2026-10-06 and 2026-10-07
used them. The 2026-10-08 entries guessed they were the old stabilizer's MPEG-4 output.
They were the raw DynCap recordings, never stabilized:

- **Format** (ffprobe): `rawvideo` without a FourCC, 8-bit palettized grey (`pal8`),
  640 × 480, stamped 30 fps.
  - That is 307 200 bytes a frame plus about 40 bytes of AVI overhead, 0.75–2.3 GB a
    file, the format of the raw downloads on the Mac.
  - The old stabilizer wrote MPEG-4 (FMP4), about 33 MB for a recording.
- **Frame counts** equal those of the Mac's raw downloads for the 5 recordings on both
  computers: FP01_Qföre 5729, FP01_Qefter_försök2 5102, FP01_W 4528, FP01_Wefter 10-13-03
  7524, FP02_Wföre 5765.
- **Movement.** The registration of `capillary.stabilize` was run on each, with the video
  writer replaced by one that writes nothing (scratch script).
  - It gives the movement and median match that the Mac measured on its raw downloads
    (2026-10-08), to 0.1 px and 0.01, despite the different OpenCV.
  - FP01_Qföre: 18.7 × 27.6 px, 0.74. FP01_Qefter_försök2: 25.8 × 24.7, 0.70. FP01_W:
    340.6 × 338.3, 0.08. FP01_Wefter 10-13-03: 47.9 × 90.8, 0.85. FP02_Wföre:
    148.3 × 166.7, 0.47.
  - A stabilized video would hardly move.
- **No trace of a stabilizer.**
  - Frame 0 is not black (the old stabilizer wrote every frame one late).
  - Frames have no black edges where a move would uncover them (13 of FP01_W's 4528
    frames have a dark edge strip).
  - There are no shift files.

### How far they move at rest

Rest is 2 s after the start to 2 s before the official occlusion; registration as above.

| Recording | Used for | Range at rest, x × y (px) | Furthest from the median position (px) | Rest frames > 4 px off | Most within 15 s (px) |
| --- | --- | --- | ---: | ---: | ---: |
| FP01_Qföre | aims 1, 2 | 15.9 × 14.7 | 12.2 | 19% | 18.4 |
| FP01_Qefter_försök2 | aim 2 | 10.3 × 9.1 | 6.5 | 6% | 12.1 |
| FP01_Wefter 10-13-03 | aim 2 | 28.9 × 24.5 | 22.1 | 76% | 30.2 |
| FP01_W 08-36-26 | aims 1, 2 | registration fails (match 0.08) | | | |
| FP02_Wföre | – | 115.3 × 143.0 | 94.4 | 89% | 100.5 |
| FP01_Qefter 09-46-17 | – | 24.3 × 10.7 | 17.3 | 36% | 25.1 |
| FP01_Wefter 10-04-19 | – | 24.4 × 14.5 | 14.1 | 72% | 22.7 |
| FP01_Wefter 10-07-49 | – | registration fails (match 0.09) | | | |

A capillary limb here is 8–15 px wide. So on every recording, a line or box placed on one
frame leaves the vessel during the rest.

### What it changes

- **Measured on a moving picture:**
  - the two-box data sets `Test` and `Test2` of FP01_Qefter 09-46-17 and `set1` of
    FP01_Wefter 10-13-03;
  - the centre-line data sets `set1` and `set2` of FP01_Qefter 09-46-17;
  - the reading set `Validation/reading1` (drawn from `set1`).

  They stay where they are.
- **The two-box verdict** (2026-10-06).
  - About 70% of a box's signal changed along the whole vessel at once. That entry named
    "small movements of the vessel or focus" as the likely cause.
  - A vessel drifting under fixed boxes does exactly that. Test the method again on
    stabilized video before ruling it out.
- **The simulator** was calibrated on the same measurements: the same-moment share, its
  size and its unevenness along the line. The synthetic benchmark may be harder than
  stabilized recordings are; measure these again on stabilized video.
- **Resting flow.**
  - The 2026-10-07 observations were on unstabilized video: near-horizontal streaks at
    rest, and no moving pattern in a row-to-row comparison.
  - The 2026-10-08 entries explained the difference from the re-stabilized video by
    MPEG-4 compression. The files were lossless, so the movement is the likelier
    explanation.
  - The occlusion result on FP01_Qföre (slow, slowing flow from 70 to 130 s) was measured
    on unstabilized video too; measure it again.
- **The app** knows a video is stabilized only by its folder. These showed as stabilized,
  the measure pages gave no warning, and "Stabilize" was greyed out, since it needs a raw
  video.

### The recordings on the desktop now

- **The 8 old files.** The user moved them to `RecordedVideos/` and removed
  `StabilizedVideos/`.
  - FP01_Qefter 09-46-17, FP01_Wefter 10-04-19 and FP01_Wefter 10-07-49 are no longer in
    the data folder. They are earlier attempts that no aim uses.
  - The data sets of FP01_Qefter 09-46-17 are still in `Statistics/`, but the app lists
    only recordings that have a video.
- **Seven new recordings** came from OneDrive (`OneDrive_1_2026-10-11.zip`): the four FP03
  ones downloaded on the Mac, both of FP04's, and FP05_Qefter. The user added "the best",
  the one with the most quality. More are on the way.
- **Each was checked** (scratch script):
  - the name is in NFC and in the official times;
  - rawvideo, 640 × 480, 30 fps;
  - every frame reads and none is black (a copy cut short can hold black frames);
  - the FP03 recordings have the Mac's frame counts;
  - every official occlusion and release falls inside the video at 30 fps.
- **Clean-up.** The 15 `:Zone.Identifier` files Windows had added were deleted.
- **Coverage.** `python -m capillary.inventory --have RecordedVideos`:
  - 9 of the 90 recordings the aims use are here: all of FP01 and FP03, and FP05's
    control efter;
  - 81 are still to come, 44 of them for aim 1;
  - FP02_Wföre and FP04's two recordings are used by no aim. FP02 has one visit, and FP04
    has no W visit.

### Stabilized

Ten recordings were stabilized with the command line, ten at a time, in about 5 minutes:
`python -m capillary.stabilize RecordedVideos/<name>.avi --out StabilizedVideos/<name>.avi`.

- `capillary/stabilize.py` is unchanged since `af1dce6`, the version the Mac used.
- FP01_W and FP03_Wefter were left raw. The stabilizer fails on their large movements
  (2026-10-08), and the app would call a failed output stabilized.

| Recording | Used for | Moved (px) | Match at rest | In occlusion | After release | Notes |
| --- | --- | --- | ---: | ---: | ---: | --- |
| FP01_Qföre | aims 1, 2 | 18.7 × 27.6 | 0.88 | 0.70 | 0.74 | |
| FP01_Qefter_försök2 | aim 2 | 25.8 × 24.7 | 0.70 | 0.84 | 0.65 | |
| FP01_Wefter 10-13-03 | aim 2 | 47.9 × 90.8 | 0.93 | 0.64 | 0.86 | |
| FP03_Qföre | aims 1, 2 | 446.1 × 360.5 | 0.68 | 0.14 | 0.11 | fails once the cuff is on: 419 frames at the search limit |
| FP03_Wföre | aims 1, 2 | 138.8 × 265.4 | 0.60 | 0.66 | 0.59 | 1 frame at the search limit |
| FP03_Qefter_försök2 | aim 2 | 105.7 × 162.1 | 0.63 | 0.66 | 0.61 | |
| FP05_Qefter | aim 2 | 38.0 × 15.9 | 0.88 | 0.81 | 0.80 | |
| FP02_Wföre | – | 148.3 × 166.7 | 0.51 | 0.41 | 0.48 | blurry; references disagree by more than 1 px on 38 frames |
| FP04_Qefter | – | 69.8 × 58.4 | 0.89 | 0.67 | 0.84 | |
| FP04_Qföre | – | 57.6 × 17.1 | 0.88 | 0.85 | 0.82 | |

Match is the median normalized cross-correlation with the references in each phase:

- rest: from 2 s after the start to 2 s before the occlusion;
- occlusion: from 2 s after it to 2 s before the release;
- after release: from 2 s after it.

Results:

- **At rest**, the window both aims use, no frame of the ten is at the search limit, and
  none has references that disagree by more than 1 px.
- **FP03_Qföre's** stabilized video is usable for its rest only.
- **Same as on the Mac.** Where the Mac stabilized the same recording (FP01's three,
  FP02_Wföre, FP03's three), the movement and median match agree to the precision of its
  DEVLOG entry, despite the different OpenCV.
- **The outputs** are rawvideo, 8-bit grey, 640 × 480, 30 fps, each with the raw video's
  frame count, its shift file and its provenance. About 18 GB in all; 916 GB are left on
  the WSL disk.
- **The app.** `gui.library.scan` now lists the ten as "Stabilized" and FP01_W and
  FP03_Wefter as "Raw only".
  - The old two-box `set1` of FP01_Wefter 10-13-03 is now shown over the stabilized
    video.
  - Its boxes were placed on the moving one (and in still tissue, 2026-10-06), so they do
    not fit.
- **Provenance.** The files record commit `fc2fc7e` with uncommitted changes. While the
  runs finished, the working tree held this entry's documentation edits; `capillary/` was
  unchanged.

### Documentation

- `CLAUDE.md`:
  - the data layout and the session start describe raw recordings in `RecordedVideos/`
    and stabilized ones in `StabilizedVideos/`;
  - the known issue about the 8 videos says what they were and what was measured on them;
  - the notes on resting flow, the two-box method, the simulator and `reading1` say they
    rest on unstabilized video.
- `metadata/README.md`: the note on the 8 local recordings says they were raw.

### Verification

- `python -m pytest`: 257 passed after the update, before any change here.
- The checks above, with scratch scripts in the session's scratchpad (not in the
  repository):
  - ffprobe;
  - the registration without writing;
  - a full read of every new recording;
  - `gui.library.scan` on the data folder: before stabilizing, all 12 recordings were
    "Raw only"; after, as above;
  - ffprobe on the ten outputs: format and frame counts;
  - the stabilizer's own summary of each run, read per phase from its shift file.

### Open

- Stabilize the recordings still arriving, after the same checks.
- FP01_W and FP03_Wefter wait for the stabilizer to follow large movements, as do
  FP03_Qföre's occlusion and release.
- Redo the work done on unstabilized video:
  - test the two-box method again;
  - recalibrate the simulator's disturbances;
  - measure FP01_Qföre's occlusion flow again.
- **"The best" recording.** If it means choosing between a visit's attempts by image
  quality, write the rule down before measuring. The inventory takes the last attempt
  with 30 s of rest; so far every recording added agrees with it.

---

## 2026-10-09 — Recording inventory: which recordings the aims use

**Branch:** `feature/recording-inventory`, from `main` at `70b9b12`.

**Commits:**

- this entry, with `capillary/inventory.py`, its tests and `metadata/derived/`

The laptop was overheating, so the user asked for work that does not process
videos. They chose an inventory of the study's recordings, built from the
official times in `metadata/`. It answers how many participants each aim can
use, and which videos to download from DynCap next.

### How (`capillary/inventory.py`)

- **Names.**
  - Each name is parsed: study, subject, condition (W/Q, S/C), role (active
    or control), före or efter, attempt (`_försökN`, or a trailing digit in
    ISMOKE), and start date and time.
  - `FP21Wföre` (no underscore) and `FP01_W_…` (neither före nor efter) are
    understood.
  - Names are compared in Unicode NFC. macOS spells the ö in file names as o
    plus a combining mark, so the first run matched only 1 of the 8 needed
    videos already downloaded.
- **Usable means enough rest.** Both aims use resting CBV, from the rest
  before the occlusion, so a recording needs 30 s of rest (2 s after the start
  to 2 s before the occlusion). A missing release time does not matter.
- **Flags**, not corrections:
  - a name without före or efter (the phase is taken from the time of day);
  - a day with two conditions;
  - a före more than 45 min after the day's first recording (probably an
    efter);
  - a condition recorded on more than one day;
  - too little rest.
- **The choice.** For each participant, the active and the control day each
  get a före and an efter: the last attempt with enough rest, on the
  assumption that a recording was repeated because the earlier attempt failed.
  The other attempts are listed.
  - **Aim 1** needs both före recordings, aim 2 all four.
  - Each aim is "yes", "check" (a chosen recording has an issue) or "no".

### Result

The table and the five recordings to check are in `metadata/README.md`:

- **Aim 1:** 13 + 1 (check) ESMOKE and 9 + 1 (check) ISMOKE participants.
  Visits are a median of 20 days apart in ESMOKE (6–68) and 7 in ISMOKE
  (7–16), and the order of the conditions is balanced.
- **Aim 2:** 12 + 1 ESMOKE and 8 ISMOKE participants.
- **Recordings:** the aims use 90 recordings, 48 for aim 1. Of the 9
  downloaded so far, 8 are among them; FP02_Wföre belongs to a participant
  with one visit only.
- **The checks most likely to change the numbers:**
  - ISMOKE FP02 (an `Sföre` and a `Cefter` on one day) would join both aims
    if the före is a C recording;
  - ISMOKE FP08 (two `Cföre` 107 min apart) would drop out of aim 1 if the
    second is the efter.

### Verification

- `tests/test_inventory.py`, 9 tests on the real metadata:
  - parsing, including the odd names and a decomposed ö;
  - all 124 recordings understood;
  - each kind of flag;
  - the last usable attempt chosen (FP05's fourth before-recording, FP01's
    third after-recording, none for ISMOKE FP04's 6-s rest);
  - the counts per aim and study;
  - the `used_for` marks;
  - matching downloaded videos;
  - the command line.
- Suite: 257 tests. flake8 is clean on the new files.

### Open

- Check the five flagged recordings in DynCap, and correct the choice if the
  labels are wrong.
- Download the 82 recordings still needed (44 for aim 1).
  `python -m capillary.inventory --have <video folder> --out <folder>` writes
  the list (`to_download.csv`).

---

## 2026-10-08 — Resting CBV: a first feasibility check (interrupted)

**Branch:** `feature/fast-flow-estimator`, after `bbf3089` (the entry below).

**Commits:**

- this entry, with two fixes to `capillary/pattern_shift.py`, their tests, and
  `analysis/resting_flow_feasibility/`

The user asked to confirm the finding below on more data: in how many
capillaries can resting flow be measured? The session stopped part-way
because the laptop overheated. It continues on the desktop;
`analysis/resting_flow_feasibility/README.md` says how.

### Two fixes to the pattern-shift estimator

- **The estimate snapped to 2 px/frame.**
  - On FP03_Qefter_försök2, both limbs of loop P came out at exactly
    ±0.080 mm/s (2.00 px/frame), with 95% intervals of zero width.
  - Cause: the rule "count a frame distance only from a 2-px shift" switched
    the consecutive-frame comparison on at exactly 2 px/frame, so the score
    jumped there and the maximum stuck to it. Without the rule, loop P's left
    limb also peaks at about 2.0 px/frame, so the speed was right but the
    interval was false.
  - Each frame distance now fades in between 1 and 2 px of shift and out over
    the last 10% of the largest shift. The score is divided by the root of
    the summed squared weights, so it stays in noise units. Loop P's left limb
    now reads 1.996 px/frame (95% CI 1.951–2.041).
- **A meaningless speed at the edge.** When the best score lay at the slowest
  speed searched (−1.00 px/frame), the parabola that refines the peak used the
  next grid point across the gap, at +1.00, and reported −1.99. The peak is
  now refined only from neighbours on the same side of the grid; such an
  estimate reports the edge, flagged out of range, as before.
- **Tests:** two new ones:
  - speeds of 1.85 and 2.15 px/frame are recovered within 5% (single 30-s
    clips of the test pattern scatter by 2–4% there), with an interval wider
    than zero;
  - flow below the range reports exactly the edge.
  - Suite: 248 passed.
- **Not yet rerun:** the synthetic validation of the fixed version
  (`validate_pattern_shift.py`); it was stopped when the laptop overheated.
  The table in the entry below is for the version before these fixes.

### Stabilizing the other 8 recordings

All were stabilized with the stabilizer of `af1dce6`:

| Recording | Moved (px) | Median match | Result |
| --- | --- | --- | --- |
| FP01_Qföre (from before) | 18.7 × 27.6 | 0.74 | good |
| FP01_Qefter_försök2 | 25.8 × 24.7 | 0.70 | good |
| FP01_W_14-Oct-2019_08-36-26 | 341 × 338 | 0.08 | **failed throughout** |
| FP01_Wefter_14-Oct-2019_10-13-03 | 47.9 × 90.8 | 0.85 | good |
| FP02_Wföre | 148 × 167 | 0.47 | aligned; the recording itself is blurry |
| FP03_Qefter_försök2 | 106 × 162 | 0.64 | good |
| FP03_Qföre | 446 × 361 | 0.15 | rest good (0.68); occlusion and after release failed |
| FP03_Wefter | 343 × 380 | 0.26 | rest mostly failed (0.24) |
| FP03_Wföre | 139 × 265 | 0.61 | good (the breathing-swing recording) |

The three failures are large movements of the finger:

- **FP01_W** drifts steadily by about 200 px over the recording. Its reference
  frame is near the end (141 s), and the early frames are beyond the coarse
  search, so following the previous frame never locks on. It is also the only
  file named without före or efter.
- **FP03_Qföre** jumps when the cuff goes on.
- **FP03_Wefter's** capillaries jump 100–200 px around the frame at rest.

The fix planned: follow the movement outwards from the reference frame in
both directions in time, so no frame is ever searched far from its
neighbour's position.

### The feasibility check

- **Line placement:** on each recording's resting image (the band-passed
  mean between 2 s and 2 s before the official occlusion), points were placed
  by eye along clearly visible capillary limbs. They were moved onto the
  vessel's ridge (within 4 px across) and smoothed. One tissue control line
  per recording runs beside the loops. Lines were chosen from the image alone.
- **Measurements:** each line was measured with the pattern shift over the
  rest window and its two halves, in occlusion and after release, and with
  the centre-line method in 3-s blocks at rest.
- **Files:** `analysis/resting_flow_feasibility/lines.json` and
  `results.csv`. FP03_Qefter_försök2's rows there predate the fixes above.

Six recordings were measured (FP01_W and FP03_Wefter could not be, and
FP03_Wföre is not done yet): 24 limbs and 6 tissue lines.

| Recording | Limbs | Resolved at rest (pattern shift) | Other signs |
| --- | ---: | --- | --- |
| FP01_Qföre | 4 | tall loop: left limb +0.083 mm/s (signal-to-noise 11.6, halves 0.085 / 0.080), right limb −0.116 (9.0) | the 44- and 30-px limbs: none |
| FP01_Qefter_försök2 | 5 | none | loop A: centre line resolved 40% of rest blocks (+0.014 mm/s) on the left limb and 20% (−0.007) on the right: very slow flow, opposite directions |
| FP01_Wefter | 3 | none | right loop at the method's lower edge (slower than 0.04 mm/s) |
| FP02_Wföre | 4 | none | blurry recording |
| FP03_Qefter_försök2 | 7 | loop P left limb: about +0.08 mm/s (9.5) | loop P right limb at the lower edge (score 9.7); loop S +0.068 at 5.7 |
| FP03_Qföre | 6 | none | none, though the limbs are long (up to 139 px) and the rest is well stabilized |

- **Tissue lines** reached at most signal-to-noise 5.3 (FP03_Qefter_försök2);
  none was resolved.
- **Where resting flow was measured,** it was 0.08–0.12 mm/s, on limbs of
  63–122 px. No limb shorter than 50 px was resolved.
- **Why most limbs show nothing.** 5-s space-time pictures at rest show it:
  - where flow was measured, diagonal streaks of plasma gaps run across the
    diagram;
  - on FP03_Qföre's limbs there is only noise. Their brightness changes over
    time with an SD of 1.1–1.2 grey levels, against 1.3 on the tissue line and
    1.5–1.6 on the limbs with flow.

  So at rest these capillaries show no moving pattern in the video. The blood
  column may be too uniform, or the flow fast enough to smear within a frame.
  No image method can measure them at 30 fps.
- **For aim 1:** resting CBV can be measured only in capillaries that show
  plasma gaps, which so far is a minority (3 of 24 limbs resolved, a few more
  near the threshold). Aim 1 needs a rule for choosing capillaries and enough
  of them per recording, and the measurement needs a rule for combining the
  two methods (the pattern shift from about 0.04 mm/s, the centre line below).

### Open (to continue on the desktop)

- Fix the stabilizer for large movements (above), then stabilize FP01_W and
  FP03_Wefter again.
- Measure FP03_Wföre, and remeasure FP03_Qefter_försök2.
- Rerun the synthetic validation of the fixed estimator.
- Decide the measurement protocol: a rule for choosing capillaries (length,
  visible plasma gaps), and a rule for combining the two methods.
- The frame rate (unverified) and the camera's exposure time decide whether
  fast resting flow is invisible or absent.

---

## 2026-10-08 — Resting flow is faint, not fast: the pattern-shift estimator

**Branch:** `feature/fast-flow-estimator`, from `main` at `c2ac5dd`.

**Commits:**

- this entry, with the estimator, its tests, the benchmark and the CLI

Aim 1 (resting CBV) was blocked by the known issue "resting flow is beyond
the centre line's range". The plan was a fast-flow estimator: measure how far
the pattern along a centre line moves between consecutive frames. Testing the
idea on real data first changed the diagnosis.

### Otsu thresholding, considered and not used

The user asked about Otsu thresholding. Otsu was tried on the stabilized
FP01_Qföre in three ways:

- **Raw frame:** it split the picture by the uneven lighting, marking 56% of
  it, half of that background.
- **Band-passed image:** the vessels are too small a share of the picture for
  Otsu to find a split.
- **Temporal SD over 10 s at rest:** rings fixed to the camera optics dominate
  it. They move once the video is stabilized, and Otsu marked 38%, mostly
  rings.

Binarizing the space-time diagram would throw away what the estimators use. So
Otsu was not implemented. Finding vessels automatically (for line placement)
would need a vessel filter and a local threshold, and its own validation.

### Real data first

On 2026-10-07 a crude row-to-row comparison found no moving pattern at rest
(best match always at zero shift, r = 0.06–0.19). That was on the old
stabilized video, which was probably MPEG-4: such compression kept only about
14% of the frame-to-frame change (entry below). It was repeated on the
lossless video from the new stabilizer.

**The first line**, placed by eye (6 points, 119 px), ran partly between the
two limbs of the tall loop. Per-block results were noise, though the
centre-line method still found the occlusion flow on it (12 of 20 blocks at
80–90 s, median 0.011 mm/s).

**A line traced along the left limb's centre** in the resting mean image (10
points, 112 px) showed a forward shift once the correlation was pooled over
2–66 s, rest only:

| Frames apart (k) | 1 | 2 | 3 |
| --- | --- | --- | --- |
| Rest: shift (strength) | +2 px (13.7× noise) | +4 px (7.7×) | +6 px (5.6×) |
| After release | +4 px | +7 px | lost |

So about 2 px/frame (0.08 mm/s) at rest, and about 3.5 px/frame after release.
During occlusion the peak sat near 2 px at every k, so the flow there is under
a pixel per frame.

**The centre-line method on the same line** agreed:
- in 3-s blocks, 8 of 123 rest blocks were resolved, median 0.082 mm/s
  (2.07 px/frame);
- the median slope over all rest blocks was +1.77 px/frame, at signal-to-noise
  4.2, below the threshold of 8;
- with 10-s and 30-s blocks it found +2.15 and +2.77 px/frame, at 3.8 and 5.7.

**Controls**, pooled over the rest, for k = 1, 2, 3:
- the right limb, also drawn top to bottom: −2, −7, −9 px (6.9×, 3.5×, 3.5×),
  the opposite direction;
- tissue 22 px beside the limb: −33, −1, +16 px (2.5×, 4.0×, 2.0×), no
  pattern.

So on this capillary the blood goes down one limb at about 0.08 mm/s and up the
other at about 0.12 mm/s, within the centre line's range (up to 0.2 mm/s on
112 px). It is too faint for single 3-s blocks. The 2026-10-07 reading of
"faint, almost horizontal streaks, roughly 0.5–1 mm/s" was probably the change
of the whole vessel at once, which draws horizontal lines, seen in the
compressed video. The known issue in CLAUDE.md is revised accordingly. This is
one capillary of one recording.

### The estimator (`capillary/pattern_shift.py`)

On the same space-time diagram:

1. In each 3-s block, the still structure and the same-moment change are
   removed and the rows differenced, as in `capillary.spacetime`.
2. For frame distances k = 1–8, row t is correlated with row t + k at every
   shift up to half the line. Numerators and energies are pooled over every row
   of every block (an FFT per row, checked against a direct sum in a test).
3. Forward minus backward correlation (direction contrast), in units of each
   k's own spread over shifts.
4. A speed's score is the sum over the k where it needs a shift of 2 px to half
   the line, divided by the square root of their number. The best speed (step
   0.01 px/frame, refined by a parabola) is the estimate, and its score the
   signal-to-noise ratio.
5. A 95% interval comes from leaving out one block at a time (jackknife).

Settings, each checked on data:

- **Signal-to-noise of 8 to count:** without flow it reached at most 3.9 on 30
  synthetic recordings (5.2 before the minimum-shift rule below), and at most
  4.3 on two tissue lines of FP01_Qföre in any phase.
- **Slowest speed 1 px/frame:** at 0.5 px/frame it read 4–8% high, where the
  centre-line method is exact.
- **Minimum shift of 2 px per frame distance:** on synthetic recordings 2 and
  3 px both lowered the error near 1 px/frame slightly (worst 0.8–0.9% against
  1.3% with none). On the real limb, 3 px dropped the comparison of
  consecutive frames at 2 px/frame. That one is the strongest there, because
  the blood rearranges within a few frames, and dropping it lowered the
  signal-to-noise from 13.7 to 9.7 and left both 30-s halves unresolved. With
  2 px the real results are unchanged.
- **The intervals cover the statistical scatter only.** In the synthetic runs
  they often missed the truth by about 1%, a systematic error probably from
  the drawn line's geometry. This is said in the docstring.

**Validation on synthetic recordings** (final settings): 138 clips of the
simulated loop, 30 s each, a 120-px hand-drawn line, motion blur for the whole
frame interval, 3 seeds per speed. The conditions are "as measured", "strong",
and "faint" (a third of the cells' contrast). Each cell shows the median error
with the worst in brackets, then the lowest signal-to-noise:

| Speed px/frame (mm/s) | As measured | Strong | Faint | Centre line, blocks resolved (as measured) |
| --- | --- | --- | --- | --- |
| 0.5 (0.020) | not reported, 2.1 | not reported, 2.0 | not reported, 2.2 | 100%, +0.1% |
| 1 (0.040) | +0.5% (0.5), 14.2 | +0.5% (0.5), 15.7 | +0.5% (0.5), 12.0 | 100%, +0.1% |
| 2 (0.080) | +0.2% (0.6), 13.9 | +0.2% (0.3), 14.6 | +0.8% (2.2), 12.8 | 100%, +0.5% |
| 3 (0.120) | −1.1% (1.2), 25.7 | −1.3% (1.5), 24.0 | −0.6% (1.3), 20.6 | 100%, +0.5% |
| 5 (0.199) | +0.2% (0.6), 25.8 | +0.6% (1.3), 21.3 | 0.0% (2.1), 18.1 | 80%, −1.5% |
| 8 (0.319) | +0.4% (0.7), 15.9 | +0.3% (0.7), 14.9 | +0.4% (3.5), 10.7 | 0% |
| 12 (0.478) | −0.1% (0.1), 9.5 | −0.1% (0.1), 9.1 | −3.1% (6.5), 5.8 | 0% |
| 16 (0.638) | −6.3% (6.3), 5.5 | −6.3% (6.3), 5.0 | −9.4% (9.6), 4.0 | 0% |
| 20–40 (0.80–1.60) | signal-to-noise 2.7–5.2 | 2.5–4.7 | 2.8–4.1 | 0% |

- **No flow** (10 clips per condition): the signal-to-noise reached at most 3.4,
  3.9 and 3.7.
- **Resolved in every seed:** from 1 to 12 px/frame as measured and strong,
  and up to 8 px/frame when faint.
- **Truth inside the 95% interval:** in 1 to 3 of the 3 seeds, mostly missed by
  about 1%. The intervals are statistical only (above).

### On FP01_Qföre with the final version

- **Left limb:**
  - rest: 0.0819 mm/s (95% CI 0.0747–0.0891), signal-to-noise 13.7;
  - first 30 s: 0.084 mm/s (8.5); second 30 s: 0.080 mm/s (9.1);
  - one 3-s block: 3.8, not resolved;
  - occlusion: below the method's range, which is right; the centre line
    measures it;
  - after release: 0.145 mm/s at 4.5, not resolved.
- **Right limb:** −0.116 mm/s at rest (5.8, not resolved; a 76-px line).
- **Tissue lines:** at most 4.3, with random speeds.

### What changed

- `capillary/pattern_shift.py` (new): `pattern_shift` for one stretch,
  `shift_time_course` for successive windows.
- `tests/test_pattern_shift.py` (new, 18 tests), checking:
  - the FFT sums against a direct computation;
  - known speeds from 1.5 to 14 px/frame despite same-moment changes;
  - reversed flow;
  - no flow, and a much stronger same-moment change, not resolved;
  - a pattern flickering in place not read as flow;
  - flow slower than the method not reported;
  - pooling making a faint pattern measurable;
  - the interval holding the estimate and narrowing;
  - unusable input; the time course;
  - a synthetic recording with motion blur, where fast flow is either right or
    unreported.
- `capillary/benchmark.py`: a third method, and speeds 16 and 25 px/frame
  added.
- `capillary/cli.py`: for a line, it also prints the pooled pattern-shift
  velocity, its interval and signal-to-noise.
- README ("Pattern shift"), CLAUDE.md (the engine, and the resting-flow known
  issue revised).

### Verification

- 246 tests pass. flake8's CI selection is clean, as is a full run on the new
  and changed files.
- Planted bugs:
  - a flipped sign fails 7 tests;
  - no conversion to noise units fails the faint-pattern test;
  - no direction contrast fails the reversed-flow test. Without it the
    flickering pattern did read as 10.0 px/frame, but at signal-to-noise 2.6,
    so that test passes either way.
- `python -m capillary.benchmark --quick` runs with the new method. In 10-s
  clips it resolves 2 and 6 px/frame within 1%. At 6 px/frame the centre line
  resolves at most 13% of blocks, 16% low.

### Open

- **The app:** show the pooled velocity on the Centre line page (the rest
  window as default stretch), and save it with the data set.
- **More recordings:** more capillaries and recordings. Stabilize the other 8
  downloaded recordings and repeat the left-limb check on several capillaries
  each.
- **Frame rate:** still unverified. Every velocity scales with it.
- **Above about 16 px/frame** the synthetic signal-to-noise falls below the
  threshold, probably from motion blur. The real exposure time is unknown.
- **The camera-fixed rings** drift through the stabilized picture. They look
  like near-zero flow and could bias slow-flow measurements; worth checking.

---

## 2026-10-08 — A new registration for the stabilizer

**Branch:** `fix/stabilizer-registration`, from `feature/streaming-stabilizer` at
`dde2fd7` (the entry below); merge `fix/macos-tk9` and that branch first.

**Commits:**

- `98f74ba` Stabilizer registration: band-pass, averaged references, template matching
- `af1dce6` Stabilizer: follow large movements, references from the sharpest frame's neighbours, re-centre
- this entry, with README and CLAUDE.md

The entry below found that the stabilizer's registration falls short by
several pixels where the image has moved far. The user asked for it to be
fixed. The method changed in two steps: first against FP01_Qföre, then again
after a second recording, FP03_Wföre, broke the first version. All scratch
scripts are outside the repository; the numbers here are what they printed.

### Choosing the method on known shifts

**The synthetic test.** One real frame of FP01_Qföre was used as the scene.
Its own lighting was divided out (by its 40-px blur), it was moved by known
sub-pixel amounts and cropped to 560 × 400. It was then multiplied by lighting
that stays with the camera (darker to the corners, a left-right gradient), and
smooth changing content and noise were added. Each method registered every
frame against an unmoved one. Error against the truth (mean |x|, mean |y|,
largest), and the time per registration:

| Method | Moves up to ±6 px | x ±10, y ±25 px | ms |
| --- | --- | --- | ---: |
| Old: CLAHE + median, circular upsampled | 0.19, 0.32, 0.66 | 0.32, 0.73, 1.98 (mean y error +0.46: too short) | 18 |
| DoG + window, circular upsampled | 0.05, 0.05, 0.18 | 0.04, 0.06, 0.15 | 23 |
| DoG + template match, parabola | 0.06, 0.06, 0.20 | 0.05, 0.06, 0.17 | 8 |
| DoG + template match, Gaussian peak fit | 0.06, 0.06, 0.20 | 0.04, 0.06, 0.16 | 8 |
| DoG + template match, ECC refinement | 0.06, 0.06, 0.20 | 0.05, 0.06, 0.14 | 16 |
| DoG + template match, upsampled refinement | 0.05, 0.06, 0.23 | 0.05, 0.06, 0.16 | 23 |

DoG is a difference of Gaussians with σ 1 and 10 px; the band-pass removes the
lighting without depending on position.

**On real frames.** Every 30th frame of FP01_Qföre was registered against its
three sharpest single frames. The references disagree (median px, rest /
occlusion / after release), and the edge similarity to frame 63 (mean, same
order):

| Method | Disagreement | Edge similarity | Closure 63→210→463 |
| --- | --- | --- | ---: |
| Old | 2.19 / 3.55 / 3.32 | 0.548 / 0.345 / 0.354 | 1.47 px |
| DoG + window, upsampled | 0.60 / 0.83 / 0.78 | 0.560 / 0.393 / 0.419 | 0.27 px |
| DoG + match, parabola | 0.56 / 0.79 / 0.71 | 0.559 / 0.393 / 0.418 | 0.28 px |
| DoG + match, ECC | 0.68 / 1.01 / 0.92 | 0.559 / 0.392 / 0.419 | 0.26 px |

Template matching with a parabola was as good as any other method and the
fastest, so it was chosen.

**Averaged references.** The remaining ~0.6 px came from the references:
single frames differ by the blood moving in them. Noise of one estimate was
measured split-half. Each frame was registered against two references made
from different frames, and the spread of the difference (robust, divided
by √2) was taken. This measures only the reference's share of the noise.
Results (x/y px, rest / occlusion / after release):

| Band-pass σ (px) | Single sharp frames | Mean of 12 aligned sharp frames each |
| --- | --- | --- |
| 1 and 10 | 0.20/0.18, 0.26/0.44, 0.31/0.32 | 0.08/0.05, 0.04/0.07, 0.10/0.05 |
| 1.5 and 6 | 0.20/0.21, 0.29/0.30, 0.34/0.43 | 0.05/0.05, 0.04/0.07, 0.06/0.06 |
| **2 and 15** | 0.12/0.19, 0.12/0.32, 0.15/0.16 | **0.02/0.02, 0.02/0.02, 0.03/0.02** |
| 1 and 5 | 0.25/0.37, 0.63/0.79, 0.61/0.51 | 0.13/0.08, 0.11/0.16, 0.15/0.14 |

**Interpolation.** Moving a frame by a fraction of a pixel with bilinear
interpolation blurs it by an amount that depends on the fraction. The share of
detail kept on a real frame, for shifts of 0, 0.25 and 0.5 px:

| Scale | Bilinear | Bicubic |
| --- | --- | --- |
| Finest, 0.5–1.5 px | 1.00, 0.72, 0.62 | 1.00, 0.94, 0.88 |
| Fine, 1–3 px | 1.00, 0.92, 0.89 | 1.00, 1.01, 1.02 |
| Cell scale, 2–6 px | 1.00, 0.99, 0.98 | 1.00, 1.00, 1.01 |

So the output now uses bicubic interpolation.

### First version (`98f74ba`) and what FP03_Wföre showed

The first version used:
- the band-pass with σ 2 and 15 px;
- two references, each the mean of every other one of the 24 sharpest frames,
  moved onto the sharpest;
- template matching of the frame's centre over ±64 px;
- a parabola for the fraction of a pixel;
- bicubic output.

It also wrote three new columns: a match score, the disagreement between the
two references, and a flag when the best offset lies at the edge of the
search. The edge flag alone caught only 2 of 17 synthetic frames moved beyond
the search; a frame far beyond lands on a false peak inside it, with a low
match. On FP01_Qföre it was good: the references disagreed by a median of
0.03 px, and there were no flags. It took 136 s.

Stabilizing a second recording as a check, FP03_Wföre, failed on most frames:
- median match 0.23;
- 3366 of 5819 frames at the search limit;
- shifts over the whole ±64 px.

The recording is dark (grey level about 53, SD about 4). A coarse wide search
on quarter-size frames showed the image moving 72 px up and 104 px down at
rest and during occlusion. The montage confirmed this. The movement swings
regularly, about every 3 s (a breath), by around 200 px. Its sharpest frames
all lay around 100 s, during the occlusion, at one extreme; the sharpness
hardly varies in this recording (0.0082–0.0084), so they were close to an
arbitrary choice.

### Second version (`af1dce6`)

- **Coarse then fine.** A coarse search on frames reduced 4 times reaches a
  third of the frame (±160 px). The fine search then looks within 12 px of two
  candidates, the coarse result and the previous frame's position, and keeps
  the better match; a match inside its search beats one at its edge.
  - The previous frame lets the search follow movement beyond the coarse
    reach. Each frame is still registered against the fixed references, so
    errors do not add up.
  - The fine search compares the largest part of the frame that stays inside
    the reference.
- **The references** are now built from the sharpest frame and the 12 frames
  on each side of it, aligned outwards from it with the previous position as a
  guide.
  - A frame is kept only if aligning it onto the sharpest frame and back gives
    opposite shifts, to within 1 px.
  - Without that check, a synthetic test with random jumps beyond the coarse
    reach put falsely aligned frames into the reference. The reference then
    held the scene twice, 35 and 47 px apart, and half the frames were
    silently 47 px off with a believable match of 0.65–0.70.
- **Re-centring.** The shifts are re-centred on their median before writing,
  so the picture sits where the recording usually is. This needs a third
  reading.
- **The edge preference.** The first run of the tests caught one frame found
  correctly (match 0.98) and still flagged. The search around the previous
  position had reached the same peak at its edge, with a match higher in the
  fourth decimal.

### Verification

- **Tests:** `tests/test_stabilize.py` now has 16 tests (228 in the suite).
  The new and rewritten ones check:
  - the band-pass moves with the image and drops a lighting field;
  - the shifts undo moves of ±5 px to within 0.15 px (largest error 0.06–0.08
    px over 4 seeds, against 0.31–0.39 for the old registration);
  - moves of x ±10, y ±25 px under camera-fixed lighting are undone to within
    0.15 px (0.05–0.07);
  - following the previous frame tracks a 130-px drift where the coarse search
    reaches 80 px, which fails without it;
  - with random jumps beyond the reach, every frame is either right (under
    0.15 px) or marked (low match or at the limit), and none within reach is
    marked;
  - the references are the sharpest frame and its neighbours;
  - memory does not grow from 60 to 180 frames.

  Each of five planted bugs fails at least one test: CLAHE tiles back in front
  of the band-pass, whole pixels only, a wrong direction, no edge flag, and no
  following of the previous frame. flake8 is clean.
- **FP01_Qföre** (5729 frames), with the final version:
  - 135 s, at most 194 MB of memory;
  - the image moved over 18.7 × 27.6 px; the references disagree by a median of
    0.03 px (0 frames over 1 px); median match 0.74 (lowest 0.66);
  - every frame equals its recorded frame moved by its saved shift.

  Edge similarity to frame 63, mean (worst):

  | Phase | Unaligned | Old registration | New registration | New better on |
  | --- | --- | --- | --- | --- |
  | Rest | 0.406 (0.219) | 0.565 (0.418) | 0.560 (0.420) | 43 of 137 |
  | Occlusion | 0.304 (0.221) | 0.366 (0.323) | 0.384 (0.346) | 118 of 124 |
  | After release | 0.325 (0.210) | 0.386 (0.322) | 0.411 (0.347) | 121 of 121 |

  - At rest the two registrations differ by a median of 0.9 px vertically. On
    the two rest frames where they differ most (2.2 and 3.7 px), the new one
    matches better (0.537 vs 0.521, 0.415 vs 0.403). Overlays show the old
    alignment offset and the new one overlapping.
  - The small average preference for the old one at rest is unexplained. A
    measure that favours small shifts, through anything fixed to the camera,
    is a guess.
  - Movement left between consecutive output frames, by phase correlation
    (robust SD, x/y px):

    | Phase | Unstabilized | Old | New |
    | --- | --- | --- | --- |
    | Rest | 0.077/0.064 | 0.069/0.067 | 0.072/0.070 |
    | Occlusion | 0.082/0.074 | 0.090/0.107 | 0.092/0.102 |
    | After release | 0.085/0.073 | 0.082/0.096 | 0.088/0.088 |

    The recordings drift rather than shake: both registrations leave about the
    raw video's own frame-to-frame movement, well below the 0.2–0.3 px that
    troubled the centre line.
- **FP03_Wföre** (5819 frames), stabilized into the scratch folder (not the
  data folder):
  - 135 s, at most 181 MB;
  - the image moved over 139 × 265 px;
  - by phase:

    | Phase | Match median (lowest) | Disagreement median | Frames over 1 px |
    | --- | --- | --- | --- |
    | Rest | 0.60 (0.53) | 0.14 px | 0 |
    | Occlusion | 0.66 (0.49) | 0.10 px | 0 |
    | After release | 0.59 (0.36) | 0.13 px | 6 |

  - 1 frame at the search limit (frame 3224);
  - frame-to-frame jumps: median 1.5 px, 99th percentile 8.0 px.
  - The 12–16 px jumps (70.5 s just before the cuff, 107, 158, 178, 192 s) keep
    normal match and low disagreement.
  - The largest, 42 px from frame 0 to frame 1, is real: frame 0 shows the
    capillaries clearly lower and to the right. It is probably a camera
    start-up artefact.
  - A montage of the stabilized output at 0–180 s shows the same capillary
    loop in the same place throughout.
- `FP01_Qföre` in `StabilizedVideos/` was stabilized again with the final
  version (provenance at `af1dce6`).

### Open

- Checked on two recordings only. The settings (σ 2 and 15 px, 25 reference
  frames, a coarse reach of a third of the frame, a fine reach of 12 px) were
  chosen on them. Check each recording's summary in its shift file: match,
  disagreement, frames at the search limit.
- Translation only. FP03_Wföre's movement is so large that up to about half of
  some frames is lost at the edges; a capillary near the top or bottom may be
  out of view for part of each breath.
- A recording that starts more than a third of the frame away from its
  sharpest frame loses its first frames until the movement comes within reach;
  those frames are marked by a low match.
- On the desktop: run the tests, since the uncompressed grey writer was checked
  only with OpenCV 5.0 on macOS. Check the codec of the 8 old stabilized videos.

---

## 2026-10-08 — The stabilizer reworked: read from disk, lossless, in step

**Branch:** `feature/streaming-stabilizer`, from `fix/macos-tk9` at `55f201e` (the
entry below); merge that branch first.

**Commits:**

- `0a1988b` Stabilizer read from disk, lossless and in step (capillary.stabilize)
- this entry

The user asked whether the stabilizer needed work before stabilizing the
downloaded recordings, and then to make it use less memory. The method stays
the same; how it runs, what it writes and how fast it is changed.

### What a review and tests found

Tests on FP01_Qföre (scratch scripts, not in the repository) showed:

- **Memory.** `Caper.VideoStabilization` held two float64 copies of the whole
  video: 22–37 GB for the 9 downloaded recordings (4528–7524 frames). That was
  impossible on the 8 GB Mac and probably on the desktop too, since WSL gets
  half of the PC's memory by default.
- **Lossy output.** It wrote MP4V into an `.avi`; FFmpeg falls back to the
  FMP4 tag, which is the same MPEG-4 Part 2 codec. On the first 15 s of
  FP01_Qföre:
  - 207 MB became 3.0 MB;
  - the error against the same shifts written uncompressed was 4.6 grey levels
    RMS (PSNR 34.9 dB), larger than the raw video's own frame-to-frame change
    (3.05);
  - the frame-to-frame change correlated only r = 0.38 with the uncompressed
    one (r² ≈ 0.14), and the moving cells show up in that change.
- **One frame late** (known since 2026-10-05): frame 0 black, frame k holding
  recorded frame k−1, the last frame dropped. This was confirmed again.
- The writer was fixed at 30 fps and 640 × 480; a video of another size would
  have been written empty without an error.
- **Slow:** 239 ms a frame, two-thirds of it in `scipy.signal.medfilt`.
- **The registration itself works.**
  - On a synthetic clip (one real frame moved by known shifts) the direction
    is right: the correction correlates −0.999 with the movement, leaving
    about 0.3 px.
  - On the real clip its alignment matches a reference frame better than plain
    phase correlation (similarity 0.980 against 0.964, and 0.959 unaligned).
    It is never worse by more than 0.02 and better on 120 of 450 frames.
  - FP01_Qföre drifts by up to about 11 px at rest within those 15 s. A
    capillary limb is about 8–15 px wide here, so the recordings need
    stabilizing before a centre line is drawn.
  - A first check by phase correlation had suggested the stabilizer added
    motion, and the interim report to the user said so. That check was the
    one failing: its peak response fell to about 0.01 on the frames in
    question.

Also found, and **not changed** here because it changes the results: the
contrast enhancement before the registration (CLAHE on a fixed 3 × 3 grid of
tiles) changes as the image moves. On known shifts of one real frame the error
was 0.21 px (x) and 0.50 px (y) on average, up to 0.87 px, against 0.08 px
without the enhancement. That is close to the slowest speeds the centre line
measures (about 0.2 px/frame). It needs its own change and verification
(CLAUDE.md, known issues).

Side finding: the DynCap downloads are uncompressed 8-bit grey AVI, so the
archive is stored losslessly. That answers an open point in the entry on the
Capture page's removal (the thesis draft says the recordings were stored
losslessly).

### What changed

- **`capillary/stabilize.py`** (new) runs the same method in two readings of
  the file:
  1. Every frame's sharpness (`quality.calculate_blur`) is computed, and the
     three sharpest frames are kept as they come along.
  2. Each frame is enhanced (CLAHE 7.65, 3 × 3 tiles; 7 × 7 median), registered
     against the three enhanced references to 1/100 px, moved by the mean of
     the three shifts (bilinear) and written.

  Only a few frames are in memory at a time. Differences from the old code:
  - **Median filter:** OpenCV's median on a zero-padded copy, equal to
    `scipy.signal.medfilt` (checked on real frames and in a test) and much
    faster.
  - **Rounding:** the moved frame is rounded to whole grey levels; the old
    code truncated, which darkened every frame by half a grey level on
    average.
  - **Output:** uncompressed 8-bit grey AVI at the source's frame rate and
    size. Output frame k is recorded frame k.
  - **Record:** next to the video, `<stem>___stabilization.csv` holds every
    frame's shift, how far the three references disagree once their fixed
    offsets are removed, its sharpness, and whether it is a reference.
    `<stem>___stabilization_provenance.json` holds the settings, the
    reference frames, a summary (how far the image moved, the largest jump
    between frames, the disagreement) and the git commit.
  - **Robustness:** progress and cancel work as in the measurements, and a
    failed or cancelled run removes its partial output.
  - **Command line:** `python3 -m capillary.stabilize <raw> --out <stabilized.avi>`.
- **`capillary/registration.py`** is `SingleStepDFT.py`, moved into the package
  (`git mv`) with only its docstring changed.
- **`Caper.py`** loses `Video` and `VideoStabilization`, and the imports only
  they used.
- **`Utilities.py`** is removed: `clahe` and `median_filter` are replaced in
  `stabilize.py`, and nothing used its re-export of `calculate_blur` (its test
  in `test_velocity.py` goes too).
- **`gui/tasks.py`:**
  - `stabilize` runs the new module and always writes `<stem>.avi`.
  - Stabilizing again moves the previous video and its two files to the trash.
  - `recording_files` includes the two files, so moving a recording to the
    trash takes them along.
  - A disk-space check replaces the memory check. The memory check's macOS
    fallback from `a71f270` goes with it; there is nothing left to check.
- **Docs:** the README gains "How a recording is stabilized", the command
  line, the new files and the code layout. CLAUDE.md gets the data layout, the
  engine, the test count and the known issues, and docstrings in `quality.py`
  and `video.py` were updated.

### Verification

- **Same shifts as before.** A lossless 450-frame clip of FP01_Qföre (frames
  0–449) was run through the old `VideoStabilization` (before any change, at
  `55f201e`) and through the new code:
  - the same reference frames (63, 210, 27);
  - shifts bit-identical for recorded frames 0–448 (the old code's frames
    1–449);
  - enhancement identical to scipy's on 20 real frames;
  - every output frame equal to its recorded frame moved by its shift, 450
    frames, frame 0 no longer black;
  - 105 s for the old code, 40 s (88 ms a frame) for the new.
- **Tests:** 13 new tests in `tests/test_stabilize.py`. A textured scene moved
  by known sub-pixel amounts (±5 px), written losslessly, then:
  - the shifts undo the movement to within 0.5 px (largest error 0.31–0.39 px
    over 4 seeds);
  - every frame is written in its place and losslessly, at the source's frame
    rate and size;
  - the stabilized frames line up;
  - the references are the sharpest frames;
  - traced memory does not grow with the length (+0.01 MB from 30 to 150
    frames, against 2.3 MB if the frames were kept);
  - the record files; cancelling; `.avi` only; the command line;
  - the GUI job: where it files the video and its record, the trash on a
    second run, cancelling, too little disk space.

  Three bugs were planted to check that the tests catch them:
  - a wrong shift direction was caught by the line-up test;
  - keeping every frame in memory was caught by the memory test;
  - the old one-frame lag was caught by three tests.

  Suite: 225 passed (215 before, minus the 2 memory tests and the
  `Utilities` test, plus the 13 new tests). The CI's flake8 selection is
  clean, and so are the new and changed files under a full flake8 run.
- **A full recording.** FP01_Qföre (5729 frames, 191 s) was stabilized through
  the GUI's job (`gui.tasks.stabilize`) into the data folder on the Mac:
  - 537 s (94 ms a frame), with at most **278 MB** of memory (macOS
    `time -l`), against about 28 GB for the old code;
  - 5729 frames at 30 fps, 1.76 GB like the raw file, and every frame equal to
    its recorded frame moved by the shift saved in the CSV (0 of 5729 differ);
  - similarity to the frame at 30 s improved in every phase (mean, and worst
    frame in brackets):

    | Phase | Unaligned | Stabilized |
    | --- | ---: | ---: |
    | Rest | 0.972 (0.912) | 0.981 (0.955) |
    | Occlusion | 0.891 (0.851) | 0.940 (0.930) |
    | After release | 0.902 (0.836) | 0.953 (0.934) |

  - the image moved up to 11.4 px from its resting position at rest, and up to
    about 20 px during occlusion and after release, mostly vertically; the
    largest jump between two frames was 4.5 px.

### The registration's accuracy on the full recording

The CSV's first definition of `disagreement_px` removed the references'
offsets as their median over all frames. It came out above 1 px on 4069 of
5729 frames: 4.9 px (median) close to the references and about 1 px far
from them, changing smoothly from frame to frame. That pointed to a
registration bias that depends on where the image is, so 12 frames were
checked against an independent estimate:

- **The independent estimate:** a template match of the frame's centre
  (580 × 420 px) after a high-pass filter (frame minus its 10-px Gaussian
  blur), which removes the uneven lighting and does not depend on position.
- **Self-consistency.** Across the three references, the independent
  estimates agree with the references' own offsets to within about 0.8 px.
  The stabilizer's contradict each other by up to 3 px.
- **During occlusion and after release** (80–187 s) the two differ by
  2.8–5.6 px vertically: the stabilizer's correction is too small.
- **At rest** they differ by 1.3 px at most (0.4–0.9 px on most frames).
- **A third measure decided between them:** the correlation of edge strength
  (Sobel magnitude) with the reference frame, used by neither method.
  - It favours the independent alignment on all 9 frames compared:
    slightly at rest (0.558 against 0.554, for example) and clearly during
    occlusion (0.403 against 0.343 at 100 s, with 0.328 unaligned).
  - An overlay of the 100-s frame on the reference shows the capillary loop
    offset with the stabilizer's correction and overlapping with the
    independent one.

So the method, old and new alike, falls short by several pixels when the
image has moved 15–20 px from the references, and is good to about a pixel at
rest. The likely cause is the enhancement before the registration (fixed CLAHE
tiles, see above), possibly together with the circular cross-correlation of
unwindowed frames. Resting CBV (aim 1) is measured at rest, where the error is
smallest. Lines drawn for the occlusion phase would drift off a vessel by up
to 5 px.

`disagreement_px` was redefined to remove the offsets between the references
as measured on the sharpest reference, where the registration is reliable.

FP01_Qföre was then stabilized again from the command line with the committed
code (`0a1988b`), replacing the first output:
- 555 s, 275 MB at most;
- the video is unchanged, and the CSV has the new column;
- its provenance says `git_uncommitted_changes: true` only because this
  DEVLOG entry was being edited during the run.

The column now reads, as a median (90th percentile in brackets):

| Phase | Disagreement |
| --- | ---: |
| Rest | 2.1 px (3.2) |
| Occlusion | 3.5 px (4.3) |
| After release | 3.3 px (4.0) |

It is highest where the shift falls shortest. It is also well above 1 px at
rest: there the estimate against the reference that lies 9 px from the other
two (frame 463) is off by up to about 1.8 px. That is still about 1 px in the
mean shift, as found above. Until the registration is fixed, the column shows
how unreliable it is rather than singling out a few bad frames.

### Also found: a video stabilized with the old code

At 10:50 the app, started at 10:27 and still running, stabilized
`FP01_Qefter_försök2_22-Oct-2019_09-50-15` with the old code. That output is
FMP4 (lossy), 33 MB, with a black frame 0. The app was started before the
memory check got its macOS fallback, so nothing stopped the run (about 25 GB
asked of an 8 GB Mac). It is still in `StabilizedVideos/`: stabilizing it
again in a restarted app moves it to the trash.

### Open

- **The registration's accuracy (above):** the next step. Use a translation-
  invariant enhancement (such as a high-pass filter instead of fixed CLAHE
  tiles) and a windowed or non-circular correlation. Check it with the three
  measures used here: an independent estimate, self-consistency across the
  references, and edge similarity. Add synthetic tests with moves of 15–20 px.
- Speed: about 88 ms a frame (about 8 minutes for a 3-minute recording),
  mostly the three registrations per frame with their 2 × upsampled
  cross-correlation. Computing the references' FFTs once would save part of
  it.
- On the desktop: run the tests there, since the uncompressed grey writer was
  checked only with OpenCV 5.0 on macOS. Check the codec of the 8 old
  stabilized videos.
- Lines drawn on an old stabilized video may not fit a newly stabilized one
  (different reference frames, and the one-frame shift is gone).

---

## 2026-10-08 — First run on macOS with the downloaded study recordings

**Branch:** `fix/macos-tk9`, from `main` at `f9e0917`.

**Commits:**

- `a71f270` Run on macOS with Tk 9: clamp canvas text widths, memory guard without /proc

The user downloaded 9 raw ESMOKE recordings from DynCap into
`Video_inventory/` (untracked) on a new computer, a MacBook with an Apple M2
and 8 GB of memory, and asked whether the program works with them. Until now
the app had only run under WSL on Windows.

### The recordings

All 9 open with OpenCV 5.0: 640 × 480, 8-bit grey stored uncompressed (no
FourCC, 307 200 bytes a frame), stamped 30 fps, 4528–7524 frames (151–251 s).
They are raw, not stabilized. All 9 are in `metadata/ESMOKE_timestamps.csv`,
and each official release falls well inside the video at 30 fps, so the
frame-rate mismatch of `FP01_Wefter_14-Oct-2019_10-07-49` does not show here.
`FP03_Wefter_21-Oct-2019_10-21-58` has no release time.

| Recording | Frames | Length at 30 fps (s) | Occlusion (s) | Release (s) |
| --- | ---: | ---: | ---: | ---: |
| `FP01_Qefter_försök2_22-Oct-2019_09-50-15` | 5102 | 170.1 | 65.9 | 125.7 |
| `FP01_Qföre_22-Oct-2019_08-16-35` | 5729 | 191.0 | 68.3 | 130.5 |
| `FP01_W_14-Oct-2019_08-36-26` | 4528 | 150.9 | 37.6 | 102.3 |
| `FP01_Wefter_14-Oct-2019_10-13-03` | 7524 | 250.8 | 62.5 | 147.4 |
| `FP02_Wföre_15-Oct-2019_08-29-10` | 5765 | 192.2 | 72.9 | 130.1 |
| `FP03_Qefter_försök2_15-Oct-2019_11-06-33` | 5746 | 191.5 | 60.0 | 134.9 |
| `FP03_Qföre_15-Oct-2019_09-15-49` | 5220 | 174.0 | 60.5 | 123.3 |
| `FP03_Wefter_21-Oct-2019_10-21-58` | 6102 | 203.4 | 74.7 | — |
| `FP03_Wföre_21-Oct-2019_08-58-40` | 5819 | 194.0 | 72.0 | 133.0 |

To avoid copying 16 GB, `RecordedVideos/` holds symbolic links to the files in
`Video_inventory/`; the library follows them. A raw recording without a
stabilized copy is analysed as it is (`Recording.video`).

### Setup on macOS

Homebrew's Python had no Tk. `brew install python-tk@3.12`, then a `venv/`
from Python 3.12 with `requirements.txt` and pytest (numpy 2.5, OpenCV 5.0,
SciPy 1.18, Tk 9.1). `settings.csv` points the data folder at the repository.

### Fixes

- **Crash on start under Tk 9.** The overlay hint on the video is drawn
  before the canvas is laid out, when its width is 1 px, so its wrap width
  `width - 60 px` was negative. Tk 8.6 (WSL) accepted that; Tk 9.1 raises
  `TclError: expected screen distance but got "-59"`. The same arithmetic was
  in the empty recording list and the reading view's message. All three are
  now at least 1 (`gui/video_view.py`, `gui/library_view.py`,
  `gui/reading_view.py`).
- **The stabilization memory guard was off on macOS.** It read only
  `/proc/meminfo`, which macOS does not have, and treated memory as unknown.
  Stabilizing one of these recordings needs about 28 GB (two float64 copies),
  more than three times this computer's memory. `available_memory_bytes` now
  falls back to the total physical memory (`os.sysconf`), so the app refuses
  instead of swapping or crashing. These recordings cannot be stabilized on
  this computer with the current stabilizer.

### Verification

- `python -m pytest`: 215 passed (213 before, plus the 2 new tests in
  `tests/test_stabilization_memory.py`: the memory is known on this platform,
  and a 5729-frame recording is refused at 8 GB with "28.2 GB").
- The app starts and stays up with the 9 recordings listed (it crashed on
  start before the fix).
- The batch CLI read 450 frames of the raw `FP01_Qföre` with an arbitrary
  3-point line (126.5 px) without errors; 0 of 25 blocks resolved, as expected
  for resting flow on a line that does not follow a capillary.

---

## 2026-10-07 — Official occlusion and release times added; the "slow flow" was the occlusion

**Branch:** `data/occlusion-times`, from `main` at `bb597e2`.

**Commits:**

- `3fbfd6d` Add the official occlusion and release times of the ESMOKE and ISMOKE recordings

The user shared the study progress report of the degree project, which the
repository's `Thesis/report_draft.tex` (July) predates. The report covers:

- **Data:** a retrospective archive of two crossover trials, stored in DynCap.
  - ESMOKE: W = e-cigarette with nicotine, Q = without nicotine.
  - ISMOKE: S = heated tobacco, C = no exposure.
- **Recordings:** each visit has one before (före) and one after (efter) the
  exposure.
- **Aims:** aim 1 is the inter-day reproducibility of resting capillary blood cell
  velocity from the two före recordings; aim 2 is the acute effect.
- **Protocol:** every recording holds about 1 min of rest, 1 min of occlusion at
  200 mmHg, and about 1 min after release.

The user then provided the "official times" of occlusion and release, exported
from DynCap.

### The data (`metadata/`)

`ESMOKE_timestamps.csv` and `ISMOKE_timestamps.csv` are kept exactly as
provided: semicolon-separated, UTF-8, columns `subject`, `occlusion`,
`release` (seconds from the start of the video) and `source_file` (the
recording's stem). A check with pandas:

- 74 + 50 recordings, 17 + 13 participants, no duplicate file names;
- 16 recordings without a release time;
- occlusion at a median 60.3 s, lasting a median 61.2 s (47.5–93.8 s);
- all 8 recordings in the local `StabilizedVideos/` are covered.

`metadata/README.md` lists the rows that differ from the pattern. Two of them:

- **`FP01_Wefter_14-Oct-2019_10-07-49`:** occlusion at 158.5 s and release at
  230.1 s, but the local video has 3435 frames: 114.5 s at the stamped 30 fps,
  and 229 s at 15 fps. Either the times use another origin, or this
  recording's true frame rate is 15 fps. A crude measure of blood movement in
  the vessels, frame to frame, was too noisy to decide. Check in DynCap.
- `FP21Wföre_…` has no underscore after the code.

### Correction: the "slow flow" of 2026-10-06 was the occlusion

The centre line along the FP01_Qföre limb (145 px) was measured over the
whole recording instead of 63–94 s. Resolved 3-s blocks per 10-s window, and
the official times:

| Window (s) | Resolved | Median (mm/s) | Phase (official 68.3 / 130.5 s) |
| --- | --- | --- | --- |
| 0–70 | 0 of 105 | – | rest |
| 70–80 | 6 of 15 | +0.017 | occlusion |
| 80–90 | 14 of 15 | +0.012 | occlusion |
| 90–100 | 15 of 15 | +0.005 | occlusion |
| 100–130 | 16 of 45 | +0.009 to −0.007 | occlusion |
| 130–190 | 3 of 90 | – (one block at +0.247) | after release |

Space-time pictures of 5-s stretches show what happens in each phase:

- **Occlusion:** the steep, curving streaks of slow, decelerating flow.
- **Rest:** faint, almost horizontal streaks; the pattern crosses the line in a
  few frames, roughly 0.5–1 mm/s.
- **After release:** crisp, almost horizontal streaks, faster still.

A crude measure of blood movement in the vessels jumps at 130 s, at the
official release. Comparing each row with the next found no pattern moving
within ±60 px at rest: the best match was always at zero shift, with weak
correlation (r = 0.06–0.19).

So the "slow flow, 0.01–0.04 mm/s" reported on 2026-10-06, and its reading
that "slow flow is expected with this protocol", describe the occlusion. That
holds for the 63–94-s stretch of the before limb, and the after-loop stretch
(47.8–77.8 s) straddles rest and occlusion. At rest and after release the
flow is faster than the centre line can measure at 30 fps: about 0.26 mm/s
for this line, from the Fourier limit |ω| ≤ 0.45 cycles/frame.

**Aim 1 needs resting CBV, so a fast-flow estimator is now the main open
item.** The streaks at rest are motion-blurred and continuous, so fitting their
slope in the image itself (Radon or Hough in the time domain) should work
while a streak still spans about 3 frames. Longer lines would help further.

### Correction: who recorded the videos

The Capture-removal entry (below) said the 2019 recordings were "most likely"
made with this app's recorder, because of their names. That evidence was
circular: the rebuilt recorder had been written to reproduce the archive's
names. The recordings were archived in DynCap, so its format (green-weighted
grey, MP4V, 30-fps stamp) need not describe them. Their frame rate remains
unverified (see `FP01_Wefter…10-07-49` above).

**Documentation:**

- `CLAUDE.md` gains a short "The study" section and the `metadata/` folder,
  and puts "resting flow is beyond the centre line's range" first among the
  known issues. Its frame-rate note no longer mentions the recorder, and it
  marks `Thesis/` as outdated.
- `README.md` lists `metadata/`.

**Verification:** both files parse as described above. The check scripts are
not in the repository. No code changed.

---

## 2026-10-07 — Capture page removed: the app no longer records

**Branch:** `refactor/remove-capture`, from `main` at `a6b367c` (after pull
request #7 was merged).

**Commits:**

- `3832afa` Remove the Capture page: the app no longer records
- `80eaab6` Update README and CLAUDE.md for the app without recording

The user asked what the Capture page was for and whether it could go. It
showed the microscope camera's live image and recorded into `RecordedVideos/`
under names like `FP03_Wföre_07-Oct-2026_14-03-22.avi` (participant and
condition, date, time), with time points marked during the recording. The
program began as the recording station for the capillaroscope: it has had a
recorder since its first commit. The 2019 recordings carry exactly the names
it produced, so they were most likely recorded with an earlier version of it.
The computer the app now runs on has no camera, and the user confirmed that no
new recordings for the thesis will be made with this app.

**How the recorder wrote videos.** This is kept here because it probably
describes how the 2019 recordings were made, which the data-acquisition
section of the thesis needs. `gui/camera.py` said it wrote "as before":

- every camera frame turned into one green-weighted grey image,
  (−0.5·R + 1.5·G + 127.5) / 2 (`Utilities.rgb_to_negR_posG`), because
  capillaries contrast best in green;
- written as three identical channels with the MP4V codec (MPEG-4 Part 2,
  lossy) into an `.avi`;
- every file stamped 30 fps, whatever the camera delivered. The rebuilt page
  warned when the measured rate differed by more than 5%.

The thesis draft says the recordings were stored losslessly. If they came from
this recorder they were not, and their true frame rate is unknown. Both are
open points (CLAUDE.md, known issues).

**Removed:**

- `gui/capture_page.py` and `gui/camera.py` (471 lines);
- the recording-name helpers in `gui/tasks.py` (`recording_name`,
  `new_recording_path`) and their two tests;
- `Utilities.rgb_to_negR_posG`;
- the record, stop and camera icons and the Record button style.

**Changed:**

- The logo colour (the red capillary loop in the header) is renamed from
  `record` to `brand`.
- Messages that pointed to the Capture page now say to copy videos into
  `RecordedVideos/` (raw, to be stabilized) or `StabilizedVideos/`.
- The pages are Ctrl+1–4: Centre line, Two boxes, Results, Validation.
- `RecordedVideos/` stays: raw videos copied there can still be stabilized.
- The module list in `gui/__init__.py` also gained the two Validation modules
  added earlier today.

**Verification:**

- 213 tests pass (215 before, less the two recording-name tests).
- pyflakes reports only the two old notes, and the CI flake8 selection is
  clean.
- Scripted GUI session: four tabs, Ctrl+1–4 open the right pages, Ctrl+5 does
  nothing, F1 lists Ctrl+1…4, the app shuts down cleanly, and there were no Tk
  errors.

**A mistake while starting this branch (no code).** Switching to the old
`main` and then updating to the new one deleted the local `settings.csv`.

- The old `main` still tracked the file, so checking it out replaced the
  ignored local copy with the tracked one.
- The new `main` untracks it, so fast-forwarding removed it.

It was restored byte for byte: the last tracked version plus the two rows the
app had added (`box_size,12` and `observer,1`), and the app reads it back.
After a commit stops tracking a file, back it up before checking out anything
older.

---

## 2026-10-07 — Pull requests #5 and #6 merged; `settings.csv` and `Validation/` no longer tracked

**Branch:** `chore/untrack-local-data`, from `main` at `2186904`.

**Merged.** The user merged #5 (`feat/centreline-velocity`, the centre-line
method) and #6 (`feat/observer-validation`, the Validation page) on GitHub,
both with merge commits, and GitHub deleted the two branches. Locally, `main`
was fast-forwarded to `2186904`. Every local branch already merged into it
was deleted (`git branch -d`, which refuses unmerged ones):
`feat/centreline-velocity`, `feat/observer-validation`, `feat/gui-rebuild`,
`refactor/remove-dead-code` and `refactor/remove-optical-flow`. The 215 tests
pass on `main`.

**Untracked.** The user's first try of the Validation page on the real data
worked: a reading set of 6 blocks from `set1` of `FP01_Qefter`, read by
observer "1" (5 with streaks, 1 without), and the agreement computed, with no
errors in the log. It also showed two things in `git status`:

1. **`Validation/`** was not in `.gitignore`, unlike the other data folders,
   so reading sets showed up as files to commit. It is now ignored.
2. **`settings.csv`** was tracked, although the app rewrites it: the data
   folder, the calibration, the box size (since the 2026-10-05 rebuild) and,
   since today, the observer. It therefore always showed as modified, and the
   tracked copy only held this computer's path. The user chose to stop
   tracking it. It is removed from the index (the local file stays as it is)
   and ignored.
   - A fresh copy of the repository has no `settings.csv`, so the app's
     welcome dialog asks for the data folder and calibration.
   - `python -m capillary.cli` then uses the default calibration unless
     `--mm-per-pixel` is given.
   - On another computer with a copy, pulling this change removes its
     `settings.csv` once.

**Verification:** the 215 tests pass. `git check-ignore` confirms both paths
are ignored, `git status` no longer lists them, and the local `settings.csv`
is unchanged.

---

## 2026-10-07 — Validation on real recordings: blinded reading by observers, and line placement

**Branch:** `feat/observer-validation`, from `feat/centreline-velocity` at
`c56d495`. That branch's pull request was not merged yet; once it is, the pull
request of this branch shows only the commits below.

**Commits:**

- `1a3c78b` Validation page: observers read space-time blocks blinded; agreement with the estimator
- `42a99b6` Line placement: the same capillary measured by different observers
- `cc4e66c` Update README and CLAUDE.md for the Validation page
- `67d4e56` Move the Validation page's reading mode into gui/reading_view.py

The user asked to keep building. Of the open items (validation on real data,
a null control for jitter near stasis, pairing before/after recordings,
calibration and frame rate) they chose validation on real data. The benchmark
of 2026-10-06 shows the centre line is accurate on synthetic recordings, but a
real recording has no ground truth. The thesis needs evidence on real data for
two questions:

1. Does the estimator read the slope a person reads from the same space-time
   diagram? Reading the slope of the streaks by hand is how line-shift
   diagrams have been read in capillaroscopy (Cap-Image), so it is the natural
   reference.
2. How much does a velocity depend on who measures it, that is on where the
   line is drawn (inter- and intra-observer reproducibility of the whole
   measurement)?

The Validation page (Ctrl+5) does both. Nothing has been read on the real
data yet; everything below was tested with simulated observers.

### Blinded reading (`capillary/validation.py`)

- **What is read.** Exactly the 3-s blocks (90 frames) the estimator
  measures: rows `start … start + 89` of a saved space-time diagram, `start`
  one of the estimator's block starts (every 15 frames). Blocks drawn from one
  data set never overlap (starts at least 90 frames apart), so no two items
  share frames.
- **How blocks are drawn.** From each chosen centre-line data set, *k* blocks
  (default 6) at random. By default balanced: ⌈k/2⌉ from the blocks the
  estimator resolved and the rest from unresolved ones, either kind making up
  a shortage of the other. Agreement on velocity needs resolved blocks;
  agreement on whether a block can be read at all needs both kinds. The seed
  is recorded (default from the system's random source); the same seed and
  data sets draw the same set (tested).
- **Frozen.** The blocks are copied (float32) into
  `Validation/<set>/blocks.npz`; `set.json` records for each its recording,
  data set, rows, video frames, fps, calibration and the estimate when drawn.
  Measuring a data set again or deleting it does not change the set. Item
  numbers are given in a random order, so they say nothing about the source.
- **Blinding.** An observer sees "Block 12 of 60", the block and their own
  lines: not the recording, the data set or the estimate. Every observer and
  session gets its own order (a shuffle seeded by the set's seed, the
  observer's code and the session; reproducible, different for each).
- **Display.** The block with the mean of every position over time and the
  mean of every frame along the line removed (still structure and changes of
  the whole line at once, as in the preview and the report), contrast from the
  1st to the 99th percentile, position along the line across (first point on
  the left), time downwards. One pixel along the line is drawn as wide as one
  frame is tall, so a streak at 45° is 1 px/frame. The scale depends only on
  the block's size, never on the estimate.
- **Reading.** The observer drags lines along streaks (the instructions say
  two or three); the block's slope is the mean of the lines' slopes,
  Δposition/Δframe. A line spanning fewer than 4 frames is refused (too flat in
  time to give a slope; on a 120-px line that is over 30 px/frame, far beyond
  what can be measured). Or "No clear streaks" (N). Lines are stored in block
  coordinates, with the time spent on each block (time away from the page not
  counted). Everything is saved after every change (the JSON is written to a
  temporary file and moved into place), so a session can stop and continue.
- **Sessions.** A second session by the same observer, some days later and in
  a new order, gives the repeatability of one person's reading.

### Statistics (`capillary/agreement.py`)

Velocities in mm/s (slope × fps × mm/px of the source data set); differences
are first minus second.

- **Bland–Altman** (Bland & Altman, Lancet 1986; Stat Methods Med Res 1999):
  bias with its 95% confidence interval (t, SE s/√n); 95% limits of agreement,
  bias ± 1.96 SD, each with an approximate 95% interval (SE √(3s²/n));
  proportional bias as the slope of the differences on the means, with its
  95% interval. The same on a log scale, as ratios (pairs of the same sign,
  magnitudes compared): geometric-mean ratio and ratio limits. Velocities span
  an order of magnitude, so differences are likely to grow with velocity; the
  page then says to read the ratio limits.
- **ICC** (McGraw & Wong, Psychol Methods 1996): two-way model, single
  measurement, absolute agreement ICC(A,1) (= Shrout & Fleiss ICC(2,1)) and
  consistency ICC(C,1) (= ICC(3,1)), with their F-distribution intervals.
- **Same direction**: share of pairs with the same sign.
- **Readability**: Cohen's kappa (yes = a velocity: the estimator resolved
  the block, or the observer drew lines), large-sample interval cut at ±1, and
  the 2×2 counts.
- **Within an observer**: repeatability coefficient 1.96 × SD of the
  differences (= 2.77 × the within-subject SD).

Checks of the arithmetic:

- Shrout & Fleiss (Psychol Bull 1979) table 2, six targets by four judges:
  ICC(2,1) = 0.290 and ICC(3,1) = 0.715, the paper's 0.29 and 0.71. The
  intervals, 0.019–0.761 and 0.342–0.946, match the values I remember R's
  psych::ICC reporting for this table; confirm with R before citing them.
- Bland–Altman and kappa against values worked by hand (in the tests).
- Coverage of the 95% intervals in 2000 simulations each (scratch script, not
  in the repository): ICC(C,1) 94–95%. ICC(A,1) 93% (n = 20) and 96% (n = 40)
  with two raters, but 90% with three raters and a large rater effect. That is
  a known weakness of this approximate interval when there are few raters, not
  a bug: the point values and the published example match. Bland–Altman bias
  95%; upper limit 93.5% (n = 20), 95% (n = 50), the approximate limit
  interval being slightly narrow for small n. Kappa 94%.

### The comparisons

The agreement report measures every block again with the current estimator,
from the frozen blocks, so it always reflects the code that runs (the
estimate when drawn is kept in `set.json`). It compares:

- the estimator against every reading;
- the estimator against the mean of the observers' first sessions, on blocks
  where all of them drew lines (for readability: yes where all drew lines, no
  where none did, left out where they disagree);
- the observers' first sessions pairwise and, with three or more observers,
  the ICC of all of them;
- each observer's first session against each later one.

Written to `Validation/<set>/report/`: `agreement_items.csv` (one row per
block: source, the estimate, every reading), `agreement_summary.csv` (one row
per comparison, every statistic above), `readings.csv` (per reading: blocks
read, with streaks, no clear streaks, median seconds per block),
`bland_altman.png` and `scatter.png`.

Caution for reading the results: the Bland–Altman comparison of estimator and
observer uses only blocks the estimator resolved and the observer read, a
sample selected by both. The readability counts and kappa describe the rest.

### Line placement (`capillary/placement.py`)

- **Observer.** The measure pages have an Observer field (initials) next to
  the data set name, shared with the reading dialog and remembered in
  `settings.csv` (`observer`). It is saved in every new data set's provenance
  (`observer`), and the Results page shows it ("by SJ"). Older data sets have
  none.
- **Matching.** Two centre-line data sets measure the same capillary if they
  are on the same recording, at least half of one line lies within 5 px of
  the other (lines sampled every pixel), and their frame ranges share at least
  80% of the frames either covers. A line drawn the other way round is
  compared with its sign reversed (the tangents where the lines meet decide).
  Connected matches form one capillary.
- **Comparison.** Per capillary, each observer's first data set and their
  second, if any. The median velocities are compared between every two
  observers (and all of them with three or more) and between an observer's
  first and second measurement, with the same statistics. Data sets without
  an observer are listed but take part in no comparison. Written to
  `Validation/line_placement/` (`measurements.csv`, `capillaries.csv`,
  `summary.csv`, the plots); the name `line_placement` is reserved and cannot
  be used for a reading set.

### The app

- **Validation page.** The left column holds "Line placement" and the reading
  sets (**New…** draws one). A reading set shows its readings (observer,
  session, blocks read, no clear streaks, last saved; Continue / Look
  through), **Start reading…** (observer and session, with the next session
  suggested), the agreement (two tables: velocity, then readability; Bland–
  Altman and scatter plots, which open full size on click) and the data sets
  it was drawn from.
- **Reading mode** fills the page: the block on the left; on the right the
  observer and session, block *n* of *N*, progress, instructions, **No clear
  streaks**, **Remove lines**, **Next block** (Enter or →), **Previous** (←),
  **Finish later** (Esc). Backspace removes the last line. F1 lists the keys.
  Leaving the page keeps the reading open.
- `Caper.generate_validation_report` draws the plots; `gui/tasks.py` has the
  background jobs; the reading mode is `gui/reading_view.py`.

### Verification

- **Unit tests:** 215 pass (184 before). `test_agreement.py` 10 (Shrout &
  Fleiss, hand-worked Bland–Altman and kappa, proportional bias found and
  removed on the ratio scale, missing values, too few pairs).
  `test_validation.py` 13: synthetic centre-line data sets with flow at 1.0
  and 0.4 px/frame and without flow; blocks identical to the data set's rows;
  the saved estimate equal to the one computed again; seeding; name rules;
  orders per observer and session; saving and resuming; simulated observers
  (5% scatter, no streaks without flow) giving bias near 0, ICC > 0.8 and
  kappa 1; three observers; report files. `test_placement.py` 6: overlap and
  direction of lines, frame overlap, grouping with reversed lines, the
  comparisons (an observer reading 10% higher gives ratio limits of exactly
  1.1), the report from saved provenance. Two in `test_gui_logic.py`: the
  reading canvas's coordinates both ways; the image observers see (no still
  structure or same-moment change left). `test_line_tasks.py` checks that the
  observer is saved.
- **Lint and imports:** pyflakes reports only the two old notes; the CI
  flake8 selection is clean; the venv was not touched.
- **Scripted GUI sessions** on a scratch data folder (links to the real
  videos, copies of the data sets), the windows never taking keyboard focus.
  Three centre-line data sets on real capillaries were measured first:
  - the before limb (`FP01_Qföre`, 145 px, frames 1909–2808): 33 of 55
    blocks resolved, median 0.0138 mm/s;
  - a line through tissue 25 px beside it: 0 of 55;
  - the after loop's left limb (`FP01_Qefter`, 126 px, frames 1435–2334): 5 of
    55, 0.0081 mm/s.

  These match 2026-10-06. Then:
  - a reading set of 18 blocks drawn through the dialog;
  - reading with every control: Next with nothing drawn (refused), too flat a
    line (refused), three lines, right-click removal, Backspace, Previous,
    switching pages and back (the reading stays open), Esc and Continue;
  - three complete readings (SJ ×2, AB) by a simulated observer that draws
    the estimator's own slope with 8% scatter;
  - the agreement report and its plots, F1;
  - the Observer field (lower case saved as upper case, an invalid code
    blocks Measure, both pages share it), "by SJ" on the Results page;
  - Line placement on seven more data sets by two pretend observers. All
    groups were found correctly: three capillaries, the reversed line, the
    tissue line kept apart, data sets without an observer listed but not
    compared.

  Screenshots were reviewed; no Tk errors. The agreement table was first
  wider than the page (kappa cut off) and was split in two, with intervals on
  a second line.

### What the real blocks look like (pilot, not a study)

A contact sheet of the 18 pilot blocks, as observers see them, with the
estimate overlaid (scratch only):

- **Before limb.** The resolved blocks show clear diagonal streaks, and the
  estimated slope runs parallel to them by eye. Some unresolved blocks also
  show faint streaks; this is the disagreement the study will measure.
- **After limb.** Blotches and sudden jumps (whole-line shifts between frames)
  and hardly any visible streak, consistent with 9% resolved. Observers will
  mostly answer "no clear streaks" there.
- **Tissue line.** Noise, plus the edge of a vessel it crosses; usable as
  negative controls if wanted.
- **Line placement on the before limb.** Two lines with different click
  spacing and up to 1.5 px off the middle gave 0.0137 and 0.0138 mm/s; a third
  drawn the other way gave −0.0140 (matched, sign reversed). These lines came
  from the same extracted skeleton, so this says little about real observers.

### Limitations and next steps

- **No real reading yet.** The readings in the checks were simulated from the
  estimator's own slopes; they test the mechanics, not the method.
- **Suggested protocol (to agree with the supervisors):**
  1. Choose capillaries with visible flow, about 2 per recording, and measure
     each over the whole recording with the Observer field filled.
  2. Draw a reading set (6 blocks per data set, balanced).
  3. Two observers read session 1 independently; one reads session 2 at
     least a week later.
  4. For line placement, a second observer measures the same capillaries
     over the same frames without seeing the first observer's line. They
     identify the capillary from a frame with an arrow, not from the line.
  5. Compute the agreement.
- **Sample size.** Bland & Altman suggest about 100 pairs for precise limits;
  15–30 capillaries give wide ICC intervals.
- **Display.** Fixed (cleaned, percentile contrast); observers cannot change
  the contrast. A control could be added if blocks are too faint, but it would
  have to be recorded.
- **Slow flow.** At 0.2 px/frame a 3-s block shows streaks moving only about
  18 px over its 90 frames: readable, but shallow.
- **References.** Bland & Altman 1986 and 1999, McGraw & Wong 1996, Shrout &
  Fleiss 1979 and Cohen 1960 need checking before they go into the thesis, as
  do Drew 2010 and Klyscz 1997 from 2026-10-06.

---

## 2026-10-06 — Velocity along a centre line (space-time diagram), validated on calibrated synthetic recordings

**Branch:** `feat/centreline-velocity`, from `main` at `bbec82a` (after the
optical-flow removal was merged as pull request #4).

**Commits:**

- `43cc549` Add the centre-line velocity estimator, a calibrated simulator and a benchmark
- `0cef0c3` Centre line page: draw a line along a capillary and measure its velocity
- `5c4e5b3` Update README and CLAUDE.md for the centre-line method

The user asked to work on the velocity estimator. Before changing anything,
the existing method was measured on the real recordings. The findings changed
the plan from "refine the two-box method" to "measure along the vessel", and
the user chose: first a benchmark, then a centre-line method.

### What the two-box method measures on real capillaries

All of this was read-only analysis with scripts outside the repository.

1. **`set1` measured tissue, not blood.** The only data set with recorded box
   positions (`FP01_Wefter_14-Oct-2019_10-13-03___set1`, made while trying out
   the new GUI on 2026-10-05) has its boxes at (433, 316) and (463, 290), about
   25 px to the right of the nearest capillary, in still tissue. A map of
   frame-to-frame variation and a space-time diagram between the boxes show
   no movement there. Its result (median −0.02 mm/s, 37% lag 0, 36% positive)
   is noise and should not be used.
2. **On a real capillary the flow is visible and slow.** The centre line of
   the tall loop in `FP01_Qefter_22-Oct-2019_09-46-17` ("after", frames
   1435–2334) and `FP01_Qföre_22-Oct-2019_08-16-35` ("before", frames
   1909–2808) was extracted from the mean image (vessel darker than the local
   background, thinned to a skeleton). Space-time diagrams along it show red
   cells and plasma gaps as slanted streaks of about 0.2–1 px/frame, roughly
   0.01–0.04 mm/s. The user confirmed that slow flow is expected with this
   protocol.
3. **Brightness changes along the whole vessel at once dominate.** Along the
   limbs, the part of the signal that is the same at every position at the
   same moment has a standard deviation of 3.1–6.3 grey levels, nearly the same
   all along the vessel (gain 1.00 ± 0.14 after, ± 0.41 before). It makes up
   71–73% (median) of the variance of a 12-px stretch, the size of a box, in
   both recordings. The likely cause is small movements of the vessel or
   focus; the per-pixel sensor noise is 3.05 grey levels.
4. **That is why the boxes find a lag of 0.** Two boxes 30 px apart on the
   after loop's left limb gave lag 0 in 44 of 70 windows, which the report
   calls "too fast to resolve", although the flow is slow. Subtracting the
   limb's mean brightness removed the lag-0 peak; lags of −19/−20 frames
   appeared (consistent with the streaks), but the estimates stayed scattered.
5. **Consequences for the earlier plan.** Rounding the lag to whole frames
   costs only 2–5% here, since the true lags are 20–70 frames. Treating lag 0
   as "faster than measurable" (an item on the plan) would have turned the
   same-moment changes into high velocities. "Too fast to resolve" in existing
   two-box reports should not be read as fast flow.

### The method (`capillary/spacetime.py`)

The user clicks points along the middle of one capillary, from where the blood
comes from to where it goes. The line is the uniform Catmull-Rom curve through
the points, sampled every pixel of arc length. In every frame the brightness
at 5 points across the line (±2 px along the normal, bilinear) is averaged;
the rows stacked over time form the space-time diagram. A pattern moving
along the vessel at `v` px/frame draws streaks of slope `v` and puts all its
power on the line `ω = −v·k` of the diagram's 2-D power spectrum (`k` in
cycles/px, `ω` in cycles/frame). Velocity = `v` × fps × mm/px, positive from
the first point towards the last.

The slope is estimated in blocks of 90 frames (3 s), every 15 frames:

1. Remove the time mean of every position (still structure) and the position
   mean of every frame (a same-moment change of the whole line).
2. Difference the block along the line (whitening, see below), apply Hann
   windows in space and time, and Fourier-transform along the line; keep
   patterns from 3 cycles per line length up to 0.3 cycles/px.
3. For candidate speeds ±0.05 to 30 px/frame (400 log-spaced, then 41 around
   the best), evaluate exactly (a direct transform in time at arbitrary
   frequency) the power at `ω = −v·k` and at the mirror `ω = +v·k`. Each
   pattern counts with weight 1 up to |ω| = 0.3 cycles/frame, fading (cos²) to
   0 at 0.45 (the unaliased part of its line). The score is the weighted mean
   of forward minus mirror power; the speed is the best score.
4. Quality: the signal-to-noise ratio is the weighted forward-minus-mirror
   power over its spread under "no flow", from a noise floor estimated locally
   (median power within ±5 temporal-frequency bins of both signs, ÷ ln 2). The
   coherence is the share of the block's energy (in the patterns used) on the
   chosen line, 1 for a clean pattern at one speed.
5. A block is resolved if the signal-to-noise ratio is at least 8, the
   coherence at least 0.03, and the speed lies in the measurable range. The
   slowest speed is 1.5 cycles of the finest pattern per block. The fastest is
   0.65 × the speed at which the unaliased patterns weigh three full patterns;
   at 30 fps that is about 0.045 × line length px/frame. Finally, if any speed
   beyond that range, scored on whatever unaliased patterns it has, beats the
   chosen one, the block is flagged "faster than measurable".

The core is the Radon-transform velocity method for space-time images (Drew
et al., J Comput Neurosci 2010;29:5–11), evaluated through the Fourier slice
theorem. The space-time ("line-shift") diagram itself is established in
capillaroscopy: Cap-Image (Klyscz et al., Biomed Tech 1997) has the user read
the slope. Both references need checking before they go into the thesis. The
direction contrast is the addition that matters for these recordings: noise,
still structure and any change that is a shape along the line times a time
course (the same-moment change, unevenly strong) have a spectrum symmetric in
`ω`, so they cancel in forward-minus-mirror, while flow does not.

### How the design was arrived at

Each choice was tested on synthetic space-time diagrams first (a moving
pattern plus the same-moment change, its unevenness, jitter along the line and
noise, at the measured levels), then on the video-level simulator below.

- **Direction contrast works where the boxes fail.** On the same synthetic
  diagrams two boxes 30 px apart gave lag 0 in 61–100% of windows at
  0.25–4 px/frame; the centre line measured them within 3%.
- **Bias −2 to −3%.** Reading the spectrum by interpolation was ruled out (an
  exact transform kept the bias). The cause is the spatial window: cell
  patterns have more power at coarse scales, and leakage into finer patterns
  reads as slower. Differencing along the line flattens the spectrum: bias
  within ±1.7%.
- **Quality score.** A first z-score was capped by the number of patterns
  (flow 3–5, no flow up to 3.6) and was dropped. The signal-to-noise ratio
  against a noise floor separates them (no flow at most 6.1, flow 9 to several
  hundred), hence the threshold of 8.
- **Aliased lines** (letting fast speeds use patterns past the Nyquist limit,
  wrapped) were tested and dropped: worse with motion blur and weak cells.
- **Speed limit.** With a hard cut-off, wrong estimates clustered at the
  speeds where one more pattern became unaliased (5.0, 6.0, 6.75, 7.7 px/frame
  on a 120-px line); the cos² fade removed that. Single blocks stay within 10%
  of the truth in all but 0–7% of cases up to about 0.6 of the limit (5 px/frame
  on a 120-px line), but 19–25% at 7–8 px/frame, hence reporting only up to
  0.65 of the limit.
- **Flow faster than the line can follow** (15 px/frame on a 120-px line)
  came back as −4.4 px/frame with a signal-to-noise ratio of 10 and was
  counted as resolved; the "faster than measurable" check fixes that. Raising
  the coherence threshold to 0.05 would also have caught it, but would also
  have dropped real flow (before limb: 57% → 49% of blocks resolved).
- **Jitter.** With a global noise floor, blocks without flow but with jitter
  were resolved as slow flow (about 0.2 px/frame) in 29% (measured
  disturbances) and 74% (strong) of cases. Jitter crowds the slow temporal
  frequencies; the local floor brought this to 7% and 11%.
- **Coherence threshold.** 0.03 and 0.05 gave identical results on the
  simulations; 0.05 dropped real resolved blocks, so 0.03 (no-flow coherence
  is about 0.015–0.02).

### Synthetic recordings (`capillary/simulate.py`)

A capillary loop (limbs 150 px, 26 px apart, 10 px wide, the limbs leaning a
little) on a textured background, with red cells of about 6 px following each
other closely and a plasma gap of 6–30 px after 10% of them. The pattern moves
along the loop at a set speed (optionally pulsing with a 1.1 Hz heart beat) and
is averaged over the distance it moves while the shutter is open (motion
blur). On top: a same-moment darkening of the whole vessel (Ornstein-Uhlenbeck,
τ = 8 frames, plus a 1.1 Hz component), uneven along the vessel; whole-image
jitter (τ = 4 frames, SD 0.3 px); optical blur (σ 1.2 px); noise. Calibrated
against the two real limbs:

| Measure (same method for both) | Real | Simulated |
| --- | ---: | ---: |
| sensor noise per pixel (grey levels) | 3.05 | 3.03 |
| same-moment change, SD along the line | 3.1–6.3 | 5.2 |
| its unevenness along the line (gain SD) | 0.14–0.41 | 0.13 |
| everything else, SD | 2.8–5.0 | 4.0 |
| same-moment share of a 12-px stretch | 71% | 70% |
| vessel darker than local background | ~10 | 13 |

The simulator reproduces the box failure: two boxes 30 px apart see lag 0 in
at least half the windows where the true lag is 30 frames (pinned by a test).

### Benchmark (`python -m capillary.benchmark`)

Each case renders a loop and measures it twice, as the app would: two 12-px
boxes 30 px apart through the two-box report arithmetic (`analyze_trace`,
windows 201–301 frames), and a 120-px line clicked every 15 px up to 1 px off
the centre through `capillary.spacetime`. Medians over 3 seeds of 30-s clips
(30 fps, 1.329 µm/px; the line can measure 0.002–0.212 mm/s; 6.5 min):

| Disturbances | True speed | Centre line: error, blocks resolved | Two boxes: error, windows resolved (lag 0) |
| --- | --- | --- | --- |
| clean | no flow | none resolved | **0.039 mm/s** reported, 100% |
| as measured | no flow | 7% falsely resolved | none (100% lag 0) |
| as measured | 0.25 px/frame (0.010 mm/s) | −0.0%, 100% | +8.1%, 64% (47%) |
| as measured | 1 (0.040) | +0.1%, 100% | +3.7%, 100% (1%) |
| as measured | 2 (0.080) | +0.4%, 100% | −9.7%, 50% (54%) |
| as measured | 4 (0.159) | +0.1%, 100% | +7.4%, 100% (0%) |
| as measured | 5 (0.199) | −2.1%, 85% | +0.2%, 100% (0%) |
| as measured | 8 / 12 (0.32 / 0.48) | unresolved (beyond range) | −6.0% / +25.3% |
| strong | no flow | 7% falsely resolved | none (100% lag 0) |
| strong | 0.25 (0.010) | −0.2%, 98% | −93%, 45%, half the wrong sign |
| strong | 2 (0.080) | +0.4%, 100% | −118%, 21% (89%), half the wrong sign |
| strong | 5 (0.199) | −1.9%, 82% | +3.6%, 100% (2%) |

Within its range the centre line's median is within −2.1% to +0.4% in every
condition, with 0–4% of resolved blocks pointing the wrong way; beyond its
range it reports nothing rather than a wrong number. The two boxes are off by
up to ±10% under the measured disturbances, fail outright under strong ones,
report velocity where there is no flow, and are coarse at high speed (−6% to
+25% at 8–12 px/frame). A shorter run (one seed, 10-s clips) once showed 20%
false resolution without flow under strong jitter, so that number varies.

### On the real recordings

Lines from the extracted centre lines, clicked every 15 px; two 30-s stretches
each; nothing to compare with except each other and lines through tissue:

- **Before limb** (145 px): 57% of blocks resolved, median 0.23 px/frame
  (0.0091 mm/s), 92% pointing down the limb. In the GUI session the first
  stretch alone (frames 1909–2808) gave 0.0138 mm/s (middle half
  0.0095–0.0173), 60% resolved, median signal-to-noise 10.
- **After loop:** weak; 12% resolved on the left limb (+0.20 px/frame, 92%
  down the limb), 15% on the other limb (−0.23, all upwards, consistent with
  flow round the loop), 17% on the whole arch with mixed directions.
- **Still tissue,** lines 25 px from the vessel: 0 of 110 blocks resolved in
  both recordings (median signal-to-noise 3.3–3.6). Two lines first
  thought to be tissue resolved some blocks; on inspection one crossed the
  apex and one ran along the other limb.

These numbers are not validated (there is no ground truth in a recording); the
benchmark is what says the method is accurate.

### The app (`0cef0c3`)

- **Centre line page** (first page, Ctrl+1): click points along the vessel
  (start where the blood comes from); click on the line inserts a point, drag
  moves one, right-click removes one, Backspace removes the last, X reverses.
  The panel shows the line's length and measurable range, and a live
  space-time diagram of the 120 frames around the playhead with the slope
  found in orange, its velocity and signal-to-noise ratio, and a message when
  the flow is unresolved, seems too fast or too slow for the line, or runs
  against it (with a Reverse button).
- **Data set** (`capillary.datasets`): `___space_time.npy` (the diagram,
  float32, loaded without pickle), `___line_velocity.csv` (one row per block:
  centre frame, time, speed, velocity, signal-to-noise, coherence, resolved),
  `___line_provenance.json` (video, the points, frames, calibration, measurable
  range, all estimator settings, summary, git commit). Reports:
  `___line_velocity.png` (velocity over time, unresolved blocks marked, median,
  time points), `___space_time.png` (the diagram with the measured slopes) and
  a one-row `___line_summary.csv` for collecting results across recordings.
- **Results page** shows both kinds (CENTRE LINE / TWO BOXES), warns when
  fewer than 25% of blocks were resolved, restores the line on its page, and
  regenerates a centre-line report from the saved diagram without the video.
- **Two boxes page** is the old Analyze page, renamed, unchanged otherwise.
- **CLI**: `python -m capillary.cli <video> --line "x1,y1;x2,y2;..."` measures
  along a line; `--start` picks the first frame for both methods.

### Verification

- **Unit tests:** 184 pass (141 this morning): `test_spacetime.py` 24 (the
  estimator on diagrams with known speed, both directions, no flow, a tenfold
  same-moment change, flow beyond the range, the line geometry, the sampler,
  block analysis, a simulated recording end to end), `test_simulate.py` 9,
  `test_line_tasks.py` 7 (the page's measurement, saving, report, results
  info, regeneration without the video, preview, clean-up after a failure),
  and new cases in `test_pipeline.py` (CLI `--line`), `test_datasets.py` and
  `test_gui_logic.py`. Each code commit passes on its own (176 and 184).
- **Lint:** pyflakes reports only the two earlier notes; the CI flake8
  selection is clean.
- **Benchmark:** the full run above (6.5 min) and `--quick` (12 s).
- **Scripted GUI session** on a scratch data folder, screenshots reviewed, no
  Tk errors: four pages and Ctrl+1–4; 11 clicks along the before limb (145 px,
  measurable 0.0022–0.256 mm/s); preview resolved at 0.0169 mm/s,
  signal-to-noise 19; inserting, dragging, right-click removal, Backspace,
  and X (velocity −0.0169 with the "against the line" message); measuring
  frames 1909–2808 (3.1 s); the Results card, restoring the line and range,
  regenerating, moving to the trash; the Two boxes page, F1, the right-click
  menu. The direction arrow, first drawn at the line's end where the last
  point hid it, was moved to the middle.

### Limitations and next steps

- **Speed limit at 30 fps.** A line follows flow up to about 0.0018 × its
  length in px, in mm/s; normal resting velocities (0.3–1 mm/s) need lines of
  170–560 px or a faster camera. Worth stating in the thesis; it also makes
  checking the real frame rate (still open) more important.
- **Jitter near stasis.** Without flow, 7–11% of blocks (up to 20% in a short
  clip) are resolved as about 0.2 px/frame under jitter, which is the speed of
  the slow real flows here. A near-stasis vessel shows as "few blocks
  resolved"; the Results page warns below 25%. A per-recording control (the
  same measurement on a parallel line through tissue) or local stabilization
  would make this stronger.
- **Real-data validation is still to do:** two observers reading the slopes
  of the same diagrams, repeated measurements, Bland–Altman against manual
  reading.
- The existing two-box data sets (`Test`, `Test2` of `FP01_Qefter`, `set1` of
  `FP01_Wefter`) are unreliable for the reasons above.
- The two-box report still sets negative velocities to 0 in
  `___report_summary.csv`; left as it was, since that method is now
  secondary.
- Frame rate and spatial calibration are still unverified.

---

## 2026-10-06 — Optical-flow measurement removed

**Branch:** `refactor/remove-optical-flow`, from `main` at `95472ee` (the GUI
rebuild, merged as pull request #3).

**Commits:**

- `284d67e` Remove the optical-flow measurement
- `38ddd3a` Update README and CLAUDE.md for the velocity-only app

### Why

At the end of the 2026-10-05 session we agreed to build the tool around the
primary endpoint, red-cell velocity, and to drop the optical-flow measurement
first. The flow measure was not a planned endpoint, and as implemented it was
not a valid one:

- **Fast motion was discarded.** Magnitudes above 10 px/frame were set to 0
  before anything else. At 1.329 µm/px and 30 fps that is about 0.4 mm/s,
  well inside the range of capillary red-cell velocities.
- **Lossy storage.** The flow was multiplied by 25.5, saved as an 8-bit MP4V
  video and read back for the measurement. That quantizes it and adds
  compression artefacts.
- **Wrong denominator.** The flow summed over the whole region (vessel and
  background) was divided by the number of vessel pixels in it.
- **Direction and unit.** "Up" and "down" meant towards the top or bottom of
  the image, not along the vessel. The unit was mm per frame, not mm/s.

### What the app no longer has

- The **Flow** page. The pages are now Analyze, Capture and Results, and
  Ctrl + 1 … 3 switches between them. Ctrl + 4 now does nothing.
- *Compute optical flow* / *Recompute optical flow…* in a recording's
  right-click menu and on the Results page, and *Compute missing optical flow*
  in the **⋯** menu above the list.
- *Measure flow* in the right-click menu and on the Results page, the "Flow"
  chip in the recording list, the "Optical flow" row of the Results page's
  Files card, and flow data set cards.
- The "Region (Flow)" section of the F1 list.

### Code removed (`284d67e`)

- `gui/flow_page.py` (426 lines), `capillary/flow.py` (138) and
  `tests/test_flow.py` (162).
- `Caper.FlowVideo` (the Farneback flow and the vessel-mask pickle) and
  `Caper.generate_flow_report`.
- From `capillary/measure.py`: `measure_flow` and `flow_region_size_bytes`.
  From `capillary/datasets.py`: the flow file names, writers, readers and
  listing. From `gui/tasks.py`: the flow job, the flow measurement and the flow
  report.
- `pickle_save` and `pickle_load` from `Utilities.py`.
- `scikit-image` from `requirements.txt`; only `FlowVideo` used it. It can be
  removed from an existing venv with `pip uninstall scikit-image`, but it does
  no harm there.
- Things only the Flow page needed:
  - colour frames in `FrameSource`
  - the skipped-frame callback of the player
  - the `prepare_frame` / `video_opened` hooks of the measure page
  - the green region colour
  - `iter_frames(single_channel=False)`
  - the second capture handle in `tasks._release`
- With one kind of data set left, the "velocity or flow" switch went too.
  `datasets.dataset_paths`, `tasks.dataset_info` and the Results page's card
  actions now take just the data set name. The measure page has no `kind` or
  `color` attribute.

In all: 28 files, 270 lines added, 1,461 removed.

### Old flow files

Nothing on disk was deleted or moved. The real data folder still holds:

- `Flows/FP01_Qefter_22-Oct-2019_09-46-17.avi` and its `.pickle`
- two flow data sets of that recording: `Test_1` and an unnamed one
  (`…______flow.pickle`, `…______mask.pickle`)
- the two plots of `Test_1` in `Reports/`

The app stops listing these, but it still knows where they are. Each recording
gets a `legacy_flow_files` list: its files in `Flows/`, plus the files of any
old flow data set in `Statistics/` and `Reports/` (found by
`datasets.legacy_flow_dataset_paths`).

- **Move recording to trash** therefore still takes them along. The
  confirmation then says "… and old optical-flow files".
- A recording that has only a flow video and no raw or stabilized video is
  no longer listed, since nothing can be done with it. No such recording
  exists at the moment.
- New data folders no longer get an empty `Flows/` folder. An existing one is
  left alone.

### Effect on measurements

None. `capillary/velocity.py`, `intensity.py`, `roi.py`, `quality.py`,
`cli.py` and `SingleStepDFT.py` are unchanged. In `Caper.py` the
`VideoStabilization` and `CrossCorrelation` classes are identical apart from
blank lines, and so is `measure_velocity`; this was checked by diffing them
between `95472ee` and `284d67e`. Provenance files of new velocity data sets
still record `"kind": "velocity"`, so the file format is unchanged.

### Verification

- **Unit tests:** 141 pass, down from 154.
  - 15 flow tests went: the 11 in `test_flow.py`, 3 in `test_measure.py` and
    the flow round trip in `test_datasets.py`.
  - 2 new tests check that old flow data sets are found with their plots
    (including the unnamed one) and that old flow files belong to their
    recording without being listed. A flow-only recording is not listed.
  - The trash test now puts an old flow video, its summary, a flow data set
    and its plots beside a recording. It checks that all of them reach the
    trash in their own subfolders.
- **Lint:** pyflakes reports only the two notes it reported before (the
  deliberate re-export in `Utilities.py`, an unused import in the vendored
  `SingleStepDFT.py`). The CI's flake8 selection is clean. `capillary.cli` and
  `Application` import.
- **Scripted GUI session.** This ran the real window under WSLg on a scratch
  data folder: links to the 8 real videos and the real flow video, plus copies
  of the flow summary, `Statistics/` and `Reports/`. The screenshots were
  reviewed, and the session ended with no Tk errors.
  - The header shows Analyze, Capture and Results. Ctrl + 1, 2 and 3 switch
    pages; Ctrl + 4 does nothing.
  - The list shows no flow chip. `FP01_Qefter_22-Oct-2019_09-46-17` shows its
    2 velocity data sets and carries its 8 old flow files.
  - The right-click menu holds *Measure velocity*, *Results*, *Stabilize*,
    *Show in folder* and *Move to trash…*. The **⋯** menu holds *Stabilize
    all raw recordings* and *Open the data folder*.
  - Frames 1000–1400 of that recording were measured as `noflow_test` in
    2.3 s, writing its five files. The boxes were placed at fixed test
    coordinates, not on a chosen capillary, so this range resolved no
    velocity; that does not bear on this change.
  - The data set was then replaced (the old files went to `.trash/`), opened in
    Results (its card highlighted), its report regenerated, its positions
    restored (both boxes and the range 1000–1400 came back), and moved to the
    trash.
  - The F1 list shows no flow section and "Ctrl + 1 … 3".
  - *Move recording to trash* listed 22 files and named the old optical-flow
    files. All 22 ended up in one `.trash/` folder with their subfolders: both
    `Flows/` files, the four flow pickles and the two flow plots. No file of
    that recording was left behind, and the real `Flows/` folder was
    untouched.

### Not done

- The old flow files in the real data folder are still there. Deleting them, or
  moving them somewhere for the record, is the user's call.
- Next, as planned: improve the velocity estimator. The list in last session's
  notes includes:
  - verify the real frame rate and the calibration
  - sub-frame lag
  - trend removal
  - treat lag 0 as censored instead of dropping it
  - path length along the vessel
  - the negative-to-zero clipping in `report_summary.csv`
  - validation

---

## 2026-10-05 — GUI rebuilt from scratch

**Branch:** `feat/gui-rebuild`, based on `refactor/remove-dead-code` (`4f785bc`),
which is not merged yet. Merge that pull request first, then this one.

**Commits:**

- `24543cf` Add frame-range measurement, data set files and flow arithmetic to capillary
- `5a1784c` Rebuild the GUI from scratch as the gui package
- `f6ccea7` Remove the old GUI
- `d7a3a1a` Update README and CLAUDE.md for the new GUI
- `45a15ac` Analyze: say so when a measurement resolved no velocity

### Why

The user asked for the GUI to be rebuilt from scratch: it was outdated and
not intuitive. Concretely, the old window had these problems:

- **Measuring meant playing the video.** Each frame shown with the boxes on it
  added one sample. A measurement took as long as the clip. Moving a box
  half-way silently mixed two positions into one data set. Frames played
  before the boxes were placed were recorded too.
- The two boxes differed only by colour (white, black) and a modifier key.
  Nothing said that box 1 must be the downstream one, although the sign of
  every velocity depends on it.
- Nothing showed whether the boxes were placed well until a report had been
  saved and generated.
- Stabilization and optical flow ran one frame per tick of the window's main
  loop, so the window was unusable for minutes.
- Six of the seven known issues listed after the clean-up were GUI defects:
  popups took over the close button, the Capture tab broke the keyboard
  controls, the save popup warned falsely, Generate report and the
  "all videos" options crashed, and the camera was never released.
- Deleting a video deleted it permanently.

### The new GUI (`5a1784c`)

One window: a list of recordings on the left, and four pages. A recording is
everything that shares one video's name: raw capture, stabilized copy,
optical flow, data sets, time points. `Application.py` only sets up logging
(now a rotating `capillaroscopy.log`) and opens the window from the new `gui/`
package (19 modules; `README.md` has the table).

- **Analyze.** Box 1 (orange) is labelled downstream and box 2 (blue)
  upstream. A dashed arrow from box 2 to box 1 shows the flow direction that
  counts as positive. A click places the selected box, and selection then
  moves on to box 2. Right-click or Ctrl+click places box 2, dragging moves a
  box, WASD nudges it, X swaps the boxes.
  - The panel shows the box separation (px and µm) and the velocities that
    separation can resolve. The fastest is a lag of 1 frame, the slowest a lag
    of 100 frames in the 201-frame window. For example, boxes 29.1 px apart
    cannot resolve anything faster than 1.16 mm/s.
  - A live **signal preview** reads the 201 frames around the playhead in the
    background and runs the report's own `lag_and_correlation` on them. It
    plots both box signals and shows the correlation, the lag and the velocity.
    It warns when the lag is 0 (too fast for this separation, or a brightness
    change over the whole image), when the lag hits the window limit, when the
    correlation is weak, or when the boxes look swapped.
- **Measure.** The user sets a frame range on the timeline (I/O), names the
  data set and presses *Measure velocity and save*.
  - `capillary.measure` reads that range straight from the file, with the
    boxes fixed, in a background job: 401 frames of a real clip took 2.9 s,
    against 13 s of playback before.
  - The data set is saved in the existing file formats, and the report is
    written by the unchanged report code. Old and new data sets therefore go
    through the same arithmetic.
  - Each data set also gets a `___velocity_provenance.json` (or
    `___flow_provenance.json`). It records the video, box centres and size,
    frame range, separation, calibration, report settings, a summary of the
    result and the git commit. The numbers can be traced to their inputs, and
    the Results page uses this file to put the boxes back.
- **Flow.** The user draws a region over a vessel on the optical-flow video.
  The vessel mask can be shown as an overlay, and a colour wheel explains the
  direction colours. The region and the current frame's flow are read out
  live. *Measure flow and save* works like velocity. Two errors in the old
  flow display are fixed: a brightness boost that wrapped around in uint8, so
  fast flow looked dark, and swapped red and blue. Only the picture changed;
  measurements read the raw frames.
- **Capture.** The camera is read on its own thread, so recording keeps the
  camera's pace, not the window's redraw rate. The page warns if the camera's
  measured frame rate is more than 5% away from the 30 fps written into every
  recording. Time points marked during recording are saved at once. The
  camera is released when the page is left.
- **Results.** For one recording: its files, time points and data sets. Each
  data set card shows a summary (median velocity and interquartile range,
  share of windows resolved, share too fast to resolve, median correlation)
  and its settings, if it has a provenance file. Its report plots open in a
  viewer. The report can be regenerated, for example after adding time points,
  and the boxes can be restored on the Analyze page. Data sets made before this
  change are marked as having no recorded settings.
- **Background work.** Stabilize, optical flow, measurements and reports run as
  jobs in two lanes, so a measurement never waits behind a long flow
  computation. Each job shows progress and time left and can be cancelled.
  Videos are written into a hidden `.partial/` folder and moved into place only
  when complete. A stabilization that would need more than 85% of the
  available memory is refused instead of crashing the app (see Not done).
- **Nothing is deleted outright.** Replacing a data set, re-stabilizing,
  recomputing flow, and removing a data set or a whole recording all move the
  old files to `.trash/<date-time>_<label>/` in the data folder. Each file
  keeps its subfolder, so it can be put back by hand. Each of these actions
  asks for confirmation first.
- **Keyboard and settings.** Keys are routed in one place and ignored while
  typing in a text field. F1 lists every control. A settings dialog holds the
  data folder, the calibration (shown in µm per pixel as well) and the default
  box size. The new `box_size` row is added to `settings.csv`, and rows the app
  does not know are kept.

### Engine additions (`24543cf`)

Everything the GUI computes goes through GUI-free code in `capillary/`:

- `measure.py`: `measure_velocity` and `measure_flow`. The first is
  `extract_traces` (the same sampling as the CLI) plus the per-frame sharpness
  score, computed on worker threads with an identical result. Both report
  progress and can be cancelled.
- `datasets.py`: file names and formats, data set names (validated, so the
  old "not saved" false alarm cannot recur), time points, the writers, and the
  provenance file.
- `flow.py`: drag-box bounds and flow magnitudes. These are copied verbatim
  from `Caper.Rectangle` and `FrameClasses.FlowFrame`, and tests check them
  against frozen copies of the originals.
- `quality.py`: `calculate_blur`, moved from `Utilities.py`, which still
  re-exports it.
- `velocity.py`: `resolvable_range` and `velocity_summary`.
- `video.py`: `iter_frames` can start at any frame.

### Caper.py (`5a1784c`)

`Caper.py` keeps stabilization, optical flow and the reports, and drops what
only the old GUI used:

- `Rectangle`, `ColorVideo`, `VideoCamera`, the `…Multiple` classes, and the
  live-recording half of `CrossCorrelation`.
- `CrossCorrelation` now takes `fps` and `mm_per_pixel` instead of a video and
  two GUI rectangles. Report generation can report its progress and closes its
  figures, so a long session does not accumulate them.
- The flow report moved here from `FrameClasses.FlowFrame` as
  `generate_flow_report`.

None of this changes a single output byte; see Verification.

### Removed (`f6ccea7`)

- `Analyze_Frame`, `Flow_Frame`, `Camera_Frame`, `FrameClasses`, `Popup_Frame`,
  `Save_Data_Popup`, `Choose_Report_Popup` and `Process_Frame`. Together with
  the old `Application.py` that is 1,897 lines, replaced by 6,542 lines in
  `gui/`.
- Five icons only they used; `Source/` keeps `Capture-Logo.png` as the window
  icon.
- The `Utilities` helpers only they called.
- `.gitlab-ci.yml` imports `gui.app` instead of `FrameClasses`. `.gitignore`
  covers `.trash/`, `.partial/` and the rotated log files.

### Differences between old and new data sets

Methods-relevant. The report arithmetic is unchanged, but the inputs are now
collected differently:

1. **Frame index.** The old Analyze tab read the next frame, then stored it
   under the previous frame's number, so frame k+1 sat at index k. Times in
   old data sets therefore read one frame (33 ms) early. New data sets store
   frame k at index k. Velocities are unaffected, since both boxes share the
   shift.
2. **Frame rate.** The old report used the integer part of the file's frame
   rate; the new one uses the exact value. This makes no difference for the
   existing videos, which are all exactly 30 fps.
3. **Box separation.** The old tab stored, per frame, the distance between the
   raw click points. The new tab stores one constant distance between the box
   centres after they are kept inside the image, as the CLI always did. The two
   differ only for a box touching the image edge.
4. **Which frames.** Old data sets contain every frame that happened to be
   played, including frames before the boxes were placed, and a replayed
   stretch overwrote the earlier samples. New data sets contain exactly the
   chosen range; all other frames are NaN. The intensity table now has a
   column for every frame; the old one dropped the last.
5. **Flow units.** The flow report's values are optical-flow displacement per
   frame (mm/frame), not per second. This is unchanged and now stated in the
   provenance file.

### Verification

- **Unit tests:** 154 pass, up from 78 before this work. New tests cover:
  - `measure_velocity`: exactly equal to `extract_traces_from_video` on MP4V
    and uncompressed video, plus ranges, the sharpness cache, progress and
    cancelling.
  - End to end: a synthetic clip is measured, saved and run through the
    unchanged report, which recovers the known velocity within 5%.
  - File formats and data set names.
  - The flow arithmetic against the original code, for all 8⁴ drag
    combinations.
  - The GUI's non-visual logic: settings, the recording list, the trash,
    recording names and background jobs.

  Each of the three code commits was also tested on its own, from a checkout of
  exactly that commit (141, 154 and 154 pass). At the first one the old GUI
  still imports.
- **Reports are byte-identical:** the refactored `Caper` regenerated the
  velocity reports of `…___Test` and `…___Test2` and the flow reports of
  `…___Test_1` and the unnamed flow data set. All 26 files are identical to the
  output of the code at `4f785bc`.
- **Scripted GUI sessions.** These ran the real window under WSLg on a scratch
  data folder: links to the real videos plus copies of `Statistics/` and
  `Reports/`. Screenshots were reviewed after each round, and every session
  ended with no Tk errors.
  - Placing boxes and checking the preview.
  - Measuring a range of a real recording.
  - Stabilizing and computing flow for a synthetic jittered recording, then
    measuring flow on it.
  - The Results page, report viewer, dialogs, and Capture without a camera.
  - Replacing a data set and moving a recording to the trash.
  - 30 keyboard checks through the key router.
  - Starting through `main()` and quitting while a preview was reading frames.
- **Two bugs found by those sessions and fixed before committing:**
  - Moving a recording to the trash flattened the folders. Its raw, stabilized
    and flow videos share a file name, so they would have overwritten each
    other. This was caught on the scratch copy of the synthetic recording. Files
    now keep their subfolders, and a test pins it.
  - Quitting while a background thread was inside OpenCV aborted the process
    ("terminate called…"). Shutdown now stops every thread and waits for it.
- **One false alarm.** In one session a "Replace data set?" confirmation seemed
  never to appear. The scripts had kept only the main test window from taking
  keyboard focus, not its dialogs, so keys typed on the desktop at that moment
  could close a dialog. With the dialogs made unfocusable as well, the
  confirmation stays open until the script answers it, and the replacement
  then runs. The app was not at fault.
- **Static checks:** pyflakes reports only the intentional `calculate_blur`
  re-export and the old unused import in `SingleStepDFT.py`. The CI's flake8
  error selection finds nothing.
- **Real data untouched:** no file in `RecordedVideos/`, `StabilizedVideos/`,
  `Flows/`, `Statistics/` or `Reports/` was modified during this session. The
  newest, the `…___Test` report written at 16:46, predates the session.
  There is no `.trash/` or `.partial/` in the repository folder.

### Not done

- **Stabilization still has its two problems.** It is off by one frame (see
  Known issues). It also keeps the whole video in memory twice as float64:
  about 21 GB for the 4,306-frame clip and 37 GB for the longest, 7,524
  frames. The new memory check refuses such runs instead of letting them crash
  the app. On a typical machine, recordings as long as the existing ones
  therefore cannot be stabilized in the app until `VideoStabilization` is
  reworked. That rework changes its output, so it needs its own verification.
- Recording has not been tried with a real camera; none is reachable under
  WSL.
- The GUI has been driven by scripts and checked on screenshots, but not yet by
  hand. A hands-on session should come first: dragging boxes, zoom, playback,
  the general feel.
- The `.thumbnails/` caches of the old GUI in `StabilizedVideos/` and `Flows/`
  are no longer used and can be deleted by hand.
- CI is still defined only in `.gitlab-ci.yml`, which GitHub ignores.

---

## 2026-10-05 — Clean-up: remove dead code and unused files

**Branch:** `refactor/remove-dead-code` (off `main` at `f87891c`), to be merged through a pull request.

**Commits:**

- `839626e` Normalize line endings to LF
- `cc99fb4` Remove dead code, unused files and leftover debugging
- `a7e53dd` Fix "Stabilize all videos" and "Calculate flow for all" on NumPy 2
- `9feb83b` Update docs and config after the clean-up

### Why

The GUI code carried a lot of material that no longer did anything: an
unreachable tab, a scratch script, never-instantiated classes, broken methods
nobody called, hundreds of lines of commented-out code, copy-pasted imports and
debug prints. It made the code hard to read and hid which parts actually run.
The aim was to remove that **without changing behaviour**, and to prove it.

Python code went from **6,426 to 4,346 lines (−32%)**; 15 unused binary
assets (about 7 MB) left the working tree. Everything removed stays in the git
history.

### Line endings first

The original modules were stored with Windows (CRLF) line endings; the newer
code uses LF. `839626e` converts them on its own, with no content changes
(`git diff --ignore-cr-at-eol` is empty), so the following commits show only
real changes. A `.gitattributes` keeps text files LF from now on.

### What was removed (`cc99fb4`)

Files:

| File | Why it was dead |
| --- | --- |
| `Stabilization.py` | Scratch script; ran on import against a hard-coded `Data/FP07_…avi` that does not exist |
| `Stabilize_Frame.py` | The Stabilize tab: its menu button was commented out and nothing else selected it. Stabilizing runs through a video's options popup and `Process_Frame` |
| `ProgressMonitor.py` | Its time-remaining text was only displayed on that unreachable tab |
| `Logo/` (12 files) | Photoshop sources and PNG/BMP icons; nothing references them |
| `Source/Capture.png`, `Source/Capture2.png`, `Source/Quicksand-Regular.ttf` | Not referenced (the font only in commented-out code) |

Code: `MatplotlibFrame` (never instantiated); `VideoStabilization.stabilize()`
(unreachable, and would have crashed: it called methods with missing
arguments); `CrossCorrelation.test()` (broken); `Video.load()` and
`ColorVideo.load()` (used only by the removed script and method); a shadowed
duplicate `Menu._resize`; unused methods, attributes and parameters; all
commented-out code; debug prints (`print('here mate')`, the correlation value
every 20 frames, the canvas size, the video list); duplicate and unused
imports, including `seaborn` and `scikit-video`. The `from Utilities import *`
star imports are now explicit, so static checks can see every name.

One removal saves work every frame: `Video.get_frame` ran a sharpness FFT on
each frame into a vector that nothing read (the blur vector that *is* saved is
computed separately in `VideoFrame.update`). Playback in the test run reached
frame 320 about 20% sooner.

### Refactors (same commit)

- `Utilities.list_videos` / `video_stem` replace three copies of the video
  listing and the Windows/Linux path splitting. For file names with a single
  dot (all current data) the result is identical; names with extra dots are
  now matched by their full stem instead of the last dot-separated part.
- `FrameClasses.load_icon` replaces five copies of the icon loading code.
- The Analyze tab maps a click to video pixels with
  `canvas_to_video_coordinates`, the function the Flow tab fix introduced; it is
  the same arithmetic the Analyze tab had inline.
- `EntryWithSet` moved from `Caper.py` to `FrameClasses.py`, so `Caper.py` no
  longer imports tkinter.
- The Swedish notes on which box is which in `CrossCorrelation` contradicted
  the code (they called rectangle 1 black; it is drawn white). They are replaced by
  an English summary that matches the report's column names and
  `capillary/velocity.py`: rectangle 1 (white) is the box the blood reaches
  last, hence `velocity = distance / -lag`.
- `SingleStepDFT.py` is a modified copy of `image_registration.register_images`
  (different defaults and a different embedding index range). Only its unused
  imports were removed, and a docstring now records where it came from and why it
  must not be swapped for the package version unchecked.

### The one intentional behaviour change (`a7e53dd`)

"Stabilize all videos" and "Calculate flow for all" used `np.in1d`, which
NumPy 2.4 (the version in the venv) no longer has. On `main` both options
showed "AttributeError: module 'numpy' has no attribute 'in1d'" and processed
nothing. `np.isin` is NumPy's documented replacement and gives the same result
for these lists. With it, both options process the pending video and return
to the Analyze tab, and the output is byte-identical to processing that clip
on its own.

### Docs and config (`9feb83b`)

`requirements.txt` drops `seaborn` and `sk-video`. The README loses the stale
`/home/jacob-widaeus/...` paths and the ffmpeg install step (only scikit-video
needed it; OpenCV ships its own), and gains a code-layout table.
`settings.csv` loses an unused `logo2,test2` row, `.gitignore` the `ffmpeg/`
entry. `CLAUDE.md` now lists the controls and the known issues below.

### Verification

Baselines were recorded on `main` *before* any change, then compared with the
cleaned code. The harness scripts lived outside the repository and only read
real data; all outputs went to a scratch folder.

- **Unit tests:** 78/78 pass before and after.
- **Report pipeline:** `CrossCorrelation.calculate_cross_correlation` and
  `generate_report` regenerated both saved data sets in `Statistics/`
  (`…___Test` and `…___Test2`). All report CSVs are **byte-identical** to
  `main` and all plots **pixel-identical**, so dropping the seaborn import did
  not change the plot style.
- **Stabilization and optical flow:** a synthetic 640×480 clip (known jitter
  plus a moving blob) was stabilized and flow-processed, singly and through the
  "all videos" classes. The registration vectors, the stabilized video, the
  flow video and the flow pickle are all **byte-identical** to `main`.
- **Whole GUI:** a scripted session drove every reachable part of the app
  through Tk. On the Analyze tab: ROI click and Ctrl+click, WASD, the box size
  field, Save data, Generate report, Register time, pause, ±500 frames and the
  video bar. On the Flow tab: drag-select, Save data and Generate report. On
  the Capture tab: recording start and stop and Register time. From the options
  popup: Stabilize, Calculate flow and Delete, the latter on scratch copies.
  Before and after, the run produced the same files, the same box positions,
  the same correlation readout and **no errors**. Stabilize and flow run from
  the GUI produced byte-identical files.
- Static checks: pyflakes is clean apart from one unused import inside the
  vendored registration function; every module imports and compiles.
- The real data folders were checked afterwards: no file modified.

### Found, not fixed (listed in CLAUDE.md under Known issues)

These are real defects, left alone so that this change stays
behaviour-preserving. Each needs its own fix and check.

- **Stabilization is off by one frame.** `load_stabilization` reopens the
  video on its first step without reading a frame. As a result frame 0 of every
  video stabilized by the app is black, stabilized frame k is recorded frame
  k−1, and the last recorded frame is dropped. This was verified on the
  synthetic clip: frame 0 has mean intensity 0, and frame k matches input frame
  k−1 exactly. The 8 videos in `StabilizedVideos/` do **not** start with a
  black frame, so they were not produced by this code. Velocities from the
  cross-correlation are unaffected, since both boxes see the same delay, but
  timestamps are shifted by one frame (33 ms at 30 fps).
- Opening any popup re-binds the **main** window's close button to that
  popup, so the window's X no longer quits the app (Escape still does).
- Visiting the Capture tab replaces the window's key bindings, so the
  Analyze/Flow keyboard controls stop working until restart. P/space on the
  Capture tab raises an AttributeError, because the camera object has no `pause`.
- The Save-report popup says "the file was not saved" for names with spaces or
  non-ASCII characters, but the data is saved under that name anyway.
- Flow tab "Generate report" with no saved flow data raises `UnboundLocalError`.
- "Stabilize all videos" / "Calculate flow for all" with nothing left to process
  raise `IndexError`; `RecordedVideos/` is currently empty, so the former
  would.
- The camera is never released when leaving the Capture tab.

### Not done

- No restructuring into packages; file names and the tab/widget split are
  unchanged. `VideoFrame` and `FlowFrame` still duplicate their canvas and
  progress-bar code, and the four popup classes their window set-up.
- CI is still defined only in `.gitlab-ci.yml`, which GitHub ignores.

---

## 2026-10-05 — Merge the 2026-09-17 branches into `main`; work moved to own GitHub copy

**Branch:** `main`

**Repository.** Work now happens in a separate private copy,
`Soohan03/Capillaroscopy` (remote `origin`), so thesis work is independent of
the shared repo. The original `Widaeus/capillaroscopy` is kept as remote
`upstream` for pulling updates. All branches were copied with full history,
except `dev`, which was dropped as not relevant.

**Merges:**

- `53f1e4e` Merge `feat/analysis-engine-extraction`: the `capillary` engine package,
  the cross-correlation lag off-by-one fix and the unit tests (2026-09-17 entry
  below).
- `c2150be` Merge `fix/flow-tab-roi-selection`: Flow tab drag-rectangle and
  paused-frame fixes (2026-09-17 entry below).

`fix/short-term-improvements` needed no merge: PR #1 (`c3e57f4`) already
brought it into `main`.

**Conflict.** Only `DEVLOG.md`, where both branches added their entry at the
top. Both entries were kept, newest first. There were no code conflicts: the
branches touch disjoint files (`Caper.py` plus the new `capillary/` and
`tests/`, versus `FrameClasses.py`). The Flow tab still passes video-pixel
coordinates into `Rectangle.calculate_corners`, which now delegates to
`capillary.roi.ROI`, so the two changes compose.

### Verification

- Before merging, both merge orders were dry-run with `git merge-tree`. Both
  give the same single `DEVLOG.md` conflict.
- The final merge tree is byte-identical to the dry-run tree checked
  beforehand. It differs from each branch only by the other branch's changes.
- On merged `main`, all unit tests pass (`python -m pytest`), `capillary`,
  `Caper`, `FrameClasses` and `Application` import, and `compileall` is
  clean.
- The Flow tab coordinate fix survives the merge: a click at (350, 200) on a
  700x400 canvas showing a 1400x800 video maps to (700, 400).

### Not done

- CI exists only as `.gitlab-ci.yml`, which GitHub ignores, so the unit tests
  do not run automatically on the new repository.
- The Flow tab drag has not yet been confirmed interactively since its fix. One
  manual drag test is worth doing.

---

## 2026-09-17 — Flow tab: drag-rectangle lands in the wrong place, paused frame double-converted

**Branch:** `fix/flow-tab-roi-selection` (off `main` at `c3e57f4`). Independent
of `feat/analysis-engine-extraction`, which is still open as a PR; both branches
add an entry at the top of this file, so expect a trivial merge conflict here.

**Context:** the 2026-07-23 entry fixed Ctrl+click on the Analyze tab and
deliberately left the Flow tab's video frame class (`FlowFrame`,
`FrameClasses.py`) alone. This session went back to it. The stated suspicion —
that Flow tab needed the same Ctrl+click fix — turned out to be wrong: the Flow
tab has only one rectangle, selected by click-and-drag, so the Ctrl branch there
was dead code. Reading the handlers properly found three real defects instead.

### Defect 1 — the drag rectangle was stored in canvas pixels, not video pixels

`FlowFrame` shows the video resized to fit the window: a 1150x770 window gives a
805x539 area, and a 640x480 clip is aspect-fitted into that as **718x539**. So a
canvas pixel is not a video pixel (scale 1.122 in both axes).

The press handler (`callback`) correctly divided `event.x/y` by that scale. But
the release handler (`callback_release`) stored the raw `event.x/y`, and then
set `rectangle1.point1 = self.clickevent` — which the press handler had *also*
stored raw, alongside the scaled copy it never used. `Rectangle.calculate_corners_drag`
then clamped and sliced those canvas coordinates against the *frame*. Result:
the box the user dragged and the box the tool sampled were different boxes —
offset towards the bottom-right by up to ~12%, and 12% too large. A drag over a
vessel near the right or bottom edge sampled a region partly or wholly off it.

This matters for the thesis: the flow report divides flow by vessel-pixel count
inside the selection (see the 2026-07-07 entry). A mis-placed selection changes
that count and therefore every value in the report.

**Fix:** both handlers now go through one mapping,
`canvas_to_video_coordinates()` (a plain module-level function in
`FrameClasses.py`, kept GUI-free so it can be checked headlessly), wrapped by
`FlowFrame._canvas_to_video()`. `point1` and `point2` are both video pixels.

### Defect 2 — dead Ctrl detection

The press handler still carried the `self.master.current_key` /
platform-magic-number test (`[4,6]` / `[8,12]`) that the 2026-07-23 entry showed
never fires under X11. Here it guarded nothing — the `else` branch was `pass`
and there is no second rectangle — so it was removed rather than ported.

### Defect 3 — paused frames were HSV->BGR converted twice

`update()` stored the *processed* frame (`process_flow_frame` = HSV->BGR, x4)
as `self.previous_frame`, and the paused branch then ran `process_flow_frame`
on it again. Every flow video loads paused (`pause = 1` in `set_video`), and the
user pauses to drag the selection, so the still image people actually work on
had a colour conversion applied twice. `previous_frame` now holds the raw
rolling-average frame; both branches convert exactly once.

### Not changed

- Flow videos still load paused. Unlike the Analyze tab, that is the right
  default here: the selection is drawn on a still frame.
- `process_flow_frame` multiplies a `uint8` frame by 4, which wraps rather than
  saturates. Pre-existing, visual only, left alone.
- `CLAUDE.md` says `Flows/` is empty; it isn't (one generated flow video and
  its mask pickle from 2026-07-07). The file lives on the engine branch; fix the
  note there when that merges.

### Verification

- `python3 -m py_compile FrameClasses.py` passes.
- **Headless, against the real class.** A script constructed an actual
  `FlowFrame` under the WSLg display on the flow video in `Flows/`, confirmed
  the canvas came out 718x539 for the 640x480 clip (so the bug is visible, not
  masked by a coincidental 1:1 size), ran the paused branch first (as the app
  does), then one played tick, then paused again — `previous_frame` stayed a
  raw `uint8 (480, 640, 3)` frame throughout. It then delivered a synthetic
  press at canvas (100,100) and release at (400,300) through Tk's own event
  queue so the real bound handlers ran. Stored endpoints: `point1=(89, 89)`,
  `point2=(356, 267)` — the correct video pixels. The old code would have stored
  `(100,100)` and `(400,300)`. A further paused tick drew the box at
  x 89..356, y 89..267 and sliced a `(178, 267, 3)` region from the frame.
- The pure mapping was checked at the corners and centre, and for the identity
  case (canvas == video size).
- Note for reproducing: Tk silently drops synthetic button events aimed at an
  unmapped window; the frame has to be packed and the root shown first.
- App relaunched under WSLg after the change; the user was asked to try a drag
  on the Flow tab interactively.

---

## 2026-09-17 — Extract the analysis engine, and fix an off-by-one in the lag

**Branch:** `feat/analysis-engine-extraction` (off `main` at `c3e57f4`, the merge
of PR #1 `fix/short-term-improvements`)

**Commits:**

- `e002558` Add CLAUDE.md project instructions
- `e85763a` Extract the analysis engine into a GUI-free `capillary` package
- `5eb538f` Fix off-by-one in the cross-correlation lag and route the GUI through the engine
- `7a29e47` Document batch analysis and run the unit tests in CI

This is item 1 of the long-term list at the bottom of this file ("extract the
analysis engine into a GUI-free module with a CLI batch mode and unit tests
against synthetic videos with known velocity"). Writing the tests immediately
turned up a measurement bug, described in full below — it affects every velocity
this tool has ever reported, so read that section before using any earlier
report in the thesis.

### Why extract the engine

The measurement was only reachable by clicking. ROI geometry lived in
`Caper.Rectangle` interleaved with cv2 drawing calls; the velocity estimate
lived in `CrossCorrelation.calculate_cross_correlation`, which read its inputs
back from CSV files the GUI had written moments earlier and could not be invoked
without a Tk canvas. Nothing about the arithmetic could be run, checked, or
re-run on a different day with the same parameters.

For a methods section that has to defend its numbers, that is the wrong shape:
a result should be reproducible from recorded parameters, and the estimator
should be checkable against a signal whose answer is known in advance.

### The new package (`capillary/`)

No module in it imports tkinter, PIL or matplotlib.

| Module | What it holds |
| --- | --- |
| `roi.py` | `ROI`: the centred, frame-clamped sampling box as a value object |
| `video.py` | `probe_video` / `iter_frames`: streaming frame access |
| `intensity.py` | `IntensityTrace`, `extract_traces`: per-frame mean ROI intensity |
| `velocity.py` | `signed_lag`, `lag_and_correlation`, `sliding_lag`, `analyze_trace` |
| `cli.py` | `python -m capillary.cli` batch entry point |

Design decisions worth recording:

- **`ROI` reproduces `Rectangle.calculate_corners` exactly**, including its
  `int(w / 2)` halves (an 11-px box samples 10 columns) and its `>=` edge test.
  Those quirks were kept deliberately: "fixing" them would silently move every
  historical measurement by a pixel. The equivalence was verified mechanically
  (see Verification) rather than by eye.
- **Frames are streamed, not loaded.** `Caper.Video.load` allocates two float64
  arrays covering the whole clip (~26 GB for 60 s at 640x480), which is why
  batch analysis of a long recording was never possible. `iter_frames` holds one
  frame at a time. This is a partial answer to item 2 of the long-term list —
  the *analysis* path no longer has the problem; stabilisation still does.
- **Sliding windows are indexed by their centre frame.** The legacy report
  assigned each window's estimate to the frame at its *end* and then applied two
  compensating shifts (`(window - st) / 2`, then `-ceil(st / 2)`) to push the
  index back towards the middle. The engine just uses the centre directly, so a
  velocity is attributed to the moment it actually describes.
- **Explicit sign convention.** `signed_lag(a, b)` is positive when trace `b`
  lags `a`, so `velocity_from_lag` returns velocity along A -> B. The Analyze tab
  names its boxes the other way round (rectangle 1, the white box, is the one
  the blood reaches *last* — hence the legacy `/ -lag`), so `analyze_trace`
  defaults to `positive_flow='b_to_a'` and batch reports carry the same sign as
  GUI reports. This was previously only recoverable from Swedish comments and a
  column name reading `firstvec_white_islast_rect1_0`.

### The bug: every reported lag was one frame too large

`np.correlate(a, b, 'same')` places zero displacement at index `n // 2`. The
estimator computed

```python
lag = int(np.ceil(len(window) / 2) - np.argmax(correlation))
```

`ceil(n / 2)` equals `n // 2` for an even `n` and exceeds it by one for an odd
`n`. Every window length the report uses — `np.arange(201, 311, 20)` = 201, 221,
241, 261, 281, 301 — is odd. So every lag the tool has ever produced was one
frame too large, and velocity goes as `1 / lag`.

The bias is not a constant scale factor; it is a shift of the whole lag axis,
so its size depends on how fast the flow was:

- A true lag of -5 frames was reported as -4: **25% too fast**.
- A true lag of -1 frame was reported as 0: an infinite velocity.
- A true lag of -50 frames was reported as -49: 2% too fast, negligible.

It systematically **over**estimates the speeds the report plots as positive
(those come from negative lags, whose magnitude the shift shrinks).

`capillary.velocity.signed_lag` uses `n // 2`. `legacy=True` (and `--legacy-lag`
on the CLI) reproduces the old behaviour for comparison against existing
reports.

### What that means for the data already collected

Regenerating the saved `FP01_Qefter_22-Oct-2019_09-46-17___Test` report with the
fixed estimator (read-only; nothing in `Statistics/` was overwritten):

- All **5824** lag values move by exactly **1.0** frame, and nothing else
  changes — so the correction is the only behavioural difference, and the
  refactor itself is inert.
- **22.4%** of that recording's window estimates (1690 of 7542) had a true lag
  of **zero**: the plug crossed both boxes within one frame. The old code
  recorded these as a definite 1-frame lag, i.e. a spurious velocity of
  ~1.16 mm/s — which is simply the fastest that ROI separation (median 29.1 px)
  can express at 30 fps. They now report as unresolvable instead of as a
  measurement.
- Of the estimates that do resolve, the median absolute lag is 59 frames — about
  2 s to cross 29 px, i.e. genuinely slow flow — where a 1-frame error is under
  2%. That is why the *median* positive velocity only moves +3.7% while the mean
  and the upper tail move a lot (positive-sample mean 0.145 -> 0.100 mm/s,
  p95 0.605 -> 0.322 mm/s): the bias is concentrated in the fast samples.

**Implication for the thesis, to discuss with the supervisors:** the sizeable
zero-lag fraction is a real limitation of the method as configured, not a
software fault. At 30 fps with boxes ~29 px apart, anything faster than
~1.16 mm/s is unmeasurable. If faster flows matter, the boxes need to sit
further apart, or the lag needs sub-frame interpolation. Any velocity previously
reported at or near ~1.16 mm/s for this configuration should be treated as
"too fast to measure" rather than as a value.

### Other corrections made in passing

- A correlation window containing missing samples now yields NaN. Previously
  `np.argmax` of an all-NaN array returned 0, which silently produced a lag of
  `ceil(n / 2)` — a fabricated estimate. It is rare in the saved report (31 of
  7542 values) but indistinguishable from a real measurement when it happens.
- A zero lag yields NaN rather than an infinite velocity. The saved report
  contains 12 infinities, each of which drags any mean computed over its column
  to infinity.

### Single source of truth

`Caper.py` now calls into the package rather than keeping its own copies:
`Rectangle.calculate_corners` delegates to `ROI`, and both
`estimate_cross_correlation` (the live "Correlation" readout) and
`calculate_cross_correlation` (the saved report) call
`capillary.velocity.lag_and_correlation`. The GUI, the batch CLI and the tests
cannot drift apart.

### Batch mode

```bash
python3 -m capillary.cli StabilizedVideos/clip.avi \
    --roi1 320,240 --roi2 320,300 --size 10x10 \
    --out report.csv --summary-out summary.csv
```

`mm_per_pixel` is read from `settings.csv` unless `--mm-per-pixel` overrides it.
The point is reproducibility: the ROI coordinates, box size, window lengths and
calibration that produced a report are all on the command line, instead of
living in where somebody clicked.

### Verification

- **78 unit tests pass** (`python3 -m pytest`, 8 s). They cover ROI geometry and
  clamping, lag recovery, the velocity formula, NaN and zero-lag handling, the
  sliding window, CLI argument handling, and an end-to-end run.
- **Ground truth.** `tests/synthetic.py` generates clips in which an intensity
  pattern is translated at a chosen pixels-per-frame rate, so the true lag
  between two boxes and the true mm/s are both known exactly. A real clip cannot
  do this job — nobody knows how fast the blood in it was moving. The pipeline
  recovers the planted velocity to within 5%, and doubling the planted speed
  doubles the measured one (within 10%).
- **The off-by-one is pinned by tests** in both directions: `legacy=True` must
  return `true_lag + 1` on odd windows and `true_lag` on even ones, and on a
  synthetic clip the legacy path must land further from the known truth.
- **The refactor is inert.** `Rectangle.calculate_corners` was compared against
  a verbatim copy of the pre-refactor arithmetic over 768 combinations of click
  position, box size and frame size (including boxes clamped against all four
  edges): 768/768 identical, and the selected pixel patch is unmoved.
- **Real data.** The saved report regeneration described above: 5824/5824 lag
  values differ by exactly 1.0 and nothing else changed.
- **The app still runs.** Relaunched under WSLg after the rewiring: the update
  loop runs and the Analyze tab's correlation readout works, with no traceback.
  (The `RuntimeWarning: Mean of empty slice` at `Caper.py:828` is the
  pre-existing benign one — `nanmean` over an empty ROI before boxes are placed.)
- `python3 -m py_compile` passes on `Caper.py`, `Application.py`,
  `FrameClasses.py` and every new module.
- CI (`.gitlab-ci.yml`) gained a `unit-tests` job running pytest. The existing
  job could only prove the modules import.

### Not done

- The legacy report path still round-trips through `Statistics/*.csv` files and
  still applies its own index shifts; only the estimator inside it was replaced.
  Rewriting `generate_report` on top of `analyze_trace` is the natural follow-up.
- `Video.load` (stabilisation) still allocates whole-clip arrays — long-term
  item 2 remains open for that path.
- No provenance sidecar yet (long-term item 3); the CLI makes parameters
  explicit but does not yet record them alongside the output.
- Flow/stabilisation are still GUI-bound. Only the cross-correlation velocity
  path was extracted.

---

## 2026-07-23 — Fix Ctrl+click (2nd ROI box) and video-not-playing on Analyze tab

**Branch:** `fix/short-term-improvements` (continued)

**Symptoms reported by user:** on the Analyze tab, (1) Ctrl + left-click did
not place the second ROI box, and (2) a loaded video did not appear to play.

**Diagnosis:**

1. *Ctrl+click.* The video-canvas click handler in `FrameClasses.py`
   (`VideoFrame.callback`) decided whether Ctrl was held by reading a
   separately-tracked keyboard state (`self.master.current_key`, set from
   `<Key>`/`<KeyRelease>` events) and comparing it against platform-specific
   magic numbers (`[4,6]` on Linux/darwin, `[8,12]` on win32). Under X11/WSLg
   `current_key` never actually holds the Control value at click time
   (`<KeyRelease>` resets it to `None`, and a Control key-press reports the
   modifier state *before* the press), so the test was always false and every
   click — Ctrl or not — fell through to `rectangle1`. Box 2 could never be
   placed.

2. *Video not playing.* Three compounding causes:
   - `VideoFrame.set_video()` ended by setting `self.master.video.pause = 1`,
     so every freshly loaded video started **frozen on frame 0**.
   - `Application._resize` (bound to `<Configure>`) set `video.pause = 1` on
     *every* configure event — which fires during normal window setup and
     redraws — and never reset it. So even after pressing P/Space, any window
     move/resize re-froze the video.
   - The main update loop's `delay` was hard-pinned to 1 ms, so once a video
     did advance it ran at hundreds of fps and flashed past in a fraction of a
     second (also reading as "not playing").
   The frozen state was visible in the console as a flood of identical `N/A`
   lines (~26+/sec): `estimate_cross_correlation` prints on
   `frame_number % 20 == 0`, and with the counter stuck at frame 0 that fired
   on essentially every tick.

**Fixes:**
- `FrameClasses.py` (`VideoFrame.callback`): detect Ctrl directly from the
  mouse event's modifier mask — `bool(event.state & 0x0004)` (0x0004 is the
  Control bit on both X11 and Windows). Removed the `current_key` /
  platform-magic-number path.
- `FrameClasses.py` (`VideoFrame.set_video`): load videos **playing**
  (`pause = 0`) instead of paused. Users pause with P/Space to position ROI
  boxes on a still frame.
- `Application.py` (`_resize`): removed the unconditional `video.pause = 1` on
  `<Configure>`. The video canvas is a fixed size, so there is nothing to
  protect by pausing on resize.
- `Application.py` (`_update_body`): pace the loop to the video's native frame
  rate — `delay = max(1, round(1000 / video.fps_))` — instead of a hard 1 ms,
  so playback runs at real (~30 fps) speed.

**Verification:** `python -m py_compile Application.py FrameClasses.py` passes.
Relaunched the app under WSLg. *Before* the fixes the console flooded with
~26 identical `N/A`/sec (counter frozen at frame 0); *after*, that flood stops
and the log shows advancing, varied output including real correlation estimates
(e.g. `0.5`, `0.8`) with no traceback — i.e. frames now advance at a sane rate.
The Ctrl+click fix was verified by inspection (standard X11/Windows Control
mask `0x0004`); the actual GUI click is not scriptable in this environment, so
the user was asked to confirm it interactively.

**Notes / not changed:**
- The `RuntimeWarning: Mean of empty slice` at `Caper.py:831` is pre-existing
  and benign (numpy `nanmean` over an empty ROI selection before boxes are
  placed); it is unrelated to these changes.
- The second video frame class (`FrameClasses.py:1194`, used by the crash-prone
  Flow tab) still loads paused and still uses the old `current_key` click path.
  Left untouched deliberately — see Known Issues (Flow tab).

---

## 2026-07-07 — Fix Flow tab drag-rectangle crash (empty reports)

**Branch:** `fix/short-term-improvements` (continued)

**Symptom reported by user:** after calculating flow for a video and
saving the selection as "Test_1", the generated flow report chart was
empty.

**Diagnosis:** inspected the saved pickles in `Statistics/`. Of 4,306
frames only 1 had flow data, and that frame's region was the default
10x10 corner box with 0 vessel pixels in its mask. The report divides
flow by vessel-pixel count, so every value was NaN and the plot was
blank. Root cause in `capillaroscopy.log`: `UnboundLocalError: 'ltr'` in
`Rectangle.calculate_corners_drag` (Caper.py). The function only set its
left-to-right flag when the drag's x-coordinates differed and only set
corners when the y-coordinates differed, so a pure click or a
vertical/horizontal drag either crashed or returned None (resetting to
the 10x10 default). The crash was caught by the new update-loop guard but
stopped flow recording after the first frame.

**Fix (commit — Caper.py):** rewrote `calculate_corners_drag` to
normalize any two drag endpoints into an axis-aligned rectangle
regardless of direction, enforce a minimum size so the region is never
degenerate, and clamp to the frame bounds. Always returns True. Corner
naming kept consistent with `get_selected_data_for_flow`/`_for_mask`
(image coordinates, y down).

**Verification:** headless test over pure click, vertical drag,
horizontal drag, both diagonal directions, and off-edge points — every
case yields a valid non-empty box and no exception; the two opposite
diagonals produce the identical rectangle.

**User-facing note:** on the Flow tab the ROI is selected by click-and-
drag over a vessel (not a single click as on the Analyze tab). The old
"Test_1" data was captured with an empty region and should be re-recorded
after this fix.

---

## 2026-07-06 — Codebase audit + short-term fixes

**Branch:** `fix/short-term-improvements` (pushed to GitLab, 7 commits)
**Context:** Full audit of the codebase (~5,100 lines, 15 modules) identified
correctness bugs, performance problems, and thesis-relevant scientific issues.
The "short-term list" from that audit was then implemented. The audit's
long-term recommendations are listed at the end of this entry.

### Commit 1 — `93adccd` WIP fixes (pre-existing work, committed separately)

Uncommitted changes that were already in the working tree, committed on their
own so they stay distinguishable from the new fixes:

- Removed a leftover `pdb.set_trace()` in `Application.py` that dropped the
  app into the debugger on start.
- `VideoCamera` (Caper.py): falls back to 640x480 @ 30 fps and a black frame
  when no camera is connected, instead of crashing.
- `ParticipantList` (FrameClasses.py): the Analyze tab falls back to
  `StabilizedVideos/` when `RecordedVideos/` is empty.
- `settings.csv`: `Application_path` updated for this machine.
- Added `run_app.sh` helper to launch the app under WSL.

### Commit 2 — `5b30edb` Crash-proof the main update loop and add logging

**Problem:** the entire UI is driven by one `master.after()` chain in
`Application.update()`. Any uncaught exception anywhere in a tab's `update()`
killed that chain and silently froze the whole app — this is exactly how the
Flow tab crash used to lock everything up.

**Change (Application.py):**
- The loop body moved into `_update_body()`; `update()` wraps it in
  try/except and always reschedules itself.
- Errors are logged with a full traceback to `capillaroscopy.log` and shown
  in a dialog once per unique error (deduplicated so a recurring error does
  not spam dialogs every millisecond).
- Replaced the commented-out logging experiments with a real
  `logging.basicConfig` (file + console) in `__main__`.

### Commit 3 — `ee10cd7` Fix Flow tab crash when Flows/ is empty

**Problem:** opening the Flow tab with no flow videos passed
`selected_item=None` into `Video.__init__`, which crashed on
`path.replace()` (the known issue from CLAUDE.md).

**Change:**
- `Video.__init__` (Caper.py) tolerates `path=None`.
- `Flow_Frame` only builds a `FlowFrame` when a video is actually selected,
  and shows an explanatory empty-state label otherwise ("No flow videos
  found in Flows/ ..."), mirroring the pattern already used by the Analyze
  tab. The `FlowFrame` is created lazily once a video is chosen.

### Commit 4 — `a1a2db9` Fix TypeError in Capture tab "Register time"

**Problem:** `Camera_Frame.register_time_point` appended `self.frame/30`,
but `self.frame` is a Tk `PhotoImage` — every click raised `TypeError`.

**Change (Camera_Frame.py):** time points are now recorded as seconds since
the recording started (from `recording_timestamp`), and the button shows an
error dialog when no recording is running. Added explicit `pandas` and
`messagebox` imports instead of relying on star-imports.

### Commit 5 — `8dddbf4` Real frame rate + configurable spatial calibration

**Problem (scientifically the most important fix):** the velocity pipeline
assumed 30 fps everywhere — velocity formula, time displays, time-point
markers, flow reports. Any video not recorded at exactly 30 fps produced
proportionally wrong velocities. The magnification coefficient
(`1.328903654e-06 * 1000`) was hardcoded in two places with no provenance.

**Changes:**
- All fps reads in Caper.py fall back to 30 only when the file reports none
  (`... or 30`); `CrossCorrelation` now takes the video's real `fps_` and
  uses it in the velocity formula and the seconds index.
- Magnification is now `mm_per_pixel` in `settings.csv` (default
  `0.001328903654`, the original value). Missing settings keys are
  auto-filled and persisted on startup. `Application` exposes it as
  `master.mm_per_pixel`; `VideoFrame` passes it into `CrossCorrelation`;
  the flow report in `FrameClasses.py` reads it too.
- Fixed the report summary CSV `time` column, which divided an index that
  was already in seconds by 30 a second time.
- Collapsed the duplicated settings/mkdir blocks in `Application.__init__`
  (ten try/except `os.mkdir` blocks) into one `os.makedirs(exist_ok=True)`
  loop; the first-run branch no longer writes the legacy `logo2` junk row.

**Note:** the existing StabilizedVideos are 30 fps, so results for current
data are unchanged; this matters for future recordings.

### Commit 6 — `8ee6fa6` Cleanup: no rename-on-listing, narrowed bare excepts

- `get_items_from_path` (two copies: FrameClasses.py, Process_Frame.py)
  renamed files on disk (stripping commas) as a side effect of *listing* a
  directory. It now just returns a sorted listing.
- `ProgressMonitor.py` ran test code at import time; removed.
- Application key handler: the q/e/p video controls were unguarded and
  raised `AttributeError` when no video was loaded; the handler now
  tolerates the no-video state explicitly.
- Narrowed several bare `except:` blocks to the exceptions they actually
  expect (missing time-point CSV, non-numeric entry text, missing flow
  pickle, first fps-ticker tick) so real bugs are no longer swallowed.
- Flow save errors are logged with a traceback instead of only showing
  "An unknown error has occured".

### Commit 7 — `247bda6` Cache video thumbnails and durations on disk

**Problem:** `ParticipantList` reopened and decoded every video on every
list refresh (each click, selection, repack) to regenerate thumbnails.

**Change (FrameClasses.py):** thumbnails + durations are cached as pickles
in a `.thumbnails/` folder next to the videos, invalidated by file mtime.
The capture handle is released after thumbnail generation (was leaked).
`.gitignore` now covers `.thumbnails/` and `capillaroscopy.log`.

### Verification

- App launched via `run_app.sh` under WSLg: no tracebacks, update loop ran,
  thumbnail cache was built on first launch, `capillaroscopy.log` stayed
  empty (0 bytes) through a full run and clean exit.
- Headless smoke test: `Video(None)` constructs without crashing;
  `CrossCorrelation` picks up fps=30.0 from a real stabilized video and the
  configured `mm_per_pixel`.
- Every commit was syntax-checked with `py_compile` before committing.

### Audit findings deliberately NOT fixed yet (long-term list)

1. Extract the analysis engine (CrossCorrelation, stabilization, flow) into
   a GUI-free module with a CLI batch mode and unit tests against synthetic
   videos with known velocity — key for thesis reproducibility.
   *Done for the cross-correlation velocity path on 2026-09-17 (`capillary/`);
   stabilization and flow are still GUI-bound.*
2. Stream video processing: `Video.load` still allocates two float64 arrays
   covering the whole video (~26 GB for a 60 s clip) — stabilization of
   long videos will exhaust memory. *The analysis path now streams
   (`capillary.video.iter_frames`, 2026-09-17); stabilization still does not.*
3. Save analysis provenance (ROI coordinates, rectangle size, window
   parameters, git hash) as a JSON sidecar with every report.
4. Worker thread/process for stabilization/flow instead of one frame per
   UI tick.
5. Consider `skimage.registration.phase_cross_correlation` to replace the
   custom DFT registration, and `cv2.DISOpticalFlow` to replace Farneback.
6. Statistics layer: aggregate per-participant results into one tidy CSV.
7. Retire the 1 ms `after()` busy-loop (renders even when paused; pins a
   CPU core) in favor of fps-paced, redraw-on-change updates.
