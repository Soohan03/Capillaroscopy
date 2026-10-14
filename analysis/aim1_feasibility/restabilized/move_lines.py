"""Move the first run's lines onto the re-stabilized videos, and check that each still lies on its vessel.

python analysis/aim1_feasibility/restabilized/move_lines.py      (about a minute)

On 2026-10-14 every stabilized video was made again by the new stabilizer, which
centres a video on its median shift over the official rest. So the picture of
each recording moved, by the same amount in every frame (DEVLOG 2026-10-14). The
stabilizer writes how far it moved each frame (`shift_x_px`, `shift_y_px` in
`<video>___stabilization.csv`): what the raw frame shows at p, the stabilized
frame shows at p + shift. A point of the old video is therefore at
p + (new shift - old shift) in the new one, and a line placed on the old resting
image moves by the median of that difference over the official rest.

1. **The move of each recording:** that median, from the new shift file and the
   old one (in .trash/, where the old videos went when they were made again),
   and how far single frames of the rest lie from it (where the stabilizer's
   references changed, old and new place some frames differently).
2. **A check of the move:** the old and new resting images (../out/ and out/,
   `rest_image.py`) registered onto each other by phase correlation.
3. **The moved lines:** every point of ../lines.json moved by its recording's
   move. Recordings in lines.json that the first run did not have (FP01_W,
   placed on the new video) are kept as they are.
4. **Whether each line still lies on its vessel:** the lines traced on the new
   resting image (`measure.traced_lines`) against the first run's traced lines
   (../results.csv) moved the same way: the mean and largest distance between
   them, and the ridge value of each (`on_ridge`, 0-1).

Writes moves.csv (one row per recording), line_check.csv (one row per line),
lines.json, and out/<recording>_lines.png.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common  # noqa: E402
import measure  # noqa: E402
from capillary import inventory  # noqa: E402
from capillary.spacetime import Centreline  # noqa: E402

FIRST_RUN = common.HERE
TRASH = os.path.join(common.REPO, '.trash')
#: The old videos were moved to .trash/ by the re-stabilization of this day (one folder per recording).
REMADE_ON = '2026-10-14'
#: The resting images are registered without this margin (px), where uncovered frame edges lie.
REGISTER_MARGIN_PX = 40


def shift_file(folder: str, stem: str) -> str:
    """The shift file of `stem`'s stabilized video in `folder`, however the name is spelled on disk."""
    for path in glob.glob(os.path.join(folder, '*___stabilization.csv')):
        if inventory.nfc(os.path.basename(path)[:-len('___stabilization.csv')]) == inventory.nfc(stem):
            return path
    raise FileNotFoundError(f'no shift file of {stem} in {folder}')


def old_shift_file(stem: str) -> str:
    """The shift file of the video `stem` had before it was made again (in .trash/)."""
    folders = sorted(path for path in glob.glob(os.path.join(TRASH, f'{REMADE_ON}_*previous stabilized video'))
                     if inventory.nfc(stem) in inventory.nfc(os.path.basename(path)))
    if len(folders) != 1:
        raise FileNotFoundError(f'{stem}: {len(folders)} folders of its previous video in .trash/')
    return shift_file(os.path.join(folders[0], 'StabilizedVideos'), stem)


def move_from_shifts(stem: str) -> dict:
    """How far the picture of `stem` moved at rest (new shift - old shift), and the spread over the rest frames."""
    _, (first, last) = common.rest_window(stem)
    new = pd.read_csv(shift_file(common.VIDEOS, stem), index_col='frame')
    old = pd.read_csv(old_shift_file(stem), index_col='frame')
    rest = range(first, last + 1)
    difference = (new.loc[rest, ['shift_x_px', 'shift_y_px']].to_numpy()
                  - old.loc[rest, ['shift_x_px', 'shift_y_px']].to_numpy())
    move = np.median(difference, axis=0)
    off = np.hypot(*(difference - move).T)
    return {'move_x_px': move[0], 'move_y_px': move[1], 'move_px': float(np.hypot(*move)),
            'frames_off_median_px': float(np.median(off)), 'frames_off_95th_px': float(np.percentile(off, 95)),
            'frames_off_max_px': float(off.max()), 'frames_off_over_2px': int((off > 2).sum()),
            'rest_frames': len(rest),
            'old_rest_match': float(np.median(old.loc[rest, 'match'])),
            'new_rest_match': float(np.median(new.loc[rest, 'match']))}


