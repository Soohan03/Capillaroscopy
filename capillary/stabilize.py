"""Translation-only stabilization of a recording, read from disk twice.

1. Every frame gets a sharpness score (`quality.calculate_blur`), and the 24
   sharpest frames are kept.
2. Registration works on a band-passed copy of each frame (difference of
   Gaussians, sigma 2 and 15 px): it removes pixel noise and the uneven
   lighting, which stays with the camera while the skin moves, and treats every
   part of the image alike.
3. Two references are made from the sharpest frames: each is the mean of every
   other one (12 frames), band-passed and moved onto the sharpest frame.
   Averaging smooths out the moving blood, which makes a single frame a noisy
   reference.
4. Each frame is located in both references by normalized cross-correlation:
   the frame's centre (all but 64 px at each edge) is compared at every
   whole-pixel offset up to 64 px, and a parabola through the best offset and
   its neighbours gives the fraction of a pixel. The frame's shift is the mean
   of the two results, after removing the fixed offset between the two
   references.
5. The original frame (not the band-passed one) is moved by that shift with
   bicubic interpolation, rounded to whole grey levels and written uncompressed
   as 8-bit grey. Edges the move uncovers are black.

The video is read once for the sharpness and once to register and write, so
memory stays at a few dozen frames whatever the length. Output frame k is
recorded frame k, losslessly.

History (all on 2026-10-08, see the DEVLOG):

- The original `Caper.VideoStabilization` held the whole video in memory twice
  as float64 (22–37 GB for the 2019 recordings), wrote MPEG-4 (lossy), and wrote
  every frame one frame late.
- It was first moved here unchanged: the same arithmetic, read from disk,
  lossless and in step.
- Its registration was then replaced by the one above. The old registration
  used CLAHE on a fixed 3 x 3 grid of tiles, a 7 x 7 median filter, upsampled
  circular cross-correlation (Guizar-Sicairos et al. 2008) against the three
  sharpest single frames, and bilinear interpolation. On FP01_Qföre its shift
  fell 3–5.6 px short where the image had moved 15–20 px, and the three
  references disagreed by a median 2–3.5 px.

Next to the stabilized video go the shift of every frame
(``<stem>___stabilization.csv``) and the settings and a summary
(``<stem>___stabilization_provenance.json``). The CSV's columns:

- ``frame``, ``time_s``: the frame and its time at the video's frame rate;
- ``shift_x_px``, ``shift_y_px``: how far the frame was moved (right and down
  positive). The image itself had moved by minus this, relative to the
  sharpest frame;
- ``match``: how well the frame matches the references where it was found
  (normalized cross-correlation, 0 to 1, the mean over the two). It falls when
  the picture changes, as during an occlusion (about 0.75 then on FP01_Qföre,
  0.92 at rest), and is low for a frame that was not found;
- ``disagreement_px``: how far apart the results against the two references
  were (the larger of x and y). Each reference is made from different frames,
  so this shows how much the shift depends on the reference: a large value
  marks a frame whose shift is unreliable;
- ``at_search_limit``: the best match lay at the edge of the search, so the
  image may have moved further than the search reaches (64 px) and the shift
  may be wrong. A frame that moved much further is usually found in a wrong
  place instead, with a low match;
- ``sharpness``: the score the reference frames were chosen by;
- ``reference``: whether the frame is one of those averaged into the references.

Run from the command line:

    python -m capillary.stabilize RecordedVideos/clip.avi --out StabilizedVideos/clip.avi
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Callable, Optional

import cv2
import numpy as np
import pandas as pd

from .datasets import SEPARATOR, software_version, write_provenance
from .measure import Cancelled
from .quality import calculate_blur
from .video import VideoInfo, iter_frames, probe_video

#: The band-pass the registration works on: fine noise below the first sigma and the
#: lighting above the second are removed (px).
BANDPASS_SIGMAS_PX = (2.0, 15.0)
#: The sharpest frames, averaged into two references of half as many each.
REFERENCE_FRAMES = 24
#: The largest movement from the references that can be measured (px); smaller in small frames.
SEARCH_PX = 64

#: Share of the progress bar for the first reading (sharpness); registering and writing take the rest.
SHARPNESS_SHARE = 0.1

ProgressCallback = Optional[Callable[[float, str], None]]
CancelCheck = Optional[Callable[[], bool]]


def enhance(frame: np.ndarray) -> np.ndarray:
    """The frame as the registration sees it: band-passed (difference of Gaussians), as float32."""
    image = frame.astype(np.float32)
    fine, coarse = BANDPASS_SIGMAS_PX
    return cv2.GaussianBlur(image, (0, 0), fine) - cv2.GaussianBlur(image, (0, 0), coarse)


def search_margin(height: int, width: int) -> int:
    """How far the search reaches in a frame of this size: `SEARCH_PX`, or a quarter of the frame if smaller."""
    return max(1, min(SEARCH_PX, min(height, width) // 4))


def _vertex(left: float, centre: float, right: float) -> float:
    """Where a parabola through three equally spaced values peaks, relative to the middle one."""
    curvature = left - 2 * centre + right
    return 0.0 if curvature >= 0 else float(0.5 * (left - right) / curvature)


def locate(enhanced: np.ndarray, reference: np.ndarray) -> tuple:
    """The shift (x, y) that moves `enhanced` onto `reference`, how well it matches there, and the edge flag.

    Both are band-passed images of the same size (`enhance`). The match is the
    normalized cross-correlation at the best offset (0 to 1). The flag is True
    when the best offset lies at the edge of the search, so the image may have
    moved further than the search reaches.
    """
    margin = search_margin(*enhanced.shape)
    scores = cv2.matchTemplate(reference, enhanced[margin:-margin, margin:-margin], cv2.TM_CCOEFF_NORMED)
    _, peak, _, (x, y) = cv2.minMaxLoc(scores)
    shift = np.array([x - margin, y - margin], dtype=float)
    inside_x, inside_y = 0 < x < scores.shape[1] - 1, 0 < y < scores.shape[0] - 1
    if inside_x:
        shift[0] += _vertex(scores[y, x - 1], scores[y, x], scores[y, x + 1])
    if inside_y:
        shift[1] += _vertex(scores[y - 1, x], scores[y, x], scores[y + 1, x])
    return shift, float(peak), not (inside_x and inside_y)


def _move(image: np.ndarray, shift) -> np.ndarray:
    height, width = image.shape
    matrix = np.float32([[1, 0, shift[0]], [0, 1, shift[1]]])
    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_CUBIC)


def build_references(sharpest: list) -> tuple:
    """The two references, from frames given sharpest first (see the module docstring).

    Returns the two band-passed references and the shift that moves the first
    onto the second.
    """
    anchor = enhance(sharpest[0])
    sums = [np.zeros_like(anchor), np.zeros_like(anchor)]
    counts = [0, 0]
    for rank, frame in enumerate(sharpest):
        enhanced = enhance(frame)
        shift, _, _ = locate(enhanced, anchor)
        sums[rank % 2] += _move(enhanced, shift)
        counts[rank % 2] += 1
    first = sums[0] / counts[0]
    second = sums[1] / counts[1] if counts[1] else first
    offset, _, _ = locate(first, second)
    return first, second, offset


def register(enhanced: np.ndarray, references: tuple) -> tuple:
    """The shift (x, y) that moves `enhanced` onto the first reference, the match, the disagreement and the edge flag.

    `references` is what `build_references` returns.
    """
    first, second, offset = references
    a, match_a, edge_a = locate(enhanced, first)
    b, match_b, edge_b = locate(enhanced, second)
    b = b - offset                       # onto the first reference, too
    return (a + b) / 2, (match_a + match_b) / 2, float(np.abs(a - b).max()), edge_a or edge_b


def shift_frame(frame: np.ndarray, shift) -> np.ndarray:
    """`frame` moved by `shift` = (x, y) pixels: bicubic, rounded to uint8, uncovered edges black."""
    height, width = frame.shape
    matrix = np.float32([[1, 0, shift[0]], [0, 1, shift[1]]])
    moved = cv2.warpAffine(frame.astype(np.float64), matrix, (width, height), flags=cv2.INTER_CUBIC)
    return np.clip(np.rint(moved), 0, 255).astype(np.uint8)


def output_bytes(info: VideoInfo) -> int:
    """About how large the stabilized video of `info` will be on disk (uncompressed 8-bit grey)."""
    return int(info.frame_count * info.width * info.height * 1.01) + 1_000_000


@dataclass
class Stabilization:
    """What `stabilize_video` did: one row per frame (see the module docstring) and the video's properties."""

    source: str
    output: str
    fps: float
    width: int
    height: int
    references: list            # frame numbers of the frames averaged into the references, sharpest first
    frames: pd.DataFrame

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    def summary(self) -> dict:
        """How much the recording moved and how sure the registration was."""
        shifts = self.frames[['shift_x_px', 'shift_y_px']].to_numpy()
        jumps = np.hypot(*np.diff(shifts, axis=0).T) if len(shifts) > 1 else np.zeros(1)
        disagreement = self.frames['disagreement_px'].to_numpy()
        match = self.frames['match'].to_numpy()
        return {'movement_range_x_px': float(np.ptp(shifts[:, 0])),
                'movement_range_y_px': float(np.ptp(shifts[:, 1])),
                'largest_jump_between_frames_px': float(jumps.max()),
                'median_match': float(np.median(match)),
                'lowest_match': float(match.min()),
                'median_disagreement_px': float(np.median(disagreement)),
                'largest_disagreement_px': float(disagreement.max()),
                'frames_disagreeing_over_1px': int(np.sum(disagreement > 1.0)),
                'frames_at_search_limit': int(self.frames['at_search_limit'].sum())}


