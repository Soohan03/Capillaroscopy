"""Region-of-interest geometry, independent of any GUI toolkit.

The two ROI boxes the user positions on the Analyze tab are centred boxes of a
fixed width/height, clamped so they stay inside the frame. `Caper.Rectangle`
implements that with mutable state and drawing code mixed in; `ROI` below is the
same arithmetic as a plain value object, so it can be constructed from a CLI
argument and unit-tested without a canvas.

The clamping reproduces `Caper.Rectangle.calculate_corners` exactly, including
its use of ``int(w / 2)`` halves (so an odd width yields a box one pixel
narrower than requested) and its ``>=`` edge test. Changing that would silently
shift every historical measurement by a pixel, so it is kept as-is and pinned by
tests in `tests/test_roi.py`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def _clamp_center(center: int, half: int, extent: int) -> int:
    """Move `center` so a box of half-size `half` fits inside `[0, extent)`.

    Mirrors `Caper.Rectangle.calculate_corners`.
    """
    if center + half >= extent:
        center = center + (extent - (center + half))
    if center - half < 0:
        center = center - (center - half)
    return center


@dataclass(frozen=True)
class ROI:
    """A centred sampling box.

    `center_x` / `center_y` are where the user clicked, in frame pixel
    coordinates (x to the right, y downwards). `width` / `height` are the box
    size taken from the Analyze tab entries.
    """

    center_x: int
    center_y: int
    width: int = 10
    height: int = 10

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f'ROI needs a positive size, got {self.width}x{self.height}')

    @property
    def half_width(self) -> int:
        return int(self.width / 2)

    @property
    def half_height(self) -> int:
        return int(self.height / 2)

    def clamped_center(self, frame_shape: tuple[int, ...]) -> tuple[int, int]:
        """The box centre after being pulled inside a frame of `frame_shape`."""
        height, width = frame_shape[0], frame_shape[1]
        x = _clamp_center(int(self.center_x), self.half_width, width)
        y = _clamp_center(int(self.center_y), self.half_height, height)
        return x, y

    def bounds(self, frame_shape: tuple[int, ...]) -> tuple[int, int, int, int]:
        """Return ``(x_start, x_stop, y_start, y_stop)`` slice bounds."""
        x, y = self.clamped_center(frame_shape)
        return (
            x - self.half_width,
            x + self.half_width,
            y - self.half_height,
            y + self.half_height,
        )

    def crop(self, frame):
        """Return the pixels inside the box (a view into `frame`)."""
        x_start, x_stop, y_start, y_stop = self.bounds(frame.shape)
        return frame[y_start:y_stop, x_start:x_stop]

    def distance_to(self, other: 'ROI', frame_shape: tuple[int, ...]) -> float:
        """Centre-to-centre distance in pixels, after clamping both boxes.

        The GUI measures between the raw click coordinates; using the clamped
        centres instead means the reported distance matches where the sampling
        boxes actually sit. The two agree except when a box is pushed off the
        edge of the frame.
        """
        x1, y1 = self.clamped_center(frame_shape)
        x2, y2 = other.clamped_center(frame_shape)
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    @classmethod
    def parse(cls, text: str, default_width: int = 10, default_height: int = 10) -> 'ROI':
        """Build an ROI from a ``"x,y"`` or ``"x,y,w,h"`` string (for the CLI)."""
        parts = [p.strip() for p in str(text).split(',') if p.strip() != '']
        if len(parts) not in (2, 4):
            raise ValueError(f'expected "x,y" or "x,y,w,h", got {text!r}')
        try:
            numbers = [int(p) for p in parts]
        except ValueError as exc:
            raise ValueError(f'ROI coordinates must be integers, got {text!r}') from exc
        if len(numbers) == 2:
            return cls(numbers[0], numbers[1], default_width, default_height)
        return cls(*numbers)
