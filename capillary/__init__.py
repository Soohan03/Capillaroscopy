"""GUI-free capillaroscopy analysis engine.

This package holds the measurement code that used to live inside the Tkinter
application (`Caper.py` / `FrameClasses.py`): region-of-interest geometry,
per-frame intensity sampling, and the cross-correlation velocity estimate.

Nothing in here imports tkinter, PIL or matplotlib, so it can be imported from
a batch script, a notebook or a test without a display. The GUI keeps its own
widgets and calls into these functions so that both paths compute velocity with
exactly the same code.

See `capillary.cli` for the batch entry point (`python -m capillary.cli`).
"""

from .roi import ROI
from .intensity import IntensityTrace, extract_traces, extract_traces_from_video
from .velocity import (
    DEFAULT_WINDOWS,
    lag_and_correlation,
    signed_lag,
    sliding_lag,
    analyze_trace,
    velocity_from_lag,
)
from .video import VideoInfo, probe_video, iter_frames

__all__ = [
    'ROI',
    'IntensityTrace',
    'extract_traces',
    'extract_traces_from_video',
    'DEFAULT_WINDOWS',
    'lag_and_correlation',
    'signed_lag',
    'sliding_lag',
    'analyze_trace',
    'velocity_from_lag',
    'VideoInfo',
    'probe_video',
    'iter_frames',
]
