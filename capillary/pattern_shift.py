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

Slow range (since 2026-10-14; asked for with ``min_speed=SLOW_MIN_SPEED``).
Below 1 px/frame the pattern moves less than 2 px over frame distances 1-8,
too little to compare, so slower flow is compared over more frames:

- To find it, a speed v is scored as 1 px/frame is, on a time axis stretched
  by 1/v: term j = 1..`MAX_LAG` compares rows j / v frames apart (between
  the two nearest frame distances) where the pattern has moved j px
  (`_stretched_scores`). Every slow speed is scored from the same number of
  terms at the same shifts, so the score stays in noise units. It is the
  signal-to-noise ratio reported. Summing all frame distances instead
  scored up to 12.5 on synthetic clips without flow: below 1 px/frame
  neighbouring frame distances are read at nearly the same shift and share
  their noise.
- The speed found is then refined with the frame distances held fixed: the
  whole frames nearest to j / v, chosen anew from each refined speed until
  they stay the same, each read at frame distance x speed as from 1 px/frame
  up. Frame distances that change with the speed tilt the estimate, because
  the longer ones correlate less (fewer row pairs per block, and real blood
  rearranges). On the recordings many estimates stopped at exactly
  1 px/frame, where the two ranges meet, until the refinement covered that
  point. Rows compared more than `MAX_LAG` frames apart are taken about
  their own mean (`CENTRED`).
- On synthetic recordings (60-s clips of the simulated loop's arterial limb,
  analysis/pattern_shift_slow_flow/), every clip from 0.15 to 1 px/frame was
  resolved within 5% of the truth (median 1%). At 0.1 px/frame, the edge,
  4 of 12 were. None of 90 clips without flow was resolved (highest score
  7.2, under strong disturbances). From 1 px/frame up the results are the
  same as without the slow range.
- But a single line cannot tell slow flow from the picture moving along it.
  A steady drift is read as flow. With the cells standing still, back-and-
  forth movements of 10-20 px over a few seconds, faster one way than the
  other, were read as flow in 2-4 of 10 synthetic clips; movements of 2 px
  were not. The recordings show both. At rest the four limbs of FP03_Wföre's
  loops E and F move the same way. In the occlusion, when the blood should
  stand still, 24 of 97 limbs gave a slow speed, some of them from such
  movements (DEVLOG 2026-10-14). From 1 px/frame up these movements stayed
  below the threshold. So the slow range is not the default: its results
  need a check that the picture held still, such as the loop's other limb
  running the opposite way.

In the app (since 2026-10-11) every centre-line data set keeps the pattern
shift of its whole range and of each half (`summarize`). A line can be marked
as a capillary loop's arterial limb, drawn from its base to the apex; the
direction of the pooled flow then tells which limb it is
(`limb_from_direction`): blood flows up the arterial limb to the apex and
down the venous limb.

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
#: Frame distances compared at 1 px/frame and faster: row t with rows t + 1 .. t + MAX_LAG. Slower flow
#: is compared over the frames the pattern takes to move 1 .. MAX_LAG px (`_speed_scores`).
MAX_LAG = 8
#: Slowest speed reported (px/frame), unless asked for the slow range (`min_speed=SLOW_MIN_SPEED`). Below
#: 1 px/frame the method cannot tell flow from the picture moving along the line by 10 px or more over
#: some seconds (validate_wobble.py), which the recordings do (DEVLOG 2026-10-14).
MIN_SPEED = 1.0
#: Slowest speed of the slow range (px/frame): 0.004 mm/s at 30 fps and 1.33 um/px. On synthetic recordings the
#: estimate was within 5% of the truth from 0.15 to 1 px/frame (median 1%); at 0.1 most stopped at the edge.
SLOW_MIN_SPEED = 0.1
#: Below 1 px/frame, the rows compared beyond MAX_LAG frames apart are taken about their own mean: the
#: block's mean, which the rows are first taken about, pulled the slowest estimates high (at 0.1 px/frame by 7-12%).
CENTRED = True
#: A speed found below 1 px/frame is refined up to this speed (px/frame), in at most REFINE_ROUNDS rounds.
REFINE_TOP = 1.5
REFINE_ROUNDS = 5
#: A frame distance counts fully for a speed once the pattern moves at least this far over it (px),
#: fading in from 1 px less. Close to zero shift, the backward correlation subtracted holds part of the
#: peak's own tail; on synthetic recordings this lowered the error near 1 px/frame slightly. 3 px would
#: drop the comparison of consecutive frames at 2 px/frame, the strongest on real recordings, where
#: the blood rearranges within a few frames (FP01_Qföre's limb at rest: signal-to-noise 13.7 -> 9.7).
MIN_SHIFT_PX = 2.0
#: Near half the line a frame distance fades out over this share of the largest shift.
FADE_SHARE = 0.1
#: Speeds are searched in steps of this many px/frame, below 1 px/frame in steps of SLOW_SPEED_STEP.
SPEED_STEP = 0.01
SLOW_SPEED_STEP = 0.002
#: Estimates with a lower signal-to-noise ratio count as unresolved. With band-passed rows, 90 synthetic
#: recordings without flow reached at most 5.4 inside the searched range (7.3 at its slow edge, which is
#: never reported), and six lines through tissue in the recordings at most 3.6 in any phase (DEVLOG
#: 2026-10-11). With differenced rows the figures were 4.4 and 5.6.
MIN_SNR = 8.0
#: Shortest line the method accepts (px).
MIN_LENGTH_PX = 24
#: Each half of a measured range is scored on its own when it holds at least this many blocks (9 s).
MIN_HALF_BLOCKS = 3
#: The role of a line drawn along a capillary loop's arterial limb, from its base to the apex.
ARTERIAL_LIMB = 'arterial limb'


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


