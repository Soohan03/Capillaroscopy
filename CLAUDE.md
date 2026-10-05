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
   - Avoid the "Flow" tab — see Known Issues.
   - Controls: WASD/arrows move the two ROI rectangles, Q/E jump ±500 frames, P/space
     pause/resume. "Correlation: N/A" in the console is normal until both ROI rectangles
     are positioned over a capillary segment.

If the user reports the app froze or crashed, check the task output file for a traceback
before relaunching.

## Data layout

- `RecordedVideos/` — raw captures (currently empty)
- `StabilizedVideos/` — stabilized videos ready for analysis (8 videos as of 2026-06)
- `Reports/`, `Statistics/`, `Flows/` — generated analysis outputs

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

- **Flow tab**: historically crashed with `AttributeError: 'NoneType' object has no
  attribute 'replace'` when `Flows/` is empty; fixed in `ee10cd7`, but the tab is still
  the least exercised part of the app and its video frame class still uses the old
  `current_key` click path. Treat with care.

## Repo state notes

- `main` is at the PR #1 merge (`c3e57f4`); the earlier WIP is committed and `run_app.sh`
  is tracked. `Thesis/` (LaTeX draft + bibliography) and `.claude/` are untracked by
  choice. Ask before committing either.
