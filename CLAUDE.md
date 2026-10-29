# Capillaroscopy Analysis Tool

GUI tool (Tkinter + OpenCV) for analyzing capillaroscopy videos, built for a medical
master's thesis on standardized capillary function analysis.

## The study

KI degree project, fall 2026: "Nailfold capillary blood cell velocity in healthy
individuals: inter-day reproducibility and response to e-cigarettes and heated tobacco
products".

- **Archive:** a retrospective archive of two crossover trials, stored in DynCap.
  - ESMOKE (2019–2020): W = e-cigarette with nicotine, Q = nicotine-free.
  - ISMOKE (2020, names start `ISMOKE_`): S = heated tobacco, C = sham (no exposure).
  - W and S are the nicotine (active) visits, Q and C the controls (confirmed by the user 2026-10-29).
- **Recordings:** each visit has a recording före (before) and efter (after) the
  exposure. The FP codes restart per study.
- **Every recording is rest → occlusion → release:** about 1 min rest, then 1 min
  occlusion at 200 mmHg, then about 1 min after release. The official times are in
  `metadata/` (see its README).
- **Aim 1 (primary):** inter-day reproducibility of resting CBV from the two före
  recordings. Reported as the within-subject CV (typical error/mean), the smallest
  detectable change (2.77 × typical error), Bland–Altman and ICC(A,1).
- **Aim 2:** the before→after change on the nicotine visit (W, S) of each participant who has
  both, per study and pooled as a separate analysis; the control visit is not used. Agreed with
  the PI about a month before unblinding; `PROTOCOL.md` had recorded an older plan (all four
  recordings, active minus control) and was corrected on 2026-10-29, after unblinding.
- **Who can be used** (`metadata/README.md`, from `capillary.inventory`): aim 1 has 14 ESMOKE and
  10 ISMOKE participants (two of them to check in DynCap); aim 2 has 13 ESMOKE and 10 ISMOKE. The
  aims use 72 recordings (90 before aim 2's correction; all 90 were on the desktop, stabilized, by
  2026-10-29). Aim 2's correction added ISMOKE FP02 Sföre and Sefter and FP08 Sefter, stabilized
  but without lines on 2026-10-29.
- **Resting CBV must come from the rest window before occlusion.**
- **Protocol and results:** `PROTOCOL.md` fixes the measurement and the analysis, agreed with the PI
  on 2026-10-29: velocity round the whole loop at rest, signal-to-noise 8 or more, one reference
  capillary per recording with two ranked backups. The lines were placed blind that day and
  unblinded at 13:07. Aim 1's report: `analysis/primary_endpoint/` (Known issues has the gist).

## Change diary (mandatory)

Every session that changes code MUST append a dated entry to `DEVLOG.md` (newest
first) before finishing: branch name, commits, what changed and why, and how it was
verified. Write it detailed enough that the user can reconstruct the session without
reading the diffs — it doubles as material for the thesis methods section. Commit the
DEVLOG entry together with (or right after) the changes it describes.

## Session start routine

When the user says they want to work on / open / run the project, do this automatically
without asking:

1. Launch the app in the background via WSL (it's a blocking Tkinter mainloop, so always
   use `run_in_background: true`):
   ```
   wsl -d Ubuntu -- bash run_app.sh
   ```
   On the Mac (since 2026-10-08), from the repository: `venv/bin/python Application.py`
   (venv from Homebrew Python 3.12 with `python-tk@3.12`).
