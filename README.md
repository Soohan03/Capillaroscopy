# Capillaroscopy Analysis Tool

This application is a GUI-based tool built with Tkinter and OpenCV for analyzing capillaroscopy videos. It provides functionalities for capturing, stabilizing, processing, and analyzing video frames.

## Project Structure

This project separates the **Application Code** from the **Research Data**:

1.  **Code Repository:** `/home/jacob-widaeus/Projects/Dev/capillaroscopy` (This folder)
2.  **Data Directory:** `/home/jacob-widaeus/Projects/Dev/CapillaroscopyData` (External folder for videos and reports)

### Data Directory Organization
When you first run the application, it will ask for an "Application folder". Point it to your data directory. The app will then automatically create the following structure within that folder:
- `RecordedVideos/`: Raw captures from the microscope.
- `StabilizedVideos/`: Videos after stabilization processing.
- `Reports/`: Generated analysis reports.
- `Statistics/`: Extracted numerical data.
- `Flows/`: Flow analysis results.

## Setup Instructions

1. **Install system dependencies:**
   Ensure `ffmpeg` is installed on your system.
   ```bash
   sudo apt install ffmpeg
   ```

2. **Set up the Python environment:**
   Create a virtual environment and install the required dependencies.
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Settings:**
   The `settings.csv` file is pre-configured to point to `/home/jacob-widaeus/Projects/Dev/CapillaroscopyData`. If you move your data folder, update the `Application_path` value in this file.

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
