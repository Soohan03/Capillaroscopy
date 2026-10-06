"""Reading frames for display, and turning them into something to look at.

None of this affects a measurement: the Measure buttons read frames through
`capillary.measure`. This module only serves the on-screen picture.
"""

from __future__ import annotations

import cv2
import numpy as np

from capillary.video import probe_video


class FrameSource:
    """Random-access frame reader on top of one ``cv2.VideoCapture``.

    Sequential reads cost one decode; any other index seeks first. Frames come
    back single-channel (channel 0, what the measurement samples).
    """

    def __init__(self, path: str):
        info = probe_video(path)
        self.path = path
        self.fps = info.fps
        self.frame_count = max(0, info.frame_count)
        self.width = info.width
        self.height = info.height
        self._cap = cv2.VideoCapture(path)
        self._next = 0

    @property
    def duration_s(self) -> float:
        return self.frame_count / self.fps if self.fps else 0.0

    def read(self, index: int):
        """Frame `index`, or None if it cannot be decoded (e.g. past the real end)."""
        if self._cap is None or self.frame_count == 0:
            return None
        index = max(0, min(int(index), self.frame_count - 1))
        if index != self._next:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = self._cap.read()
        if not ok or frame is None:
            self._next = -1
            return None
        self._next = index + 1
        return frame if frame.ndim == 2 else frame[:, :, 0]

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


def make_thumbnail(path: str, max_width: int, max_height: int):
    """``(rgb thumbnail, VideoInfo)`` for a video, from a frame 10% of the way in.

    Frame 0 is avoided because videos written by the current stabilizer start
    with a black frame (see Known issues in CLAUDE.md).
    """
    info = probe_video(path)
    cap = cv2.VideoCapture(path)
    try:
        frame = None
        if info.frame_count > 10:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(info.frame_count * 0.1))
            ok, frame = cap.read()
            if not ok:
                frame = None
        if frame is None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = cap.read()
            if not ok:
                return None, info
    finally:
        cap.release()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if frame.ndim == 3 else cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
    scale = min(max_width / rgb.shape[1], max_height / rgb.shape[0])
    size = (max(1, int(rgb.shape[1] * scale)), max(1, int(rgb.shape[0] * scale)))
    return cv2.resize(rgb, size, interpolation=cv2.INTER_AREA), info


def format_time(seconds: float, precise: bool = True) -> str:
    """``m:ss.sss`` (or ``h:mm:ss.sss``); ``precise=False`` drops the fraction."""
    if seconds is None or not np.isfinite(seconds):
        return '–'
    negative = seconds < 0
    # round first, so 59.9996 s reads 1:00.000 rather than 0:60.000
    seconds = round(abs(seconds), 3) if precise else float(int(abs(seconds)))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    text = f'{int(secs):02d}' if not precise else f'{secs:06.3f}'
    if hours >= 1:
        text = f'{int(hours)}:{int(minutes):02d}:{text}'
    else:
        text = f'{int(minutes)}:{text}'
    return ('-' if negative else '') + text
