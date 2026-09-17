"""Synthetic capillary videos with an exactly known velocity.

A real capillaroscopy clip has no ground truth — nobody knows how fast the
blood in it was actually moving, so it cannot tell us whether the estimator is
right. These generated clips can: an intensity pattern is translated down the
frame at a chosen number of pixels per frame, so the true lag between two boxes
`d` pixels apart is exactly `d / velocity` frames, and the true velocity in mm/s
is `velocity * fps * mm_per_pixel`.

The pattern moves towards increasing y, so a box higher up the frame (smaller y)
encounters each feature first.
"""

from __future__ import annotations

import numpy as np


def flow_profile(length: int, seed: int = 0, smooth: int = 15) -> np.ndarray:
    """A smooth 1-D intensity profile standing in for a train of red-cell plugs.

    Smoothing matters: white noise correlates against itself over a single
    sample, which would let the estimator look good on a signal no real
    capillary produces. A smoothed profile survives the averaging over a 10x10
    box the way a genuine plug does.
    """
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=length + 4 * smooth)
    kernel = np.ones(smooth) / smooth
    smoothed = np.convolve(raw, kernel, mode='same')[:length]

    spread = smoothed.max() - smoothed.min()
    if spread == 0:  # pragma: no cover - only for a degenerate smooth window
        return np.full(length, 128.0)
    # Map into 40..215 so added noise cannot clip against the uint8 range.
    return 40.0 + 175.0 * (smoothed - smoothed.min()) / spread


def make_flow_frames(
    n_frames: int = 400,
    height: int = 240,
    width: int = 120,
    velocity_px_per_frame: float = 2.5,
    seed: int = 0,
    noise_sd: float = 1.0,
    smooth: int = 15,
) -> list[np.ndarray]:
    """Return `n_frames` greyscale frames of a pattern flowing towards +y."""
    if velocity_px_per_frame <= 0:
        raise ValueError('velocity must be positive')

    margin = 10
    origin = velocity_px_per_frame * (n_frames - 1) + margin
    length = int(np.ceil(origin + height + margin))
    profile = flow_profile(length, seed=seed, smooth=smooth)
    coordinates = np.arange(length, dtype=float)
    rng = np.random.default_rng(seed + 1)

    rows = np.arange(height, dtype=float)
    frames = []
    for frame_index in range(n_frames):
        sample_at = origin + rows - velocity_px_per_frame * frame_index
        column = np.interp(sample_at, coordinates, profile)
        frame = np.repeat(column[:, None], width, axis=1)
        if noise_sd:
            frame = frame + rng.normal(0.0, noise_sd, frame.shape)
        frames.append(np.clip(frame, 0, 255).astype(np.uint8))
    return frames


def expected_lag_frames(distance_px: float, velocity_px_per_frame: float) -> float:
    """Ground-truth lag between two boxes `distance_px` apart."""
    return distance_px / velocity_px_per_frame


def expected_velocity_mm_s(
    velocity_px_per_frame: float, fps: float, mm_per_pixel: float
) -> float:
    """Ground-truth velocity in mm/s."""
    return velocity_px_per_frame * fps * mm_per_pixel