def _block_sums(block: np.ndarray, lags: np.ndarray, max_shift: int, bandpass_px=BANDPASS_PX,
                centre_beyond=None) -> np.ndarray:
    """For each frame distance and shift -max..max: the cross product and the two energies, shape (lags, 3, shifts).

    The correlation of row t with row t + k shifted by d is
    ``sum_x a_t(x) a_{t+k}(x + d)`` over the positions where both exist.
    At frame distances k beyond `centre_beyond` (None: none), the rows
    compared (rows 0..T-k-1 and k..T-1 of the block) are each taken about
    their own mean first.
    """
    b = _prepared(block, bandpass_px)
    frames, n = b.shape
    size = 2 * n
    shifts = np.arange(-max_shift, max_shift + 1)
    out = np.zeros((len(lags), 3, shifts.size))
    spectra = np.fft.rfft(b, size, axis=1)
    # sums over the rows before row t: per position, and per frequency
    energy = np.vstack([np.zeros(n), np.cumsum(b * b, axis=0)])
    level = np.vstack([np.zeros(n), np.cumsum(b, axis=0)])
    spectrum = np.vstack([np.zeros(spectra.shape[1], complex), np.cumsum(spectra, axis=0)])
    for i, k in enumerate(lags):
        if k >= frames:
            continue
        pairs = frames - k
        product = (np.conj(spectra[:-k]) * spectra[k:]).sum(axis=0)
        early_energy, late_energy = energy[pairs], energy[frames] - energy[k]
        if centre_beyond is not None and k > centre_beyond:
            product = product - np.conj(spectrum[pairs]) * (spectrum[frames] - spectrum[k]) / pairs
            early_energy = early_energy - level[pairs] ** 2 / pairs
            late_energy = late_energy - (level[frames] - level[k]) ** 2 / pairs
        out[i, 0] = np.fft.irfft(product, size)[shifts % size]
        early = np.concatenate([[0.0], np.cumsum(early_energy)])                  # energy of x < m
        late = np.concatenate([[0.0], np.cumsum(late_energy)])
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


def _contrasts(sums: np.ndarray, max_shift: int) -> np.ndarray:
    """Each frame distance's direction contrast at shifts 0..max_shift, in units of its own noise (NaN if none)."""
    with np.errstate(invalid='ignore', divide='ignore'):
        corr = sums[:, 0] / np.sqrt(sums[:, 1] * sums[:, 2])
    corr = np.nan_to_num(corr)
    centre = max_shift
    contrast = corr[:, centre:] - corr[:, centre::-1]                  # (lags, 0..max_shift)
    out = np.full(contrast.shape, np.nan)
    for i, row in enumerate(contrast):
        noise = 1.4826 * np.median(np.abs(row[1:] - np.median(row[1:])))
        if np.isfinite(noise) and noise > 0:
            out[i] = row / noise
    return out


