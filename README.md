# Capillaroscopy Analysis Tool

A desktop tool (Tkinter + OpenCV) for analysing nailfold capillaroscopy
videos: it stabilizes a recording and measures red-cell velocity in a
capillary, along a line drawn on the vessel or between two boxes. Videos are
recorded with other software and copied into the data folder (the app's own
recorder was removed on 2026-10-07).

## Using the app

The window has a list of recordings on the left (everything that shares one
video's name: raw recording, stabilized copy, data sets) and four pages:

| Page | What you do there |
| --- | --- |
| **Centre line** | Click points along the middle of one capillary, starting where the blood comes from. A live preview shows the space-time diagram of the frames around the playhead with the slope it found, the velocity and its signal-to-noise ratio, and which velocities this line can measure. Choose a frame range (for a recording of the study, **Rest**, **Occlusion** or **After release** from its official times), name the data set, press **Measure velocity and save**. The result gives the velocity pooled over the range (pattern shift) and that of the 3-s blocks. For the resting velocity of an arterial limb, tick **Arterial limb** and draw the line from the base of the limb to the apex: the direction of the flow then shows whether it is the arterial limb. |
| **Two boxes** | The original method: place box 1 (downstream, orange) and box 2 (upstream, blue) on a capillary; the velocity comes from the delay between their brightness signals. Kept for comparison and for the data sets made with it (see below). |
| **Results** | The files, time points and saved data sets of a recording, with their reports. Reports can be regenerated, data sets moved to the trash, and the line or boxes of a data set restored on its page. |
| **Validation** | Checks the centre-line velocity on real recordings, where there is no ground truth. A *reading set* draws 3-s blocks from centre-line data sets; observers read them by hand, blinded, by drawing lines along the streaks; the agreement with the estimator, between observers and between two sessions of one observer is computed with Bland–Altman limits, intraclass correlation and kappa. *Line placement* compares data sets of the same capillary measured by different observers (or twice by one). |

A measurement reads the chosen frame range straight from the video file with
the line (or boxes) held fixed, so it takes seconds rather than the length of
the clip, and it is fully described by its parameters. Each data set gets a
small `…_provenance.json` file beside it that records the line or box
positions, frame range, calibration, estimator settings, video and code
version it was made with, and the observer (initials) entered next to its
name.

Stabilizing runs in the background (right-click a recording, or the **⋯** menu
above the list for all at once); you can keep working meanwhile. Press **F1**
for all keyboard and mouse controls.

Nothing is deleted outright: replaced or removed videos and data sets go to
`.trash/` in the data folder, keeping their subfolders, so they can be put back
by hand.

## How a recording is stabilized

The skin moves under the microscope, so before measuring every frame is moved
back into place (`capillary/stabilize.py`); only translation is corrected.

1. The registration works on a band-passed copy of each frame (difference of
   Gaussians, σ 2 and 15 px). It removes pixel noise and the uneven lighting,
   which stays with the camera while the skin moves.
2. The sharpest frame and the 12 frames on each side of it are aligned onto it
   and averaged, alternately, into two references. Averaging smooths out the
   moving blood, which makes a single frame a noisy reference.
3. Each frame is found in both references, to a fraction of a pixel. A coarse
   search on reduced frames reaches a third of the frame. The previous frame's
   position is a second starting point, so the search can follow a recording
   that moves further than that: FP03_Wföre swings by about 200 px with
   breathing.
4. Each frame is moved by the mean of the two results, re-centred on the
   recording's median position, with bicubic interpolation.

The stabilized video is written frame for frame and uncompressed (8-bit grey,
like the recordings from DynCap). Next to it, `<recording>___stabilization.csv`
holds the shift of every frame and how sure it is: how well the frame matched
the references, how far apart the two references' results were, and whether
the match lay at the edge of the search. The video is read from disk three
times and never held in memory, so recordings of any length can be
stabilized; a 3-minute recording takes about 2–3 minutes.

## How velocity is measured

**Centre line (since 2026-10-06).** Along the drawn line the brightness is
sampled in every frame (averaged over 5 pixels across the line). Stacked over
time this is the *space-time diagram*: red cells and plasma gaps moving along
the vessel draw slanted streaks in it, and the slope of the streaks is their
speed. The slope is found in 3-s blocks with a Radon-transform method
evaluated in the Fourier domain (`capillary/spacetime.py` explains it in
full). Brightness changes that happen along the whole vessel at once, the
power of a pattern moving the opposite way, and noise are subtracted out by
comparing every line in the spectrum with its mirror image. Each block gets a
signal-to-noise ratio and a coherence (the share of its energy on the slope
found); blocks with a ratio below 8, a coherence below 0.03, or a speed outside
the measurable range count as unresolved and are left out of the median.

The measurable range depends on the line and the frame rate. At 30 fps the
fastest speed a line of *L* pixels can follow is about 0.045 × *L* pixels per
frame (at 1.33 µm per pixel: 0.18 mm/s for a 100-px line, 0.35 mm/s for
200 px); faster flow is reported as unresolved, not as a wrong number. The
page shows the range for the line drawn.

**Pattern shift (since 2026-10-08).** The same diagram, read another way: how
far the pattern along the line moves between a frame and the next few (1–8
frames later). Rows are band-passed along the line (patterns of about 4–30 px:
cells and plasma gaps), correlated at every shift, forward minus backward, and
pooled over all 3-s blocks of a stretch such as the minute of rest
(`capillary/pattern_shift.py`). Pooling is what makes faint patterns
measurable. On FP01_Qföre the resting flow of a capillary limb, about
0.08 mm/s, was too faint for single 3-s blocks of the centre line (8 of 123
resolved) but clear over the minute of rest, with each half of the minute
agreeing. The estimate comes with a signal-to-noise ratio (8 to count) and a
95% interval. On synthetic recordings it is within about 1% from 1.5 to
8 px/frame (0.06–0.32 mm/s at 30 fps) on a 120-px line and reads about 5% low
at 12 px/frame (0.48 mm/s); faster flow, smeared by the shutter, is reported
as unresolved. A longer line reaches further: round a whole simulated loop
(300 px), 0.48–1.6 mm/s were measured within about 1%. Until 2026-10-11 the
rows were differenced instead; on the recordings band-passing resolved more
limbs (5 against 3 of 29 at rest) and stayed lower on lines through tissue
(`analysis/pattern_shift_bandpass/`). Since 2026-10-11 every centre-line data
set keeps the pattern shift of its whole range and of each half (the halves
show whether the flow stayed the same), and the batch command prints them for
a line (below).

**The arterial limb (since 2026-10-11).** Resting velocity is measured on the
arterial limb of a capillary loop, since the velocity changes towards the
venous side. Blood flows up the arterial limb to the apex and down the venous
limb, so a line drawn from a limb's base to the apex shows which limb it is by
the direction of the pooled flow: towards the apex in the arterial limb. A line
marked as an arterial limb saves this check with its data set
(`limb_check`: arterial, venous, or unknown when the flow is not resolved),
and the range's official phase (`phase`: rest, occlusion, after release, or
several).

