"""Lag and velocity estimation, against signals whose true lag is known."""

import numpy as np
import pandas as pd
import pytest

from capillary.intensity import IntensityTrace
from capillary.velocity import (
    analyze_trace,
    lag_and_correlation,
    signed_lag,
    sliding_lag,
    velocity_from_lag,
)


def delayed_pair(delay, length=201, seed=0):
    """Two traces where `b` lags `a` by exactly `delay` frames."""
    rng = np.random.default_rng(seed)
    base = rng.normal(size=length + 200)
    start = 100
    a = base[start:start + length]
    b = base[start - delay:start - delay + length]
    return a, b


@pytest.mark.parametrize('delay', [-20, -7, -1, 0, 1, 7, 20])
@pytest.mark.parametrize('length', [200, 201, 220, 221])
def test_signed_lag_recovers_a_known_delay(delay, length):
    a, b = delayed_pair(delay, length=length)
    assert signed_lag(a, b) == delay


@pytest.mark.parametrize('delay', [-7, 0, 7])
def test_legacy_lag_is_one_frame_high_on_odd_windows(delay):
    """Pins the off-by-one this module fixes.

    `np.correlate(..., 'same')` places zero displacement at ``n // 2``, but the
    original code used ``ceil(n / 2)``. Every report window (201...301) is odd,
    so every historical velocity came from a lag one frame too large.
    """
    a_odd, b_odd = delayed_pair(delay, length=201)
    assert signed_lag(a_odd, b_odd, legacy=True) == delay + 1

    a_even, b_even = delayed_pair(delay, length=200)
    assert signed_lag(a_even, b_even, legacy=True) == delay


def test_lag_is_antisymmetric():
    a, b = delayed_pair(6)
    assert signed_lag(a, b) == 6
    assert signed_lag(b, a) == -6


def test_non_finite_samples_give_no_estimate():
    a, b = delayed_pair(5)
    a = a.copy()
    a[17] = np.nan
    assert np.isnan(signed_lag(a, b))
    assert all(np.isnan(value) for value in lag_and_correlation(a, b))


def test_mismatched_lengths_are_rejected():
    with pytest.raises(ValueError):
        signed_lag(np.zeros(10), np.zeros(11))


def test_correlation_is_high_for_a_clean_delay_and_low_for_noise():
    a, b = delayed_pair(5)
    lag, correlation = lag_and_correlation(a, b)
    assert lag == 5
    assert correlation > 0.95

    rng = np.random.default_rng(99)
    _, unrelated = lag_and_correlation(rng.normal(size=201), rng.normal(size=201))
    assert abs(unrelated) < 0.5


def test_velocity_formula():
    # 100 px in 40 frames at 30 fps = 75 px/s; at 0.002 mm/px that is 0.15 mm/s.
    assert velocity_from_lag(40, 100, 30, 0.002) == pytest.approx(0.15)
    # Reversing the lag reverses the direction, not the speed.
    assert velocity_from_lag(-40, 100, 30, 0.002) == pytest.approx(-0.15)


def test_zero_or_missing_lag_is_not_infinite_velocity():
    # A lag of zero means "faster than one frame", not "infinitely fast"; an
    # inf here would poison every mean computed downstream.
    assert np.isnan(velocity_from_lag(0, 100, 30, 0.002))
    assert np.isnan(velocity_from_lag(np.nan, 100, 30, 0.002))


def test_sliding_lag_is_indexed_by_window_centre():
    a, b = delayed_pair(4, length=500)
    estimates = sliding_lag(a, b, window=201, step=10)

    assert estimates.index[0] == 100          # first window covers 0..200
    assert estimates.index.name == 'frame'
    assert (estimates.index.to_series().diff().dropna() == 10).all()
    assert (estimates['lag'] == 4).mean() > 0.9


def test_sliding_lag_rejects_degenerate_parameters():
    a, b = delayed_pair(1, length=50)
    with pytest.raises(ValueError):
        sliding_lag(a, b, window=1)
    with pytest.raises(ValueError):
        sliding_lag(a, b, window=10, step=0)


def make_trace(delay=40, distance_px=100.0, fps=30.0, length=600):
    a, b = delayed_pair(delay, length=length)
    return IntensityTrace(a=a, b=b, distance_px=distance_px, fps=fps)


def test_analyze_trace_recovers_the_known_velocity():
    trace = make_trace(delay=40, distance_px=100.0, fps=30.0)
    report = analyze_trace(trace, mm_per_pixel=0.002, positive_flow='a_to_b')

    # 100 px / 40 frames * 30 fps * 0.002 mm/px = 0.15 mm/s
    assert report['velocity'].median() == pytest.approx(0.15, rel=1e-6)
    assert report['correlation'].median() > 0.95
    assert report['time_s'].iloc[0] == pytest.approx(report.index[0] / 30.0)


