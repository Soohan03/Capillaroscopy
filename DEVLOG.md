# Development Log

Diary of all changes made to the capillaroscopy analysis tool. Every session
that changes code gets a dated entry: what branch, what changed, why, and how
it was verified. Newest entries first.

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
2. Stream video processing: `Video.load` still allocates two float64 arrays
   covering the whole video (~26 GB for a 60 s clip) — stabilization of
   long videos will exhaust memory.
3. Save analysis provenance (ROI coordinates, rectangle size, window
   parameters, git hash) as a JSON sidecar with every report.
4. Worker thread/process for stabilization/flow instead of one frame per
   UI tick.
5. Consider `skimage.registration.phase_cross_correlation` to replace the
   custom DFT registration, and `cv2.DISOpticalFlow` to replace Farneback.
6. Statistics layer: aggregate per-participant results into one tidy CSV.
7. Retire the 1 ms `after()` busy-loop (renders even when paused; pins a
   CPU core) in favor of fps-paced, redraw-on-change updates.
