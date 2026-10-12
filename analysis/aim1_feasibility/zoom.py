"""A zoomed part of a recording's resting image with a grid every 10 px, to place points.

python analysis/aim1_feasibility/zoom.py <recording> x0 y0 x1 y1 [scale]

Needs out/<recording>_rest_mean.npy (rest_image.py). Writes
out/<recording>_zoom_<x0>_<y0>.png, `scale` (default 4) times enlarged,
labels every 50 px.
"""
import os
import sys

import cv2
import numpy as np

from common import OUT, to_uint8, vessel_image

LABEL = (0, 200, 255)
GRID = (0, 90, 0)

if __name__ == '__main__':
    stem, (x0, y0, x1, y1) = sys.argv[1], map(int, sys.argv[2:6])
    scale = int(sys.argv[6]) if len(sys.argv) > 6 else 4
    mean = np.load(os.path.join(OUT, f'{stem}_rest_mean.npy'))
    image = to_uint8(vessel_image(mean)[y0:y1, x0:x1], high=99.5, margin=0)
    image = cv2.cvtColor(cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC),
                         cv2.COLOR_GRAY2BGR)
    for x in range((x0 // 10 + 1) * 10, x1, 10):
        colour = LABEL if x % 50 == 0 else GRID
        cv2.line(image, (scale * (x - x0), 0), (scale * (x - x0), image.shape[0]), colour, 1)
        if x % 50 == 0:
            cv2.putText(image, str(x), (scale * (x - x0) + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, colour, 1)
    for y in range((y0 // 10 + 1) * 10, y1, 10):
        colour = LABEL if y % 50 == 0 else GRID
        cv2.line(image, (0, scale * (y - y0)), (image.shape[1], scale * (y - y0)), colour, 1)
        if y % 50 == 0:
            cv2.putText(image, str(y), (2, scale * (y - y0) + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, colour, 1)
    name = f'{stem}_zoom_{x0}_{y0}.png'
    cv2.imwrite(os.path.join(OUT, name), image)
    print(name)