def test_default_direction_matches_the_gui_report_sign():
    """Rectangle 1 is the downstream box, so the GUI's positive velocity is b -> a."""
    trace = make_trace(delay=40)
    towards_b = analyze_trace(trace, mm_per_pixel=0.002, positive_flow='a_to_b')
    default = analyze_trace(trace, mm_per_pixel=0.002)

    assert default['velocity'].median() == pytest.approx(-towards_b['velocity'].median())


def test_analyze_trace_reports_every_window_plus_the_mean():
    trace = make_trace(delay=20, length=700)
    report = analyze_trace(trace, mm_per_pixel=0.002, windows=(201, 301), step=25)

    for window in (201, 301):
        for prefix in ('lag', 'correlation', 'velocity'):
            assert f'{prefix}_{window}' in report.columns
    assert {'lag', 'correlation', 'velocity', 'velocity_smoothed'} <= set(report.columns)
    assert report['lag'].median() == pytest.approx(20)


def test_windows_longer_than_the_clip_are_skipped():
    trace = make_trace(delay=5, length=250)
    report = analyze_trace(trace, mm_per_pixel=0.002, windows=(201, 999))

    assert 'lag_201' in report.columns
    assert 'lag_999' not in report.columns

    with pytest.raises(ValueError, match='longer than'):
        analyze_trace(trace, mm_per_pixel=0.002, windows=(999,))


def test_invalid_direction_is_rejected():
    with pytest.raises(ValueError, match='positive_flow'):
        analyze_trace(make_trace(), mm_per_pixel=0.002, positive_flow='sideways')


def test_legacy_mode_reproduces_the_old_biased_velocity():
    """The old code's velocities were biased fast; keep a way to reproduce them."""
    trace = make_trace(delay=40, distance_px=100.0, fps=30.0)
    fixed = analyze_trace(trace, mm_per_pixel=0.002, positive_flow='a_to_b')
    legacy = analyze_trace(trace, mm_per_pixel=0.002, positive_flow='a_to_b', legacy_lag=True)

    # lag 41 instead of 40 -> velocity low by 1/41 in this direction
    assert legacy['lag'].median() == pytest.approx(fixed['lag'].median() + 1)
    assert legacy['velocity'].median() == pytest.approx(100 / 41 * 30 * 0.002, rel=1e-6)


def test_trace_rejects_mismatched_channels():
    with pytest.raises(ValueError, match='differ in length'):
        IntensityTrace(a=np.zeros(10), b=np.zeros(11), distance_px=10.0, fps=30.0)


def test_trace_counts_usable_frames():
    a = np.array([1.0, 2.0, np.nan, 4.0])
    b = np.array([1.0, np.nan, 3.0, 4.0])
    trace = IntensityTrace(a=a, b=b, distance_px=10.0, fps=30.0)

    assert trace.n_frames == 4
    assert trace.valid_count() == 2
    assert trace.duration_s == pytest.approx(4 / 30)


def test_lag_and_correlation_returns_plain_floats():
    lag, correlation = lag_and_correlation(*delayed_pair(3))
    assert isinstance(lag, float) and isinstance(correlation, float)
    assert not isinstance(correlation, pd.Series)


def test_resolvable_range_spans_one_frame_to_half_a_window():
    from capillary.velocity import resolvable_range

    # 100 px at 0.002 mm/px is 0.2 mm; crossing it in 1 frame at 30 fps is 6 mm/s,
    # in 100 frames (half of a 201-frame window) 0.06 mm/s.
    slowest, fastest = resolvable_range(100, 30, 0.002)
    assert fastest == pytest.approx(6.0)
    assert slowest == pytest.approx(0.06)
    assert all(np.isnan(v) for v in resolvable_range(0, 30, 0.002))


def test_resolvable_range_matches_the_zero_lag_limit_found_in_real_data():
    """The 2026-09-17 entry: ~29.1 px apart at 30 fps, nothing above ~1.16 mm/s resolves."""
    from capillary.velocity import resolvable_range

    assert resolvable_range(29.1, 30, 0.001328903654)[1] == pytest.approx(1.16, abs=0.005)


def test_velocity_summary():
    from capillary.velocity import velocity_summary

    summary = velocity_summary([1.0, 2.0, np.nan, -1.0, 3.0], correlation=[0.2, 0.8, np.nan],
                               lag=[[0, 4], [np.nan, 0], [2, 3]])
    assert summary['estimates'] == 5 and summary['resolved'] == 4
    assert summary['resolved_fraction'] == pytest.approx(0.8)
    assert summary['median'] == pytest.approx(1.5)
    assert summary['positive_fraction'] == pytest.approx(0.75)
    assert summary['median_correlation'] == pytest.approx(0.5)
    assert summary['zero_lag_fraction'] == pytest.approx(2 / 5)

    empty = velocity_summary([np.nan, np.nan])
    assert empty['resolved'] == 0 and np.isnan(empty['median'])


def test_sharpness_score_is_shared_with_utilities():
    import Utilities
    from capillary.quality import calculate_blur

    assert Utilities.calculate_blur is calculate_blur