def move_from_images(stem: str) -> dict:
    """How far the picture of `stem` moved, from its old and new resting images (phase correlation)."""
    images = []
    for folder in (FIRST_RUN, HERE):
        mean = np.load(os.path.join(folder, 'out', f'{stem}_rest_mean.npy'))
        m = REGISTER_MARGIN_PX
        images.append(common.vessel_image(mean)[m:-m, m:-m].astype(np.float32))
    window = cv2.createHanningWindow(images[0].shape[::-1], cv2.CV_32F)
    (dx, dy), peak = cv2.phaseCorrelate(images[0], images[1], window)
    return {'image_move_x_px': dx, 'image_move_y_px': dy, 'image_peak': peak}


def moved(specs: dict, move) -> dict:
    """`specs` (a recording's lines) with every point moved by `move` (x, y)."""
    out = {}
    for name, spec in specs.items():
        out[name] = dict(spec)
        out[name]['points'] = [[round(x + move[0], 1), round(y + move[1], 1)] for x, y in spec['points']]
    return out


def apart(points_a, points_b) -> tuple:
    """The mean and largest distance (px) between the lines through two sets of points, the larger either way."""
    a = Centreline.from_points(points_a).sample_positions(0.5)[0]
    b = Centreline.from_points(points_b).sample_positions(0.5)[0]
    distances = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=-1))
    one, other = distances.min(axis=1), distances.min(axis=0)
    return max(one.mean(), other.mean()), max(one.max(), other.max())


def main() -> None:
    with open(common.LINES, encoding='utf-8') as handle:
        first_lines = json.load(handle)
    first_results = pd.read_csv(common.RESULTS)
    common.use('restabilized')
    kept = {}
    if os.path.exists(common.LINES):
        with open(common.LINES, encoding='utf-8') as handle:
            kept = {stem: specs for stem, specs in json.load(handle).items() if stem not in first_lines}

    moves, checks, lines = [], [], {}
    for stem, specs in first_lines.items():
        row = {'recording': stem, **move_from_shifts(stem), **move_from_images(stem)}
        row['image_minus_shifts_px'] = float(np.hypot(row['image_move_x_px'] - row['move_x_px'],
                                                      row['image_move_y_px'] - row['move_y_px']))
        moves.append(row)
        move = (row['move_x_px'], row['move_y_px'])
        lines[stem] = moved(specs, move)
        traced, on_ridge = measure.traced_lines(stem, lines[stem])
        before = first_results[first_results['recording'] == stem].set_index('line')
        for name, line in traced.items():
            old = [[float(v) for v in point.split(',')] for point in before.loc[name, 'points'].split(';')]
            old = [[x + move[0], y + move[1]] for x, y in old]
            mean_apart, most_apart = apart(line.points, old)
            checks.append({'recording': stem, 'line': name, 'kind': specs[name]['kind'],
                           'length_px': round(line.length_px, 1), 'old_length_px': before.loc[name, 'length_px'],
                           'mean_apart_px': round(mean_apart, 2), 'most_apart_px': round(most_apart, 2),
                           'on_ridge': round(on_ridge[name], 2), 'old_on_ridge': before.loc[name, 'on_ridge']})
        print(f"{stem}: moved {move[0]:+.1f}, {move[1]:+.1f} px (images {row['image_move_x_px']:+.1f}, "
              f"{row['image_move_y_px']:+.1f}); rest frames off the median by {row['frames_off_median_px']:.2f} px "
              f"(95th {row['frames_off_95th_px']:.2f}); match at rest {row['old_rest_match']:.2f} -> "
              f"{row['new_rest_match']:.2f}", flush=True)

    lines.update(kept)
    with open(common.LINES, 'w', encoding='utf-8') as handle:
        json.dump(lines, handle, ensure_ascii=False, indent=1)
    pd.DataFrame(moves).round(3).to_csv(os.path.join(HERE, 'moves.csv'), index=False)
    checks = pd.DataFrame(checks)
    checks.to_csv(os.path.join(HERE, 'line_check.csv'), index=False)
    limbs = checks[checks['kind'] == 'limb']
    print(f"\n{len(limbs)} limbs: traced within a mean 1 px of the old line {int((limbs['mean_apart_px'] <= 1).sum())}, "
          f"1-2 px {int(((limbs['mean_apart_px'] > 1) & (limbs['mean_apart_px'] <= 2)).sum())}, "
          f"more {int((limbs['mean_apart_px'] > 2).sum())}; ridge value new - old: median "
          f"{(limbs['on_ridge'] - limbs['old_on_ridge']).median():+.2f}")
    pd.set_option('display.width', 200)
    print(limbs.sort_values('mean_apart_px', ascending=False).head(15).to_string(index=False))


if __name__ == '__main__':
    main()
