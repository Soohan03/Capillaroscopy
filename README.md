# Capillaroscopy Analysis Tool

This application is a GUI-based tool built with Tkinter and OpenCV for analyzing capillaroscopy videos. It provides functionalities for capturing, stabilizing, processing, and analyzing video frames.

## Code layout

| File | What it holds |
| --- | --- |
| `Application.py` | Entry point: window, `settings.csv`, tab switching, the main update loop |
| `Analyze_Frame.py`, `Flow_Frame.py`, `Camera_Frame.py` | The Analyze, Flow and Capture tabs |
| `FrameClasses.py` | The widgets inside the tabs: menu, video panels, video list, record controls |
| `Popup_Frame.py`, `Save_Data_Popup.py`, `Choose_Report_Popup.py`, `Process_Frame.py` | Small windows: a video's options, naming saved data, choosing a report, running a processing job |
| `Caper.py` | Video reading and writing, stabilization, optical flow, ROI boxes, report generation |
| `SingleStepDFT.py` | Sub-pixel image registration used by stabilization (vendored, see its docstring) |
| `Utilities.py` | Small shared helpers |
| `capillary/` | The GUI-free measurement engine and batch CLI (see below) |
| `tests/` | Unit tests for `capillary/` |

## Data folder

`settings.csv` stores `Application_path`, the folder that holds the research data, and
`mm_per_pixel`, the spatial calibration of the microscope. If the file is missing, the
application asks for a folder on first start. Inside that folder it creates:
- `RecordedVideos/`: Raw captures from the microscope.
- `StabilizedVideos/`: Videos after stabilization processing.
- `Reports/`: Generated analysis reports.
- `Statistics/`: Extracted numerical data.
- `Flows/`: Flow analysis results.

## Setup Instructions

1. **Set up the Python environment:**
   Create a virtual environment and install the required dependencies.
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
   Tkinter comes from the system Python (on Ubuntu: `sudo apt install python3-tk`).
   No separate ffmpeg is needed; the OpenCV wheel brings its own.

2. **Configure Settings:**
   Set `Application_path` in `settings.csv` to your data folder, or delete the file to be
   asked on the next start.

## Running the Application
Activate your virtual environment and start the application:
```bash
source venv/bin/activate
python3 Application.py
```

## Batch analysis without the GUI

The measurement itself — ROI geometry, per-frame intensity sampling and the
cross-correlation velocity estimate — lives in the `capillary` package, which
imports no GUI toolkit. The Analyze tab and the command line therefore run the
same arithmetic, and a result can be regenerated from the command line alone:

```bash
python3 -m capillary.cli StabilizedVideos/clip.avi \
    --roi1 320,240 --roi2 320,300 --size 10x10 \
    --out report.csv --summary-out summary.csv
```

`--roi1` is rectangle 1 (the white box, downstream) and `--roi2` is rectangle 2,
in pixel coordinates; `--size` sets the box size for ROIs given as just `x,y`.
The spatial calibration comes from `settings.csv` (`mm_per_pixel`) unless
`--mm-per-pixel` overrides it. `python3 -m capillary.cli --help` lists the rest.

Because every parameter is on the command line, a report made this way is
reproducible: the ROI coordinates, box size, window lengths and calibration that
produced it are all recorded, rather than living in where someone clicked.

## Tests

```bash
source venv/bin/activate
pip install pytest
python3 -m pytest
```

The suite checks the engine against synthetic videos with an exactly known
velocity — a real clip has no ground truth, so it cannot tell you whether the
estimator is right. `tests/synthetic.py` generates a pattern moving at a chosen
pixels-per-frame rate, which fixes the true lag and the true mm/s.