2. Check the task output briefly to confirm it started without an immediate traceback.
3. Tell the user the app window should now be visible via WSLg, and remind them:
   - The list on the left shows the recordings (raw ones in `RecordedVideos/`, with their
     stabilized copies in `StabilizedVideos/`); right-click one to stabilize it or move it to
     the trash. The 48 recordings aim 1 uses carry an "Aim 1" chip (hidden during blind
     placement); typing "aim 1" in the filter lists only them.
   - Centre line page (opens first): click points along the middle of one capillary,
     starting where the blood comes from; drag a point to move it, click on the line to
     add one, right-click a point to remove it, Backspace removes the last, X reverses.
     The space-time preview (with the slope found, velocity and signal-to-noise ratio)
     fills in once there are two points; the panel shows what the line can measure.
     For a capillary loop's resting velocity (the study's plan since 2026-10-14): choose
     "Whole loop", click from the base of one limb over the apex to the base of the other,
     press Rest and measure. The result gives the velocity pooled over the range (pattern
     shift) and which end of the line lies on the arterial limb. ("Arterial limb" lines run
     from a limb's base to the apex.) The recording's saved lines are drawn dashed.
     On a stabilized video a dashed outline shows where every frame of the range has
     picture: keep the line inside it (where the picture moved, the stabilized frame has a
     black strip along its edge); a line that leaves it is refused, with how far to move it.
   - Blind placement (the header button): only the aims' recordings are listed, under
     codes; the preview and every result are hidden; measuring uses the official rest;
     every line is saved as a whole loop; Two boxes, Results and Validation are closed. It stays
     on until turned off. `python3 -m capillary.aims --progress` checks the placement by code
     without a result; `--unblind` gives the results (the study's were unblinded on 2026-10-29).
   - Two boxes page (the original method, kept for comparison): click places box 1
     (orange, downstream), the next click box 2 (blue, upstream); WASD nudges a box.
   - On both: Space plays/pauses, ←/→ step a frame, Q/E jump ±500 frames, I/O set the
     measured range, and Rest / Occlusion / After release set it from the recording's
     official times (the timeline marks the occlusion in orange); "Measure velocity and
     save" is at the bottom right, next to the data set name and the Observer initials
     (saved with the data set).
   - Validation page (Ctrl+4): draw a reading set of 3-s blocks from centre-line data
     sets, read them blinded (drag along the streaks, N for "no clear streaks", Enter
     next), then compute the agreement; "Line placement" compares the same capillary
     measured by different observers.
   - F1 shows every keyboard and mouse control.
   - The app does not record: new videos are copied into `RecordedVideos/` (raw, to be
     stabilized) or `StabilizedVideos/`.

If the user reports the app froze or crashed, check the task output file and
`capillaroscopy.log` for a traceback before relaunching.

## Data layout

- `RecordedVideos/` — raw recordings copied in to be stabilized. On the Mac: links to the 9
  ESMOKE recordings downloaded from DynCap into `Video_inventory/` (untracked, 2026-10-08).
  On the desktop: the raw recordings themselves, copied in from OneDrive (since 2026-10-11;
  35 ESMOKE recordings by 2026-10-12, 30 of them used by the aims; 63 by 2026-10-14, among them
  all 54 the aims use; and 42 ISMOKE recordings by the end of that day, 32 of them used by the
  aims). Files copied from Windows bring `<video>:Zone.Identifier` files along;
  the app ignores them
- `StabilizedVideos/` — stabilized videos ready for analysis, made by `capillary.stabilize`.
  Each has `<stem>___stabilization.csv` (the shift of every frame) and
  `___stabilization_provenance.json` next to it; a video without them was not made by the
  current stabilizer. The app calls every video in this folder stabilized, so put nothing
  else here. Until 2026-10-11 the desktop's folder held 8 raw recordings that had never
  been stabilized (Known issues). The study need not be sorted into separate folders: ISMOKE
  names start with `ISMOKE_`, and the inventory sorts by name (on 2026-10-12 the folder was
  briefly renamed `ESMOKE_Videos/`, which the app cannot see, and renamed back)
- `Flows/` — optical-flow video of one recording, from before the flow feature was
  removed (2026-10-06); kept on disk, not shown, trashed along with its recording
- `Statistics/` — data sets (`<recording>___<name>___…`) with `…_provenance.json`, time
  points; centre-line data sets keep their space-time diagram (`___space_time.npy`)
- `Reports/` — plots and summary tables written from the data sets
- `Validation/` — reading sets (`<set>/set.json`, `blocks.npz`, `readings/`, `report/`)
  and the line-placement comparison (`line_placement/`); so far only `reading1`, the
  user's first try (6 blocks, observer "1"), drawn from video that had not been stabilized
- `.trash/` — what the app moved to the trash (one dated folder per action, subfolders
  kept); emptied only by hand
- `metadata/` (in the repository, tracked, unlike the data folders above) — the official
  occlusion and release times of every ESMOKE and ISMOKE recording, exported from
  DynCap, with notes on odd rows in its README

## Code layout

Exploratory analyses with their inputs and results live in `analysis/` (for example
`analysis/resting_flow_feasibility/`, with a README on how to rerun it).

See the table in `README.md`. The GUI is `Application.py` → `gui/app.py` (window,
recording list, keyboard routing) → one module per page (`gui/line_page.py` "Centre
line", `analyze_page.py` "Two boxes", `results_page.py`, `validation_page.py` with its
reading mode in `reading_view.py`; the two measure pages build on
`gui/measure_page.py`). Long work runs as background jobs: `gui/jobs.py` runs them,
`gui/tasks.py` holds the work and has no Tk in it. The report plots of both methods
are in `Caper.py`; stabilization is in `capillary/stabilize.py`.

The app measures velocity only. The optical-flow measurement (Flow page, flow
videos, flow data sets) was removed on 2026-10-06 because it was not a valid measure
as implemented and not an endpoint; see that DEVLOG entry. Old flow files are listed
on a recording only so that moving it to the trash takes them along. The app no
longer records either: the Capture page (camera preview and recording) was removed
on 2026-10-07, since the thesis recordings are not made with this app.

## Analysis engine (`capillary/`)

The measurement lives in the GUI-free `capillary` package; the pages, the batch CLI and
the tests all run the same arithmetic. Put new measurement code there, not in the
Tkinter classes.

- **Centre line (the primary method since 2026-10-06):** `capillary/spacetime.py`. The
  space-time diagram along a drawn line; the streak slope per 3-s block by a
  direction-contrast Radon method in the Fourier domain, with a signal-to-noise ratio,
  coherence and measurable range per block. Its module docstring explains the method;
  the 2026-10-06 DEVLOG entry how it was chosen and calibrated. The measurable range at
  30 fps is about 0.045 × line length (px) px/frame; faster flow is reported unresolved.
- **Pattern shift (since 2026-10-08):** `capillary/pattern_shift.py`. The same diagram: the
  shift of the pattern between a frame and the next 1–8, by correlation pooled over all 3-s
  blocks of a stretch (forward minus backward), with a signal-to-noise ratio (8 to count) and a
  jackknife 95% interval. It measures faint flow that single blocks miss (FP01_Qföre's limb at
  rest). Since 2026-10-11 every centre-line data set keeps it, pooled over the range and over
  each half (`pattern_shift.summarize`, keys `pattern_shift_...` in the summary); the Centre line
  and Results pages show it and the batch CLI prints it.
  - Since 2026-10-11 rows are band-passed along the line (difference of Gaussians, σ 1 and
    4 px) instead of differenced (`bandpass_px=None` reproduces the old method). On the
    recordings it resolved 5 of 29 limbs at rest instead of 3; tissue lines stayed at or below
    3.6. Validation: `analysis/pattern_shift_bandpass/`.
  - On synthetic recordings (120-px line, shutter open the whole frame): within about 1% from
    1.5 to 8 px/frame, about 5% low at 12, unresolved above. On a 300-px line round the loop:
    12–40 px/frame (0.48–1.6 mm/s) within about 1%.
  - **Slow range (2026-10-14, not the default):** `min_speed=pattern_shift.SLOW_MIN_SPEED`
    (`summarize` too) or `--slow-flow` in the batch CLI searches from 0.1 px/frame (0.004 mm/s)
    instead of 1.
    - A slow speed is scored as 1 px/frame is, on a time axis stretched by 1/speed, then refined
      with the frame distances held fixed. The default gives exactly the old results, and the
      slow range leaves results from 1 px/frame up unchanged.
    - Synthetic: 0.15–1 px/frame within 5% (median 1%), no false positives in 90 no-flow clips.
    - Real: 42 of the aim-1 check's 109 limbs at rest instead of 24.
    - But a single line cannot tell slow flow from the picture moving along it (drift, or
      uneven back-and-forth movements of 10–20 px). The recordings show both, so it is not the
      default (Known issues). Validation: `analysis/pattern_shift_slow_flow/`.
- **Arterial limb (since 2026-10-11):** the user's PI wants resting CBV from the arterial limb
  only, since velocity changes towards the venous side. A line marked as an arterial limb runs
  from the limb's base to the apex. The sign of its pooled pattern shift tells the limb
  (`pattern_shift.limb_from_direction`): towards the apex is arterial, away from it venous.
  - Saved as `line.role` in the provenance and `limb_check` (arterial, venous, unknown) in the
    summary.
  - Every data set (both methods) also saves the official phase of its range as `phase`
    (`inventory.recording_phases`: rest, occlusion, after release, or several joined by ' + ').
- **Whole loop (since 2026-10-14):** a line from the base of one limb, over the apex, to the base
  of the other (`pattern_shift.WHOLE_LOOP`). The resting CBV of the study since 2026-10-14: the user
  places the lines by hand (blind placement, `gui/blind.py`), and a recording's value is the mean
  of its counted loops (`capillary/aims.py`).
  - The sign tells which end lies on the arterial limb (`arterial_end`: start, end, unknown;
    `pattern_shift.loop_from_direction`).
  - Split at the apex (`Centreline.apex_arc_px`, the point farthest from both ends; on the aim-1
    check's 53 loops a median 1.3 px from where the traced limbs met), each limb is measured on its
    own (`pattern_shift.loop_limbs`). Limbs resolved with opposite signs along the line mean the
    picture moved (`loop_movement`); such loops are not counted.
  - The app's task reproduces `analysis/aim1_feasibility/measure.py`'s whole loops exactly (all 53,
    velocities and scores identical), and the split marks the same one loop as separately traced
    limbs did (DEVLOG 2026-10-14).
- **The aims (since 2026-10-14):** `python3 -m capillary.aims [--data <folder>] [--observer XX]`. A
  loop counts when it is a whole loop, within the official rest, resolved, without movement, on a
  stabilized video and not crossing itself; a recording's value is its reference capillary (`loop1`)
  if it counts, else the first backup that counts (`PROTOCOL.md`; `--value reference-only|mean` and
  `--min-snr` for the sensitivity analyses, `--progress` and `--unblind` for blind placement, the
  codes in `capillary/blinding.py`); loops on top of each other are listed for checking. Aim 1 per
  study: CV (typical error / mean, and on the log scale), SDC (2.77 × typical error), Bland–Altman,
  ICC(A,1). Aim 2 per study and pooled (`aims.POOLED`): the change after minus before on the
  nicotine visit, paired t-test, Wilcoxon, ratio after / before. Tables in `Reports/aims/`.
- **Two boxes (original):** `roi.py`, `intensity.py`, `velocity.py`, `measure.py`
  (fixed boxes, an explicit frame range read straight from the file), saved in the
  file formats the report has always read.
- Both save through `capillary.datasets`.
- **Recordings:** `capillary/inventory.py` parses the recording names and the official times,
  flags names and visits that do not fit, and chooses each aim's recordings (the last attempt
  with 30 s of rest). Run `python3 -m capillary.inventory [--have <video folder>] [--out <folder>]`;
  the tables are in `metadata/derived/`.
- **Stabilization:** `capillary/stabilize.py` (rewritten 2026-10-08; its docstring has the
  method and history). Translation only. The registration works on a band-passed copy of
  each frame (difference of Gaussians, σ 2 and 15 px) against two references, each averaged
  from alternate frames of a sharp frame's 25-frame neighbourhood.
  - Since 2026-10-14 every frame is first registered onto the frame before it, giving a path
    of the picture. A match below 0.3 breaks the path.
  - The references' centre is the sharpest frame where the picture usually is: within 40 px
    of the median path position and of usual mean grey, from the official rest when there is
    one.
  - A coarse search on 4× reduced frames (±160 px), then a fine normalized
    cross-correlation within 12 px of the coarse result and of where the frame should be (the
    frame before plus the step between them), so it follows large movement.
  - A frame the references do not place (match < 0.3, references disagreeing > 2 px, or at
    the search limit) is carried along the path from placed frames (`placed_by`
    'neighbours'). A stretch of path with none is 'lost', written black with no shift.
  - Shifts are re-centred on their median over the official rest (else all frames). The video
    is read from disk four times (memory stays small) and written uncompressed 8-bit grey,
    frame for frame, with bicubic interpolation.
  - Every frame's shift, how it was placed, match, disagreement, search-limit flag, step onto
    the frame before and mean grey go to `___stabilization.csv`.
  - `python3 -m capillary.stabilize <raw> --out <stabilized.avi>`.
  - **Lines stay in the picture** (since 2026-10-14): where the picture moved, a stabilized
    frame has a black strip along its edge. `stabilize.check_picture` refuses a line whose
    samples come within `EDGE_MARGIN_PX` (3 px; 2 is just enough for the bicubic blend and the
    bilinear read) of the strip in any frame of the range, or a range with lost frames. The
    Centre line page (dashed outline), the measurement job and the batch CLI use it, and a
    data set's provenance keeps the area and the line's clearance (`picture`).
- Validation on synthetic data: `capillary/simulate.py` renders capillary loops with a
  known speed and the disturbances measured in the 2019 recordings (measured on video that
  had not been stabilized; see Known issues);
  `python3 -m capillary.benchmark` compares both methods on them (~6 min; `--quick` ~12 s).
- Validation on real data (since 2026-10-07): `capillary/validation.py` (reading sets,
  blinded readings, the comparisons), `capillary/placement.py` (the same capillary
  measured by different observers, matched by line geometry and frames),
  `capillary/agreement.py` (Bland–Altman, ICC(A,1)/(C,1), kappa; checked against
  Shrout & Fleiss 1979). The protocol and statistics are in the 2026-10-07 DEVLOG entry.
- Batch: `python3 -m capillary.cli <video> --line "x1,y1;x2,y2;..." --out blocks.csv`,
  or `--roi1 x,y --roi2 x,y` for two boxes; `--start`/`--max-frames` pick the frames.
- Tests: `python3 -m pytest` (318 tests, ~50 s; synthetic videos with known velocity,
  the agreement statistics, simulated observers, plus the GUI's non-visual logic; no
  display needed)

Velocities computed before 2026-09-17 are biased — the lag was one frame too large on
every (odd) report window. See the 2026-09-17 DEVLOG entry; `--legacy-lag` reproduces
the old numbers. Data sets saved by the old GUI (before the 2026-10-05 rebuild) store
frame k+1 at index k, so their times read 33 ms early; velocities are unaffected. See
the 2026-10-05 GUI rebuild entry.

## Known issues

- **Aim 1 as the protocol fixed it** (unblinded 2026-10-29, `analysis/primary_endpoint/`).
  - 91 of 200 whole loops count, and 54 of 90 recordings have a value. Of the rest, 69 loops scored
    below 8, a median of 3.4 (no moving pattern), and 36 scored high (median 35) but sat at the
    slowest speed searched, 1 px/frame (0.040 mm/s): slow flow or slow movement of the picture,
    which one line cannot tell apart (the slow range below). Counting them would add 14 recordings
    and 1 ESMOKE and 3 ISMOKE participants to aim 1: a decision for the PI.
  - ESMOKE: 7 of 14 participants, CV 67% (95% CI 43–147%), ICC(A,1) 0.01; ISMOKE: 2 of 10.
    Thresholds from 6.5 to 9 change nothing; the mean of the counted loops gives CV 65%.
  - Post hoc, not agreed with the PI (`analysis/coarse_filter/`, plan committed before its checks): loops the
    protocol doesn't resolve, measured again with rows band-passed at σ 4–16 px from 5 px/frame, pass every
    check (no false flow in synthetic loops or the occlusion; same direction after release). ESMOKE 9
    participants, CV 69%, ICC 0.31 (−0.39 to 0.79). The added loops are faster (median 0.38 against 0.08 mm/s):
    the protocol counts mainly slow capillaries, but adding the fast ones doesn't make CBV more reproducible.
  - Aim 2 as agreed (computed 2026-10-29 19:05, after the corrected protocol's three new recordings were placed
    blind; none of their loops counted): the change after minus before nicotine, ESMOKE 5 of 13 participants
    −0.087 mm/s (−0.204 to 0.030, p 0.11), ISMOKE 3 of 10 −0.042 (p 0.30), pooled 8 of 23 −0.070 (−0.137 to
    −0.003, p 0.043; ratio 0.55). 7 of 8 decreased; no control visit, few pairs, three tests without correction.
  - Fixed before unblinding: returning to a recording seen before restored its earlier line's
    role, which carried over, so 29 lines were saved without the whole-loop role. They were
    re-saved from their own diagrams (`analysis/primary_endpoint/relabel_whole_loops.py`), and the
    app now fixes the role during blind placement.
- **Resting flow** (revised 2026-10-08). The earlier note said resting flow was beyond the
  centre line's range (0.5–1 mm/s, from near-horizontal streaks). That rested on video that
  had never been stabilized (thought on 2026-10-08 to be MPEG-4-compressed; found to be the
  raw recording on 2026-10-11) and on how the diagram looked.
  - On the lossless re-stabilized FP01_Qföre, the left limb of the tall loop (112 px) moves at
    about 0.08 mm/s at rest: pattern shift pooled over the minute of rest, signal-to-noise 13.7,
    each half agreeing (0.084 / 0.080 mm/s).
  - The right limb runs the opposite way at about 0.12 mm/s (signal-to-noise 5.8, a 76-px
    line); tissue beside the loop shows nothing.
  - So on this capillary resting flow lies within the centre line's range, but it is too faint
    for single 3-s blocks (signal-to-noise about 4).
  - The near-horizontal streaks were probably the change of the whole vessel at once, as the
    unstabilized picture moved.
  - A first feasibility check (6 recordings, 24 limbs, `analysis/resting_flow_feasibility/`,
    interrupted): resting flow was resolved in 3 limbs (0.08–0.12 mm/s), with a few more near
    the threshold. Most capillaries show no moving pattern at rest at all (their space-time
    pictures are noise), so they cannot be measured from these videos at 30 fps. Aim 1 needs a
    rule for choosing capillaries with visible plasma gaps.
  - **Aim 1's feasibility** (2026-10-12, `analysis/aim1_feasibility/`): 15 före recordings of 8
    ESMOKE participants, 109 limbs placed by Claude Code on the resting image.
    - The pattern shift resolved 24 limbs at rest (16 robust), at 0.04–0.14 mm/s.
    - 18 more scored high at its slowest speed. Adding the centre-line blocks for flow below
      0.04 mm/s (an exploratory rule: 25% of blocks resolved, 90% one way) measures 30 limbs.
    - All 12 loops with both limbs measured then run opposite ways, and no tissue line shows
      flow.
    - An arterial limb at both visits in 1 of 7 participants (any limb in 4). Arterial-only
      resting CBV looks infeasible with these videos. The choice (any limb? the combined rule?)
      is for the supervisors.
    - **Rerun on the re-stabilized videos** (2026-10-14, `analysis/aim1_feasibility/restabilized/`):
      the same lines moved onto them, FP01_W added (none of its 6 limbs resolved).
      - Almost nothing changed: 23 of 115 limbs resolved (3 limbs near the threshold changed,
        both ways), and velocities agree within 0.005 mm/s.
      - Of 8 participants, an arterial limb at both visits in 0–3 and any limb in 2–5, by rule.
      - A sub-pixel change of a line moves its score by about 5%, so limbs within about 1.5 of
        the threshold of 8 can fall either side of it.
    - **Whole-loop lines** (2026-10-14, `analysis/whole_loop/`): one line up one limb, over the
      apex and down the other, joined from the traced limbs (`measure.py`, kind `loop`).
      - At the app's rule: 23 of 53 loops against 14 by their single limbs. 5 of 8 participants
        have a loop at both visits, against 2 by limbs.
      - The gain is signal (score a median 1.6 times the better limb's), not range: the limbs saw
        the same flow too weakly.
      - Not counted when both limbs run the same way (movement).
      - In the occlusion: none of the 21 loops measured at rest shows flow.
      - The app has measured whole loops since 2026-10-14 (Whole loop on the Centre line page).
      - As a per-visit mean (`capillary.aims` on the app's measurement of the same loops): 13 of 15
        recordings with loops have a mean, from 1–3 loops (median 2); 5 of 8 participants have one
        at both visits. CV 26%, ICC(A,1) 0.12 (−0.15 to 0.73): too few participants to judge. Loops
        of one recording differ up to 3.4-fold, so with about 2 per visit the choice of loops alone
        moves the mean by roughly 40% between days. The W visit's mean was higher in all 5 (1.4–2.8×,
        both before exposure; chance 1 in 16).
  - **The pattern shift's slow range** (2026-10-14, `analysis/pattern_shift_slow_flow/`) replaces
    the combined rule's centre-line blocks in principle. On the same 109 limbs at rest:
    - it resolved 42 (17 below 1 px/frame);
    - loops with both limbs resolved: 14 opposite, 4 the same way;
    - it agreed in direction with all 16 limbs whose blocks qualified (median ratio 0.96);
    - a limb at both visits in 3 of 7 participants, an arterial one in 2;
    - on the re-stabilized videos (rerun above) 41 of 115. Below 1 px/frame its speed can change
      by up to 2.6 times with a sub-pixel change of the line.
  - **Movement of the picture looks like slow flow** (found 2026-10-14). Below 1 px/frame a line
    cannot tell the blood moving from the picture moving along it.
    - FP03_Wföre's loops E and F move the same way in all four limbs at rest (signal-to-noise
      23–63). On the re-stabilized videos this was the stabilizer's black strip, not the picture
      moving: all four limbs reach it at rest, and on the stretches they keep clear of it the
      slow flow is gone (E left: signal-to-noise 3.3–3.6 against 68.5). Such lines have been
      refused since 2026-10-14 (`stabilize.check_picture`, DEVLOG).
    - In the occlusion, when the blood should stand still, 24 of 97 limbs gave a slow speed:
      - FP13_Qföre's loop E bows sideways and back in both limbs;
      - FP13_Qföre G left is crossed by the stabilized frame's black strip (refused since
        2026-10-14);
      - FP05_Qföre's loop B looks like real residual flow.
      - On the re-stabilized videos 6 of the 22 such limbs read the black strip (FP03_Wföre A, E,
        F; FP13_Qföre G left). The other 16 are not explained by it.
    - In synthetic clips with still cells, uneven movements of 10–20 px over a few seconds read
      as flow in 2–4 of 10, a steady drift always, and 2-px movements never.
    - From 1 px/frame up none of this reached the threshold. A check that the picture held still
      near the line (for example the tissue beside it) would make the slow range usable.
    - The re-stabilized videos did not remove it: in the occlusion, 22 of the same 91 limbs
      against 23 before.
- **Lines near the edge of a picture that moved** (2026-10-14). A line must stay clear of the
  stabilizer's black strip in every frame of its range, so on a recording that moved a lot at
  rest it can only lie in the part of the frame every rest frame shows (the dashed outline).
  - Over the official rest that part is a median 92% of the frame on the 60 aims recordings on
    the desktop (10th percentile 77%); below 75% on 6: FP03_Qföre 53%, FP03_Wföre 54%, FP06_Wföre
    59%, FP06_Qefter_försök2 69%, FP07_Qföre 70%, and FP03_Wefter 0%.
  - FP03_Wefter moved more than 250 px up and down during its rest, so no line on it can be
    measured over the whole rest (blind placement measures nothing else). A line in its middle
    reaches the strip in only 125 of its 2121 rest frames.
  - Not built: measuring only the frames in which a line lies in the picture. It would recover
    such lines, but which frames count is a methods decision for the PI.
- **Large movements** (found 2026-10-08, fixed 2026-10-14 by following the movement frame to
  frame).
  - FP01_W (references were built in its darkening last seconds) and FP03_Wefter
    (excursions of 100–200 px at rest) now stabilize: the match at rest is 0.85 and 0.74, and
    their resting mean images are sharp.
  - FP01_W's last 8 s are dark and lost.
  - FP03_Qföre moves about 500 px when the cuff goes on, to a view that shares almost nothing
    with the rest. From then on it is lost; its rest is as before, now centred.
  - Building the references in the rest lowers the match in later phases where the old
    references lay there, though the frames stay where they were (median within 1 px). In
    the occlusion: FP03_Wföre 0.66 → 0.57, FP06_Qföre 0.75 → 0.36, the four FP12 about
    0.85 → 0.50. At rest the match rose in 16 of 18 such recordings (FP12_Wföre
    0.42 → 0.87).
  - All 33 videos in `StabilizedVideos/` were re-made with it on 2026-10-14; the old ones are in
    `.trash/`. The new centring moved their picture by 2–169 px (median 25), so lines placed
    on the old videos (`analysis/aim1_feasibility/lines.json`, the slow-range validation's)
    no longer fit (DEVLOG). They were moved onto the new videos in
    `analysis/aim1_feasibility/restabilized/` (`--dir restabilized` for the aim-1 scripts and
    `validate_real.py`).
- **The two-box method failed on the 2019 recordings** (found 2026-10-06): about
  70% of a box's signal changes along the whole vessel at once, so the delay comes out
  as zero ("too fast to resolve") even where the flow is slow, and the existing two-box
  data sets are unreliable. `set1` of `FP01_Wefter_14-Oct-2019_10-13-03` has its boxes
  in still tissue next to a capillary and measured noise.
  - This was found on video that had never been stabilized (2026-10-11). A vessel moving
    under fixed boxes changes every position at once, so test the method again on
    stabilized video before ruling it out.
- **Centre-line limits:** at 30 fps a line follows flow up to about 0.0018 × its length
  in px, in mm/s (0.18 mm/s for 100 px); normal resting velocities need long lines or a
  faster camera. With no flow but strong jitter, the benchmark still resolves ~7–11% of
  blocks at about 0.2 px/frame, so a near-stasis vessel shows as "few blocks resolved".
- **Stabilization** (2026-10-08): the registration is new.
  - Checked on synthetic moves of up to 25 px (error under 0.08 px) and on two recordings
    (DEVLOG):
    - FP01_Qföre moves about 28 px. Edge similarity is better than the old registration's
      in occlusion and after release.
    - FP03_Wföre is dark, with low contrast, and swings by about 200 px with breathing.
      It stays aligned throughout, with a median match of about 0.6.
  - Any video stabilized before the new registration is off by up to 5.6 px where the
    image had moved far; re-stabilize it. (All of the desktop's were re-made on 2026-10-14.)
  - Translation only: local deformation is not corrected. The match falls during the
    occlusion on FP01_Qföre (0.92 at rest with the earlier references, 0.75 in occlusion);
    changed content or deformation, not told apart.
  - The settings were chosen on these two recordings. Check each recording's summary in
    the shift file: match, disagreement, frames at the search limit.
  - FP03_Wföre's first frame is offset by about 42 px from the second, probably a
    camera start-up artefact.
- **The desktop's first "stabilized" videos had never been stabilized** (found 2026-10-11).
  The 8 files in `StabilizedVideos/` (copied in June 2026) were the raw DynCap recordings:
  uncompressed 8-bit grey, with the raw downloads' frame counts. The registration finds the
  same movement in them as in the Mac's raw downloads, to 0.1 px. At rest they moved
  10–143 px; a capillary limb is 8–15 px wide.
  - Everything measured on the desktop before 2026-10-11 was measured on a moving picture:
    the two-box data sets (`Test`, `Test2` of FP01_Qefter 09-46-17, `set1` of FP01_Wefter
    10-13-03), the centre-line `set1` and `set2` of FP01_Qefter 09-46-17,
    `Validation/reading1`, and the real-data numbers the simulator was calibrated on.
  - The files were moved to `RecordedVideos/` and stabilized (DEVLOG 2026-10-11).
- **Frame rate unverified:** the recordings come from the DynCap archive, and the local
  copies are stamped 30 fps. Every velocity scales with the true rate.
  - FP01_Qföre agrees with its official times at 30 fps.
  - `FP01_Wefter_14-Oct-2019_10-07-49` does not: its release at 230.1 s fits its 3435
    frames only at 15 fps (see `metadata/README.md`).
  - Earlier notes that these videos were made by this app's old recorder (MP4V, 30-fps
    stamp) rested on circular evidence and do not hold.

## Repo state notes

- Work happens in the private repo `Soohan03/Capillaroscopy` (`origin`);
  `Widaeus/capillaroscopy` is `upstream`, used only to pull updates. `main` is protected:
  make changes on a branch and open a pull request. `Thesis/` (LaTeX draft + bibliography,
  from July and outdated; the user keeps the current report elsewhere) and `.claude/` are
  untracked by choice. Ask before committing either.
