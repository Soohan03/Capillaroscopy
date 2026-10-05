"""Optical-flow region measurement, independent of any GUI toolkit.

`Caper.FlowVideo` turns a stabilized video into a flow video: every frame holds
the Farneback flow between two consecutive frames, with the direction in
channel 0 (OpenCV hue, 0-180 for 0-360 degrees, measured from +x with y
pointing down), 255 in channel 1, and the magnitude in pixels per frame times
`FLOW_SCALE` in channel 2. A pickle beside the video holds the average flow,
the average intensity and a vessel mask (channel 2) derived from them.

On the Flow tab the user drags a region over a vessel. Each measured frame
contributes the region of the flow frame and of the mask; the report divides
the flow summed over the region by the number of vessel pixels in it.

The arithmetic below is moved verbatim from the Tkinter code it used to live in
(`Caper.Rectangle.calculate_corners_drag` and
`FrameClasses.FlowFrame.generate_report`, removed in the 2026-10 GUI rebuild),
so reports keep their values; `tests/test_flow.py` pins that against copies of
the original code.
"""

from __future__ import annotations

import numpy as np

#: FlowVideo stores the flow magnitude (px/frame) multiplied by this.
FLOW_SCALE = 25.5

#: Hue (channel 0) at or above this counts as upward flow, at or below as downward.
UP_DOWN_HUE_SPLIT = 90


def drag_box_bounds(point1, point2, frame_shape, min_size=5):
    """Return ``(x_left, x_right, y_top, y_bottom)`` of the box a drag spans.

    Works for any drag direction, including a plain click or a purely
    horizontal or vertical drag: the box is at least `min_size` pixels in each
    direction and is kept inside a frame of `frame_shape` (height, width, ...).
    The bounds are slice bounds, so the region is
    ``frame[y_top:y_bottom, x_left:x_right]``.
    """
    height, width = frame_shape[0], frame_shape[1]

    x_left, x_right = sorted((int(point1[0]), int(point2[0])))
    y_top, y_bottom = sorted((int(point1[1]), int(point2[1])))

    # guarantee a non-degenerate region so the selection is never empty
    if x_right - x_left < min_size:
        x_right = x_left + min_size
    if y_bottom - y_top < min_size:
        y_bottom = y_top + min_size

    # keep the rectangle inside the frame
    x_left = max(0, min(x_left, width - min_size))
    x_right = max(min_size, min(x_right, width))
    y_top = max(0, min(y_top, height - min_size))
    y_bottom = max(min_size, min(y_bottom, height))

    return x_left, x_right, y_top, y_bottom


def crop_box(frame, bounds):
    """The part of `frame` inside `bounds` from `drag_box_bounds` (a view)."""
    x_left, x_right, y_top, y_bottom = bounds
    return frame[y_top:y_bottom, x_left:x_right]


def vessel_mask(flow_summary):
    """The vessel mask stored in a flow video's pickle (1 = vessel pixel)."""
    return np.asarray(flow_summary)[:, :, 2].astype(np.uint8)


def empty_frame_dict(frame_count):
    """``{frame: NaN}`` for every frame: the layout of the saved flow and mask files."""
    return dict(zip(np.arange(0, frame_count), [np.nan] * frame_count))


def flow_magnitudes(flow_regions, mask_regions, mm_per_pixel):
    """Per-frame flow magnitude per vessel pixel: arrays ``(up, down, both)``.

    `flow_regions` and `mask_regions` are the saved ``{frame: region}`` dicts
    (NaN for frames that were not measured). Each value is the flow magnitude
    summed over the whole region, converted to mm with `mm_per_pixel`, divided
    by the number of vessel pixels in the region; ``up`` counts only flow with
    a hue of at least `UP_DOWN_HUE_SPLIT` (pointing up the image), ``down``
    only flow at most that, ``both`` all of it. Frames without data are NaN,
    and the last frame is left out, as in the original report.
    """
    b = flow_regions
    a = mask_regions
    magnification_coefficient = mm_per_pixel

    up = np.array([[np.nan] * (len(b) - 1)])[0]
    down = np.array([[np.nan] * (len(b) - 1)])[0]
    both = np.array([[np.nan] * (len(b) - 1)])[0]

    for i in range(len(b) - 1):
        if str(b[i]) != 'nan':
            temp = b[i][:, :, 2].copy()
            temp_ang = b[i][:, :, 0].copy()
            temp[temp_ang < UP_DOWN_HUE_SPLIT] = 0
            temp = temp / FLOW_SCALE
            temp = temp * magnification_coefficient
            up[i] = np.sum(temp) / np.sum(a[i])

    for i in range(len(b) - 1):
        if str(b[i]) != 'nan':
            temp = b[i][:, :, 2].copy()
            temp_ang = b[i][:, :, 0].copy()
            temp[temp_ang > UP_DOWN_HUE_SPLIT] = 0
            temp = temp / FLOW_SCALE
            temp = temp * magnification_coefficient
            down[i] = np.sum(temp) / np.sum(a[i])

    for i in range(len(b) - 1):
        if str(b[i]) != 'nan':
            temp = b[i][:, :, 2].copy()
            temp = temp / FLOW_SCALE
            temp = temp * magnification_coefficient
            both[i] = np.sum(temp) / np.sum(a[i])

    return up, down, both


def frame_flow(flow_region, mask_region, mm_per_pixel):
    """``(up, down, both)`` for a single frame's region, as in `flow_magnitudes`.

    Used for the live readout while positioning a region. NaN when the region
    holds no vessel pixels.
    """
    vessel_pixels = np.sum(mask_region)
    if vessel_pixels == 0:
        return float('nan'), float('nan'), float('nan')
    magnitude = flow_region[:, :, 2] / FLOW_SCALE * mm_per_pixel
    hue = flow_region[:, :, 0]
    up = np.sum(np.where(hue >= UP_DOWN_HUE_SPLIT, magnitude, 0)) / vessel_pixels
    down = np.sum(np.where(hue <= UP_DOWN_HUE_SPLIT, magnitude, 0)) / vessel_pixels
    both = np.sum(magnitude) / vessel_pixels
    return float(up), float(down), float(both)
