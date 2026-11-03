"""Do a visit's before- and after-exposure recordings show the same capillaries? (2026-11-03)

python analysis/fore_efter_fields/same_field.py [--videos <folder>] [--summary]

For aim 2 (the change from före to efter on the nicotine visit) it matters whether both recordings
film the same field. If the camera was placed anew after the exposure, each change compares
different capillaries.

For every recording, the mean image over its official rest (from `capillary.inventory`), band-passed
(difference of Gaussians, sigma 2 and 15 px; the stabilizer's black strips set to zero). The central
half (320 x 240) of one image is searched in the other by normalized cross-correlation
(`cv2.matchTemplate`), which allows shifts of up to 160 px across and 120 px down. Three kinds of
pair:

- `halves`: the first and second half of one rest. The same field, so a high score; a low one means
  the rest's mean image is blurred (the stabilizer lost the picture, or it changed).
- `same visit`: the före and efter recordings the aims use for one visit
  (`metadata/derived/participants.csv`), wherever both videos are in the folder.
- `different people`: före recordings of two different participants of one study, where nothing
  can match.

Writes scores.csv and, for each same-visit pair, out/<participant>_<visit>.png (both band-passed
mean images side by side, not tracked) to look at. The score alone does not settle it: look at the
pictures.
"""
import argparse
import itertools
import os
import sys
import unicodedata

import cv2
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
from capillary import aims, inventory  # noqa: E402
from capillary.video import iter_frames, probe_video  # noqa: E402

OUT = os.path.join(HERE, 'scores.csv')
PICTURES = os.path.join(HERE, 'out')
#: Below this score the two halves of one rest do not match: that recording's mean image is not reliable.
SHARP_HALVES = 0.9
#: At most this many different-people pairs per study.
MAX_CONTROLS = 12


def videos_by_name(folder: str) -> dict:
    """{NFC stem: path} of the .avi videos in `folder` (macOS stores names decomposed)."""
    out = {}
    for entry in sorted(os.listdir(folder)):
        if entry.endswith('.avi'):
            out[unicodedata.normalize('NFC', entry[:-4])] = os.path.join(folder, entry)
    return out


def rest_means(name: str, path: str):
    """The mean image of the official rest, and of its first and second half (float arrays)."""
    info = probe_video(path)
    phases = inventory.recording_phases(name, info.fps, info.frame_count)
    if phases is None or 'rest' not in phases.windows:
        return None
    first, last = phases.windows['rest']
    middle = (first + last) // 2
    sums = [np.zeros((info.height, info.width)), np.zeros((info.height, info.width))]
    counts = [0, 0]
    for offset, frame in enumerate(iter_frames(path, start=first, max_frames=last - first + 1)):
        half = 0 if first + offset <= middle else 1
        sums[half] += frame
        counts[half] += 1
    a, b = sums[0] / counts[0], sums[1] / counts[1]
    return (a * counts[0] + b * counts[1]) / sum(counts), a, b


def bandpass(image: np.ndarray) -> np.ndarray:
    image = image.astype(np.float32)
    out = cv2.GaussianBlur(image, (0, 0), 2) - cv2.GaussianBlur(image, (0, 0), 15)
    out[image < 5] = 0                       # the stabilizer's black strip must not drive the match
    return out


def match(first: np.ndarray, second: np.ndarray) -> tuple:
    """The best normalized cross-correlation of `first`'s central half within `second`, and the shift (x, y)."""
    a, b = bandpass(first), bandpass(second)
    h, w = a.shape
    template = a[h // 4: h // 4 + h // 2, w // 4: w // 4 + w // 2]
    _, best, _, where = cv2.minMaxLoc(cv2.matchTemplate(b, template, cv2.TM_CCOEFF_NORMED))
    return float(best), (where[0] - w // 4, where[1] - h // 4)


def picture(image: np.ndarray) -> np.ndarray:
    b = bandpass(image)
    lo, hi = np.percentile(b, [1, 99])
    return np.clip((b - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)


def visits(available: dict) -> list:
    """(study, subject, visit, före name, efter name) for every visit whose two chosen recordings are available."""
    people = pd.read_csv(os.path.join(inventory.METADATA, 'derived', 'participants.csv'))
    out = []
    for person in people.itertuples(index=False):
        for visit in ('active', 'control'):
            before, after = getattr(person, f'{visit}_före'), getattr(person, f'{visit}_efter')
            if isinstance(before, str) and isinstance(after, str):
                before, after = inventory.nfc(before), inventory.nfc(after)
                if before in available and after in available:
                    out.append((person.study, person.subject, visit, before, after))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--videos', default=None, help='the stabilized videos (default: StabilizedVideos/ of the data folder)')
    parser.add_argument('--summary', action='store_true', help='print the summary of the saved scores.csv')
    args = parser.parse_args()
    if not args.summary:
        folder = args.videos or os.path.join(aims.default_data_folder() or REPO, 'StabilizedVideos')
        available = videos_by_name(folder)
        wanted = visits(available)
        names = sorted({n for v in wanted for n in v[3:]})
        means = {}
        for name in names:
            result = rest_means(name, available[name])
            if result is not None:
                means[name] = result
                print(f'{name}: rest mean done', flush=True)
        rows = []
        for name, (_, a, b) in means.items():
            score, shift = match(a, b)
            rows.append({'kind': 'halves', 'first': name, 'second': name, 'score': score, 'shift': shift})
        os.makedirs(PICTURES, exist_ok=True)
        for study, subject, visit, before, after in wanted:
            if before in means and after in means:
                score, shift = match(means[before][0], means[after][0])
                rows.append({'kind': 'same visit', 'first': before, 'second': after, 'score': score, 'shift': shift})
                gap = np.full((means[before][0].shape[0], 8), 255, np.uint8)
                sheet = np.hstack([picture(means[before][0]), gap, picture(means[after][0])])
                cv2.imwrite(os.path.join(PICTURES, f'{study}_{subject}_{visit}.png'), sheet)
        subject = {v[3]: v[1] for v in wanted}
        for study in sorted({v[0] for v in wanted}):
            befores = [v[3] for v in wanted if v[0] == study and v[3] in means]
            pairs = [(x, y) for x, y in itertools.combinations(befores, 2) if subject[x] != subject[y]]
            for x, y in pairs[:MAX_CONTROLS]:
                score, shift = match(means[x][0], means[y][0])
                rows.append({'kind': 'different people', 'first': x, 'second': y, 'score': score, 'shift': shift})
        pd.DataFrame(rows).to_csv(OUT, index=False, float_format='%.4f')
    table = pd.read_csv(OUT)
    halves = table[table.kind == 'halves'].set_index('first').score
    blurred = set(halves[halves < SHARP_HALVES].index)
    print(f'halves of one rest: {len(halves)} recordings, median {halves.median():.2f}; below {SHARP_HALVES} '
          f'(mean image not reliable): {", ".join(sorted(blurred)) or "none"}')
    for kind in ('same visit', 'different people'):
        part = table[table.kind == kind]
        clean = part[~part['first'].isin(blurred) & ~part['second'].isin(blurred)]
        print(f'{kind}: {len(part)} pairs, {len(clean)} without an unreliable recording, scores '
              f'{clean.score.min():.2f}-{clean.score.max():.2f} (median {clean.score.median():.2f})')
        if kind == 'same visit':
            for row in part.itertuples(index=False):
                flag = ' (unreliable mean image)' if row.first in blurred or row.second in blurred else ''
                print(f'  {row.first} / {row.second}: {row.score:.2f}{flag}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
