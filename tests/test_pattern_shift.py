"""The pattern-shift velocity estimator (`capillary.pattern_shift`), against diagrams with a known speed."""

import numpy as np
import pytest

from capillary import simulate
from capillary.pattern_shift import (
    BANDPASS_PX,
    BLOCK_FRAMES,
    MIN_SNR,
    MIN_SPEED,
    _block_sums,
    _prepared,
    pattern_shift,
    shift_time_course,
)
from capillary.spacetime import space_time_diagram

from .test_spacetime import diagram, smooth

FPS, MM_PER_PIXEL = 30.0, 0.002


@pytest.mark.parametrize('bandpass_px', [BANDPASS_PX, None])
def test_the_correlation_sums_equal_a_direct_computation(bandpass_px):
    block = np.random.default_rng(1).normal(size=(40, 30))
    lags, max_shift = np.array([1, 3]), 6
    sums = _block_sums(block, lags, max_shift, bandpass_px)
    b = _prepared(block, bandpass_px)
    n = b.shape[1]
    for i, k in enumerate(lags):
        for j, d in enumerate(range(-max_shift, max_shift + 1)):
            x, y = (b[:-k, :n - d], b[k:, d:]) if d >= 0 else (b[:-k, -d:], b[k:, :n + d])
            np.testing.assert_allclose(sums[i, :, j], [(x * y).sum(), (x * x).sum(), (y * y).sum()], rtol=1e-9)


def test_rows_are_prepared_without_still_structure_and_band_passed():
    rng = np.random.default_rng(0)
    still, same = rng.normal(size=200), rng.normal(size=6)
    x = np.arange(200)

    def gain(wavelength):
        wave = np.cos(2 * np.pi * x / wavelength)
        sign = np.array([1, -1, 1, -1, 1, -1])[:, None]          # changes over time, so it is not still
        out = _prepared(still[None, :] + same[:, None] + sign * wave[None, :])
        return np.abs(out[:, 50:150]).max()                       # away from the ends of the line

    assert gain(10) > 0.7               # cells, plasma gaps and groups of cells pass
    assert gain(2) < 0.02               # pixel-to-pixel noise does not
    assert gain(200) < 0.05             # nor the line's coarse shading
    assert np.allclose(_prepared(still[None, :] + same[:, None] + 0 * x), 0)       # still and same-moment: gone
    assert _prepared(np.zeros((6, 200)), None).shape == (6, 199)                     # the old method differences


@pytest.mark.parametrize('speed, tolerance', [(1.5, 0.06), (4.0, 0.02), (9.0, 0.02), (14.0, 0.02)])
def test_known_speed_is_recovered_despite_same_moment_changes(speed, tolerance):
    # near 1 px/frame a coarse pattern can put a single 30-s clip some 5% off (over seeds the error is ~0)
    estimate = pattern_shift(diagram(speed, frames=900, seed=2))
    assert estimate.resolved
    assert estimate.speed_px_per_frame == pytest.approx(speed, rel=tolerance)


@pytest.mark.parametrize('speed', [1.85, 2.15])
def test_no_speed_attracts_the_estimate(speed):
    # a frame distance switched on at a fixed speed (k = 1 at 2 px/frame) made the score jump there and the
    # estimate snap to exactly 2.00 px/frame, with an interval of zero width (FP03_Qefter_försök2)
    # (single 30-s clips of this coarse pattern scatter by 2-4% here; snapping to 2.00 would be 7-8% off)
    estimate = pattern_shift(diagram(speed, frames=900, seed=12))
    assert estimate.resolved and estimate.speed_px_per_frame == pytest.approx(speed, rel=0.05)
    assert estimate.ci95[1] - estimate.ci95[0] > 0.001


def test_flow_the_other_way_reads_negative():
    estimate = pattern_shift(diagram(5.0, frames=900, seed=3)[:, ::-1])
    assert estimate.resolved and estimate.speed_px_per_frame == pytest.approx(-5.0, rel=0.02)


@pytest.mark.parametrize('seed', range(4))
def test_no_flow_is_not_resolved(seed):
    estimate = pattern_shift(diagram(0.0, frames=900, seed=seed))
    assert not estimate.resolved and estimate.snr < MIN_SNR


def test_a_much_stronger_same_moment_change_does_not_create_flow():
    estimate = pattern_shift(diagram(0.0, frames=900, seed=5, same_moment_sd=40.0))
    assert not estimate.resolved