def _report(progress: ProgressCallback, fraction: float, stage: str) -> None:
    if progress is not None:
        progress(min(max(fraction, 0.0), 1.0), stage)


def _check(should_cancel: CancelCheck) -> None:
    if should_cancel is not None and should_cancel():
        raise Cancelled()


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def stabilize_video(source: str, output: str, *, progress: ProgressCallback = None,
                    should_cancel: CancelCheck = None) -> Stabilization:
    """Stabilize `source` into `output` (an ``.avi``); see the module docstring.

    The output has the source's frames, size and frame rate. `progress` is
    called with (fraction done, stage); `should_cancel` returning True raises
    `Cancelled`. On any failure the partly written output is removed. The
    shifts are returned, not saved; `save_record` writes them next to a video.
    """
    if os.path.splitext(output)[1].lower() != '.avi':
        raise ValueError(f'the stabilized video must be an .avi file, not {os.path.basename(output)}')
    info = probe_video(source)
    expected = max(info.frame_count, 1)

    # first reading: the sharpness of every frame, keeping the sharpest ones
    sharpness, best = [], []          # best: (score, frame number, frame), sharpest first
    for number, frame in enumerate(iter_frames(source)):
        if number % 25 == 0:
            _check(should_cancel)
            _report(progress, SHARPNESS_SHARE * number / expected, 'Scoring sharpness')
        score = float(calculate_blur(frame))
        sharpness.append(score)
        if len(best) < REFERENCE_FRAMES or score > best[-1][0]:
            best.append((score, number, frame.copy()))
            best.sort(key=lambda item: (-item[0], item[1]))
            del best[REFERENCE_FRAMES:]
    if not sharpness:
        raise ValueError(f'no frames could be read from {source}')
    count = len(sharpness)
    height, width = best[0][2].shape
    references = [number for _, number, _ in best]
    reference_images = build_references([frame for _, _, frame in best])
    del best

    # second reading: register each frame, move it and write it
    writer = cv2.VideoWriter(output, 0, info.fps, (width, height), isColor=False)
    if not writer.isOpened():
        writer.release()
        raise OSError(f'cannot write an uncompressed video to {output}')
    shifts = np.full((count, 2), np.nan)
    match = np.full(count, np.nan)
    disagreement = np.full(count, np.nan)
    at_limit = np.zeros(count, dtype=bool)
    written = 0
    try:
        for number, frame in enumerate(iter_frames(source, max_frames=count)):
            _check(should_cancel)
            if number % 25 == 0:
                _report(progress, SHARPNESS_SHARE + (1 - SHARPNESS_SHARE) * number / count,
                        'Aligning and writing frames')
            shifts[number], match[number], disagreement[number], at_limit[number] = register(
                enhance(frame), reference_images)
            writer.write(shift_frame(frame, shifts[number]))
            written += 1
        writer.release()
        if written != count:
            raise OSError(f'{source} gave {count} frames on the first reading but {written} on the second')
    except BaseException:
        writer.release()
        _remove(output)
        raise
    _report(progress, 1.0, 'Aligning and writing frames')

    numbers = np.arange(count)
    frames = pd.DataFrame({'frame': numbers, 'time_s': numbers / info.fps,
                           'shift_x_px': shifts[:, 0], 'shift_y_px': shifts[:, 1],
                           'match': match, 'disagreement_px': disagreement, 'at_search_limit': at_limit,
                           'sharpness': sharpness, 'reference': np.isin(numbers, references)})
    return Stabilization(source=source, output=output, fps=info.fps, width=width, height=height,
                         references=references, frames=frames)


