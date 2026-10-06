"""The synthetic recordings the benchmark validates the estimators on (`capillary.simulate`)."""

import numpy as np
import pytest

from capillary import simulate
from capillary.intensity import extract_traces
from capillary.velocity import lag_and_correlation


@pytest.fixture(scope='module')
def recording():
    return simulate.simulate(simulate.hairpin(), 240, 1.0, seed=2)


def test_frames_and_ground_truth(recording):
    assert recording.frames.shape == (240, 230, 150) and recording.frames.dtype == np.uint8
    assert recording.mean_speed_px_per_frame == pytest.approx(1.0)
    assert recording.true_velocity_mm_s(0.002) == pytest.approx(1.0 * 30 * 0.002)


def test_the_same_seed_renders_the_same_clip(recording):
    again = simulate.simulate(simulate.hairpin(), 240, 1.0, seed=2)
    np.testing.assert_array_equal(again.frames, recording.frames)
    other = simulate.simulate(simulate.hairpin(), 240, 1.0, seed=3)
    assert not np.array_equal(other.frames, recording.frames)


def test_noise_matches_the_recordings(recording):
    frames = recording.frames.astype(np.float32)
    residual = frames[1:-1] - (frames[:-2] + frames[2:]) / 2
    assert np.median(residual.std(axis=0)) / np.sqrt(1.5) == pytest.approx(3.0, abs=0.3)


def test_the_vessel_is_darker_than_its_surroundings(recording):
    mean = recording.frames.mean(axis=0)
    x, y = recording.point_at(60)
    assert mean[int(y), int(x)] < mean[int(y), int(x) - 15] - 5


def test_pulsatile_speed_keeps_its_mean():
    pulsing = simulate.simulate(simulate.hairpin(), 300, 2.0, pulsatility=0.3, seed=1)
    assert pulsing.speed_px_per_frame.std() > 0.3
    assert pulsing.mean_speed_px_per_frame == pytest.approx(2.0, rel=0.05)


def test_boxes_and_drawn_lines_follow_the_vessel(recording):
    box1, box2 = recording.boxes(30, 30)
    assert np.hypot(box1.center_x - box2.center_x, box1.center_y - box2.center_y) == pytest.approx(30, abs=1.5)
    assert box2.center_y > box1.center_y           # the arterial limb runs up the image
    line = recording.drawn_line(20, 140, wobble_px=1.0, seed=4)
    assert line.length_px == pytest.approx(120, rel=0.05)
    positions, _ = recording.centreline.sample_positions(0.25)
    for point in line.points:
        assert np.min(np.hypot(*(positions - point).T)) <= 1.01


def test_clean_disturbances_switch_the_same_moment_change_off():
    clean = simulate.Disturbances.clean()
    assert clean.same_moment_sd == 0 and clean.jitter_px == 0 and clean.noise_sd > 0
    assert simulate.Disturbances.strong().same_moment_sd > simulate.Disturbances().same_moment_sd


def test_negative_speed_is_rejected():
    with pytest.raises(ValueError, match='reverse'):
        simulate.simulate(simulate.hairpin(), 10, -1.0)


def test_two_boxes_mostly_see_the_same_moment_change(recording):
    """The failure this simulator was calibrated to reproduce: on the real recordings two boxes 30 px
    apart on a capillary correlate best at a delay of zero, whatever the flow."""
    box1, box2 = recording.boxes(30, 30)
    trace = extract_traces(recording.frames, box1, box2, fps=recording.fps)
    lags = [lag_and_correlation(trace.a[i:i + 201], trace.b[i:i + 201])[0] for i in range(0, 40, 5)]
    assert np.mean(np.array(lags) == 0) >= 0.5          # the true lag is 30 frames