**Two boxes (the original method).** The delay between the brightness signals
of two boxes on the vessel, found by cross-correlation in windows of
201–301 frames, gives the velocity as distance ÷ delay. In the 2019
recordings about 70% of what a box on a capillary sees is a change of the
whole vessel at once (probably small movements or focus), which both boxes see
simultaneously, so the delay comes out as zero ("too fast to resolve") even
where the flow is slow. See the 2026-10-06 entries in `DEVLOG.md`.

**Validation on synthetic recordings.** `python3 -m capillary.benchmark`
renders synthetic capillary loops with a known red-cell speed and the
disturbances measured in the 2019 recordings (`capillary/simulate.py`),
measures them with all three methods, and writes a table of errors (about 8
minutes; `--quick` for a short run). On it the centre line measures within ±2%
in its range and reports flow it cannot measure as unresolved; the two boxes
are off by up to ±10%, and much more under stronger disturbances.

**Validation on real recordings (Validation page).** A recording has no ground
truth, so the estimator is compared with people:

1. *Blinded reading.* A reading set draws a few non-overlapping 3-s blocks at
   random from each chosen centre-line data set (by default half of them
   from blocks the estimator resolved) and copies them, with a recorded seed,
   into `Validation/<set>/`. Each observer reads every block in an order of
   their own, without seeing its recording or the estimator's result: they
   draw lines along the streaks (the block's slope is the mean of their
   slopes) or mark it as having no clear streaks. A second session by the same
   observer gives the repeatability. The agreement report measures every block
   again with the current estimator and compares it with every reading, with
   the mean of the observers, observers with each other and sessions with each
   other (`capillary/validation.py`).
2. *Line placement.* Centre-line data sets of the same capillary over the same
   frames (lines running along each other, frame ranges overlapping by at
   least 80%) are matched automatically, and their median velocities compared
   between observers and between two measurements by one observer
   (`capillary/placement.py`).

Velocities are compared with Bland–Altman bias and 95% limits of agreement
(with confidence intervals, a test for a difference that grows with the
velocity, and the same on a log scale as ratios) and the intraclass
correlation ICC(A,1); whether a block can be read at all with Cohen's kappa
(`capillary/agreement.py`).

## Data folder

`settings.csv` stores `Application_path`, the folder that holds the research
data, `mm_per_pixel`, the spatial calibration of the microscope,
`box_size`, the default box size, and `observer`, the initials last entered.
Each computer has its own `settings.csv`; git ignores it. On first start (or
if the file is missing) the app asks for the folder; the settings can be
changed later with the gear button. Inside the folder it uses:

- `RecordedVideos/`: raw recordings, copied in to be stabilized.
- `StabilizedVideos/`: stabilized copies, used for measuring, each with the
  shift of every frame (`<recording>___stabilization.csv`) and how it was made
  (`<recording>___stabilization_provenance.json`).
- `Statistics/`: the saved data sets (`<recording>___<data set>___…`), their
  provenance files, and each recording's time points. A centre-line data set
  keeps its space-time diagram (`___space_time.npy`), so its report can be
  written again without the video.