# ---------------------------------------------------------------------------- record

def record_paths(video_path: str) -> dict:
    """The files kept next to a stabilized video: the shift of every frame, and the provenance."""
    base = os.path.splitext(video_path)[0]
    return {'shifts': f'{base}{SEPARATOR}stabilization.csv',
            'provenance': f'{base}{SEPARATOR}stabilization_provenance.json'}


def save_record(result: Stabilization, video_path: Optional[str] = None) -> dict:
    """Write the shifts and the provenance next to `video_path` (default: the output); returns their paths."""
    paths = record_paths(video_path or result.output)
    result.frames.to_csv(paths['shifts'], index=False)
    half = REFERENCE_FRAMES // 2
    write_provenance(paths['provenance'], {
        'source_video': os.path.basename(result.source),
        'frames': result.frame_count,
        'fps': result.fps,
        'width': result.width,
        'height': result.height,
        'method': {
            'movement': 'translation only, one shift per frame',
            'reference_frames': result.references,
            'references': f'two, each the mean of every other one of the {REFERENCE_FRAMES} sharpest frames '
                          f'({half} each; capillary.quality.calculate_blur), moved onto the sharpest',
            'enhancement_for_registration': {'band_pass': 'difference of Gaussians',
                                             'sigmas_px': list(BANDPASS_SIGMAS_PX)},
            'registration': f'normalized cross-correlation of the frame\'s centre at every whole-pixel offset up to '
                            f'{search_margin(result.height, result.width)} px, refined by a parabola through the '
                            'peak; the mean over the two references',
            'output': 'original frames moved with bicubic interpolation, rounded, uncompressed 8-bit grey AVI; '
                      'uncovered edges black',
        },
        'summary': result.summary(),
        'software': software_version(),
    })
    return paths


