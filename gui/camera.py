"""Camera capture and recording on a background thread. No Tk here.

Frames are grabbed on their own thread, so recording keeps the camera's pace
instead of the window's redraw rate, and the window only ever shows the newest
frame. Recordings are written as before: the green-weighted signal of
`Utilities.rgb_to_negR_posG` (capillaries contrast best in green) as a
three-channel MP4V ``.avi``, stamped 30 fps.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np

from Utilities import rgb_to_negR_posG

log = logging.getLogger(__name__)

#: Frame rate written into recordings, as the old recorder did. If the camera
#: delivers a different rate the playback speed (and every velocity) would be
#: off, so the Capture tab warns when the measured rate differs.
RECORDING_FPS = 30.0


def recorded_signal(rgb: np.ndarray) -> np.ndarray:
    """The single-channel image that gets recorded for an RGB camera frame."""
    return rgb_to_negR_posG(rgb)


class Recorder:
    def __init__(self, path: str, size: tuple[int, int], fps: float = RECORDING_FPS):
        self.path = path
        self.frames = 0
        self.started = time.monotonic()
        self._writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'MP4V'), fps, size)
        if not self._writer.isOpened():
            self._writer.release()
            raise OSError(f'Could not create the video file {path}')

    def write(self, rgb: np.ndarray) -> None:
        signal = recorded_signal(rgb)
        self._writer.write(cv2.merge((signal, signal, signal)).astype(np.uint8))
        self.frames += 1

    @property
    def seconds(self) -> float:
        return time.monotonic() - self.started

    def close(self) -> None:
        self._writer.release()


class Camera:
    """One camera, read on a daemon thread. `status` is opening, live, unavailable or lost."""

    def __init__(self):
        self.index = 0
        self.status = 'closed'
        self.size: Optional[tuple[int, int]] = None
        self.nominal_fps: Optional[float] = None
        self.measured_fps: Optional[float] = None
        self.frame_number = 0
        self._latest: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._recorder: Optional[Recorder] = None
        self._recorder_lock = threading.Lock()   # held while a frame is written, so close never interrupts it

    # control (Tk thread) ------------------------------------------------------------
    def open(self, index: int = 0) -> None:
        self.close()
        self.index = index
        self.status = 'opening'
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name='camera', daemon=True)
        self._thread.start()

    def close(self) -> Optional[Recorder]:
        """Stop the camera (finishing any recording, which is returned)."""
        recorder = self.stop_recording()
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None
        self.status = 'closed'
        with self._lock:
            self._latest = None
        return recorder

    def latest(self) -> tuple[Optional[np.ndarray], int]:
        with self._lock:
            return self._latest, self.frame_number

    @property
    def recording(self) -> Optional[Recorder]:
        return self._recorder

    def start_recording(self, path: str) -> Recorder:
        if self.status != 'live' or self.size is None:
            raise RuntimeError('The camera is not running.')
        recorder = Recorder(path, self.size)
        with self._recorder_lock:
            self._recorder = recorder
        return recorder

    def stop_recording(self) -> Optional[Recorder]:
        with self._recorder_lock:
            recorder, self._recorder = self._recorder, None
            if recorder is not None:
                recorder.close()
        return recorder

    # capture thread -------------------------------------------------------------------
    def _run(self) -> None:
        cap = cv2.VideoCapture(self.index)
        try:
            if not cap.isOpened():
                self.status = 'unavailable'
                return
            fps = cap.get(cv2.CAP_PROP_FPS)
            self.nominal_fps = fps if fps and np.isfinite(fps) else None
            failures = 0
            last = time.monotonic()
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    failures += 1
                    if failures > 50:
                        self.status = 'lost'
                        return
                    time.sleep(0.02)
                    continue
                failures = 0
                rgb = frame[:, :, ::-1].copy() if frame.ndim == 3 else cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
                now = time.monotonic()
                interval = now - last
                last = now
                if interval > 0:
                    rate = 1.0 / interval
                    self.measured_fps = rate if self.measured_fps is None else 0.9 * self.measured_fps + 0.1 * rate
                with self._lock:
                    self.size = (rgb.shape[1], rgb.shape[0])
                    self._latest = rgb
                    self.frame_number += 1
                with self._recorder_lock:
                    if self._recorder is not None:
                        try:
                            self._recorder.write(rgb)
                        except Exception:  # noqa: BLE001 - logged; the preview keeps running
                            log.exception('Writing a recorded frame failed')
                self.status = 'live'
        finally:
            cap.release()
