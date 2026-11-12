"""GUI-free capillaroscopy analysis engine.

Red-cell velocity in a nailfold capillary, measured from a video along a line
drawn on the vessel:

- `capillary.stabilize` moves every frame of a raw recording back into place
  (``python -m capillary.stabilize``);
- `capillary.spacetime` samples the space-time diagram along the line and reads
  the velocity from the slope of its streaks, in 3-s blocks;
- `capillary.pattern_shift` reads the same diagram pooled over a whole stretch,
  which measures the faint flow at rest;
- `capillary.datasets` is the file layout of saved measurements, and
  `capillary.cli` measures a line without the GUI (``python -m capillary.cli``).

For the study the tool was built for, `capillary.inventory` reads the
recordings' names and official times and chooses each aim's recordings,
`capillary.blinding` gives the codes of blind placement, and `capillary.aims`
turns the saved data sets into the aims' statistics (``python -m
capillary.aims``) with those of `capillary.agreement`. `capillary.placement`
tells whether two lines follow the same capillary.

Validation: `capillary.simulate` renders synthetic recordings with a known
velocity and `capillary.benchmark` measures them (``python -m
capillary.benchmark``).

Nothing in here imports tkinter, PIL or matplotlib, so it can be imported from
a batch script, a notebook or a test without a display. The GUI (`gui/`) keeps
its own widgets and calls into these functions, so that both paths compute
velocity with exactly the same code.
"""

from .spacetime import Centreline, analyze_space_time, space_time_diagram, space_time_summary, streak_speed
from .video import VideoInfo, probe_video, iter_frames

__all__ = [
    'Centreline',
    'space_time_diagram',
    'analyze_space_time',
    'space_time_summary',
    'streak_speed',
    'VideoInfo',
    'probe_video',
    'iter_frames',
]
