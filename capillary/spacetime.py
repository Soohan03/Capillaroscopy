"""Red-cell velocity along a capillary's centre line, from its space-time diagram.

The measurement
---------------
The user draws a line along the capillary, from the end the blood comes from
to the end it goes to. For every frame, the brightness is sampled along that
line (averaged over a few pixels across it), which gives one row of the
*space-time diagram*: position along the vessel across, time down. Red cells
and plasma gaps travelling along the vessel draw slanted streaks in it, and
the slope of the streaks is their speed:

    speed = distance along the line / time  [px per frame]
    velocity = speed * fps * mm_per_pixel   [mm/s]

The diagram uses every position along the line, where the two-box method uses
two, and the speed comes from a slope rather than from a whole number of
frames of delay, so it is not limited to distance / 1, distance / 2, ...

Why not two boxes
-----------------
In the recordings this tool was built for, about 70% of the brightness change
seen by a box on a capillary happens at the same moment along the whole vessel
(probably small movements of the vessel, or focus). Two boxes see that change
simultaneously, so their correlation peaks at a delay of zero, which the box
method reports as "too fast to resolve" even where the flow is slow (see the
2026-10-06 entry in DEVLOG.md).

How the slope is found
----------------------
A pattern moving along the line at `v` px/frame puts all of its power on the
line ``omega = -v * k`` of the diagram's two-dimensional power spectrum
(`k` in cycles per pixel, `omega` in cycles per frame). This is the Radon-
transform velocity method of Drew et al. (J Comput Neurosci 2010;29:5-11),
evaluated through the Fourier slice theorem. Two refinements:

1. **Direction contrast.** The score of a speed `v` is the power on its line
   minus the power on the mirror line ``omega = +v * k``. Noise, still
   structure and any change that is the same pattern at every moment (the
   same-moment change above, in any position-dependent strength) are a
   product of a shape along the line and a time course; their spectrum is
   symmetric, so they cancel in the difference. Flow is not symmetric.
2. **Whitening.** The diagram is differenced along the line first. Cell
   patterns have more power at coarse scales, and the spatial window leaks
   some of it into finer ones, which otherwise reads as a speed a few percent
   too slow.

Only the unaliased part of each line is used (``|omega| <= 0.45`` cycles per
frame): at 30 fps a pattern that moves more than half its own size between
frames cannot be followed. The fastest measurable speed therefore grows with
the length of the line (about 0.09 * length px/frame), the slowest falls with
the length of the time block (see `resolvable_speeds`).

Quality
-------
Each estimate comes with two numbers, and a block counts as resolved only if
both are high enough and the speed lies in the measurable range:

- the signal-to-noise ratio: the direction contrast of the chosen line
  divided by its spread under "no flow". That spread is estimated locally,
  from the power at nearby temporal frequencies of both signs: jitter and the
  same-moment change crowd the slow frequencies where slow flow is measured,
  and a global estimate let them pass as slow flow. The threshold is `MIN_SNR`.
- the coherence: the share of the block's energy (in the patterns used) that
  lies on the chosen line, 1 for a clean pattern moving at one speed. Flow
  faster than the line can measure can give a high signal-to-noise ratio at
  a wrong, slower speed; its coherence stays near that of noise (about 0.02).
  The threshold is `MIN_COHERENCE`.

Nothing here imports a GUI toolkit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

#: Sample this many pixels to either side of the line, every pixel (2 -> 5 samples across).
DEFAULT_HALF_WIDTH_PX = 2
#: Frames per estimate (3 s at 30 fps), and how far successive estimates move along.
DEFAULT_BLOCK_FRAMES = 90
DEFAULT_STEP_FRAMES = 15
#: Estimates with a lower signal-to-noise ratio or coherence count as unresolved (calibrated on the
#: benchmark and on lines through still tissue in the recordings; see the 2026-10-06 DEVLOG entry).
MIN_SNR = 8.0
MIN_COHERENCE = 0.03
#: Finest pattern used, in cycles per pixel (patterns of at least ~3.3 px).
K_MAX = 0.3
#: The unaliased part of each line: patterns count fully up to TAPER_START cycles per frame and
#: fade out to nothing at MAX_OMEGA, so that no pattern enters or leaves the score abruptly.
TAPER_START = 0.3
MAX_OMEGA = 0.45
#: A speed is only scored if its usable patterns weigh at least this much (three at full weight).
MIN_WEIGHT = 3.0
#: Speeds are reported up to this fraction of the fastest the patterns allow. Below it the benchmark
#: keeps all but a few percent of single blocks within 10% of the truth; above it estimates crowd
#: towards the limit, and flow faster than the line can follow lands there too, so it is not reported.
FASTEST_FRACTION = 0.65
#: Speeds searched, in px/frame, in both directions.
SPEED_RANGE = (0.05, 30.0)
#: Shortest line and block the estimator accepts.
MIN_LENGTH_PX = 16
MIN_BLOCK_FRAMES = 16

_COARSE = np.geomspace(SPEED_RANGE[0], SPEED_RANGE[1], 200)
_COARSE_SPEEDS = np.concatenate([-_COARSE[::-1], _COARSE])


# ----------------------------------------------------------------------------- the line

def _catmull_rom(points: np.ndarray, samples_per_segment: int = 24) -> np.ndarray:
    """A smooth curve through every point (uniform Catmull-Rom), densely sampled."""
    if len(points) == 2:
        t = np.linspace(0.0, 1.0, samples_per_segment + 1)[:, None]
        return points[0] + t * (points[1] - points[0])
    padded = np.vstack([2 * points[0] - points[1], points, 2 * points[-1] - points[-2]])
    curve = []
    t = np.linspace(0.0, 1.0, samples_per_segment, endpoint=False)[:, None]
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
        curve.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                            + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    curve.append(points[-1:])
    return np.vstack(curve)


@dataclass(frozen=True)
class Centreline:
    """The line the user drew along a capillary, from upstream to downstream.

    `points` are the clicked points in video pixels (x to the right, y down).
    Positive velocity means flow from the first point towards the last.
    """

    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError('a centre line needs at least two points')

    @classmethod
    def from_points(cls, points: Iterable[Sequence[float]]) -> 'Centreline':
        cleaned: list[tuple[float, float]] = []
        for x, y in points:
            point = (float(x), float(y))
            if not cleaned or np.hypot(point[0] - cleaned[-1][0], point[1] - cleaned[-1][1]) > 1e-6:
                cleaned.append(point)
        return cls(tuple(cleaned))

    def curve(self) -> np.ndarray:
        """The smooth curve through the points, densely sampled, shape (n, 2)."""
        return _catmull_rom(np.asarray(self.points, dtype=float))

    @property
    def length_px(self) -> float:
        curve = self.curve()
        return float(np.hypot(*np.diff(curve, axis=0).T).sum())

    def sample_positions(self, spacing_px: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
        """Positions every `spacing_px` along the curve and the unit normals there, each (S, 2)."""
        curve = self.curve()
        arc = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(curve, axis=0).T))])
        s = np.arange(0.0, arc[-1] + 1e-9, spacing_px)
        positions = np.column_stack([np.interp(s, arc, curve[:, 0]), np.interp(s, arc, curve[:, 1])])
        tangent = np.gradient(positions, axis=0)
        tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-12)
        normal = np.column_stack([-tangent[:, 1], tangent[:, 0]])
        return positions, normal

    def reversed(self) -> 'Centreline':
        return Centreline(tuple(reversed(self.points)))

    def apex_arc_px(self) -> float:
        """Distance along the curve (px from the first point) of the apex of a line drawn round a capillary loop.

        The line runs from the base of one limb, over the apex, to the base of
        the other: the apex is the point farthest from both ends (the largest
        of the smaller of its two distances), searched in the middle 80% of the
        line. On the 53 loops of the aim-1 check it lay a median 1.3 px (at most
        17.5) from where the two separately traced limbs met (DEVLOG 2026-10-14).
        """
        curve = self.curve()
        arc = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(curve, axis=0).T))])
        nearer_end = np.minimum(np.hypot(*(curve - curve[0]).T), np.hypot(*(curve - curve[-1]).T))
        middle = (arc >= 0.1 * arc[-1]) & (arc <= 0.9 * arc[-1])
        return float(arc[np.argmax(np.where(middle, nearer_end, -1.0))])


# ------------------------------------------------------------------- the space-time diagram

class SpaceTimeSampler:
    """Samples one row of the space-time diagram per frame (bilinear, averaged across the line)."""

    def __init__(self, centreline: Centreline, half_width_px: int = DEFAULT_HALF_WIDTH_PX,
                 spacing_px: float = 1.0):
        import cv2  # only needed here; the estimator itself works on plain arrays

        self._cv2 = cv2
        self.centreline = centreline
        self.half_width_px = int(half_width_px)
        self.spacing_px = float(spacing_px)
        positions, normals = centreline.sample_positions(spacing_px)
        offsets = np.arange(-self.half_width_px, self.half_width_px + 1, dtype=float)
        across = positions[None, :, :] + offsets[:, None, None] * normals[None, :, :]   # (K, S, 2)
        self.positions = positions
        self.map_x = np.ascontiguousarray(across[:, :, 0], dtype=np.float32)
        self.map_y = np.ascontiguousarray(across[:, :, 1], dtype=np.float32)

    @property
    def n_positions(self) -> int:
        return int(self.positions.shape[0])

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """(x0, y0, x1, y1): the smallest rectangle holding every sample, in video pixels."""
        return (float(self.map_x.min()), float(self.map_y.min()), float(self.map_x.max()), float(self.map_y.max()))

    def inside(self, frame_shape) -> bool:
        """True if every sample lies inside a frame of `frame_shape`.

        On a stabilized video the samples must also stay in the picture in every frame measured, clear of
        the black strip the stabilizer leaves where the picture moved (`capillary.stabilize.check_picture`).
        """
        height, width = frame_shape[0], frame_shape[1]
        x0, y0, x1, y1 = self.bounds
        return bool(x0 >= 0 and y0 >= 0 and x1 <= width - 1 and y1 <= height - 1)

    def row(self, frame: np.ndarray) -> np.ndarray:
        frame = np.asarray(frame)
        if frame.ndim == 3:
            frame = frame[:, :, 0]
        samples = self._cv2.remap(frame.astype(np.float32, copy=False), self.map_x, self.map_y,
                                  self._cv2.INTER_LINEAR, borderMode=self._cv2.BORDER_REPLICATE)
        return samples.mean(axis=0)


def space_time_diagram(frames: Iterable[np.ndarray], centreline: Centreline,
                       half_width_px: int = DEFAULT_HALF_WIDTH_PX, spacing_px: float = 1.0,
                       should_continue=None) -> np.ndarray:
    """The space-time diagram of `frames` along `centreline`, shape (frames, positions), float32.

    `should_continue`, if given, is called once per frame; returning False stops early.
    """
    sampler = SpaceTimeSampler(centreline, half_width_px, spacing_px)
    rows = []
    for frame in frames:
        if should_continue is not None and not should_continue():
            break
        rows.append(sampler.row(frame))
    if not rows:
        raise ValueError('no frames to sample')
    return np.asarray(rows, dtype=np.float32)


# ----------------------------------------------------------------------------- the slope

def _omega_weight(omega: np.ndarray) -> np.ndarray:
    """How much a pattern counts at temporal frequency `omega`: fully up to `TAPER_START` cycles per
    frame, fading out (cos^2) to nothing at `MAX_OMEGA`, so the score changes smoothly with speed."""
    magnitude = np.abs(np.asarray(omega, dtype=float))
    weight = np.ones_like(magnitude)
    fading = (magnitude > TAPER_START) & (magnitude < MAX_OMEGA)
    weight[fading] = np.cos(0.5 * np.pi * (magnitude[fading] - TAPER_START) / (MAX_OMEGA - TAPER_START)) ** 2
    weight[magnitude >= MAX_OMEGA] = 0.0
    return weight


def _usable_k(n_positions: int, k_max: float = K_MAX) -> np.ndarray:
    """Spatial frequencies (cycles/px) the estimator uses for a line of `n_positions` samples."""
    n = int(n_positions) - 1                          # the differenced line
    if n < 3:
        return np.empty(0)
    k = np.fft.rfftfreq(n)
    return k[(k >= 3.0 / n) & (k <= k_max)]


def speed_limits(n_positions: int, n_frames: int) -> tuple[float, float]:
    """Slowest and fastest speed (px/frame) a block of this size measures reliably.

    Fastest: the patterns that are still unaliased at that speed must together
    weigh `MIN_WEIGHT` (three patterns at full weight); speeds are reported up
    to `FASTEST_FRACTION` of that, where the synthetic benchmark keeps single
    blocks within 10% of the truth. Slowest: the finest pattern must change by
    at least 1.5 cycles over the block, ``speed * K_MAX * frames >= 1.5``.
    """
    k = _usable_k(n_positions)
    slowest = max(1.5 / (K_MAX * max(1, int(n_frames))), SPEED_RANGE[0])
    if k.size < 3:
        return slowest, 0.0
    speeds = np.linspace(SPEED_RANGE[0], MAX_OMEGA / k[0], 4000)
    weight = _omega_weight(speeds[:, None] * k[None, :]).sum(axis=1)
    usable = speeds[weight >= MIN_WEIGHT]
    fastest = FASTEST_FRACTION * float(usable.max()) if usable.size else 0.0
    return slowest, fastest


@dataclass(frozen=True)
class StreakEstimate:
    """Speed of the streaks in one block of the diagram.

    `speed_px_per_frame` is positive for flow along the line's direction.
    `snr` is the direction contrast at that speed over its "no flow" spread,
    `coherence` the share of the block's energy on that speed's line, and
    `in_range` whether the speed lies in the block's measurable range.
    """

    speed_px_per_frame: float
    snr: float
    coherence: float
    in_range: bool

    def is_resolved(self, min_snr: float = MIN_SNR, min_coherence: float = MIN_COHERENCE) -> bool:
        return bool(self.in_range and np.isfinite(self.snr) and self.snr >= min_snr
                    and np.isfinite(self.coherence) and self.coherence >= min_coherence)

    @property
    def resolved(self) -> bool:
        return self.is_resolved()


_NO_ESTIMATE = StreakEstimate(float('nan'), float('nan'), float('nan'), False)


class _Spectrum:
    """The whitened, windowed block, one complex time series per spatial frequency."""

    def __init__(self, block: np.ndarray, k_max: float):
        block = np.asarray(block, dtype=float)
        n_frames, n_positions = block.shape
        b = block - block.mean(axis=0, keepdims=True)          # still structure
        b = b - b.mean(axis=1, keepdims=True)                  # the same-moment change of the whole line
        b = np.diff(b, axis=1)                                 # whitening along the line
        n = n_positions - 1
        spatial = np.fft.rfft(b * np.hanning(n)[None, :], axis=1)
        k = np.fft.rfftfreq(n)
        keep = (k >= 3.0 / n) & (k <= k_max)
        window = np.hanning(n_frames)
        self.k = k[keep]
        self.series = spatial[:, keep] * window[:, None]
        self.t = np.arange(n_frames, dtype=float)
        # Power to expect at (k, omega) without flow. Disturbances (jitter, the same-moment change) are not
        # white: they crowd the slow temporal frequencies where slow flow is measured. So the floor is
        # local: the median, over the nearest temporal frequencies of both signs, of the column's power
        # (median of an exponential / ln 2).
        power = np.abs(np.fft.fft(self.series, axis=0)) ** 2                  # (T, K), omega = fftfreq(T)
        omega = np.fft.fftfreq(n_frames)
        order = np.argsort(np.abs(omega), kind='stable')
        magnitude = np.abs(omega)[order]
        symmetric = power[order]
        half = 5
        local = np.empty_like(symmetric)
        for i in range(len(order)):
            near = np.abs(magnitude - magnitude[i]) <= (half + 0.5) / n_frames
            local[i] = np.median(symmetric[near], axis=0)
        self._floor_omega = magnitude
        self._floor = local / np.log(2)
        # the largest line power a column's energy allows (all of it at one temporal frequency)
        self.ceiling = (window.sum() ** 2 / np.sum(window ** 2)) * np.sum(np.abs(self.series) ** 2, axis=0)

    def local_floor(self, omega: np.ndarray, columns: np.ndarray) -> np.ndarray:
        """The floor at temporal frequency `omega` (either sign) in each of `columns`."""
        rows = np.clip(np.searchsorted(self._floor_omega, np.abs(omega)), 0, len(self._floor_omega) - 1)
        return self._floor[rows, columns]

    def powers(self, speeds: np.ndarray):
        """Forward and mirror line power, shape (speeds, k), and each pattern's weight at that speed."""
        omega = -np.asarray(speeds, dtype=float)[:, None] * self.k[None, :]
        weight = _omega_weight(omega)
        phase = np.exp(-2j * np.pi * omega[:, :, None] * self.t[None, None, :])        # (V, K, T)
        forward = np.abs(np.einsum('tk,vkt->vk', self.series, phase)) ** 2
        mirror = np.abs(np.einsum('tk,vkt->vk', self.series, np.conj(phase))) ** 2
        return forward, mirror, weight

    def scores(self, speeds: np.ndarray, min_weight: float = MIN_WEIGHT) -> np.ndarray:
        """Weighted mean direction contrast of each speed's line; NaN where its patterns weigh too little."""
        forward, mirror, weight = self.powers(speeds)
        total_weight = weight.sum(axis=1)
        total = (weight * (forward - mirror)).sum(axis=1)
        with np.errstate(invalid='ignore', divide='ignore'):
            return np.where(total_weight >= min_weight, total / np.maximum(total_weight, 1e-12), np.nan)

    def quality(self, speed: float) -> tuple[float, float]:
        """(signal-to-noise ratio, coherence) of the line of `speed`."""
        forward, mirror, weight = self.powers(np.array([speed]))
        w = weight[0]
        if w.sum() < MIN_WEIGHT:
            return float('nan'), float('nan')
        contrast = float(np.sum(w * (forward[0] - mirror[0])))
        columns = np.arange(self.k.size)
        floor = self.local_floor(-speed * self.k, columns)
        spread = np.sqrt(2.0 * np.sum((w * floor) ** 2))
        ceiling = float(np.sum(w * self.ceiling))
        snr = contrast / spread if spread > 0 else float('nan')
        coherence = contrast / ceiling if ceiling > 0 else float('nan')
        return float(snr), float(coherence)


