"""Tkinter front end of the capillaroscopy tool; start it with ``python3 Application.py``.

The package only lays out windows, handles input and runs work in background
threads. The measurement lives in `capillary/`, stabilization and the report
generator in `Caper.py`, so the GUI, the batch CLI and the tests share one
implementation.

    app.py           main window: header, pages, library, status bar, shortcuts
    theme.py         colours, fonts, ttk styles and the drawn icons
    widgets.py       small reusable widgets (scrolling panel, charts, tooltips)
    dialogs.py       modal dialogs, settings, shortcuts, image viewer
    video_view.py    the zoomable video canvas and its overlay
    transport.py     playback, timeline and transport bar
    library_view.py  the list of recordings on the left
    measure_page.py  video, frame range, time points and Measure footer of Analyze
    analyze_page.py  velocity measurement with two boxes
    capture_page.py  camera preview and recording
    results_page.py  saved data sets and their reports

No Tk in these (they can be used and tested without a display):

    settings.py      settings.csv and the data folder layout
    library.py       which recordings exist and what has been done to them
    media.py         frame reading and display conversion
    jobs.py          background jobs with progress and cancel
    tasks.py         the work the pages hand to background jobs
    camera.py        camera capture and recording thread
"""
import matplotlib

# Reports are drawn off-screen from worker threads, so pyplot must never pick an
# interactive backend. The PNGs are identical to the ones the old GUI made.
matplotlib.use('Agg')