def _fixed_lag_scores(z: np.ndarray, chosen, speeds: np.ndarray, max_shift: int) -> np.ndarray:
    """Score of each speed from the frame distances `chosen`, each read where the pattern has moved lag x speed px.

    `z` holds the contrasts of frame distances 1, 2, .. (`_contrasts`).
    """
    d = np.arange(max_shift + 1)
    speed, sign = np.abs(speeds), np.sign(speeds)
    total = np.zeros(speeds.size)
    squares = np.zeros(speeds.size)
    for k in chosen:
        if not np.all(np.isfinite(z[k - 1])):
            continue
        weight = _lag_weight(k * speed, max_shift)
        used = weight > 0
        total[used] += weight[used] * sign[used] * CubicSpline(d, z[k - 1])(k * speed[used])
        squares[used] += weight[used] ** 2
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(squares > 0, total / np.sqrt(squares), np.nan)


def _stretched_scores(z: np.ndarray, speeds: np.ndarray, max_shift: int, max_lag: int) -> np.ndarray:
    """Score of each speed below 1 px/frame, read as flow of 1 px/frame on a stretched time axis.

    Term j = 1..`max_lag` compares rows j / speed frames apart (between the two
    nearest frame distances, linearly) where the pattern has moved j px: the
    same number of terms at the same shifts as frame distances 1..`max_lag` at
    1 px/frame. This finds the speed roughly; `_slow_lags` then refines it.
    """
    speed, sign = np.abs(speeds), np.sign(speeds)
    longest = z.shape[0]
    total = np.zeros(speeds.size)
    squares = np.zeros(speeds.size)
    for j in range(1, min(max_lag, max_shift) + 1):
        weight = float(_lag_weight(np.array(float(j)), max_shift))
        if weight <= 0:
            continue
        stretched = j / speed                                          # frames apart, between two frame distances
        low = np.floor(stretched).astype(int)
        share = stretched - low
        inside = (low >= 1) & (low + (share > 0) <= longest)
        value = ((1 - share) * z[np.clip(low, 1, longest) - 1, j]
                 + share * z[np.clip(low + 1, 1, longest) - 1, j])
        used = inside & np.isfinite(value)
        total[used] += weight * sign[used] * value[used]
        squares[used] += weight ** 2
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(squares > 0, total / np.sqrt(squares), np.nan)


def _speed_scores(sums: np.ndarray, lags: np.ndarray, max_shift: int, speeds: np.ndarray,
                  max_lag: int = MAX_LAG) -> np.ndarray:
    """Score of every speed (signed), in noise units, from pooled sums (lags, 3, shifts).

    From 1 px/frame up, frame distances 1..`max_lag` (`_fixed_lag_scores`);
    slower flow on a stretched time axis (`_stretched_scores`). `lags` must be
    1, 2, .. without gaps.
    """
    z = _contrasts(sums, max_shift)
    scores = np.full(speeds.size, np.nan)
    fast = np.abs(speeds) >= 1.0
    scores[fast] = _fixed_lag_scores(z, range(1, max_lag + 1), speeds[fast], max_shift)
    if not fast.all():
        scores[~fast] = _stretched_scores(z, speeds[~fast], max_shift, max_lag)
    return scores


def _slow_lags(speed: float, max_lag: int, longest: int) -> np.ndarray:
    """Fixed frame distances to refine a speed below 1 px/frame: the nearest to j / speed, j = 1..`max_lag`."""
    return np.unique(np.clip(np.round(np.arange(1, max_lag + 1) / speed).astype(int), 1, longest))


def _speed_grid(min_speed: float, max_shift: int) -> np.ndarray:
    """The speeds searched, both ways: `SLOW_SPEED_STEP` apart below 1 px/frame, `SPEED_STEP` from there on."""
    slow = np.arange(min_speed, 1.0 - SLOW_SPEED_STEP / 2, SLOW_SPEED_STEP) if min_speed < 1.0 else np.empty(0)
    upper = np.concatenate([slow, np.arange(max(min_speed, 1.0), max_shift + SPEED_STEP / 2, SPEED_STEP)])
    return np.concatenate([-upper[::-1], upper])