# ------------------------------------------------------------------------------- CLI

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='python -m capillary.stabilize',
                                     description='Stabilize a recording (see capillary/stabilize.py).')
    parser.add_argument('video', help='the recording to stabilize')
    parser.add_argument('--out', required=True, help='the stabilized video to write (.avi)')
    args = parser.parse_args(argv)

    folder, name = os.path.split(os.path.abspath(args.out))
    os.makedirs(folder, exist_ok=True)
    partial = os.path.join(folder, f'.{name}')          # hidden until complete

    def show(fraction, stage):
        print(f'\r{stage}: {fraction:4.0%}', end='', file=sys.stderr, flush=True)

    try:
        result = stabilize_video(args.video, partial, progress=show)
        partial_records = save_record(result)
    except Exception:
        for path in [partial, *record_paths(partial).values()]:
            _remove(path)
        raise
    print(file=sys.stderr)
    final_records = record_paths(os.path.join(folder, name))
    os.replace(partial, os.path.join(folder, name))
    for key, path in partial_records.items():
        os.replace(path, final_records[key])

    summary = result.summary()
    print(f'{args.video} -> {args.out}')
    print(f'  {result.frame_count} frames, {result.width}x{result.height} @ {result.fps:g} fps; '
          f'{len(result.references)} reference frames, the sharpest {result.references[0]}')
    print(f'  moved over {summary["movement_range_x_px"]:.1f} x {summary["movement_range_y_px"]:.1f} px, '
          f'largest jump {summary["largest_jump_between_frames_px"]:.1f} px; the references disagree by a median '
          f'{summary["median_disagreement_px"]:.2f} px, over 1 px on {summary["frames_disagreeing_over_1px"]} frames')
    print(f'  match with the references: median {summary["median_match"]:.2f}, lowest {summary["lowest_match"]:.2f}')
    if summary['frames_at_search_limit']:
        print(f'  WARNING: on {summary["frames_at_search_limit"]} frames the image may have moved further than the '
              'search reaches; check their shifts')
    print(f'  shifts: {final_records["shifts"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
