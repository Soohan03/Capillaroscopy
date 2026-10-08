"""Zoomed crop of a recording's resting image with a fine grid (every 10 px), to place points: stem x0 y0 x1 y1."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
import cv2, numpy as np
from capillary.stabilize import enhance
OUT = os.path.join(HERE, 'out')
stem, x0, y0, x1, y1 = sys.argv[1], *map(int, sys.argv[2:6])
mean = np.load(os.path.join(OUT, f'{stem}_rest_mean.npy'))
img = -enhance(mean)[y0:y1, x0:x1]
lo, hi = np.percentile(img, [1, 99.5]); img = np.clip((img - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
s = 4
img = cv2.cvtColor(cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC), cv2.COLOR_GRAY2BGR)
for x in range((x0 // 10 + 1) * 10, x1, 10):
    c = (0, 200, 255) if x % 50 == 0 else (0, 90, 0)
    cv2.line(img, (s * (x - x0), 0), (s * (x - x0), img.shape[0]), c, 1)
    if x % 50 == 0: cv2.putText(img, str(x), (s * (x - x0) + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, c, 1)
for y in range((y0 // 10 + 1) * 10, y1, 10):
    c = (0, 200, 255) if y % 50 == 0 else (0, 90, 0)
    cv2.line(img, (0, s * (y - y0)), (img.shape[1], s * (y - y0)), c, 1)
    if y % 50 == 0: cv2.putText(img, str(y), (2, s * (y - y0) + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, c, 1)
name = f'{stem}_zoom_{x0}_{y0}.png'
cv2.imwrite(os.path.join(OUT, name), img); print(name)
