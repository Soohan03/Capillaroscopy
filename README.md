# Capillaroscopy Analysis Tool

A desktop tool (Tkinter + OpenCV) for recording and analysing nailfold
capillaroscopy videos: it records from the microscope camera, stabilizes the
recording, measures red-cell velocity between two boxes on a capillary, and
measures optical flow over a vessel region.

## Using the app

The window has a list of recordings on the left (everything that shares one
video's name: raw capture, stabilized copy, optical flow, data sets) and four
pages:

| Page | What you do there |
| --- | --- |
| **Analyze** | Place box 1 (downstream, orange) and box 2 (upstream, blue) on a capillary. A live preview shows both box signals, their correlation and the velocity around the current frame, and which velocities these boxes can resolve. Choose a frame range, name the data set, press **Measure velocity and save**. |
| **Flow** | Draw a region over a vessel on the optical-flow video and press **Measure flow and save**. |
| **Capture** | Camera preview, recording into `RecordedVideos/`, marking time points (e.g. cuff release) while recording. |
| **Results** | The files, time points and saved data sets of a recording, with their reports. Reports can be regenerated, data sets moved to the trash, and the boxes of a data set restored on the Analyze page. |

A measurement reads the chosen frame range straight from the video file with
the boxes held fixed, so it takes seconds rather than the length of the clip,
and it is fully described by its parameters. Each data set gets a small
`…_provenance.json` file beside it that records the box positions, frame
range, calibration, video and code version it was made with.

Stabilizing and computing optical flow run in the background (right-click a
recording, or the **⋯** menu above the list for all at once); you can keep
working meanwhile. Press **F1** for all keyboard and mouse controls.

Nothing is deleted outright: replaced or removed videos and data sets go to
`.trash/` in the data folder, keeping their subfolders, so they can be put back
by hand.

## Data folder

`settings.csv` stores `Application_path`, the folder that holds the research
data, `mm_per_pixel`, the spatial calibration of the microscope, and
`box_size`, the default box size. On first start (or if the file is missing)
the app asks for the folder; the settings can be changed later with the gear
button. Inside the folder it uses:

- `RecordedVideos/`: raw captures from the microscope.
- `StabilizedVideos/`: stabilized copies, used for measuring.
- `Flows/`: optical-flow videos and their summaries (`.pickle`).
- `Statistics/`: the saved data sets (`<recording>___<data set>___…`), their
  provenance files, and each recording's time points.
- `Reports/`: the plots and summary tables written from the data sets.
- `.trash/`: what was moved to the trash, one dated folder per action.

## Code layout

| Path | What it holds |
| --- | --- |
| `Application.py` | Entry point: logging, then the window from `gui/` |
| `gui/app.py` | The main window: header, recording list, pages, status bar, keyboard routing, application-wide actions |
| `gui/analyze_page.py`, `gui/flow_page.py`, `gui/capture_page.py`, `gui/results_page.py` | The four pages |
| `gui/measure_page.py` | What Analyze and Flow share: video, timeline, frame range, time points, the Measure footer, the last result |
| `gui/video_view.py`, `gui/transport.py`, `gui/library_view.py`, `gui/widgets.py`, `gui/dialogs.py`, `gui/theme.py` | Video canvas with zoom and pan, playback and timeline, the recording list, small widgets, dialogs, colours and icons |
| `gui/jobs.py`, `gui/tasks.py` | Background jobs, and the work they run (stabilize, optical flow, measure, reports) |
| `gui/library.py`, `gui/settings.py`, `gui/media.py`, `gui/camera.py` | Finding recordings, settings, frames for display, camera capture |
| `Caper.py` | Stabilization, optical flow and report generation |
| `SingleStepDFT.py` | Sub-pixel image registration used by stabilization (vendored, see its docstring) |
| `Utilities.py` | Small shared helpers |
| `capillary/` | The GUI-free measurement engine and batch CLI (see below) |
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

The measurement itself — ROI geometry, per-frame intensity sampling and the
cross-correlation velocity estimate — lives in the `capillary` package, which
imports no GUI toolkit. The Analyze page and the command line therefore run the
same arithmetic, and a result can be regenerated from the command line alone:

```bash
python3 -m capillary.cli StabilizedVideos/clip.avi \
    --roi1 320,240 --roi2 320,300 --size 10x10 \
    --out report.csv --summary-out summary.csv
```

`--roi1` is box 1 (downstream) and `--roi2` is box 2 (upstream), in pixel
coordinates; `--size` sets the box size for boxes given as just `x,y`. The box
centres of a data set made in the app are in its `…_provenance.json`. The
spatial calibration comes from `settings.csv` (`mm_per_pixel`) unless
`--mm-per-pixel` overrides it. `python3 -m capillary.cli --help` lists the rest.

## Tests

```bash
source venv/bin/activate
pip install pytest
python3 -m pytest
```

The suite checks the engine against synthetic videos with an exactly known
velocity — a real clip has no ground truth, so it cannot tell you whether the
estimator is right. `tests/synthetic.py` generates a pattern moving at a chosen
pixels-per-frame rate, which fixes the true lag and the true mm/s. Further
tests cover the measurement used by the Measure button, the saved file
formats, the flow-region arithmetic, and the GUI's non-visual logic (settings,
the recording list, the trash, background jobs). None of them needs a display.
