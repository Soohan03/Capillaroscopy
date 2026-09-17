"""ROI geometry — the arithmetic that decides which pixels a measurement uses.

The expected values here are the behaviour of `Caper.Rectangle`, written out
explicitly so the engine can be checked without importing the GUI.
"""

import numpy as np
import pytest

from capillary.roi import ROI


def test_parse_accepts_centre_only_and_full_form():
    assert ROI.parse('320,240', 16, 8) == ROI(320, 240, 16, 8)
    assert ROI.parse('320, 240, 20, 30') == ROI(320, 240, 20, 30)


@pytest.mark.parametrize('text', ['320', '320,240,20', 'a,b', ''])
def test_parse_rejects_malformed_input(text):
    with pytest.raises(ValueError):
        ROI.parse(text)


def test_rejects_non_positive_size():
    with pytest.raises(ValueError):
        ROI(10, 10, 0, 10)


def test_crop_is_centred_on_the_click():
    frame = np.arange(100 * 100).reshape(100, 100)
    roi = ROI(50, 40, 10, 10)

    assert roi.bounds(frame.shape) == (45, 55, 35, 45)
    assert roi.crop(frame).shape == (10, 10)
    np.testing.assert_array_equal(roi.crop(frame), frame[35:45, 45:55])


def test_odd_box_size_loses_a_pixel_like_the_gui():
    # int(11 / 2) == 5 on each side, so an 11-wide box samples 10 columns.
    # Kept deliberately: changing it would move every historical measurement.
    frame = np.zeros((100, 100))
    assert ROI(50, 50, 11, 11).crop(frame).shape == (10, 10)


@pytest.mark.parametrize(
    'centre,expected',
    [
        ((50, 40), (45, 55, 35, 45)),   # well inside the frame
        ((2, 40), (0, 10, 35, 45)),     # pushed off the left edge
        ((40, 3), (35, 45, 0, 10)),     # pushed off the top edge
        ((98, 40), (90, 100, 35, 45)),  # pushed off the right edge
        ((40, 97), (35, 45, 90, 100)),  # pushed off the bottom edge
    ],
)
def test_box_is_clamped_inside_the_frame(centre, expected):
    frame = np.zeros((100, 100))
    roi = ROI(centre[0], centre[1], 10, 10)

    assert roi.bounds(frame.shape) == expected
    assert roi.crop(frame).shape == (10, 10)


def test_distance_uses_clamped_centres():
    frame_shape = (240, 320)
    # Same column, 100 rows apart: the separation is exactly 100 px.
    assert ROI(160, 60).distance_to(ROI(160, 160), frame_shape) == pytest.approx(100.0)
    # 3-4-5 triangle.
    assert ROI(100, 100).distance_to(ROI(130, 140), frame_shape) == pytest.approx(50.0)


def test_crop_of_a_colour_frame_keeps_the_box_shape():
    frame = np.zeros((100, 100, 3))
    assert ROI(50, 50, 10, 10).crop(frame).shape == (10, 10, 3)
