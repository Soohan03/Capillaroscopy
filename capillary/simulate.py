"""Synthetic capillary recordings with a known red-cell velocity, for validating the estimators.

A real recording has no ground truth: nobody knows how fast the blood in it
was moving, so it cannot show whether an estimator is right. These clips can.
A capillary loop is drawn on a textured background, a pattern of red cells
and plasma gaps moves along it at a chosen speed, and the disturbances
measured in the 2019 recordings (see the 2026-10-06 entries in DEVLOG.md) are
added on top:

- sensor noise of about 3 grey levels per pixel,
- a darkening of the whole vessel that changes at the same moment along all
  of it (in the recordings about 70% of what a box on the vessel sees),
  slightly stronger in some parts of the vessel than in others,
- residual movement of the whole image after stabilization (jitter),
- optical blur, and motion blur while the shutter is open.

`tests/synthetic.py` keeps the simpler clips the older tests use: a pattern
sliding down the whole frame, with no vessel and no disturbances.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .roi import ROI
from .spacetime import Centreline


@dataclass(frozen=True)
class Disturbances:
    """What makes a recording harder to measure than a clean moving pattern."""

    noise_sd: float = 3.0                # sensor noise per pixel, grey levels (measured: 3.05)
    same_moment_sd: float = 0.38         # vessel-wide darkness change, relative to the vessel's contrast
    same_moment_unevenness: float = 0.15  # how much that change varies along the vessel (measured: 0.14-0.41)
    jitter_px: float = 0.3               # residual whole-image movement, SD in pixels
    optical_blur_px: float = 1.2         # Gaussian blur of the optics, sigma in pixels
    exposure: float = 1.0                # shutter open for this fraction of a frame interval (motion blur)

    @classmethod
    def clean(cls) -> 'Disturbances':
        """Sensor noise and optics only."""
        return cls(same_moment_sd=0.0, same_moment_unevenness=0.0, jitter_px=0.0)

    @classmethod
    def strong(cls) -> 'Disturbances':
        """Twice the measured same-moment change, uneven, and three times the jitter."""
        return cls(same_moment_sd=0.6, same_moment_unevenness=0.4, jitter_px=1.0)


@dataclass
class SyntheticRecording:
    frames: np.ndarray                   # (frames, height, width) uint8
    centreline: Centreline               # the vessel's true centre line, in the direction of flow
    speed_px_per_frame: np.ndarray       # true speed along the centre line in every frame
    fps: float
    vessel_width_px: float
    disturbances: Disturbances = field(default_factory=Disturbances)

    @property
    def mean_speed_px_per_frame(self) -> float:
        return float(np.mean(self.speed_px_per_frame))

    def true_velocity_mm_s(self, mm_per_pixel: float) -> float:
        return self.mean_speed_px_per_frame * self.fps * mm_per_pixel

    def point_at(self, arc_px: float) -> tuple[float, float]:
        positions, _ = self.centreline.sample_positions(0.25)
        index = int(np.clip(round(arc_px / 0.25), 0, len(positions) - 1))
        return float(positions[index, 0]), float(positions[index, 1])

    def boxes(self, upstream_arc_px: float, distance_px: float, size: int = 12) -> tuple[ROI, ROI]:
        """Two boxes on the vessel `distance_px` apart along it: (box 1 downstream, box 2 upstream)."""
        up = self.point_at(upstream_arc_px)
        down = self.point_at(upstream_arc_px + distance_px)
        return (ROI(int(round(down[0])), int(round(down[1])), size, size),
                ROI(int(round(up[0])), int(round(up[1])), size, size))

    def drawn_line(self, start_arc_px: float, end_arc_px: float, every_px: float = 15.0,
                   wobble_px: float = 1.0, seed: int = 0) -> Centreline:
        """A line as a person might click it: a point every `every_px`, up to `wobble_px` off centre."""
        rng = np.random.default_rng(seed)
        positions, normals = self.centreline.sample_positions(1.0)
        arcs = np.linspace(start_arc_px, end_arc_px, max(2, int(round(abs(end_arc_px - start_arc_px) / every_px)) + 1))
        points = []
        for arc in arcs:
            i = int(np.clip(round(arc), 0, len(positions) - 1))
            offset = rng.uniform(-wobble_px, wobble_px)
            points.append(positions[i] + offset * normals[i])
        return Centreline.from_points(points)


def hairpin(limb_length_px: float = 150.0, limb_gap_px: float = 26.0, left_x: float = 60.0,
            bottom_y: float = 200.0, lean_px: float = 10.0) -> Centreline:
    """A capillary loop: up the arterial limb on the left, round the apex, down the venous limb.

    The limbs lean slightly, so that nothing lines up with the pixel grid.
    """
    top_y = bottom_y - limb_length_px
    radius = limb_gap_px / 2.0
    points = []
    for t in np.linspace(0.0, 1.0, 16):
        points.append((left_x + lean_px * t, bottom_y - t * limb_length_px))
    centre = (left_x + lean_px + radius, top_y)
    for angle in np.linspace(np.pi, 0.0, 14)[1:-1]:
        points.append((centre[0] + radius * np.cos(angle), centre[1] - radius * np.sin(angle)))
    for t in np.linspace(0.0, 1.0, 16):
        points.append((left_x + lean_px + limb_gap_px + lean_px * 0.5 * t, top_y + t * limb_length_px))
    return Centreline.from_points(points)


def _smooth_noise(rng: np.random.Generator, n: int, sigma: float) -> np.ndarray:
    half = int(4 * sigma) + 1
    raw = rng.normal(size=n + 2 * half)
    x = np.arange(-half, half + 1)
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    out = np.convolve(raw, kernel / kernel.sum(), 'valid')[:n]
    return (out - out.mean()) / (out.std() or 1.0)


def _red_cells(rng: np.random.Generator, length: float, step: float, cell_px: float = 6.0,
               gap_rate: float = 0.1, gap_px: tuple[float, float] = (6.0, 30.0)) -> np.ndarray:
    """How full of red cells the vessel is, 0..1, sampled every `step` px along `length` px.

    Cells of about `cell_px` follow each other closely, with a plasma gap of
    `gap_px` between them now and then.
    """
    n = int(np.ceil(length / step)) + 1
    u = np.arange(n) * step
    occupancy = np.zeros(n)
    position = -2 * cell_px
    width = cell_px / 2.0
    while position < length + 2 * cell_px:
        lo, hi = np.searchsorted(u, [position - 2 * width, position + 2 * width])
        occupancy[lo:hi] += np.exp(-0.5 * ((u[lo:hi] - position) / (width / 1.5)) ** 2)
        position += cell_px * (0.9 + 0.25 * rng.random())
        if rng.random() < gap_rate:
            position += rng.uniform(*gap_px)
    return np.clip(occupancy, 0.0, 1.0)


def _ou(rng: np.random.Generator, n: int, tau: float, sd: float) -> np.ndarray:
    a = np.exp(-1.0 / tau)
    out = np.zeros(n)
    noise = rng.normal(size=n) * sd * np.sqrt(1 - a * a)
    for i in range(1, n):
        out[i] = a * out[i - 1] + noise[i]
    return out


def simulate(
    centreline: Centreline,
    n_frames: int,
    speed_px_per_frame: float,
    shape: tuple[int, int] = (230, 150),
    fps: float = 30.0,
    vessel_width_px: float = 10.0,
    contrast: float = 20.0,
    background: float = 110.0,
    pulsatility: float = 0.0,
    heart_rate_hz: float = 1.1,
    disturbances: Optional[Disturbances] = None,
    seed: int = 0,
) -> SyntheticRecording:
    """Render a recording of red cells moving along `centreline` (from its first point to its last).

    `speed_px_per_frame` is the mean speed along the line; with `pulsatility`
    > 0 it varies with the heart beat by that fraction. `contrast` is how many
    grey levels a vessel full of red cells is darker than the background at
    its centre. Frames are greyscale uint8, `shape` is (height, width).
    """
    import cv2
    from scipy.spatial import cKDTree

    if n_frames < 1:
        raise ValueError('n_frames must be at least 1')
    if speed_px_per_frame < 0:
        raise ValueError('speed must not be negative; reverse the centre line for the other direction')
    disturbances = disturbances or Disturbances()
    rng = np.random.default_rng(seed)
    height, width = shape
    t = np.arange(n_frames)

    # speed and displacement of the cell pattern
    phase = rng.uniform(0, 2 * np.pi)
    speed = speed_px_per_frame * (1 + pulsatility * np.sin(2 * np.pi * heart_rate_hz * t / fps + phase))
    shift = np.concatenate([[0.0], np.cumsum(speed[:-1])])

    # where every pixel lies along and across the vessel
    step = 0.25
    dense, _ = centreline.sample_positions(step)
    tree = cKDTree(dense)
    yy, xx = np.mgrid[0:height, 0:width]
    pixels = np.column_stack([xx.ravel(), yy.ravel()]).astype(float)
    distance, nearest = tree.query(pixels)
    radius = vessel_width_px / 2.0
    on_vessel = distance <= radius
    arc = nearest[on_vessel] * step
    thickness = np.sqrt(np.clip(1 - (distance[on_vessel] / radius) ** 2, 0, 1))
    flat_index = np.nonzero(on_vessel)[0]

    # the cell pattern, long enough for everything that passes; cumulative sum for motion blur
    length = arc.max() if arc.size else 0.0
    lo, hi = -shift[-1] - 3 * max(speed.max(), 1) - 20, length + 20
    cells = _red_cells(rng, hi - lo, step)
    cumulative = np.concatenate([[0.0], np.cumsum(cells) * step])
    coords = lo + np.arange(cumulative.size) * step

    def occupancy(u: np.ndarray, blur: float) -> np.ndarray:
        if blur < step:
            return np.interp(u, coords[:-1], cells)
        return (np.interp(u, coords, cumulative) - np.interp(u - blur, coords, cumulative)) / blur

    # what changes at the same moment along the whole vessel, and how evenly
    same = (_ou(rng, n_frames, 8.0, 0.8 * disturbances.same_moment_sd)
            + 0.6 * disturbances.same_moment_sd * np.sin(2 * np.pi * heart_rate_hz * t / fps + rng.uniform(0, 6.3)))
    unevenness = 1 + disturbances.same_moment_unevenness * _smooth_noise(rng, int(length / step) + 2, 15.0 / step)
    unevenness = unevenness[np.clip((arc / step).astype(int), 0, unevenness.size - 1)]
    jitter = np.column_stack([_ou(rng, n_frames, 4.0, disturbances.jitter_px),
                              _ou(rng, n_frames, 4.0, disturbances.jitter_px)])

    # a still, textured background with some vignetting
    texture = cv2.GaussianBlur(rng.normal(0, 1, (height, width)).astype(np.float32), (0, 0), 10)
    texture *= 6.0 / (texture.std() or 1.0)
    ramp = np.linspace(-1, 1, width)[None, :] * 4.0 + np.linspace(-1, 1, height)[:, None] * 3.0
    base = (background + texture + ramp).astype(np.float32).ravel()

    frames = np.empty((n_frames, height, width), np.uint8)
    for i in range(n_frames):
        darkness = contrast * thickness * occupancy(arc - shift[i], disturbances.exposure * speed[i])
        darkness *= 1 + same[i] * unevenness
        image = base.copy()
        image[flat_index] -= darkness
        image = image.reshape(height, width)
        if disturbances.jitter_px:
            matrix = np.float32([[1, 0, jitter[i, 0]], [0, 1, jitter[i, 1]]])
            image = cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_REFLECT)
        if disturbances.optical_blur_px:
            image = cv2.GaussianBlur(image, (0, 0), disturbances.optical_blur_px)
        if disturbances.noise_sd:
            image = image + rng.normal(0, disturbances.noise_sd, image.shape).astype(np.float32)
        frames[i] = np.clip(np.round(image), 0, 255).astype(np.uint8)

    return SyntheticRecording(frames=frames, centreline=centreline, speed_px_per_frame=speed, fps=fps,
                              vessel_width_px=vessel_width_px, disturbances=disturbances)
