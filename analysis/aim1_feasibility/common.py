"""What the aim-1 feasibility scripts share: paths, the recordings aim 1 uses, the official rest window.

Each run of the check has a folder of its own with its lines.json, results and out/: this one (the first
run, 2026-10-12, on the videos as stabilized then) or restabilized/ (the rerun of 2026-10-14 on the
re-stabilized videos). The scripts work on this folder's run unless given `--dir <folder>` (`run_args`).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from capillary import inventory  # noqa: E402
from capillary.video import probe_video  # noqa: E402

#: The run worked on: its folder, its lines and results, and out/ for its images and diagrams (`use`).
FOLDER = HERE
OUT = os.path.join(HERE, 'out')
LINES = os.path.join(HERE, 'lines.json')
RESULTS = os.path.join(HERE, 'results.csv')
VIDEOS = os.path.join(REPO, 'StabilizedVideos')
#: The app's default calibration (mm per pixel of the video).
MM_PER_PIXEL = 0.001328903654
#: The resting image is band-passed with a difference of Gaussians of these sigmas (px). Finer than the
#: stabilizer's (2 and 15 px), which merges the two limbs of a narrow loop; the mean of a minute of rest
#: is smooth enough for it.
VESSEL_SIGMAS_PX = (1.0, 8.0)


def use(folder: str) -> None:
    """Work on the run in `folder` (relative to this one): its lines.json and results.csv, and its out/."""
    global FOLDER, OUT, LINES, RESULTS
    FOLDER = os.path.join(HERE, folder)
    OUT = os.path.join(FOLDER, 'out')
    LINES = os.path.join(FOLDER, 'lines.json')
    RESULTS = os.path.join(FOLDER, 'results.csv')


def run_args(args) -> list:
    """`args` without `--dir <folder>`; when that is given, the run in `folder` is worked on (`use`)."""
    args = list(args)
    if '--dir' in args:
        at = args.index('--dir')
        use(args[at + 1])
        del args[at:at + 2]
    return args


def video_path(stem: str) -> str:
    """The stabilized video of the recording `stem`, however its name is spelled on disk."""
    for name in os.listdir(VIDEOS):
        base, ext = os.path.splitext(name)
        if ext.lower() == '.avi' and inventory.nfc(base) == inventory.nfc(stem):
            return os.path.join(VIDEOS, name)
    raise FileNotFoundError(f'no stabilized video of {stem} in {VIDEOS}')


def rest_window(stem: str) -> tuple:
    """The frame rate and the official rest window (first and last frame, inclusive) of `stem`'s video."""
    info = probe_video(video_path(stem))
    phases = inventory.recording_phases(stem, info.fps, info.frame_count)
    if phases is None or 'rest' not in phases.windows:
        raise ValueError(f'{stem}: no official rest window')
    return info.fps, phases.windows['rest']


def aim1_recordings():
    """The recordings aim 1 uses (each visit's before-exposure recording), from `capillary.inventory`."""
    table = inventory.recordings()
    table = inventory.mark_use(table, inventory.participants(table))
    return table[table['used_for'].fillna('').str.contains(r'aims? 1\b')].reset_index(drop=True)


def vessel_image(mean: np.ndarray) -> np.ndarray:
    """The resting image as lines are placed on it: band-passed (`VESSEL_SIGMAS_PX`), vessels bright."""
    image = mean.astype(np.float32)
    fine, coarse = VESSEL_SIGMAS_PX
    return cv2.GaussianBlur(image, (0, 0), coarse) - cv2.GaussianBlur(image, (0, 0), fine)


def to_uint8(image: np.ndarray, low: float = 1.0, high: float = 99.7, margin: int = 40) -> np.ndarray:
    """`image` scaled to 0-255 between two percentiles of its inner part (a moved frame leaves empty edges)."""
    inner = image[margin:-margin, margin:-margin] if margin else image
    lo, hi = np.percentile(inner, [low, high])
    return np.clip((image - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
