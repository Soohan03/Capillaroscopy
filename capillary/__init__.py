"""GUI-free capillaroscopy analysis engine.

This package holds the measurement code: the centre-line velocity estimate
from a space-time diagram (`capillary.spacetime`, the Centre line page), and
the older two-box cross-correlation estimate with its region-of-interest
geometry and per-frame intensity sampling (the Two boxes page), which used to
live inside the Tkinter application (`Caper.py` and the original GUI's
`FrameClasses.py`).

Nothing in here imports tkinter, PIL or matplotlib, so it can be imported from
a batch script, a notebook or a test without a display. The GUI (`gui/`) keeps
its own widgets and calls into these functions so that both paths compute
velocity with exactly the same code.

See `capillary.cli` for the batch entry point (`python -m capillary.cli`).
`capillary.measure` is what the Two boxes page's Measure button runs,
`capillary.datasets` the file layout of saved measurements,
`capillary.simulate` synthetic recordings with a known velocity, and
`capillary.benchmark` the comparison of both estimators on them
(`python -m capillary.benchmark`). `capillary.stabilize` stabilizes a raw recording
(`python -m capillary.stabilize`). On real recordings, which have no ground
truth, `capillary.validation` compares the estimator with observers reading
the same blocks blinded, `capillary.placement` the same capillary measured by
different observers, both with the statistics of `capillary.agreement`.
"""

from .roi import ROI
from .intensity import IntensityTrace, extract_traces, extract_traces_from_video
from .spacetime import Centreline, analyze_space_time, space_time_diagram, space_time_summary, streak_speed
from .velocity import (
    DEFAULT_WINDOWS,
    lag_and_correlation,
    signed_lag,
    sliding_lag,
    analyze_trace,
    velocity_from_lag,
    resolvable_range,
    velocity_summary,
)
from .video import VideoInfo, probe_video, iter_frames

__all__ = [
    'Centreline',
    'space_time_diagram',
    'analyze_space_time',
    'space_time_summary',
    'streak_speed',
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
    'resolvable_range',
    'velocity_summary',
    'VideoInfo',
    'probe_video',
    'iter_frames',
]