def streak_speed(block: np.ndarray, k_max: float = K_MAX) -> StreakEstimate:
    """Speed (px/frame along the line) of the streaks in one block of a space-time diagram.

    `block` has frames down and positions across, as `space_time_diagram`
    returns it. NaN when the block is too small or contains missing samples.
    """
    block = np.asarray(block, dtype=float)
    if block.ndim != 2 or block.shape[0] < MIN_BLOCK_FRAMES or block.shape[1] < MIN_LENGTH_PX:
        return _NO_ESTIMATE
    if not np.all(np.isfinite(block)):
        return _NO_ESTIMATE
    spectrum = _Spectrum(block, k_max)
    if spectrum.k.size < 3:
        return _NO_ESTIMATE
    scores = spectrum.scores(_COARSE_SPEEDS)
    if np.all(np.isnan(scores)):
        return _NO_ESTIMATE
    i = int(np.nanargmax(scores))
    lo = _COARSE_SPEEDS[max(0, i - 1)]
    hi = _COARSE_SPEEDS[min(len(_COARSE_SPEEDS) - 1, i + 1)]
    fine = np.linspace(lo, hi, 41)
    fine_scores = spectrum.scores(fine)
    if np.all(np.isnan(fine_scores)):
        return _NO_ESTIMATE
    j = int(np.nanargmax(fine_scores))
    best, best_score = float(fine[j]), float(fine_scores[j])
    snr, coherence = spectrum.quality(best)
    slowest, fastest = speed_limits(block.shape[1], block.shape[0])
    in_range = bool(slowest <= abs(best) <= fastest) and not _faster_than_measurable(spectrum, fastest, best_score)
    return StreakEstimate(best, snr, coherence, in_range)


