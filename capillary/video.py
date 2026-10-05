"""Streaming video access for the analysis engine.

`Caper.Video.load` reads a whole clip into two float64 arrays of shape
(frames, height, width) — about 26 GB for a 60 s 640x480 clip — which is fine
for the GUI's one-frame-per-tick use but unusable for batch analysis. The
helpers here keep a single capture open and yield one frame at a time, so
memory stays flat regardless of clip length.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional

import cv2
import numpy as np

DEFAULT_FPS = 30.0


@dataclass(frozen=True)
class VideoInfo:
    """Container metadata as reported by the file itself."""

    path: str
    frame_count: int
    fps: float
    width: int
    height: int

    @property
    def duration_s(self) -> float:
        return self.frame_count / self.fps if self.fps else 0.0


def _open(path: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        cap.release()
        raise FileNotFoundError(f'could not open video: {path}')
    return cap


def probe_video(path: str) -> VideoInfo:
    """Read frame count, fps and resolution without decoding the whole clip."""
    cap = _open(path)
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        # Some containers report 0 fps; the recorder's rate is the sane default
        # and matches the fallback the GUI uses.
        if not fps or not np.isfinite(fps):
            fps = DEFAULT_FPS
        return VideoInfo(
            path=str(path),
            frame_count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            fps=fps,
            width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
    finally:
        cap.release()


def to_single_channel(frame: np.ndarray) -> np.ndarray:
    """Reduce a decoded frame to one channel.

    The GUI samples ``frame[:, :, 0]``. The capillaroscopy clips are greyscale
    recordings stored in a colour container, so all three channels carry the
    same data and taking the first one costs nothing; doing the same here keeps
    batch results bit-identical to the interactive ones.
    """
    if frame.ndim == 3:
        return frame[:, :, 0]
    return frame


def iter_frames(path: str, max_frames: Optional[int] = None) -> Iterator[np.ndarray]:
    """Yield single-channel frames from `path`, one at a time.

    Stops at `max_frames` if given, or when the decoder runs out — a container
    whose header over-reports its frame count (common after stabilisation
    re-encodes) simply ends early instead of raising.
    """
    cap = _open(path)
    try:
        yielded = 0
        while max_frames is None or yielded < max_frames:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            yield to_single_channel(frame)
            yielded += 1
    finally:
        cap.release()