- `Reports/`: the plots and summary tables written from the data sets.
- `Validation/`: reading sets, one folder each (`set.json`, the blocks in
  `blocks.npz`, `readings/<observer>_s<session>.json`, the agreement tables
  and plots in `report/`), and the line-placement comparison in
  `line_placement/`. Created when the first reading set is drawn.
- `.trash/`: what was moved to the trash, one dated folder per action.
- `Flows/`: optical-flow videos from versions before 2026-10-06, when the
  optical-flow measurement was removed. The app no longer creates or reads
  this folder, except to move a recording's old flow files to the trash along
  with the recording.

## Code layout

| Path | What it holds |
| --- | --- |
| `Application.py` | Entry point: logging, then the window from `gui/` |
| `gui/app.py` | The main window: header, recording list, pages, status bar, keyboard routing, application-wide actions |
| `gui/line_page.py`, `gui/analyze_page.py`, `gui/results_page.py`, `gui/validation_page.py` | The four pages (Centre line, Two boxes, Results, Validation) |
| `gui/measure_page.py` | What both measure pages build on: video, timeline, frame range, time points, the Measure footer, the last result |
| `gui/reading_view.py` | The Validation page's reading mode: one block at a time, lines drawn along its streaks |
| `gui/video_view.py`, `gui/transport.py`, `gui/library_view.py`, `gui/widgets.py`, `gui/dialogs.py`, `gui/theme.py` | Video canvas with zoom and pan, playback and timeline, the recording list, small widgets, dialogs, colours and icons |
| `gui/jobs.py`, `gui/tasks.py` | Background jobs, and the work they run (stabilize, previews, measurements, reports, reading sets, agreement) |
| `gui/library.py`, `gui/settings.py`, `gui/media.py` | Finding recordings, settings, frames for display |
| `Caper.py` | The report plots of both methods, and the agreement plots of the Validation page |
| `capillary/` | The GUI-free measurement engine, the stabilizer (`stabilize.py`, with the vendored registration in `registration.py`), simulator, benchmark and batch CLI (see below), and the validation on real recordings (`validation.py`, `placement.py`, `agreement.py`) |
| `tests/` | Unit tests |
| `metadata/` | Study metadata: the official occlusion and release times of every ESMOKE and ISMOKE recording, exported from DynCap (see its README); the measure pages take their Rest, Occlusion and After release ranges from them |

## Setup

1. **Set up the Python environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
   Tkinter comes from the system Python (on Ubuntu: `sudo apt install python3-tk`).
   No separate ffmpeg is needed; the OpenCV wheel brings its own.

2. **Start the application:**
   ```bash
   source venv/bin/activate
   python3 Application.py
   ```
   On first start it asks for the data folder and the calibration. Messages and
   errors are written to `capillaroscopy.log`.

## Batch analysis without the GUI

The measurement itself lives in the `capillary` package, which imports no GUI
toolkit: `spacetime.py` (centre line), `roi.py`, `intensity.py` and
`velocity.py` (two boxes). The pages and the command line therefore run the
same arithmetic, and a result can be regenerated from the command line alone:

```bash
python3 -m capillary.cli StabilizedVideos/clip.avi \
    --line "372,110;352,160;338,205" --start 1909 --max-frames 900 \
    --out blocks.csv --summary-out summary.csv

python3 -m capillary.cli StabilizedVideos/clip.avi \
    --roi1 320,240 --roi2 320,300 --size 10x10 \
    --out report.csv --summary-out summary.csv
```

`--line` lists the points of a centre line in pixel coordinates, from where
the blood comes from; for a line it also prints the pattern-shift velocity
pooled over all the frames measured; `--roi1` is box 1 (downstream) and `--roi2` box 2
(upstream), `--size` the box size for boxes given as just `x,y`. The points or
box centres and the frames of a data set made in the app are in its
`…_provenance.json`. The spatial calibration comes from `settings.csv`
(`mm_per_pixel`) unless `--mm-per-pixel` overrides it.
`python3 -m capillary.cli --help` lists the rest.

Recordings can be stabilized the same way, for example one after another on
a computer without a display:

```bash
python3 -m capillary.stabilize RecordedVideos/clip.avi --out StabilizedVideos/clip.avi
```

## Tests

```bash
source venv/bin/activate
pip install pytest
python3 -m pytest
```

The suite checks the engine against synthetic videos with an exactly known
velocity — a real clip has no ground truth, so it cannot tell you whether the
estimator is right. `tests/synthetic.py` generates a pattern sliding at a
chosen pixels-per-frame rate; `capillary/simulate.py` renders capillary loops
with the disturbances of the real recordings. Further tests cover both
measurements as the pages run them, the saved file formats, the agreement
statistics (against the published example of Shrout & Fleiss 1979 and values
worked by hand), reading sets with simulated observers, the matching of line
placements, and the GUI's non-visual logic (settings, the recording list, the
trash, background jobs, the reading canvas). None of them needs a display.
