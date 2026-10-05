"""Measuring a frame range with fixed boxes: what the GUI's Measure button runs.

Up to the 2026-10 GUI rebuild the Analyze and Flow tabs recorded data while the
video *played*: each displayed frame added one sample, a measurement took as
long as the clip, and moving a box mid-way silently mixed positions. Here the
boxes are fixed and an explicit frame range is read straight from the file, so
a measurement takes seconds and is fully described by its parameters.

The sampling itself is `extract_traces`, exactly as in the batch CLI. The two
functions add progress reporting and cancellation, so a front end can run them
in a worker thread, plus the per-frame sharpness score saved with velocity
data sets.
"""

from __future__ import annotations

import collections
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from .flow import crop_box, empty_frame_dict
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


def flow_region_size_bytes(bounds, frame_count: int) -> int:
    """Memory (and roughly disk) a flow measurement of `frame_count` frames needs."""
    x_left, x_right, y_top, y_bottom = bounds
    pixels = max(0, x_right - x_left) * max(0, y_bottom - y_top)
    return pixels * 4 * frame_count  # three flow channels plus the mask, one byte each


def measure_flow(
    path: str,
    mask: np.ndarray,
    bounds,
    start: int,
    stop: int,
    progress: ProgressCallback = None,
    should_cancel: CancelCheck = None,
) -> tuple[dict, dict, int]:
    """Collect the region `bounds` of flow frames ``start..stop-1``.

    Returns ``(flow, mask, frames_read)``: two ``{frame: region}`` dicts that
    cover every frame of the video, NaN outside the range, in the layout the
    flow report reads. `mask` is the vessel mask of the flow video
    (`capillary.flow.vessel_mask`).
    """
    info = probe_video(path)
    if not 0 <= start < stop:
        raise ValueError(f'invalid frame range {start}..{stop}')
    wanted = stop - start
    flow_regions = empty_frame_dict(info.frame_count)
    mask_regions = empty_frame_dict(info.frame_count)
    mask_region = crop_box(mask, bounds)

    frames_read = 0
    wanted = min(wanted, max(0, info.frame_count - start))  # the saved dicts cover the header's frame count
    for offset, frame in enumerate(iter_frames(path, max_frames=wanted, start=start, single_channel=False)):
        _check(should_cancel)
        index = start + offset
        flow_regions[index] = crop_box(frame, bounds).copy()
        mask_regions[index] = mask_region.copy()
        frames_read += 1
        if progress is not None and offset % 25 == 0:
            progress(offset / wanted)
    if progress is not None:
        progress(1.0)
    return flow_regions, mask_regions, frames_read
