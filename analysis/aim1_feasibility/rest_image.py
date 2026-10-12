"""The resting image of a stabilized recording, to place lines on.

python analysis/aim1_feasibility/rest_image.py [--again] <recording> [<recording> ...]

A mean saved before is reused; --again reads the video again.

The mean of the official rest window (`capillary.inventory.recording_phases`:
2 s after the start to 2 s before the occlusion), band-passed
(`common.vessel_image`), vessels bright. Writes out/<recording>_rest_mean.npy and
out/<recording>_rest_grid.png, 1.5 times enlarged, with a grid line every
20 px and a label every 100 px (video pixels).
"""
import os
import sys

import cv2
import numpy as np

from common import OUT, rest_window, to_uint8, vessel_image, video_path
from capillary.video import iter_frames

SCALE = 1.5
MINOR, MAJOR = 20, 100
LABEL = (0, 200, 255)
GRID = (0, 70, 0)


def rest_mean(stem: str) -> np.ndarray:
    """The mean frame of the official rest window, saved to out/<stem>_rest_mean.npy."""
    _, (first, last) = rest_window(stem)
    total, count = None, 0
    for frame in iter_frames(video_path(stem), start=first, max_frames=last - first + 1):
        total = frame.astype(np.float64) if total is None else total + frame
        count += 1
    mean = (total / count).astype(np.float32)
    os.makedirs(OUT, exist_ok=True)
    np.save(os.path.join(OUT, f'{stem}_rest_mean.npy'), mean)
    return mean


def grid_image(mean: np.ndarray, scale: float = SCALE) -> np.ndarray:
    """The band-passed resting image, enlarged, with the grid and labels in video pixels."""
    image = cv2.resize(to_uint8(vessel_image(mean)), None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    height, width = mean.shape
    for x in range(0, width, MINOR):
        colour = LABEL if x % MAJOR == 0 else GRID
        cv2.line(image, (int(scale * x), 0), (int(scale * x), image.shape[0]), colour, 1)
        if x % MAJOR == 0:
            cv2.putText(image, str(x), (int(scale * x) + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, LABEL, 1)
    for y in range(0, height, MINOR):
        colour = LABEL if y % MAJOR == 0 else GRID
        cv2.line(image, (0, int(scale * y)), (image.shape[1], int(scale * y)), colour, 1)
        if y % MAJOR == 0:
            cv2.putText(image, str(y), (2, int(scale * y) + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, LABEL, 1)
    return image


if __name__ == '__main__':
    again = '--again' in sys.argv[1:]
    for stem in (arg for arg in sys.argv[1:] if arg != '--again'):
        saved = os.path.join(OUT, f'{stem}_rest_mean.npy')
        mean = np.load(saved) if os.path.exists(saved) and not again else rest_mean(stem)
        cv2.imwrite(os.path.join(OUT, f'{stem}_rest_grid.png'), grid_image(mean))
        print('saved', stem)
