"""Cross-correlation velocity estimation.

Physics of the measurement
--------------------------
Two ROI boxes sit on the same capillary segment, `distance_px` pixels apart.
The same red-cell plug darkens one box and then the other, so the two intensity
traces are the same signal shifted in time. Cross-correlating a window of the
two traces recovers that shift (`lag`, in frames), and

    velocity = distance_px / lag  [pixels/frame]
             * fps                [pixels/second]
             * mm_per_pixel       [mm/second]

Sign convention
---------------
`signed_lag(a, b)` is positive when trace `b` lags behind trace `a`, i.e. when
the plug reaches box A first and the flow runs A -> B. `velocity_from_lag`
therefore returns velocity along A -> B, negative if the flow actually runs the
other way.

The Analyze tab names its boxes the opposite way round: rectangle 1 (the white
box, `isForward=True`) is the box the blood reaches *last*, which is why the
legacy report formula divides by `-lag`. `analyze_trace` keeps that convention
by default (`positive_flow='b_to_a'`) so batch reports carry the same sign as
the reports generated from the GUI.

The off-by-one
--------------
The original `Caper.CrossCorrelation` computed

    lag = int(np.ceil(len(window) / 2) - np.argmax(correlation))

`np.correlate(..., 'same')` puts zero displacement at index ``n // 2``, not at
``ceil(n / 2)``. The two agree for an even window and differ by one for an odd
one — and every window the report uses (201, 221, ... 301) is odd, so every
historical velocity was computed from a lag one frame too large. Since velocity
goes as 1/lag and the lags are single-digit, that is a large systematic bias
(a true lag of -5 frames was reported as -4: 25% too fast).

`signed_lag` uses the correct origin. Pass ``legacy=True`` to reproduce the old
numbers when comparing against previously generated reports.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd

from .intensity import IntensityTrace

#: Window lengths (in frames) used by the legacy report — `np.arange(201, 311, 20)`.
DEFAULT_WINDOWS: tuple[int, ...] = (201, 221, 241, 261, 281, 301)


def signed_lag(a: Sequence[float], b: Sequence[float], legacy: bool = False) -> float:
    """Frames by which trace `b` lags behind trace `a`.

    Returns NaN if either window contains a non-finite sample, since
    `np.correlate` would propagate it across the whole correlation.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size != b.size:
        raise ValueError(f'windows differ in length: {a.size} vs {b.size}')
    if a.size == 0:
        return float('nan')
    if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
        return float('nan')

    a = a - a.mean()
    b = b - b.mean()
    correlation = np.correlate(a, b, 'same')

    n = a.size
    origin = int(np.ceil(n / 2)) if legacy else n // 2
    return float(origin - int(np.argmax(correlation)))


def lag_and_correlation(
    a: Sequence[float], b: Sequence[float], legacy: bool = False
) -> tuple[float, float]:
    """Return ``(lag, r)``: the lag in frames and Pearson r at that alignment.

    `r` quantifies how well the two traces actually match once aligned, and is
    what the Analyze tab shows as "Correlation" — a low value means the lag is
    noise rather than a real plug transit.
    """
    lag = signed_lag(a, b, legacy=legacy)
    if not np.isfinite(lag):
        return float('nan'), float('nan')

    # Shifting `a` forward by `lag` lines it up with `b` (b lags a by `lag`).
    aligned = pd.Series(np.asarray(a, dtype=float)).shift(int(lag))
    other = pd.Series(np.asarray(b, dtype=float))
    paired = pd.DataFrame({'a': aligned, 'b': other}).dropna()
    if len(paired) < 2:
        return lag, float('nan')

    correlation = paired['a'].corr(paired['b'])
    return lag, float(correlation)


def velocity_from_lag(
    lag: float, distance_px: float, fps: float, mm_per_pixel: float
) -> float:
    """Velocity in mm/s along A -> B for a lag in frames.

    A zero lag means the plug reached both boxes within one frame — the
    measurement is saturated, not infinitely fast — so it yields NaN rather
    than an infinity that would poison every downstream mean.
    """
    if not np.isfinite(lag) or lag == 0:
        return float('nan')
    return float((distance_px / lag) * fps * mm_per_pixel)


def sliding_lag(
    a: Sequence[float],
    b: Sequence[float],
    window: int,
    step: int = 1,
    legacy: bool = False,
) -> pd.DataFrame:
    """Estimate the lag in a sliding window over the whole trace.

    Each row is indexed by the *centre* frame of its window, so a velocity is
    attributed to the moment it describes rather than to the end of the window.

    Returns a frame with columns ``lag`` and ``correlation``.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if window < 2:
        raise ValueError(f'window must be at least 2 frames, got {window}')
    if step < 1:
        raise ValueError(f'step must be at least 1, got {step}')

    centres: list[int] = []
    lags: list[float] = []
    correlations: list[float] = []

    for end in range(window, a.size + 1, step):
        start = end - window
        lag, correlation = lag_and_correlation(a[start:end], b[start:end], legacy=legacy)
        centres.append(start + window // 2)
        lags.append(lag)
        correlations.append(correlation)

    return pd.DataFrame(
        {'lag': lags, 'correlation': correlations},
        index=pd.Index(centres, name='frame'),
    )


def analyze_trace(
    trace: IntensityTrace,
    mm_per_pixel: float,
    windows: Iterable[int] = DEFAULT_WINDOWS,
    step: int = 1,
    legacy_lag: bool = False,
    positive_flow: str = 'b_to_a',
    smooth_frames: Optional[int] = 30,
) -> pd.DataFrame:
    """Run the full estimate over one intensity trace.

    Produces one column trio per window (``lag_<w>``, ``correlation_<w>``,
    ``velocity_<w>``) plus the across-window means (``lag``, ``correlation``,
    ``velocity``) that the report plots, indexed by time in seconds.

    `positive_flow` selects which direction counts as positive velocity;
    ``'b_to_a'`` (the default) matches the GUI reports, where rectangle 1 is the
    downstream box.
    """
    if positive_flow not in ('a_to_b', 'b_to_a'):
        raise ValueError(f"positive_flow must be 'a_to_b' or 'b_to_a', got {positive_flow!r}")
    sign = 1.0 if positive_flow == 'a_to_b' else -1.0

    windows = [int(w) for w in windows]
    if not windows:
        raise ValueError('at least one window length is required')

    per_window = {}
    for window in windows:
        if window > trace.n_frames:
            continue
        estimates = sliding_lag(trace.a, trace.b, window, step=step, legacy=legacy_lag)
        velocity = estimates['lag'].map(
            lambda lag: velocity_from_lag(lag, trace.distance_px, trace.fps, mm_per_pixel)
        )
        per_window[f'lag_{window}'] = estimates['lag']
        per_window[f'correlation_{window}'] = estimates['correlation']
        per_window[f'velocity_{window}'] = velocity * sign

    if not per_window:
        raise ValueError(
            f'every window {windows} is longer than the {trace.n_frames}-frame trace'
        )

    report = pd.DataFrame(per_window).sort_index()
    report['lag'] = report.filter(like='lag_').mean(axis=1)
    report['correlation'] = report.filter(like='correlation_').mean(axis=1)
    report['velocity'] = report.filter(like='velocity_').mean(axis=1)

    if smooth_frames:
        report['velocity_smoothed'] = (
            report['velocity'].rolling(int(smooth_frames), min_periods=1).mean()
        )

    report.insert(0, 'time_s', report.index / trace.fps if trace.fps else np.nan)
    report.index.name = 'frame'
    return report