def test_a_pattern_flickering_in_place_is_not_flow():
    # a still pattern repeating every 10 px that brightens and darkens over several frames: its correlation
    # peaks every 10 px of shift, on both sides, and must not be read as flow of 10 px/frame
    rng = np.random.default_rng(10)
    positions = np.arange(120)
    brightness = smooth(rng, 900, 6.0)                       # changing over several frames, like the recordings
    flicker = brightness[:, None] * 3.0 * np.cos(2 * np.pi * positions / 10.0)[None, :]
    estimate = pattern_shift(flicker + rng.normal(0, 1.5, flicker.shape))
    assert not estimate.resolved


def test_flow_slower_than_the_method_measures_is_not_reported():
    # the centre-line method measures this; the search starts at MIN_SPEED
    estimate = pattern_shift(diagram(0.3, frames=900, seed=6))
    assert MIN_SPEED > 0.3 and not estimate.resolved
    assert abs(estimate.speed_px_per_frame) == pytest.approx(MIN_SPEED, abs=0.02)     # the edge, nothing beyond it


def test_pooling_makes_a_faint_pattern_measurable():
    # (the differenced rows used before 2026-10-11 needed about three times this contrast to resolve it pooled)
    faint = diagram(6.0, frames=1800, seed=7, cells_sd=0.4, noise_sd=1.5)
    one_block = pattern_shift(faint[:BLOCK_FRAMES])
    pooled = pattern_shift(faint)
    assert not one_block.resolved
    assert pooled.resolved and pooled.speed_px_per_frame == pytest.approx(6.0, rel=0.03)
    assert pooled.blocks == 20


def test_the_interval_holds_the_estimate_and_narrows_with_more_blocks():
    widths = []
    for seed in range(8, 12):
        data = diagram(4.0, frames=2700, seed=seed)
        short, long = pattern_shift(data[:900]), pattern_shift(data)
        for estimate in (short, long):
            assert estimate.resolved and estimate.ci95[0] < estimate.speed_px_per_frame < estimate.ci95[1]
        widths.append((np.diff(short.ci95)[0], np.diff(long.ci95)[0]))
    short_width, long_width = np.median(widths, axis=0)
    assert long_width < short_width
    assert np.isnan(pattern_shift(data[:2 * BLOCK_FRAMES]).ci95[0])          # too few blocks to leave one out


def test_unusable_input_gives_no_estimate():
    assert np.isnan(pattern_shift(diagram(3.0, frames=900)[:, :20]).speed_px_per_frame)     # line too short
    assert np.isnan(pattern_shift(diagram(3.0, frames=60)).speed_px_per_frame)              # less than a block
    data = diagram(3.0, frames=900)
    data[5, 5] = np.nan
    assert np.isnan(pattern_shift(data).speed_px_per_frame)


def test_time_course_in_windows():
    data = diagram(5.0, frames=1800, seed=9)
    course = shift_time_course(data, FPS, MM_PER_PIXEL, window_frames=900, step_frames=450, first_frame=100)
    assert list(course.index) == [550, 1000, 1450]
    assert list(course.columns) == ['time_s', 'speed_px_per_frame', 'velocity_mm_s', 'ci95_low_mm_s',
                                    'ci95_high_mm_s', 'snr', 'resolved']
    assert course['resolved'].all()
    np.testing.assert_allclose(course['velocity_mm_s'], course['speed_px_per_frame'] * FPS * MM_PER_PIXEL)
    with pytest.raises(ValueError):
        shift_time_course(data[:600], FPS, MM_PER_PIXEL, window_frames=900, step_frames=450)


def test_a_synthetic_recording_with_motion_blur():
    """A capillary loop with the measured disturbances, the shutter open for the whole frame."""
    for speed, seed in ((6.0, 3), (25.0, 4)):
        recording = simulate.simulate(simulate.hairpin(), 900, speed, seed=seed)
        estimate = pattern_shift(space_time_diagram(recording.frames, recording.drawn_line(20, 140, seed=1)))
        if speed == 6.0:
            assert estimate.resolved and estimate.speed_px_per_frame == pytest.approx(speed, rel=0.03)
        else:
            # cells smeared over 25 px: either right or not reported, never a wrong speed
            assert not estimate.resolved or estimate.speed_px_per_frame == pytest.approx(speed, rel=0.05)
