"""Resting image of a stabilized recording (band-passed mean over the rest window) with a grid, to place lines."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
import cv2, numpy as np, pandas as pd
from capillary.video import iter_frames, probe_video
from capillary.stabilize import enhance
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)
times = pd.read_csv(os.path.join(REPO, 'metadata', 'ESMOKE_timestamps.csv'), sep=';').set_index('source_file')

def rest_window(stem, fps):
    occ = float(times.loc[stem, 'occlusion'])
    return int(2 * fps), int((occ - 2) * fps)

def rest_mean(stem):
    path = os.path.join(REPO, 'StabilizedVideos', f'{stem}.avi')
    fps = probe_video(path).fps; a, b = rest_window(stem, fps)
    total, n = None, 0
    for f in iter_frames(path, start=a, max_frames=b - a):
        total = f.astype(np.float64) if total is None else total + f; n += 1
    mean = (total / n).astype(np.float32)
    np.save(os.path.join(OUT, f'{stem}_rest_mean.npy'), mean)
    return mean

if __name__ == '__main__':
    stem = sys.argv[1]
    mean = rest_mean(stem)
    img = -enhance(mean)
    lo, hi = np.percentile(img[40:-40, 40:-40], [1, 99.7])
    img = np.clip((img - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
    scale = 1.5
    img = cv2.cvtColor(cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC), cv2.COLOR_GRAY2BGR)
    for x in range(0, 640, 20):
        cv2.line(img, (int(scale * x), 0), (int(scale * x), img.shape[0]), (0, 200, 255) if x % 100 == 0 else (0, 70, 0), 1)
        if x % 100 == 0: cv2.putText(img, str(x), (int(scale * x) + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1)
    for y in range(0, 480, 20):
        cv2.line(img, (0, int(scale * y)), (img.shape[1], int(scale * y)), (0, 200, 255) if y % 100 == 0 else (0, 70, 0), 1)
        if y % 100 == 0: cv2.putText(img, str(y), (2, int(scale * y) + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1)
    cv2.imwrite(os.path.join(OUT, f'{stem}_rest_grid.png'), img)
    print('saved', stem)