def _faster_than_measurable(spectrum: _Spectrum, fastest: float, best_score: float) -> bool:
    """True if a speed beyond the measurable range explains the block better than the chosen one.

    Flow faster than the line can follow has almost no unaliased patterns
    left, so its own line cannot be scored the normal way, and its aliased
    energy can make a wrong, slower speed win. Its coarsest patterns still
    carry it, though: scored on whatever unaliased weight they have, a speed
    beyond the range beats the chosen one.
    """
    beyond = _COARSE_SPEEDS[np.abs(_COARSE_SPEEDS) > fastest]
    if beyond.size == 0:
        return False
    scores = spectrum.scores(beyond, min_weight=0.25)
    return bool(np.any(np.isfinite(scores)) and np.nanmax(scores) > best_score)


def resolvable_speeds(length_px: float, fps: float, mm_per_pixel: float,
                      block_frames: int = DEFAULT_BLOCK_FRAMES) -> tuple[float, float]:
    """Slowest and fastest velocity (mm/s) a line of `length_px` measures in blocks of `block_frames`."""
    if not np.isfinite(length_px) or length_px < MIN_LENGTH_PX or not fps or not mm_per_pixel:
        return float('nan'), float('nan')
    slowest, fastest = speed_limits(int(length_px) + 1, block_frames)
    to_mm_s = fps * mm_per_pixel
    return slowest * to_mm_s, fastest * to_mm_s


