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
   - The Analyze tab lists videos from `StabilizedVideos/` (since `RecordedVideos/` is empty).
   - Click places ROI box 1 (white), Ctrl+click places box 2 (black). WASD/arrows move
     both boxes, Q/E jump ±500 frames, P/space pause/resume. The "Correlation" readout
     shows N/A until both boxes sit on a capillary segment.
   - Middle-click a video in the list for its options (stabilize, calculate flow, delete).
   - The Flow tab is the least exercised part of the app; its 2026-09-17 drag fix has
     not been confirmed by hand yet.

If the user reports the app froze or crashed, check the task output file for a traceback
before relaunching.

## Data layout

- `RecordedVideos/` — raw captures (currently empty)
- `StabilizedVideos/` — stabilized videos ready for analysis (8 videos as of 2026-06)
- `Reports/`, `Statistics/`, `Flows/` — generated analysis outputs

## Code layout

See the table in `README.md`. The GUI is `Application.py` → one tab module per tab
(`Analyze_Frame`, `Flow_Frame`, `Camera_Frame`) → widgets in `FrameClasses.py` → video,
stabilization, flow and report classes in `Caper.py`.

## Analysis engine (`capillary/`)

The measurement — ROI geometry, per-frame intensity sampling, cross-correlation lag,
velocity — lives in the GUI-free `capillary` package. `Caper.py` calls into it, so the
Analyze tab, the batch CLI and the tests all run the same arithmetic; put new
measurement code there, not in the Tkinter classes.

- Batch: `python3 -m capillary.cli <video> --roi1 x,y --roi2 x,y --out report.csv`
- Tests: `python3 -m pytest` (78 tests, ~8 s; synthetic videos with known velocity)

Velocities computed before 2026-09-17 are biased — the lag was one frame too large on
every (odd) report window. See the 2026-09-17 DEVLOG entry; `--legacy-lag` reproduces
the old numbers.

## Known issues

Found during the 2026-10-05 clean-up and deliberately left unchanged (see that DEVLOG
entry for details):

- **Stabilization is off by one frame**: frame 0 of a video stabilized by the app is
  black, frame k holds recorded frame k-1, and the last recorded frame is dropped. The 8
  existing videos in `StabilizedVideos/` do not show this, so they were not made by the
  current stabilizer.
- Opening any popup re-binds the main window's close button to that popup, so the
  window's X no longer quits the app afterwards (Escape still does).
- Visiting the Capture tab replaces the window's key bindings, so the Analyze/Flow
  keyboard controls stop working until restart; P/space on the Capture tab raises an
  AttributeError (the camera object has no `pause`).
- The Save-report popup warns "the file was not saved" for names with spaces or
  non-ASCII characters, but the data is saved under that name anyway.
- Flow tab "Generate report" without saved flow data raises `UnboundLocalError`.
- "Stabilize all videos" / "Calculate flow for all" with nothing left to process raise
  `IndexError`.
- The camera is never released when leaving the Capture tab.

## Repo state notes

- Work happens in the private repo `Soohan03/Capillaroscopy` (`origin`);
  `Widaeus/capillaroscopy` is `upstream`, used only to pull updates. `main` is protected:
  make changes on a branch and open a pull request. `Thesis/` (LaTeX draft + bibliography)
  and `.claude/` are untracked by choice. Ask before committing either.
