# Capillaroscopy Analysis Tool

A desktop tool (Tkinter + OpenCV) for recording and analysing nailfold
capillaroscopy videos: it records from the microscope camera, stabilizes the
recording, and measures red-cell velocity in a capillary, along a line drawn
on the vessel or between two boxes.

## Using the app

The window has a list of recordings on the left (everything that shares one
video's name: raw capture, stabilized copy, data sets) and four pages:

| Page | What you do there |
| --- | --- |
| **Centre line** | Click points along the middle of one capillary, starting where the blood comes from. A live preview shows the space-time diagram of the frames around the playhead with the slope it found, the velocity and its signal-to-noise ratio, and which velocities this line can measure. Choose a frame range, name the data set, press **Measure velocity and save**. |
| **Two boxes** | The original method: place box 1 (downstream, orange) and box 2 (upstream, blue) on a capillary; the velocity comes from the delay between their brightness signals. Kept for comparison and for the data sets made with it (see below). |
| **Capture** | Camera preview, recording into `RecordedVideos/`, marking time points (e.g. cuff release) while recording. |
| **Results** | The files, time points and saved data sets of a recording, with their reports. Reports can be regenerated, data sets moved to the trash, and the line or boxes of a data set restored on its page. |

A measurement reads the chosen frame range straight from the video file with
the line (or boxes) held fixed, so it takes seconds rather than the length of
the clip, and it is fully described by its parameters. Each data set gets a
small `…_provenance.json` file beside it that records the line or box
positions, frame range, calibration, estimator settings, video and code
version it was made with.

Stabilizing runs in the background (right-click a recording, or the **⋯** menu
above the list for all at once); you can keep working meanwhile. Press **F1**
for all keyboard and mouse controls.

Nothing is deleted outright: replaced or removed videos and data sets go to
`.trash/` in the data folder, keeping their subfolders, so they can be put back
by hand.

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

**Two boxes (the original method).** The delay between the brightness signals
of two boxes on the vessel, found by cross-correlation in windows of
201–301 frames, gives the velocity as distance ÷ delay. In the 2019
recordings about 70% of what a box on a capillary sees is a change of the
whole vessel at once (probably small movements or focus), which both boxes see
simultaneously, so the delay comes out as zero ("too fast to resolve") even
where the flow is slow. See the 2026-10-06 entries in `DEVLOG.md`.

**Validation.** `python3 -m capillary.benchmark` renders synthetic capillary
loops with a known red-cell speed and the disturbances measured in the 2019
recordings (`capillary/simulate.py`), measures them with both methods, and
writes a table of errors (about 6 minutes; `--quick` for a short run). On it
the centre line measures within ±2% in its range and reports flow it cannot
measure as unresolved; the two boxes are off by up to ±10%, and much more under
stronger disturbances.

## Data folder

`settings.csv` stores `Application_path`, the folder that holds the research
data, `mm_per_pixel`, the spatial calibration of the microscope, and
`box_size`, the default box size. On first start (or if the file is missing)
the app asks for the folder; the settings can be changed later with the gear
button. Inside the folder it uses:

- `RecordedVideos/`: raw captures from the microscope.
- `StabilizedVideos/`: stabilized copies, used for measuring.
- `Statistics/`: the saved data sets (`<recording>___<data set>___…`), their
  provenance files, and each recording's time points. A centre-line data set
  keeps its space-time diagram (`___space_time.npy`), so its report can be
  written again without the video.
- `Reports/`: the plots and summary tables written from the data sets.
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
| `gui/line_page.py`, `gui/analyze_page.py`, `gui/capture_page.py`, `gui/results_page.py` | The four pages (Centre line, Two boxes, Capture, Results) |
| `gui/measure_page.py` | What both measure pages build on: video, timeline, frame range, time points, the Measure footer, the last result |
| `gui/video_view.py`, `gui/transport.py`, `gui/library_view.py`, `gui/widgets.py`, `gui/dialogs.py`, `gui/theme.py` | Video canvas with zoom and pan, playback and timeline, the recording list, small widgets, dialogs, colours and icons |
| `gui/jobs.py`, `gui/tasks.py` | Background jobs, and the work they run (stabilize, previews, measurements, reports) |
| `gui/library.py`, `gui/settings.py`, `gui/media.py`, `gui/camera.py` | Finding recordings, settings, frames for display, camera capture |
| `Caper.py` | Stabilization and the report plots of both methods |
| `SingleStepDFT.py` | Sub-pixel image registration used by stabilization (vendored, see its docstring) |
| `Utilities.py` | Small shared helpers |
| `capillary/` | The GUI-free measurement engine, simulator, benchmark and batch CLI (see below) |
| `tests/` | Unit tests |

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
the blood comes from; `--roi1` is box 1 (downstream) and `--roi2` box 2
(upstream), `--size` the box size for boxes given as just `x,y`. The points or
box centres and the frames of a data set made in the app are in its
`…_provenance.json`. The spatial calibration comes from `settings.csv`
(`mm_per_pixel`) unless `--mm-per-pixel` overrides it.
`python3 -m capillary.cli --help` lists the rest.

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
measurements as the pages run them, the saved file formats, and the GUI's
non-visual logic (settings, the recording list, the trash, background jobs).
None of them needs a display.
