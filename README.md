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
