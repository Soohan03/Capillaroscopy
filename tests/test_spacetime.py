"""The centre-line velocity estimator (`capillary.spacetime`), against diagrams with a known speed."""

import numpy as np
import pandas as pd
import pytest

from capillary import simulate
from capillary.spacetime import (
    MIN_COHERENCE,
    MIN_SNR,
    Centreline,
    SpaceTimeSampler,
    analyze_space_time,
    resolvable_speeds,
    space_time_diagram,
    space_time_summary,
    speed_limits,
    streak_speed,
)

FPS, MM_PER_PIXEL = 30.0, 0.002


def smooth(rng, n, sigma):
    half = int(4 * sigma) + 1
    x = np.arange(-half, half + 1)
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    out = np.convolve(rng.normal(size=n + 2 * half), kernel / kernel.sum(), 'valid')[:n]
    return (out - out.mean()) / out.std()


def diagram(speed, frames=90, positions=120, seed=0, cells_sd=2.5, same_moment_sd=4.0, noise_sd=1.5):
    """Frames x positions: a pattern moving `speed` px/frame towards higher positions, plus what
    every position sees at the same moment (unevenly), still structure and noise."""
    rng = np.random.default_rng(seed)
    shift = speed * np.arange(frames)
    lo, hi = -max(shift.max(), 0) - 50, positions - min(shift.min(), 0) + 50
    coords = np.arange(lo, hi)
    pattern = cells_sd * (0.6 * smooth(rng, coords.size, 2.0) + 0.8 * smooth(rng, coords.size, 7.0))
    s = np.arange(positions, dtype=float)
    moving = np.array([np.interp(s - x, coords, pattern) for x in shift])
    same = same_moment_sd * smooth(rng, frames, 4.0)
    gain = 1 + 0.2 * smooth(rng, positions, 15.0)
    still = 5 * smooth(rng, positions, 10.0)
    return still[None, :] + moving + gain[None, :] * same[:, None] + rng.normal(0, noise_sd, (frames, positions))


# ------------------------------------------------------------------------------ the line

def test_line_from_points_drops_repeated_points_and_needs_two():
    line = Centreline.from_points([(0, 0), (0, 0), (10, 0)])
    assert line.points == ((0.0, 0.0), (10.0, 0.0))
    with pytest.raises(ValueError):
        Centreline.from_points([(1, 1), (1, 1)])


def test_straight_line_is_sampled_every_pixel():
    line = Centreline.from_points([(10, 20), (40, 60)])                # 30-40-50 triangle
    assert line.length_px == pytest.approx(50.0)
    positions, normals = line.sample_positions(1.0)
    assert len(positions) == 51
    np.testing.assert_allclose(positions[0], (10, 20))
    np.testing.assert_allclose(positions[-1], (40, 60), atol=1e-6)
    np.testing.assert_allclose(np.hypot(*np.diff(positions, axis=0).T), 1.0, atol=1e-6)
    np.testing.assert_allclose(normals @ np.array([0.6, 0.8]), 0.0, atol=1e-9)   # across the line


def test_curve_passes_through_every_clicked_point():
    points = [(0, 0), (20, 10), (40, 0), (60, 15)]
    curve = Centreline.from_points(points).curve()
    for point in points:
        assert np.min(np.hypot(*(curve - point).T)) < 1e-6


def test_reversing_a_line_reverses_its_direction():
    line = Centreline.from_points([(0, 0), (20, 10), (40, 0)])
    assert line.reversed().points == tuple(reversed(line.points))


def test_sampler_averages_across_the_line():
    image = np.tile(np.arange(100, dtype=np.float32), (60, 1))        # brightness = x
    sampler = SpaceTimeSampler(Centreline.from_points([(10, 30), (90, 30)]), half_width_px=2)
    row = sampler.row(image)
    np.testing.assert_allclose(row, np.arange(10, 91), atol=1e-4)
    vertical = SpaceTimeSampler(Centreline.from_points([(50, 5), (50, 55)]), half_width_px=2)
    np.testing.assert_allclose(vertical.row(image), 50.0, atol=1e-4)    # across: 48..52, mean 50


def test_sampler_knows_when_the_line_leaves_the_frame():
    assert SpaceTimeSampler(Centreline.from_points([(10, 30), (90, 30)])).inside((60, 100))
    assert not SpaceTimeSampler(Centreline.from_points([(10, 1), (90, 1)])).inside((60, 100))


# ----------------------------------------------------------------------------- the slope

@pytest.mark.parametrize('speed', [0.25, 0.5, 1.0, 2.0, 3.0, 4.0])
def test_known_speed_is_recovered_despite_same_moment_changes(speed):
    """The median of eight 3-s blocks within 4%, single blocks within 10%, up to 3/4 of the fastest
    speed a 120-px line reports (about 5.3 px/frame; at the top only the coarsest patterns are unaliased)."""
    estimates = [streak_speed(diagram(speed, seed=seed)) for seed in range(8)]
    assert all(estimate.resolved for estimate in estimates)
    speeds = np.array([estimate.speed_px_per_frame for estimate in estimates])
    assert np.median(speeds) == pytest.approx(speed, rel=0.04)
    assert np.all(np.abs(speeds / speed - 1) < 0.10)
    assert all(MIN_COHERENCE <= estimate.coherence <= 1.0 for estimate in estimates)