# ------------------------------------------------------------------------ whole diagrams

def analyze_space_time(
    diagram: np.ndarray,
    fps: float,
    mm_per_pixel: float,
    spacing_px: float = 1.0,
    block_frames: int = DEFAULT_BLOCK_FRAMES,
    step_frames: int = DEFAULT_STEP_FRAMES,
    min_snr: float = MIN_SNR,
    min_coherence: float = MIN_COHERENCE,
    first_frame: int = 0,
    progress=None,
) -> pd.DataFrame:
    """Estimate the velocity in successive blocks of a diagram.

    One row per block, indexed by the block's centre frame (counted from
    `first_frame`, the video frame of the diagram's first row): ``time_s``,
    ``speed_px_per_frame``, ``velocity_mm_s`` (positive along the line),
    ``snr``, ``coherence`` and ``resolved``. Unresolved blocks keep their speed
    but get NaN velocity, so nothing downstream averages them in by accident.
    """
    diagram = np.asarray(diagram, dtype=float)
    n_frames = diagram.shape[0]
    block_frames = int(block_frames)
    step_frames = max(1, int(step_frames))
    if n_frames < block_frames:
        raise ValueError(f'the diagram has {n_frames} frames, fewer than one block of {block_frames}')
    starts = list(range(0, n_frames - block_frames + 1, step_frames))
    rows = []
    for number, start in enumerate(starts):
        estimate = streak_speed(diagram[start:start + block_frames])
        resolved = estimate.is_resolved(min_snr, min_coherence)
        speed = estimate.speed_px_per_frame
        velocity = speed * spacing_px * fps * mm_per_pixel if resolved else float('nan')
        centre = first_frame + start + block_frames // 2
        rows.append({'frame': centre, 'time_s': centre / fps if fps else float('nan'),
                     'speed_px_per_frame': speed, 'velocity_mm_s': velocity, 'snr': estimate.snr,
                     'coherence': estimate.coherence, 'resolved': resolved})
        if progress is not None:
            progress((number + 1) / len(starts))
    return pd.DataFrame(rows).set_index('frame')


