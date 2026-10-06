"""Measuring a frame range with fixed boxes: what the GUI's Measure button runs.

Up to the 2026-10 GUI rebuild the Analyze tab recorded data while the video
*played*: each displayed frame added one sample, a measurement took as long as
the clip, and moving a box mid-way silently mixed positions. Here the boxes are
fixed and an explicit frame range is read straight from the file, so a
measurement takes seconds and is fully described by its parameters.

The sampling itself is `extract_traces`, exactly as in the batch CLI.
`measure_velocity` adds progress reporting and cancellation, so a front end can
run it in a worker thread, plus the per-frame sharpness score saved with
velocity data sets.
"""

from __future__ import annotations

import collections
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from .intensity import IntensityTrace, extract_traces
from .quality import calculate_blur
from .roi import ROI
from .video import iter_frames, probe_video

ProgressCallback = Optional[Callable[[float], None]]
CancelCheck = Optional[Callable[[], bool]]


class Cancelled(Exception):
    """Raised inside a measurement when `should_cancel` returns True."""


@dataclass
class VelocityMeasurement:
    """Box intensities over a frame range, plus what is needed to save them."""

    trace: IntensityTrace
    blur: np.ndarray
    start_frame: int
    frames_read: int
    frame_count: int
    fps: float
    width: int
    height: int


def _check(should_cancel: CancelCheck) -> None:
    if should_cancel is not None and should_cancel():
        raise Cancelled()


def measure_velocity(
    path: str,
    roi_a: ROI,
    roi_b: ROI,
    start: int,
    stop: int,
    progress: ProgressCallback = None,
    should_cancel: CancelCheck = None,
    blur_cache: Optional[dict] = None,
    blur_workers: int = 4,
) -> VelocityMeasurement:
    """Sample box A (rectangle 1) and box B (rectangle 2) on frames ``start..stop-1``.

    `blur_cache`, if given, maps frame index to sharpness for this video; it is
    used where it has values and filled in where it does not, so measuring the
    same video again skips that work (sharpness does not depend on the boxes).
    The sharpness FFTs run on `blur_workers` threads; numpy releases the GIL
    for them, and the result is identical to computing them one by one.
    """
    info = probe_video(path)
    if not 0 <= start < stop:
        raise ValueError(f'invalid frame range {start}..{stop}')
    wanted = stop - start
    cache = blur_cache if blur_cache is not None else {}
    blur = np.full(wanted, np.nan)
    pending = collections.deque()
    max_pending = max(8, blur_workers * 8)

    def collect(limit: int) -> None:
        while len(pending) > limit:
            index, future = pending.popleft()
            value = float(future.result())
            blur[index - start] = value
            cache[index] = value

    with ThreadPoolExecutor(max_workers=max(1, blur_workers)) as pool:
        def frames():
            for offset, frame in enumerate(iter_frames(path, max_frames=wanted, start=start)):
                _check(should_cancel)
                index = start + offset
                if index in cache:
                    blur[offset] = cache[index]
                else:
                    pending.append((index, pool.submit(calculate_blur, np.ascontiguousarray(frame))))
                    collect(max_pending)
                if progress is not None and offset % 25 == 0:
                    progress(offset / wanted)
                yield frame

        try:
            trace = extract_traces(frames(), roi_a, roi_b, fps=info.fps, source=str(path))
            collect(0)
        except Cancelled:
            for _, future in pending:
                future.cancel()
            raise

    frames_read = trace.n_frames
    if progress is not None:
        progress(1.0)
    return VelocityMeasurement(
        trace=trace,
        blur=blur[:frames_read],
        start_frame=start,
        frames_read=frames_read,
        frame_count=info.frame_count,
        fps=info.fps,
        width=info.width,
        height=info.height,
    )
