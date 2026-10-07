# Capillaroscopy Analysis Tool

GUI tool (Tkinter + OpenCV) for analyzing capillaroscopy videos, built for a medical
master's thesis on standardized capillary function analysis.

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
2. Check the task output briefly to confirm it started without an immediate traceback
   (camera-not-found warnings are normal and harmless).
3. Tell the user the app window should now be visible via WSLg, and remind them:
   - The list on the left shows the recordings (the 8 videos in `StabilizedVideos/`);
     right-click one to stabilize it or move it to the trash.
   - Centre line page (opens first): click points along the middle of one capillary,
     starting where the blood comes from; drag a point to move it, click on the line to
     add one, right-click a point to remove it, Backspace removes the last, X reverses.
     The space-time preview (with the slope found, velocity and signal-to-noise ratio)
     fills in once there are two points; the panel shows what the line can measure.
   - Two boxes page (the original method, kept for comparison): click places box 1
     (orange, downstream), the next click box 2 (blue, upstream); WASD nudges a box.
   - On both: Space plays/pauses, ←/→ step a frame, Q/E jump ±500 frames, I/O set the
     measured range; "Measure velocity and save" is at the bottom right.
   - F1 shows every keyboard and mouse control.
   - The Capture page has no camera under WSL unless a USB camera is attached to Linux.

If the user reports the app froze or crashed, check the task output file and
`capillaroscopy.log` for a traceback before relaunching.

## Data layout

- `RecordedVideos/` — raw captures (currently empty)
- `StabilizedVideos/` — stabilized videos ready for analysis (8 videos as of 2026-06)
- `Flows/` — optical-flow video of one recording, from before the flow feature was
  removed (2026-10-06); kept on disk, not shown, trashed along with its recording
- `Statistics/` — data sets (`<recording>___<name>___…`) with `…_provenance.json`, time
  points; centre-line data sets keep their space-time diagram (`___space_time.npy`)
- `Reports/` — plots and summary tables written from the data sets
- `.trash/` — what the app moved to the trash (one dated folder per action, subfolders
  kept); emptied only by hand

## Code layout

See the table in `README.md`. The GUI is `Application.py` → `gui/app.py` (window,
recording list, keyboard routing) → one module per page (`gui/line_page.py` "Centre
line", `analyze_page.py` "Two boxes", `capture_page.py`, `results_page.py`; the two
measure pages build on `gui/measure_page.py`). Long work runs as background jobs:
`gui/jobs.py` runs them, `gui/tasks.py` holds the work and has no Tk in it.
Stabilization and the report plots of both methods are in `Caper.py`.

The app measures velocity only. The optical-flow measurement (Flow page, flow
videos, flow data sets) was removed on 2026-10-06 because it was not a valid measure
as implemented and not an endpoint; see that DEVLOG entry. Old flow files are listed
on a recording only so that moving it to the trash takes them along.

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
- **Two boxes (original):** `roi.py`, `intensity.py`, `velocity.py`, `measure.py`
  (fixed boxes, an explicit frame range read straight from the file), saved in the
  file formats the report has always read.
- Both save through `capillary.datasets`.
- Validation: `capillary/simulate.py` renders capillary loops with a known speed and the
  disturbances measured in the 2019 recordings; `python3 -m capillary.benchmark`
  compares both methods on them (~6 min; `--quick` ~12 s).
- Batch: `python3 -m capillary.cli <video> --line "x1,y1;x2,y2;..." --out blocks.csv`,
  or `--roi1 x,y --roi2 x,y` for two boxes; `--start`/`--max-frames` pick the frames.
- Tests: `python3 -m pytest` (184 tests, ~20 s; synthetic videos with known velocity,
  plus the GUI's non-visual logic; no display needed)

Velocities computed before 2026-09-17 are biased — the lag was one frame too large on
every (odd) report window. See the 2026-09-17 DEVLOG entry; `--legacy-lag` reproduces
the old numbers. Data sets saved by the old GUI (before the 2026-10-05 rebuild) store
frame k+1 at index k, so their times read 33 ms early; velocities are unaffected. See
the 2026-10-05 GUI rebuild entry.

## Known issues

- **The two-box method is not valid on the 2019 recordings** (found 2026-10-06): about
  70% of a box's signal changes along the whole vessel at once, so the delay comes out
  as zero ("too fast to resolve") even where the flow is slow, and the existing two-box
  data sets are unreliable. `set1` of `FP01_Wefter_14-Oct-2019_10-13-03` has its boxes
  in still tissue next to a capillary and measured noise.
- **Centre-line limits:** at 30 fps a line follows flow up to about 0.0018 × its length
  in px, in mm/s (0.18 mm/s for 100 px); normal resting velocities need long lines or a
  faster camera. With no flow but strong jitter, the benchmark still resolves ~7–11% of
  blocks at about 0.2 px/frame, so a near-stasis vessel shows as "few blocks resolved".
- **Stabilization is off by one frame** (found in the 2026-10-05 clean-up): frame 0 of
  a video stabilized by the app is black, frame k holds recorded frame k-1, and the last
  recorded frame is dropped. The 8 existing videos in `StabilizedVideos/` do not show
  this, so they were not made by the current stabilizer.
- **Stabilization needs the whole video in memory twice, as float64**: about 21 GB for
  one of the existing 2–3 minute clips. The app refuses to start a stabilization that
  would need more than 85% of the available memory, instead of crashing.
- Recordings are stamped 30 fps whatever the camera delivers; the Capture page warns
  when the measured rate differs by more than 5%. Recording has not been tried with a
  real camera since the rebuild (none is reachable under WSL).

## Repo state notes

- Work happens in the private repo `Soohan03/Capillaroscopy` (`origin`);
  `Widaeus/capillaroscopy` is `upstream`, used only to pull updates. `main` is protected:
  make changes on a branch and open a pull request. `Thesis/` (LaTeX draft + bibliography)
  and `.claude/` are untracked by choice. Ask before committing either.
