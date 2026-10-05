"""Flow-region arithmetic, pinned against verbatim copies of the code it replaced.

`drag_box_bounds` and `flow_magnitudes` were moved out of the Tkinter classes
(`Caper.Rectangle`, `FrameClasses.FlowFrame`) in the 2026-10 GUI rebuild. The
`original_*` functions below are those methods as they were, so the tests prove
the move changed nothing.
"""

import itertools

import numpy as np
import pytest

from capillary.flow import (
    crop_box,
    drag_box_bounds,
    empty_frame_dict,
    flow_magnitudes,
    frame_flow,
    vessel_mask,
)


def original_calculate_corners_drag(point1, point2, width, height, min_size=5):
    """`Caper.Rectangle.calculate_corners_drag` as of 2026-10-05, returning its corners."""
    x_left, x_right = sorted((int(point1[0]), int(point2[0])))
    y_top, y_bottom = sorted((int(point1[1]), int(point2[1])))
    if x_right - x_left < min_size:
        x_right = x_left + min_size
    if y_bottom - y_top < min_size:
        y_bottom = y_top + min_size
    x_left = max(0, min(x_left, width - min_size))
    x_right = max(min_size, min(x_right, width))
    y_top = max(0, min(y_top, height - min_size))
    y_bottom = max(min_size, min(y_bottom, height))
    top_left = (x_left, y_top)
    lower_left = (x_left, y_bottom)
    lower_right = (x_right, y_bottom)
    return top_left, lower_left, lower_right


def original_region(frame, corners):
    """`Rectangle.get_selected_data_for_flow`: frame[top_left y : lower_left y, lower_left x : lower_right x]."""
    top_left, lower_left, lower_right = corners
    return frame[top_left[1]:lower_left[1], lower_left[0]:lower_right[0]]


def original_flow_report_values(b, a, magnification_coefficient):
    """The numeric part of `FrameClasses.FlowFrame.generate_report` as of 2026-10-05."""
    up = np.array([[np.nan] * (len(b) - 1)])[0]
    down = np.array([[np.nan] * (len(b) - 1)])[0]
    both = np.array([[np.nan] * (len(b) - 1)])[0]
    for i in range(len(b) - 1):
        if str(b[i]) != 'nan':
            temp = b[i][:, :, 2].copy()
            temp_ang = b[i][:, :, 0].copy()
            temp[temp_ang < 90] = 0
            temp = temp / 25.5
            temp = temp * magnification_coefficient
            up[i] = np.sum(temp) / np.sum(a[i])
    for i in range(len(b) - 1):
        if str(b[i]) != 'nan':
            temp = b[i][:, :, 2].copy()
            temp_ang = b[i][:, :, 0].copy()
            temp[temp_ang > 90] = 0
            temp = temp / 25.5
            temp = temp * magnification_coefficient
            down[i] = np.sum(temp) / np.sum(a[i])
    for i in range(len(b) - 1):
        if str(b[i]) != 'nan':
            temp = b[i][:, :, 2].copy()
            temp = temp / 25.5
            temp = temp * magnification_coefficient
            both[i] = np.sum(temp) / np.sum(a[i])
    return up, down, both


COORDINATES = [-20, 0, 3, 50, 317, 636, 640, 700]


def test_drag_box_matches_the_original_for_every_drag():
    height, width = 480, 640
    frame = np.arange(height * width * 3).reshape(height, width, 3)
    checked = 0
    for x1, y1, x2, y2 in itertools.product(COORDINATES, repeat=4):
        corners = original_calculate_corners_drag((x1, y1), (x2, y2), width, height)
        bounds = drag_box_bounds((x1, y1), (x2, y2), frame.shape)
        x_left, x_right, y_top, y_bottom = bounds
        assert (x_left, y_top) == corners[0]
        assert (x_left, y_bottom) == corners[1]
        assert (x_right, y_bottom) == corners[2]
        np.testing.assert_array_equal(crop_box(frame, bounds), original_region(frame, corners))
        checked += 1
    assert checked == len(COORDINATES) ** 4


@pytest.mark.parametrize('point1,point2', [((10, 10), (10, 10)), ((100, 40), (100, 300)), ((5, 60), (400, 60))])
def test_degenerate_drags_still_give_a_region(point1, point2):
    x_left, x_right, y_top, y_bottom = drag_box_bounds(point1, point2, (480, 640))
    assert x_right - x_left >= 5
    assert y_bottom - y_top >= 5


def test_drag_direction_does_not_matter():
    shape = (480, 640)
    assert drag_box_bounds((300, 200), (100, 50), shape) == drag_box_bounds((100, 50), (300, 200), shape)
    assert drag_box_bounds((300, 50), (100, 200), shape) == (100, 300, 50, 200)


def random_flow_data(frames=40, size=(12, 9), measured=range(5, 30), seed=0):
    rng = np.random.default_rng(seed)
    flow = empty_frame_dict(frames)
    mask = empty_frame_dict(frames)
    region_mask = (rng.random(size) > 0.6).astype(np.uint8)
    for i in measured:
        region = np.zeros(size + (3,), dtype=np.uint8)
        region[:, :, 0] = rng.integers(0, 181, size)
        region[:, :, 1] = 255
        region[:, :, 2] = rng.integers(0, 256, size)
        flow[i] = region
        mask[i] = region_mask.copy()
    return flow, mask


def test_flow_values_match_the_original_report_exactly():
    flow, mask = random_flow_data()
    for new, old in zip(flow_magnitudes(flow, mask, 0.0013), original_flow_report_values(flow, mask, 0.0013)):
        np.testing.assert_array_equal(new, old)


def test_unmeasured_frames_stay_nan_and_the_last_frame_is_left_out():
    flow, mask = random_flow_data(frames=40, measured=range(5, 40))
    up, down, both = flow_magnitudes(flow, mask, 0.001)
    assert len(up) == 39
    assert np.isnan(up[:5]).all() and np.isfinite(up[5:]).all()


def test_up_and_down_split_at_hue_90_and_add_up_to_more_than_both():
    flow, mask = random_flow_data()
    up, down, both = flow_magnitudes(flow, mask, 0.001)
    measured = np.isfinite(both)
    # hue == 90 counts in both directions, so up + down >= both
    assert np.all(up[measured] + down[measured] >= both[measured] - 1e-12)


def test_single_frame_readout_agrees_with_the_report_values():
    flow, mask = random_flow_data()
    up, down, both = flow_magnitudes(flow, mask, 0.0013)
    for i in (5, 17, 29):
        assert frame_flow(flow[i], mask[i], 0.0013) == pytest.approx((up[i], down[i], both[i]), rel=1e-9)


def test_single_frame_readout_without_vessel_pixels_is_nan():
    region = np.zeros((4, 4, 3), dtype=np.uint8)
    assert all(np.isnan(v) for v in frame_flow(region, np.zeros((4, 4), dtype=np.uint8), 0.001))


def test_vessel_mask_is_channel_two():
    summary = np.zeros((6, 8, 3), dtype=np.uint8)
    summary[2:4, 3:5, 2] = 1
    mask = vessel_mask(summary)
    assert mask.dtype == np.uint8 and mask.sum() == 4
