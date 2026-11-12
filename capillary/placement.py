"""Whether two centre lines follow the same capillary.

Two lines on one recording measure the same capillary if they run along each
other: at least `MIN_LINE_OVERLAP` of one line lies within `MATCH_PX` of the
other. The study's placement repeat (`analysis/placement_repeat/`) uses this to
tell whether the observer chose the same capillary the second time.

Nothing here imports a GUI toolkit.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .spacetime import Centreline

#: Lines whose samples lie this close (px) count as running along each other.
MATCH_PX = 5.0
#: Share of one line that must run along the other.
MIN_LINE_OVERLAP = 0.5


def line_overlap(a_points: Sequence, b_points: Sequence, tolerance: float = MATCH_PX) -> tuple[float, float, int]:
    """How far two lines run along each other.

    Returns the share of line a within `tolerance` px of line b, the share of
    b within `tolerance` of a, and +1 if they run the same way where they
    meet, -1 if opposite (+1 if they do not meet).
    """
    a_positions, a_normals = Centreline.from_points(a_points).sample_positions(1.0)
    b_positions, b_normals = Centreline.from_points(b_points).sample_positions(1.0)
    distance = np.hypot(a_positions[:, None, 0] - b_positions[None, :, 0],
                        a_positions[:, None, 1] - b_positions[None, :, 1])
    near_a = distance.min(axis=1) <= tolerance
    near_b = distance.min(axis=0) <= tolerance
    direction = 1
    if near_a.any():
        nearest = distance.argmin(axis=1)[near_a]
        # the normals are the tangents turned by 90 degrees, so their dot product compares the tangents
        dots = np.sum(a_normals[near_a] * b_normals[nearest], axis=1)
        direction = 1 if float(np.mean(dots)) >= 0 else -1
    return float(near_a.mean()), float(near_b.mean()), direction