def _best(scores: np.ndarray, speeds: np.ndarray) -> tuple:
    """The best speed, refined, its score, and whether it lies inside the searched range rather than at its edge."""
    if np.all(np.isnan(scores)):
        return float('nan'), float('nan'), False
    i = int(np.nanargmax(scores))
    speed = float(speeds[i])
    # refined between evenly spaced neighbours (not across zero, where the search jumps from one way to the other)
    neighbours = 0 < i < speeds.size - 1 and np.isclose(speeds[i] - speeds[i - 1], speeds[i + 1] - speeds[i])
    if neighbours and np.isfinite(scores[i - 1]) and np.isfinite(scores[i + 1]):
        left, centre, right = scores[i - 1], scores[i], scores[i + 1]
        curvature = left - 2 * centre + right
        if curvature < 0:
            speed += float(0.5 * (left - right) / curvature) * (speeds[i + 1] - speeds[i])
    edge = i in (0, speeds.size - 1) or np.isclose(abs(speeds[i]), np.abs(speeds).min())
    return speed, float(scores[i]), not edge


def pattern_shift(diagram: np.ndarray, block_frames: int = BLOCK_FRAMES, max_lag: int = MAX_LAG,
                  bandpass_px=BANDPASS_PX, min_speed: float = MIN_SPEED,
                  centred: bool = CENTRED) -> ShiftEstimate:
    """The speed (px/frame along the line) of the pattern in `diagram`, pooled over all its blocks.

    `diagram` has frames down and positions across, as
    `capillary.spacetime.space_time_diagram` returns it; frames that do not
    fill a whole block at the end are left out. NaN when the diagram is too
    small or contains missing samples. `bandpass_px` None compares
    differenced rows, as before 2026-10-11. `min_speed` is the slowest speed
    searched: `MIN_SPEED` by default, `SLOW_MIN_SPEED` for the slow range
    (see the module's docstring), where `centred` takes the rows compared
    more than `max_lag` frames apart about their own mean.
    """
    diagram = np.asarray(diagram, dtype=float)
    if diagram.ndim != 2 or diagram.shape[1] < MIN_LENGTH_PX or not np.all(np.isfinite(diagram)):
        return _NO_ESTIMATE
    n_blocks = diagram.shape[0] // block_frames
    if n_blocks < 1:
        return _NO_ESTIMATE
    max_shift = (diagram.shape[1] - 1) // 2
    # the slowest flow is compared up to max_lag / speed frames apart, inside a block
    min_speed = max(min_speed, max_lag / (block_frames - 2))
    longest = max_lag if min_speed >= 1.0 else int(np.ceil(max_lag / min_speed)) + 1
    lags = np.arange(1, min(longest, block_frames - 1) + 1)
    per_block = np.stack([_block_sums(diagram[j * block_frames:(j + 1) * block_frames], lags, max_shift,
                                      bandpass_px, max_lag if centred else None) for j in range(n_blocks)])
    speeds = _speed_grid(min_speed, max_shift)
    pooled = per_block.sum(axis=0)
    speed, snr, in_range = _best(_speed_scores(pooled, lags, max_shift, speeds, max_lag), speeds)
    refine = in_range and min_speed < 1.0 and abs(speed) <= 1.0
    if refine:
        # Found below 1 px/frame, or where that range meets the faster one: refined with the frame distances held
        # fixed (`_slow_lags`), chosen anew from each refined speed until they stay the same. The score stays the one
        # that found the flow: searching again with other frame distances would fit the noise a second time.
        window = np.sign(speed) * np.arange(min_speed, REFINE_TOP + SLOW_SPEED_STEP / 2, SLOW_SPEED_STEP)
        z = _contrasts(pooled, max_shift)
        chosen, refined, inside = None, speed, in_range
        for _ in range(REFINE_ROUNDS):
            again = _slow_lags(abs(refined), max_lag, lags.size)
            if chosen is not None and np.array_equal(again, chosen):
                break
            chosen = again
            refined, _, inside = _best(_fixed_lag_scores(z, chosen, window, max_shift), window)
            if not np.isfinite(refined):
                break
        if np.isfinite(refined):
            speed, in_range = refined, inside
        else:
            refine = False

    def best(sums):
        if refine:
            return _best(_fixed_lag_scores(_contrasts(sums, max_shift), chosen, window, max_shift), window)
        return _best(_speed_scores(sums, lags, max_shift, speeds, max_lag), speeds)

    ci = (float('nan'), float('nan'))
    if n_blocks >= 3 and np.isfinite(speed):
        others = []
        for j in range(n_blocks):
            s, _, _ = best(pooled - per_block[j])
            others.append(s)
        others = np.asarray(others)
        if np.all(np.isfinite(others)):
            se = np.sqrt((n_blocks - 1) / n_blocks * np.sum((others - others.mean()) ** 2))
            ci = (speed - 1.96 * se, speed + 1.96 * se)
    return ShiftEstimate(speed, snr, ci, n_blocks, in_range)


