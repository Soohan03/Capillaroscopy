"""Per-frame ROI intensity sampling — the raw signal behind every velocity.

Both ROI boxes sit over the same capillary segment, a known distance apart.
Each frame contributes one mean intensity per box; a red-cell plug darkens the
upstream box first and the downstream box a few frames later, and that delay is
what `capillary.velocity` measures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np

from .roi import ROI
from .video import DEFAULT_FPS, iter_frames, probe_video


@dataclass
class IntensityTrace:
    """Mean ROI intensity per frame for the two boxes.

    `a` and `b` correspond to rectangle 1 (white box) and rectangle 2 (black
    box) on the Analyze tab. Frames where a box fell outside the image, or that
    failed to decode, are NaN.
    """

    a: np.ndarray
    b: np.ndarray
    distance_px: float
    fps: float
    roi_a: Optional[ROI] = None
    roi_b: Optional[ROI] = None
    source: Optional[str] = None

    def __post_init__(self) -> None:
        self.a = np.asarray(self.a, dtype=float)
        self.b = np.asarray(self.b, dtype=float)
        if self.a.shape != self.b.shape:
            raise ValueError(f'traces differ in length: {self.a.shape} vs {self.b.shape}')

    @property
    def n_frames(self) -> int:
        return int(self.a.size)

    @property
    def duration_s(self) -> float:
        return self.n_frames / self.fps if self.fps else 0.0

    def valid_count(self) -> int:
        """How many frames have a usable sample in both boxes."""
        return int(np.count_nonzero(np.isfinite(self.a) & np.isfinite(self.b)))


def extract_traces(
    frames: Iterable[np.ndarray],
    roi_a: ROI,
    roi_b: ROI,
    fps: float = DEFAULT_FPS,
    distance_px: Optional[float] = None,
    source: Optional[str] = None,
) -> IntensityTrace:
    """Sample both ROIs over an iterable of single-channel frames.

    Works on anything iterable — a decoder, a list of arrays from a test, or a
    generator — so the sampling logic can be tested without encoding a video.
    """
    a_values: list[float] = []
    b_values: list[float] = []
    frame_shape = None

    for frame in frames:
        frame = np.asarray(frame)
        if frame.ndim == 3:
            frame = frame[:, :, 0]
        frame_shape = frame.shape
        a_values.append(_mean_or_nan(roi_a.crop(frame)))
        b_values.append(_mean_or_nan(roi_b.crop(frame)))

    if frame_shape is None:
        raise ValueError('no frames to analyse')

    if distance_px is None:
        distance_px = roi_a.distance_to(roi_b, frame_shape)

    return IntensityTrace(
        a=np.array(a_values, dtype=float),
        b=np.array(b_values, dtype=float),
        distance_px=float(distance_px),
        fps=float(fps),
        roi_a=roi_a,
        roi_b=roi_b,
        source=source,
    )


def extract_traces_from_video(
    path: str,
    roi_a: ROI,
    roi_b: ROI,
    max_frames: Optional[int] = None,
    fps: Optional[float] = None,
) -> IntensityTrace:
    """Open `path` and sample both ROIs frame by frame."""
    info = probe_video(path)
    return extract_traces(
        iter_frames(path, max_frames=max_frames),
        roi_a,
        roi_b,
        fps=float(fps) if fps else info.fps,
        source=str(path),
    )


def _mean_or_nan(patch: np.ndarray) -> float:
    """Mean of a patch, or NaN when the box is empty (clamped off-frame)."""
    if patch.size == 0:
        return float('nan')
    return float(np.mean(patch))
