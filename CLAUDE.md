# Capillaroscopy Analysis Tool

GUI tool (Tkinter + OpenCV) for analyzing capillaroscopy videos, built for a medical
master's thesis on standardized capillary function analysis.

## The study

KI degree project, fall 2026: "Nailfold capillary blood cell velocity in healthy
individuals: inter-day reproducibility and response to e-cigarettes and heated tobacco
products".

- **Archive:** a retrospective archive of two crossover trials, stored in DynCap.
  - ESMOKE (2019–2020): W = e-cigarette with nicotine, Q = nicotine-free.
  - ISMOKE (2020, names start `ISMOKE_`): S = heated tobacco, C = no exposure.
- **Recordings:** each visit has a recording före (before) and efter (after) the
  exposure. The FP codes restart per study.
- **Every recording is rest → occlusion → release:** about 1 min rest, then 1 min
  occlusion at 200 mmHg, then about 1 min after release. The official times are in
  `metadata/` (see its README).
- **Aim 1 (primary):** inter-day reproducibility of resting CBV from the two före
  recordings. Reported as the within-subject CV (typical error/mean), the smallest
  detectable change (2.77 × typical error), Bland–Altman and ICC(A,1).
- **Aim 2:** the difference in before→after change, active minus control.
- **Who can be used** (`metadata/README.md`, from `capillary.inventory`): aim 1 has 14 ESMOKE and
  10 ISMOKE participants (two of them to check in DynCap); aim 2 has 13 ESMOKE and 8 ISMOKE. The
  aims use 90 recordings; 8 of them had been downloaded by 2026-10-09.
- **Resting CBV must come from the rest window before occlusion.**

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
     the trash.
   - Centre line page (opens first): click points along the middle of one capillary,
     starting where the blood comes from; drag a point to move it, click on the line to
     add one, right-click a point to remove it, Backspace removes the last, X reverses.
     The space-time preview (with the slope found, velocity and signal-to-noise ratio)
     fills in once there are two points; the panel shows what the line can measure.
   - Two boxes page (the original method, kept for comparison): click places box 1
     (orange, downstream), the next click box 2 (blue, upstream); WASD nudges a box.
   - On both: Space plays/pauses, ←/→ step a frame, Q/E jump ±500 frames, I/O set the
     measured range; "Measure velocity and save" is at the bottom right, next to the
     data set name and the Observer initials (saved with the data set).
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
  On the desktop: the raw recordings themselves, copied in from OneDrive (since 2026-10-11)
- `StabilizedVideos/` — stabilized videos ready for analysis, made by `capillary.stabilize`.
  Each has `<stem>___stabilization.csv` (the shift of every frame) and
  `___stabilization_provenance.json` next to it; a video without them was not made by the
  current stabilizer. The app calls every video in this folder stabilized, so put nothing
  else here. Until 2026-10-11 the desktop's folder held 8 raw recordings that had never
  been stabilized (Known issues)
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
  rest) and, on synthetic recordings, 1–12 px/frame within 1–2%. The batch CLI prints it for a
  line; the app does not show it yet.
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
  from alternate frames of the sharpest frame's 25-frame neighbourhood.
  - A coarse search on 4× reduced frames (±160 px), then a fine normalized
    cross-correlation within 12 px of the coarse result and of the previous frame's
    position, so it follows large movement.
  - Shifts are re-centred on their median. The video is read from disk three times
    (memory stays small) and written uncompressed 8-bit grey, frame for frame, with bicubic
    interpolation.
  - Every frame's shift, match, disagreement and search-limit flag go to
    `___stabilization.csv`.
  - `python3 -m capillary.stabilize <raw> --out <stabilized.avi>`.
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
- Tests: `python3 -m pytest` (257 tests, ~25 s; synthetic videos with known velocity,
  the agreement statistics, simulated observers, plus the GUI's non-visual logic; no
  display needed)

Velocities computed before 2026-09-17 are biased — the lag was one frame too large on
every (odd) report window. See the 2026-09-17 DEVLOG entry; `--legacy-lag` reproduces
the old numbers. Data sets saved by the old GUI (before the 2026-10-05 rebuild) store
frame k+1 at index k, so their times read 33 ms early; velocities are unaffected. See
the 2026-10-05 GUI rebuild entry.

## Known issues

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
- **Large movements defeat the stabilizer** (found 2026-10-08). On FP01_W (a steady drift of about
  200 px), FP03_Qföre (after the cuff) and FP03_Wefter (jumps of 100–200 px at rest) the match
  falls to 0.1–0.3. Planned fix: follow the movement outwards from the reference frame in both
  directions in time.
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
    image had moved far; re-stabilize it.
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