@pytest.mark.parametrize('speed', [15.0, 25.0])
def test_flow_faster_than_the_line_can_measure_is_not_reported(speed):
    """A 120-px line cannot follow 15 px/frame at all; whatever slope comes out must not count."""
    for seed in range(5):
        estimate = streak_speed(diagram(speed, seed=seed))
        assert not estimate.resolved, (seed, estimate)


def test_flow_the_other_way_reads_negative():
    estimate = streak_speed(diagram(1.5, seed=4)[:, ::-1])
    assert estimate.speed_px_per_frame == pytest.approx(-1.5, rel=0.05)


def test_no_flow_is_not_resolved():
    for seed in range(8):
        estimate = streak_speed(diagram(0.0, seed=seed))
        assert not estimate.resolved
        assert not (estimate.snr >= MIN_SNR)


def test_a_much_stronger_same_moment_change_does_not_move_the_estimate():
    calm = streak_speed(diagram(2.0, seed=5, same_moment_sd=1.0))
    stormy = streak_speed(diagram(2.0, seed=5, same_moment_sd=40.0))
    assert stormy.resolved
    assert stormy.speed_px_per_frame == pytest.approx(calm.speed_px_per_frame, rel=0.02)


def test_unusable_blocks_give_no_estimate():
    assert np.isnan(streak_speed(np.zeros((10, 100))).speed_px_per_frame)     # too few frames
    assert np.isnan(streak_speed(np.zeros((90, 8))).speed_px_per_frame)       # too short a line
    block = diagram(1.0)
    block[5, 7] = np.nan
    assert np.isnan(streak_speed(block).speed_px_per_frame)


def test_resolvable_speeds_grow_with_line_length():
    slow_100, fast_100 = resolvable_speeds(100, FPS, MM_PER_PIXEL)
    slow_200, fast_200 = resolvable_speeds(200, FPS, MM_PER_PIXEL)
    to_px = 1 / (FPS * MM_PER_PIXEL)
    assert 0.04 * 100 < fast_100 * to_px < 0.05 * 100          # about 0.045 px/frame per pixel of line
    assert fast_200 == pytest.approx(2 * fast_100, rel=0.05)
    assert slow_100 == slow_200 < fast_100
    assert speed_limits(101, 90) == pytest.approx((slow_100 * to_px, fast_100 * to_px))
    assert all(np.isnan(v) for v in resolvable_speeds(5, FPS, MM_PER_PIXEL))


def test_the_fastest_speed_is_where_the_usable_patterns_run_out():
    """At the theoretical limit the unaliased patterns weigh exactly three full patterns."""
    from capillary.spacetime import FASTEST_FRACTION, MIN_WEIGHT, _omega_weight, _usable_k

    _, fastest = speed_limits(121, 90)
    limit = fastest / FASTEST_FRACTION
    k = _usable_k(121)
    assert _omega_weight(limit * k).sum() == pytest.approx(MIN_WEIGHT, abs=0.05)
    assert _omega_weight(1.05 * limit * k).sum() < MIN_WEIGHT


# ------------------------------------------------------------------------ whole diagrams

def test_analysis_runs_block_by_block_and_converts_to_mm_per_s():
    data = np.vstack([diagram(2.0, frames=90, seed=s) for s in range(3)])     # 270 frames
    report = analyze_space_time(data, FPS, MM_PER_PIXEL, block_frames=90, step_frames=45, first_frame=1000)
    assert list(report.index) == [1045, 1090, 1135, 1180, 1225]
    assert set(report.columns) == {'time_s', 'speed_px_per_frame', 'velocity_mm_s', 'snr', 'coherence', 'resolved'}
    assert report['time_s'].iloc[0] == pytest.approx(1045 / FPS)
    resolved = report[report['resolved']]
    assert len(resolved) >= 3
    np.testing.assert_allclose(resolved['velocity_mm_s'], resolved['speed_px_per_frame'] * FPS * MM_PER_PIXEL)
    assert resolved['velocity_mm_s'].median() == pytest.approx(2.0 * FPS * MM_PER_PIXEL, rel=0.1)
    assert report.loc[~report['resolved'], 'velocity_mm_s'].isna().all()


def test_analysis_needs_one_block():
    with pytest.raises(ValueError, match='fewer than one block'):
        analyze_space_time(np.zeros((50, 100)), FPS, MM_PER_PIXEL, block_frames=90)


def test_summary():
    report = pd.DataFrame({'velocity_mm_s': [0.1, 0.2, np.nan, -0.1], 'snr': [20, 30, 2, 10],
                           'speed_px_per_frame': [1, 2, 0.5, -1], 'resolved': [True, True, False, True]})
    summary = space_time_summary(report)
    assert summary['blocks'] == 4 and summary['resolved'] == 3
    assert summary['median'] == pytest.approx(0.1)
    assert summary['positive_fraction'] == pytest.approx(2 / 3)
    assert summary['median_snr'] == pytest.approx(15)


# ---------------------------------------------------------------- end to end, on video

def test_velocity_from_a_synthetic_recording():
    """Render a capillary loop with the measured disturbances; a hand-drawn line finds the speed."""
    recording = simulate.simulate(simulate.hairpin(), 300, 1.5, seed=3)
    line = recording.drawn_line(20, 140, seed=1)
    data = space_time_diagram(recording.frames, line)
    report = analyze_space_time(data, recording.fps, MM_PER_PIXEL, step_frames=30)
    truth = recording.true_velocity_mm_s(MM_PER_PIXEL)
    assert report['resolved'].mean() > 0.8
    assert report['velocity_mm_s'].median() == pytest.approx(truth, rel=0.05)