def space_time_summary(report: pd.DataFrame) -> dict:
    """Headline numbers of `analyze_space_time` output (velocities in mm/s)."""
    velocity = report['velocity_mm_s'].to_numpy(dtype=float)
    resolved = velocity[np.isfinite(velocity)]
    snr = report['snr'].to_numpy(dtype=float)
    snr = snr[np.isfinite(snr)]
    count = int(len(report))
    return {
        'blocks': count,
        'resolved': int(resolved.size),
        'resolved_fraction': resolved.size / count if count else float('nan'),
        'median': float(np.median(resolved)) if resolved.size else float('nan'),
        'q25': float(np.percentile(resolved, 25)) if resolved.size else float('nan'),
        'q75': float(np.percentile(resolved, 75)) if resolved.size else float('nan'),
        'mean': float(np.mean(resolved)) if resolved.size else float('nan'),
        'positive_fraction': float(np.mean(resolved > 0)) if resolved.size else float('nan'),
        'median_snr': float(np.median(snr)) if snr.size else float('nan'),
    }


def estimate_from_frames(frames: Iterable[np.ndarray], centreline: Centreline, fps: float,
                         mm_per_pixel: float, half_width_px: int = DEFAULT_HALF_WIDTH_PX,
                         block_frames: int = DEFAULT_BLOCK_FRAMES, step_frames: int = DEFAULT_STEP_FRAMES,
                         first_frame: int = 0) -> tuple[np.ndarray, pd.DataFrame]:
    """Diagram and per-block velocities in one call (for scripts and tests)."""
    diagram = space_time_diagram(frames, centreline, half_width_px)
    report = analyze_space_time(diagram, fps, mm_per_pixel, block_frames=block_frames,
                                step_frames=step_frames, first_frame=first_frame)
    return diagram, report
