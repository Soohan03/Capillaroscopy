"""Red-cell velocity from how far the pattern along a centre line moves between frames.

The same space-time diagram as `capillary.spacetime` (one row per frame, the
brightness along the line), read another way: instead of the slope of the
streaks within one block, the shift that best carries a row onto a later one.

    row t, shifted by d px along the line  ~  row t + k      ->  speed = d / k  [px per frame]

How it works
------------
1. The diagram is cut into blocks of `BLOCK_FRAMES` (3 s). In each, the still
   structure (each position's mean) and the change of the whole line at the
   same moment (each row's mean) are removed, and each row is band-passed
   along the line (`BANDPASS_PX`, see below).
2. For each frame distance k = 1..`MAX_LAG`, the correlation of row t with row
   t + k is computed at every shift d up to half the line, pooled over all rows
   of all blocks (an ensemble correlation: numerators and energies are summed
   before dividing).
3. Direction contrast: the correlation at -d is subtracted from that at +d. A
   pattern moving one way along the vessel correlates on one side only, while
   noise, still structure, the same-moment change and jitter are symmetric and
   cancel, as in `capillary.spacetime`.
4. Each frame distance's contrast is put into units of its own noise (its
   spread over all shifts). A speed's score is the weighted sum of the frame
   distances' contrasts at shift = speed x k, divided by the square root of
   the sum of the squared weights, so it stays in noise units. A frame
   distance counts fully between `MIN_SHIFT_PX` and half the line and fades
   in and out smoothly at both ends. A frame distance switched on or off at a
   fixed speed made the score jump there, and the estimate snapped to it,
   with an interval of zero width (seen on FP03_Qefter_försök2 at exactly
   2 px/frame). The best speed, to a hundredth of a pixel per frame, is the
   estimate, and its score the signal-to-noise ratio.
5. The uncertainty comes from leaving out one block at a time (jackknife): a
   95% interval of the speed. It covers the statistical scatter only. A
   systematic error of about 1%, such as a drawn line slightly off the
   vessel's centre, is not in it.

Pooling is what makes faint patterns measurable. On FP01_Qföre at rest (see
the DEVLOG entry of 2026-10-08), a single 3-s block of the centre-line method
reached a signal-to-noise ratio of about 4. Pooled over the minute of rest,
the shift was about 14 times its noise at k = 1, and lay at 2, 4 and 6 px for
k = 1, 2 and 3. The loop's other limb showed the opposite direction, and
tissue beside the limb showed nothing. Band-passed rows (since 2026-10-11)
raised that limb's score from 11 to 19 on the line of the feasibility check,
and resolved 5 of that check's 29 limbs at rest where differenced rows
resolved 3.

Range. Speeds are searched from `MIN_SPEED` up to half the line's length per
frame. On synthetic recordings (the arterial limb of a simulated loop, a
120-px line, 30-s clips, the shutter open for the whole frame interval;
DEVLOG 2026-10-11) the estimate was within about 1% of the truth from 1.5 to
8 px/frame (0.06-0.32 mm/s at 30 fps and 1.33 um/px), also with a third of
the contrast. At 12 px/frame (0.48 mm/s) it read about 5% low, and faster
flow stayed below the threshold: each cell is smeared over its own movement
while the shutter is open. With the shutter open for half the frame, 16
px/frame was resolved. A longer line reaches much further: on a 300-px line
round the simulated loop (60 s), 12 to 40 px/frame (0.48-1.6 mm/s) were all
measured within about 1%; in a real loop the speed differs between the limbs.
The centre-line method stops at about 5 px/frame on a 120-px line and is the
better method for flow slower than `MIN_SPEED`.

Nothing here imports a GUI toolkit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter1d

#: Frames per block (3 s at 30 fps); still structure is removed per block.
BLOCK_FRAMES = 90
#: Band-pass along the line before rows are compared: a difference of Gaussians with these sigmas (px).
#: It passes patterns of about 4-30 px, most strongly near 10 px: cells, plasma gaps and groups of cells.
#: It drops pixel-to-pixel noise and the line's coarse shading. Until 2026-10-11 the rows were
#: differenced instead, which weights the finest scale most; ``bandpass_px=None`` still does that. On
#: the recordings, band-passed rows resolved more limbs and stayed lower on lines through tissue; of five
#: bands this one lost none of the limbs resolved before and did best on synthetic recordings (DEVLOG
#: 2026-10-11, analysis/pattern_shift_bandpass/).
BANDPASS_PX = (1.0, 4.0)
#: Frame distances compared: row t with rows t + 1 .. t + MAX_LAG.
MAX_LAG = 8
#: Slowest speed this method reports (px/frame). At 0.5 px/frame it read 4-8% high on synthetic
#: recordings; the centre-line method measures slower flow exactly.
MIN_SPEED = 1.0
#: A frame distance counts fully for a speed once the pattern moves at least this far over it (px),
#: fading in from 1 px less. Close to zero shift, the backward correlation subtracted holds part of the
#: peak's own tail; on synthetic recordings this lowered the error near 1 px/frame slightly. 3 px would
#: drop the comparison of consecutive frames at 2 px/frame, the strongest on real recordings, where
#: the blood rearranges within a few frames (FP01_Qföre's limb at rest: signal-to-noise 13.7 -> 9.7).
MIN_SHIFT_PX = 2.0
#: Near half the line a frame distance fades out over this share of the largest shift.
FADE_SHARE = 0.1
#: Speeds are searched in steps of this many px/frame.
SPEED_STEP = 0.01
#: Estimates with a lower signal-to-noise ratio count as unresolved. With band-passed rows, 90 synthetic
#: recordings without flow reached at most 5.4 inside the searched range (7.3 at its slow edge, which is
#: never reported), and six lines through tissue in the recordings at most 3.6 in any phase (DEVLOG
#: 2026-10-11). With differenced rows the figures were 4.4 and 5.6.
MIN_SNR = 8.0
#: Shortest line the method accepts (px).
MIN_LENGTH_PX = 24


@dataclass(frozen=True)
class ShiftEstimate:
    """The speed of the pattern along the line over the frames pooled.

    `speed_px_per_frame` is positive along the line (first point to last);
    `snr` is the best speed's score in units of the noise; `ci95` the jackknife
    95% interval of the speed; `blocks` the number of 3-s blocks pooled;
    `in_range` whether the speed lies inside the searched range rather than at
    its edge.
    """

    speed_px_per_frame: float
    snr: float
    ci95: tuple
    blocks: int
    in_range: bool

    def is_resolved(self, min_snr: float = MIN_SNR) -> bool:
        return bool(self.in_range and np.isfinite(self.snr) and self.snr >= min_snr)

    @property
    def resolved(self) -> bool:
        return self.is_resolved()

    def velocity_mm_s(self, fps: float, mm_per_pixel: float, spacing_px: float = 1.0) -> float:
        return self.speed_px_per_frame * spacing_px * fps * mm_per_pixel


_NO_ESTIMATE = ShiftEstimate(float('nan'), float('nan'), (float('nan'), float('nan')), 0, False)


def _prepared(block: np.ndarray, bandpass_px=BANDPASS_PX) -> np.ndarray:
    """A block without its still structure and same-moment change, band-passed along the line.

    With `bandpass_px` None the rows are differenced instead (the method before 2026-10-11).
    """
    b = np.asarray(block, dtype=float)
    b = b - b.mean(axis=0, keepdims=True)
    b = b - b.mean(axis=1, keepdims=True)
    if bandpass_px is None:
        return np.diff(b, axis=1)
    fine, coarse = bandpass_px
    return (gaussian_filter1d(b, fine, axis=1, mode='reflect')
            - gaussian_filter1d(b, coarse, axis=1, mode='reflect'))


def _block_sums(block: np.ndarray, lags: np.ndarray, max_shift: int, bandpass_px=BANDPASS_PX) -> np.ndarray:
    """For each frame distance and shift -max..max: the cross product and the two energies, shape (lags, 3, shifts).

    The correlation of row t with row t + k shifted by d is
    ``sum_x a_t(x) a_{t+k}(x + d)`` over the positions where both exist.
    """
    b = _prepared(block, bandpass_px)
    frames, n = b.shape
    size = 2 * n
    shifts = np.arange(-max_shift, max_shift + 1)
    out = np.zeros((len(lags), 3, shifts.size))
    spectra = np.fft.rfft(b, size, axis=1)
    squares = b * b
    for i, k in enumerate(lags):
        if k >= frames:
            continue
        cross = np.fft.irfft(np.conj(spectra[:-k]) * spectra[k:], size, axis=1).sum(axis=0)
        out[i, 0] = cross[shifts % size]
        early = np.concatenate([[0.0], np.cumsum(squares[:-k].sum(axis=0))])     # energy of x < m
        late = np.concatenate([[0.0], np.cumsum(squares[k:].sum(axis=0))])
        forward = shifts >= 0
        d = np.abs(shifts)
        # d >= 0: early rows over x in [0, n - d), late rows over x in [d, n); d < 0 the other way round
        out[i, 1] = np.where(forward, early[n - d], early[n] - early[d])
        out[i, 2] = np.where(forward, late[n] - late[d], late[n - d])
    return out


def _lag_weight(reach: np.ndarray, max_shift: int) -> np.ndarray:
    """How much a frame distance counts at a shift of `reach` px: fading in up to `MIN_SHIFT_PX`, out near `max_shift`."""
    rise = np.clip(reach - (MIN_SHIFT_PX - 1.0), 0.0, 1.0)
    fade = max(2.0, FADE_SHARE * max_shift)
    fall = np.clip((max_shift - reach) / fade, 0.0, 1.0)
    return rise * fall


def _speed_scores(sums: np.ndarray, lags: np.ndarray, max_shift: int, speeds: np.ndarray) -> np.ndarray:
    """Score of every speed (signed), in noise units, from pooled sums (lags, 3, shifts)."""
    with np.errstate(invalid='ignore', divide='ignore'):
        corr = sums[:, 0] / np.sqrt(sums[:, 1] * sums[:, 2])
    corr = np.nan_to_num(corr)
    centre = max_shift
    contrast = corr[:, centre:] - corr[:, centre::-1]                  # (lags, 0..max_shift)
    d = np.arange(max_shift + 1)
    total = np.zeros(speeds.size)
    weights = np.zeros(speeds.size)
    for i, k in enumerate(lags):
        c = contrast[i, 1:]
        noise = 1.4826 * np.median(np.abs(c - np.median(c)))
        if not np.isfinite(noise) or noise <= 0:
            continue
        spline = CubicSpline(d, contrast[i] / noise)
        reach = k * np.abs(speeds)
        weight = _lag_weight(reach, max_shift)
        used = weight > 0
        total[used] += weight[used] * np.sign(speeds[used]) * spline(reach[used])
        weights[used] += weight[used] ** 2
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(weights > 0, total / np.sqrt(weights), np.nan)


def _best(scores: np.ndarray, speeds: np.ndarray) -> tuple:
    if np.all(np.isnan(scores)):
        return float('nan'), float('nan'), False
    i = int(np.nanargmax(scores))
    speed = float(speeds[i])
    neighbours = 0 < i < speeds.size - 1 and np.allclose(np.diff(speeds[i - 1:i + 2]), SPEED_STEP)
    if neighbours and np.isfinite(scores[i - 1]) and np.isfinite(scores[i + 1]):
        left, centre, right = scores[i - 1], scores[i], scores[i + 1]
        curvature = left - 2 * centre + right
        if curvature < 0:
            speed += float(0.5 * (left - right) / curvature) * (speeds[i + 1] - speeds[i])
    edge = i in (0, speeds.size - 1) or abs(abs(speeds[i]) - MIN_SPEED) < SPEED_STEP / 2
    return speed, float(scores[i]), not edge


def pattern_shift(diagram: np.ndarray, block_frames: int = BLOCK_FRAMES, max_lag: int = MAX_LAG,
                  bandpass_px=BANDPASS_PX) -> ShiftEstimate:
    """The speed (px/frame along the line) of the pattern in `diagram`, pooled over all its blocks.

    `diagram` has frames down and positions across, as
    `capillary.spacetime.space_time_diagram` returns it; frames that do not
    fill a whole block at the end are left out. NaN when the diagram is too
    small or contains missing samples. `bandpass_px` None compares
    differenced rows, as before 2026-10-11.
    """
    diagram = np.asarray(diagram, dtype=float)
    if diagram.ndim != 2 or diagram.shape[1] < MIN_LENGTH_PX or not np.all(np.isfinite(diagram)):
        return _NO_ESTIMATE
    n_blocks = diagram.shape[0] // block_frames
    if n_blocks < 1:
        return _NO_ESTIMATE
    max_shift = (diagram.shape[1] - 1) // 2
    lags = np.arange(1, min(max_lag, block_frames - 1) + 1)
    per_block = np.stack([_block_sums(diagram[j * block_frames:(j + 1) * block_frames], lags, max_shift,
                                      bandpass_px) for j in range(n_blocks)])
    upper = np.arange(MIN_SPEED, max_shift + SPEED_STEP / 2, SPEED_STEP)
    speeds = np.concatenate([-upper[::-1], upper])
    pooled = per_block.sum(axis=0)
    speed, snr, in_range = _best(_speed_scores(pooled, lags, max_shift, speeds), speeds)
    ci = (float('nan'), float('nan'))
    if n_blocks >= 3 and np.isfinite(speed):
        others = []
        for j in range(n_blocks):
            s, _, _ = _best(_speed_scores(pooled - per_block[j], lags, max_shift, speeds), speeds)
            others.append(s)
        others = np.asarray(others)
        if np.all(np.isfinite(others)):
            se = np.sqrt((n_blocks - 1) / n_blocks * np.sum((others - others.mean()) ** 2))
            ci = (speed - 1.96 * se, speed + 1.96 * se)
    return ShiftEstimate(speed, snr, ci, n_blocks, in_range)


def shift_time_course(diagram: np.ndarray, fps: float, mm_per_pixel: float, window_frames: int,
                      step_frames: int, spacing_px: float = 1.0, first_frame: int = 0,
                      min_snr: float = MIN_SNR, bandpass_px=BANDPASS_PX) -> pd.DataFrame:
    """`pattern_shift` in successive windows of `window_frames`, one row per window, indexed by its centre frame.

    Columns: ``time_s``, ``speed_px_per_frame``, ``velocity_mm_s`` (NaN when
    unresolved), ``ci95_low_mm_s``, ``ci95_high_mm_s``, ``snr``, ``resolved``.
    """
    diagram = np.asarray(diagram, dtype=float)
    if diagram.shape[0] < window_frames:
        raise ValueError(f'the diagram has {diagram.shape[0]} frames, fewer than one window of {window_frames}')
    to_mm_s = spacing_px * fps * mm_per_pixel
    rows = []
    for start in range(0, diagram.shape[0] - window_frames + 1, max(1, int(step_frames))):
        estimate = pattern_shift(diagram[start:start + window_frames], bandpass_px=bandpass_px)
        resolved = estimate.is_resolved(min_snr)
        centre = first_frame + start + window_frames // 2
        rows.append({'frame': centre, 'time_s': centre / fps,
                     'speed_px_per_frame': estimate.speed_px_per_frame,
                     'velocity_mm_s': estimate.speed_px_per_frame * to_mm_s if resolved else float('nan'),
                     'ci95_low_mm_s': estimate.ci95[0] * to_mm_s, 'ci95_high_mm_s': estimate.ci95[1] * to_mm_s,
                     'snr': estimate.snr, 'resolved': resolved})
    return pd.DataFrame(rows).set_index('frame')
