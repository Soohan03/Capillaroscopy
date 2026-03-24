# Capillaroscopy Analysis Tool

This application is a GUI-based tool built with Tkinter and OpenCV for analyzing capillaroscopy videos. It provides functionalities for capturing, stabilizing, processing, and analyzing video frames.

## Requirements
- Python 3.x
- `ffmpeg` (required for video processing)
- Virtual Environment (recommended)

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
   The `settings.csv` file should point to the correct project directory to ensure the application can save and load videos, reports, and statistics properly.

## Running the Application
Activate your virtual environment and start the application:
```bash
source venv/bin/activate
python3 Application.py
```