def shift_time_course(diagram: np.ndarray, fps: float, mm_per_pixel: float, window_frames: int,
                      step_frames: int, spacing_px: float = 1.0, first_frame: int = 0,
                      min_snr: float = MIN_SNR, bandpass_px=BANDPASS_PX,
                      min_speed: float = MIN_SPEED) -> pd.DataFrame:
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
        estimate = pattern_shift(diagram[start:start + window_frames], bandpass_px=bandpass_px, min_speed=min_speed)
        resolved = estimate.is_resolved(min_snr)
        centre = first_frame + start + window_frames // 2
        rows.append({'frame': centre, 'time_s': centre / fps,
                     'speed_px_per_frame': estimate.speed_px_per_frame,
                     'velocity_mm_s': estimate.speed_px_per_frame * to_mm_s if resolved else float('nan'),
                     'ci95_low_mm_s': estimate.ci95[0] * to_mm_s, 'ci95_high_mm_s': estimate.ci95[1] * to_mm_s,
                     'snr': estimate.snr, 'resolved': resolved})
    return pd.DataFrame(rows).set_index('frame')


def summarize(diagram: np.ndarray, fps: float, mm_per_pixel: float, spacing_px: float = 1.0,
              min_speed: float = MIN_SPEED) -> dict:
    """The pattern shift of a measured range, pooled over all of it and over each half: what a data set keeps.

    `min_speed` is the slowest speed searched (px/frame); `SLOW_MIN_SPEED`
    adds the slow range. Keys, all starting with ``pattern_shift_``:

    - ``velocity_mm_s`` (positive along the line; NaN unless resolved) and
      ``speed_px_per_frame`` (the best speed, also when unresolved);
    - ``snr``, ``resolved``, ``blocks`` (3-s blocks pooled);
    - ``ci95_low_mm_s`` and ``ci95_high_mm_s``, the jackknife interval (NaN
      unless resolved), which covers the statistical scatter only;
    - ``first_half_mm_s``, ``first_half_snr``, ``second_half_mm_s`` and
      ``second_half_snr``: the two halves of the range in time, each pooled on
      its own (NaN velocity unless resolved; NaN when a half holds fewer than
      `MIN_HALF_BLOCKS` blocks). They show whether the flow stayed the same.
    """
    diagram = np.asarray(diagram, dtype=float)
    to_mm_s = spacing_px * fps * mm_per_pixel
    whole = pattern_shift(diagram, min_speed=min_speed)
    out = {'pattern_shift_velocity_mm_s': whole.speed_px_per_frame * to_mm_s if whole.resolved else float('nan'),
           'pattern_shift_speed_px_per_frame': whole.speed_px_per_frame,
           'pattern_shift_snr': whole.snr,
           'pattern_shift_resolved': whole.resolved,
           'pattern_shift_blocks': whole.blocks,
           'pattern_shift_ci95_low_mm_s': whole.ci95[0] * to_mm_s if whole.resolved else float('nan'),
           'pattern_shift_ci95_high_mm_s': whole.ci95[1] * to_mm_s if whole.resolved else float('nan')}
    middle = diagram.shape[0] // 2 if diagram.ndim == 2 else 0
    for label, half in (('first_half', diagram[:middle]), ('second_half', diagram[middle:])):
        estimate = (pattern_shift(half, min_speed=min_speed) if middle // BLOCK_FRAMES >= MIN_HALF_BLOCKS
                    else _NO_ESTIMATE)
        out[f'pattern_shift_{label}_mm_s'] = (estimate.speed_px_per_frame * to_mm_s if estimate.resolved
                                              else float('nan'))
        out[f'pattern_shift_{label}_snr'] = estimate.snr
    return out


def limb_from_direction(velocity: float) -> str:
    """Which limb a line drawn from a capillary loop's base to its apex follows, by the direction of its flow.

    Blood flows up the arterial limb to the apex and down the venous limb, so
    flow along the line (positive velocity) shows the arterial limb, and flow
    against it the venous limb. 'unknown' when the flow is not resolved (NaN).
    """
    if velocity is None or not np.isfinite(velocity) or velocity == 0:
        return 'unknown'
    return 'arterial' if velocity > 0 else 'venous'
