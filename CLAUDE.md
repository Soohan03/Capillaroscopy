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

## Known issues

- **Flow tab crash**: clicking "Flow" always raises `AttributeError: 'NoneType' object has
  no attribute 'replace'` in `Caper.py` (`Video.__init__`), because `Flow_Frame`'s
  `ParticipantList` is built from `Flows/` (empty), which resets `selected_item` to `None`,
  and `Caper.Video.__init__` doesn't handle `path=None`. This freezes the app's update loop
  (no traceback recovery). Not yet fixed.

## Repo state notes

- `Application.py`, `Caper.py`, `settings.csv`, `FrameClasses.py` have uncommitted WIP
  changes (camera fallback handling, settings path fix, StabilizedVideos fallback for the
  Analyze tab list). `run_app.sh` is an untracked helper script. Ask before committing.
