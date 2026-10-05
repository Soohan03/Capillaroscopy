# Development Log

Diary of all changes made to the capillaroscopy analysis tool. Every session
that changes code gets a dated entry: what branch, what changed, why, and how
it was verified. Newest entries first.

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
