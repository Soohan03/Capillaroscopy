"""Translation-only stabilization of a recording, read from disk three times.

1. Every frame gets a sharpness score (`quality.calculate_blur`). The
   sharpest frame and the 12 frames on each side of it are kept.
2. Registration works on a band-passed copy of each frame (difference of
   Gaussians, sigma 2 and 15 px): it removes pixel noise and the uneven
   lighting, which stays with the camera while the skin moves, and treats every
   part of the image alike.
3. Two references are made from those 25 frames: each is the mean of every
   other one, band-passed and moved onto the sharpest frame. Averaging smooths
   out the moving blood, which makes a single frame a noisy reference.
   - Neighbouring frames lie close together, so each is aligned with the
     previous frame's position as a guide (see step 4).
   - A frame is left out unless aligning it onto the sharpest frame and the
     sharpest frame onto it give opposite shifts, to within 1 px. A false match
     would otherwise be averaged into the reference.
4. Each frame is found in both references in two steps.
   - A coarse search on frames made 4 times smaller reaches about a third of
     the frame (±160 px in a 640 x 480 recording).
   - A fine search by normalized cross-correlation then looks within 12 px of
     two candidates, the coarse result and the previous frame's position, and
     keeps the better match. A parabola through the best offset and its
     neighbours gives the fraction of a pixel.
   - Following the previous frame lets the search track a recording that moves
     further than the coarse search reaches; FP03_Wföre swings by about 200 px
     with each breath. The coarse result finds the frame again if the previous
     one was lost.
   - The fine search compares the largest part of the frame that stays inside
     the reference.
   - The frame's shift is the mean of the two references' results, after
     removing the fixed offset between the two references.
5. The shifts are measured from the sharpest frame, which may lie far from
   where the recording usually is. They are re-centred on their median, so the
   stabilized picture sits where the recording spends most of its time and
   loses as little as possible at its edges.
6. The original frame (not the band-passed one) is moved by its shift with
   bicubic interpolation, rounded to whole grey levels and written uncompressed
   as 8-bit grey. Edges the move uncovers are black.

The video is read three times: for the sharpness, to register, and to write.
Memory stays at a few dozen frames whatever the length. Output frame k is
recorded frame k, losslessly.

History (all on 2026-10-08, see the DEVLOG):

- The original `Caper.VideoStabilization` held the whole video in memory twice
  as float64 (22–37 GB for the 2019 recordings), wrote MPEG-4 (lossy), and wrote
  every frame one frame late.
- It was first moved here unchanged: the same arithmetic, read from disk,
  lossless and in step.
- Its registration was then replaced. The old one used CLAHE on a fixed 3 x 3
  grid of tiles, a 7 x 7 median filter, upsampled circular cross-correlation
  (Guizar-Sicairos et al. 2008) against the three sharpest single frames, and
  bilinear interpolation. On FP01_Qföre its shift fell 3–5.6 px short where the
  image had moved 15–20 px, and the three references disagreed by a median of
  2–3.5 px.
- A first version of the new registration searched only ±64 px from the
  references and did not re-centre. It lost most frames of FP03_Wföre.

Next to the stabilized video go the shift of every frame
(``<stem>___stabilization.csv``) and the settings and a summary
(``<stem>___stabilization_provenance.json``). The CSV's columns:

- ``frame``, ``time_s``: the frame and its time at the video's frame rate;
- ``shift_x_px``, ``shift_y_px``: how far the frame was moved (right and down
  positive). The image itself had moved by minus this from the recording's
  median position;
- ``match``: how well the frame matches the references where it was found
  (normalized cross-correlation, 0 to 1, the mean over the two). It falls when
  the picture changes. On FP01_Qföre it is about 0.92 at rest and 0.75 during
  the occlusion; a frame that was not found has a low match;
- ``disagreement_px``: how far apart the results against the two references
  were (the larger of x and y). Each reference is made from different frames,
  so this shows how much the shift depends on the reference: a large value
  marks a frame whose shift is unreliable;
- ``at_search_limit``: the best match lay at the edge of the fine search, or
  too little of the frame overlapped the reference to search, so the shift may
  be wrong;
- ``sharpness``: the score the reference frames were chosen by;
- ``reference``: whether the frame was averaged into the references.

Run from the command line:

    python -m capillary.stabilize RecordedVideos/clip.avi --out StabilizedVideos/clip.avi
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import deque
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
#: The frames on each side of the sharpest one that are averaged into the references with it.
REFERENCE_NEIGHBOURS = 12
#: How many times smaller the frames are for the coarse search, which then reaches a third of the frame.
#: Small frames are reduced less.
COARSE_REDUCTION = 4
#: How far the fine search looks around each candidate position (px).
FINE_REACH_PX = 12

#: Shares of the progress bar for the three readings: sharpness, registration, writing.
PROGRESS_SHARES = (0.1, 0.75, 0.15)

ProgressCallback = Optional[Callable[[float, str], None]]
CancelCheck = Optional[Callable[[], bool]]


def enhance(frame: np.ndarray) -> np.ndarray:
    """The frame as the registration sees it: band-passed (difference of Gaussians), as float32."""
    image = frame.astype(np.float32)
    fine, coarse = BANDPASS_SIGMAS_PX
    return cv2.GaussianBlur(image, (0, 0), fine) - cv2.GaussianBlur(image, (0, 0), coarse)


def _vertex(left: float, centre: float, right: float) -> float:
    """Where a parabola through three equally spaced values peaks, relative to the middle one."""
    curvature = left - 2 * centre + right
    return 0.0 if curvature >= 0 else float(0.5 * (left - right) / curvature)


def _search(enhanced: np.ndarray, reference: np.ndarray, around, reach: int) -> tuple:
    """Normalized cross-correlation at every whole-pixel shift within `reach` of `around`.

    It compares the largest part of `enhanced` that stays inside `reference`
    under all those shifts. Returns the best shift (to a fraction of a pixel),
    its match, and whether it lies at the edge of the search; the last is also
    True when too little of the frame overlaps the reference to search.
    """
    height, width = enhanced.shape
    ax, ay = int(round(around[0])), int(round(around[1]))
    x0, x1 = max(0, reach - ax), min(width, width - reach - ax)
    y0, y1 = max(0, reach - ay), min(height, height - reach - ay)
    if x1 - x0 < width // 4 or y1 - y0 < height // 4:
        return np.array([ax, ay], dtype=float), 0.0, True
    window = reference[y0 + ay - reach:y1 + ay + reach, x0 + ax - reach:x1 + ax + reach]
    scores = cv2.matchTemplate(window, enhanced[y0:y1, x0:x1], cv2.TM_CCOEFF_NORMED)
    _, peak, _, (x, y) = cv2.minMaxLoc(scores)
    shift = np.array([ax - reach + x, ay - reach + y], dtype=float)
    inside_x, inside_y = 0 < x < scores.shape[1] - 1, 0 < y < scores.shape[0] - 1
    if inside_x:
        shift[0] += _vertex(scores[y, x - 1], scores[y, x], scores[y, x + 1])
    if inside_y:
        shift[1] += _vertex(scores[y - 1, x], scores[y, x], scores[y + 1, x])
    return shift, float(peak), not (inside_x and inside_y)


def coarse_shift(enhanced: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """A first guess of the shift from reduced frames, reaching about a third of the frame."""
    height, width = enhanced.shape
    reduction = max(1, min(COARSE_REDUCTION, min(height, width) // 120))
    if reduction > 1:
        size = (width // reduction, height // reduction)
        enhanced = cv2.resize(enhanced, size, interpolation=cv2.INTER_AREA)
        reference = cv2.resize(reference, size, interpolation=cv2.INTER_AREA)
    shift, _, _ = _search(enhanced, reference, (0, 0), min(enhanced.shape) // 3)
    return shift * reduction


def locate(enhanced: np.ndarray, reference: np.ndarray, previous=None) -> tuple:
    """The shift (x, y) that moves `enhanced` onto `reference`, how well it matches there, and the edge flag.

    Both are band-passed images of the same size (`enhance`). The fine search
    runs around the coarse guess and around `previous` (the previous frame's
    shift, if given) and keeps the better match (normalized cross-correlation,
    0 to 1); a match inside its search beats one at the edge, which may lie
    outside it. The flag is True when the kept match lies at the edge.
    """
    candidates = [coarse_shift(enhanced, reference)]
    if previous is not None and np.abs(np.asarray(previous, dtype=float) - candidates[0]).max() > FINE_REACH_PX / 2:
        candidates.append(np.asarray(previous, dtype=float))
    return max((_search(enhanced, reference, candidate, FINE_REACH_PX) for candidate in candidates),
               key=lambda result: (not result[2], result[1]))


def _move(image: np.ndarray, shift) -> np.ndarray:
    height, width = image.shape
    matrix = np.float32([[1, 0, shift[0]], [0, 1, shift[1]]])
    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_CUBIC)


def build_references(frames: list, sharpest: int) -> tuple:
    """The two references, from consecutive frames of which `sharpest` (an index) is the sharpest.

    See the module docstring. Returns the references for `register` (the two
    band-passed references and the shift that moves the first onto the
    second), and the indices of the frames used.
    """
    enhanced = [enhance(frame) for frame in frames]
    anchor = enhanced[sharpest]
    shifts = {sharpest: np.zeros(2)}
    for step in (1, -1):                         # outwards from the sharpest frame, following the movement
        previous, index = np.zeros(2), sharpest + step
        while 0 <= index < len(frames):
            shift, _, at_edge = locate(enhanced[index], anchor, previous)
            back, _, back_at_edge = locate(anchor, enhanced[index], -shift)
            if not (at_edge or back_at_edge) and np.abs(shift + back).max() < 1.0:
                shifts[index] = previous = shift
            index += step
    used = sorted(shifts)
    groups = ([], [])
    for index in used:
        groups[(index - sharpest) % 2].append(_move(enhanced[index], shifts[index]))
    first = np.mean(groups[0], axis=0)
    second = np.mean(groups[1], axis=0) if groups[1] else first
    offset, _, _ = locate(first, second)
    return (first, second, offset), used


def register(enhanced: np.ndarray, references: tuple, previous=None) -> tuple:
    """The shift (x, y) that moves `enhanced` onto the first reference, the match, the disagreement and the edge flag.

    `references` is what `build_references` returns; `previous` is the shift
    `register` gave the frame before, if any.
    """
    first, second, offset = references
    a, match_a, edge_a = locate(enhanced, first, previous)
    b, match_b, edge_b = locate(enhanced, second, None if previous is None else np.asarray(previous) + offset)
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
    sharpest: int               # frame number of the sharpest frame, the references' position
    references: list            # frame numbers of the frames averaged into the references
    frames: pd.DataFrame
    centre: tuple = (0.0, 0.0)  # the median shift from the sharpest frame, taken off every shift

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

    sharpness_share, register_share, _ = PROGRESS_SHARES

    # first reading: the sharpness of every frame, keeping the sharpest one and its neighbours
    sharpness, before, window = [], deque(maxlen=REFERENCE_NEIGHBOURS), []
    best_score, sharpest, still_to_keep = -np.inf, 0, 0
    for number, frame in enumerate(iter_frames(source)):
        if number % 25 == 0:
            _check(should_cancel)
            _report(progress, sharpness_share * number / expected, 'Scoring sharpness')
        score = float(calculate_blur(frame))
        sharpness.append(score)
        frame = frame.copy()
        if score > best_score:
            best_score, window = score, list(before) + [(number, frame)]
            sharpest, still_to_keep = len(window) - 1, REFERENCE_NEIGHBOURS
        elif still_to_keep:
            window.append((number, frame))
            still_to_keep -= 1
        before.append((number, frame))
    if not sharpness:
        raise ValueError(f'no frames could be read from {source}')
    count = len(sharpness)
    height, width = window[sharpest][1].shape
    reference_images, used = build_references([frame for _, frame in window], sharpest)
    references = [window[index][0] for index in used]
    sharpest = window[sharpest][0]
    del before, window

    # second reading: register every frame, following the one before
    shifts = np.full((count, 2), np.nan)
    match = np.full(count, np.nan)
    disagreement = np.full(count, np.nan)
    at_limit = np.zeros(count, dtype=bool)
    previous = None
    registered = 0
    for number, frame in enumerate(iter_frames(source, max_frames=count)):
        _check(should_cancel)
        if number % 25 == 0:
            _report(progress, sharpness_share + register_share * number / count, 'Aligning frames')
        shifts[number], match[number], disagreement[number], at_limit[number] = register(
            enhance(frame), reference_images, previous)
        previous = shifts[number]
        registered += 1
    if registered != count:
        raise OSError(f'{source} gave {count} frames on the first reading but {registered} on the second')
    centre = np.median(shifts, axis=0)
    shifts -= centre

    # third reading: move every frame and write it
    writer = cv2.VideoWriter(output, 0, info.fps, (width, height), isColor=False)
    if not writer.isOpened():
        writer.release()
        raise OSError(f'cannot write an uncompressed video to {output}')
    written = 0
    try:
        for number, frame in enumerate(iter_frames(source, max_frames=count)):
            _check(should_cancel)
            if number % 25 == 0:
                _report(progress, sharpness_share + register_share + (1 - sharpness_share - register_share)
                        * number / count, 'Writing the stabilized video')
            writer.write(shift_frame(frame, shifts[number]))
            written += 1
        writer.release()
        if written != count:
            raise OSError(f'{source} gave {count} frames on the first reading but {written} on the third')
    except BaseException:
        writer.release()
        _remove(output)
        raise
    _report(progress, 1.0, 'Writing the stabilized video')

    numbers = np.arange(count)
    frames = pd.DataFrame({'frame': numbers, 'time_s': numbers / info.fps,
                           'shift_x_px': shifts[:, 0], 'shift_y_px': shifts[:, 1],
                           'match': match, 'disagreement_px': disagreement, 'at_search_limit': at_limit,
                           'sharpness': sharpness, 'reference': np.isin(numbers, references)})
    return Stabilization(source=source, output=output, fps=info.fps, width=width, height=height,
                         sharpest=sharpest, references=references, frames=frames,
                         centre=(float(centre[0]), float(centre[1])))


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
    write_provenance(paths['provenance'], {
        'source_video': os.path.basename(result.source),
        'frames': result.frame_count,
        'fps': result.fps,
        'width': result.width,
        'height': result.height,
        'method': {
            'movement': 'translation only, one shift per frame',
            'sharpest_frame': result.sharpest,
            'reference_frames': result.references,
            'references': f'two, each the mean of every other one of the sharpest frame '
                          f'(capillary.quality.calculate_blur) and the {REFERENCE_NEIGHBOURS} frames on each side, '
                          'moved onto the sharpest; frames whose alignment failed a forward-backward check '
                          '(1 px) left out',
            'enhancement_for_registration': {'band_pass': 'difference of Gaussians',
                                             'sigmas_px': list(BANDPASS_SIGMAS_PX)},
            'registration': f'a coarse search on frames reduced up to {COARSE_REDUCTION} times, reaching a third '
                            f'of the frame; then normalized cross-correlation within {FINE_REACH_PX} px of the '
                            'coarse result and of the previous frame\'s position, the better match kept, refined '
                            'by a parabola through the peak; the mean over the two references',
            'recentred_by_px': list(result.centre),
            'output': 'original frames moved with bicubic interpolation, rounded, uncompressed 8-bit grey AVI; '
                      'uncovered edges black; shifts measured from the sharpest frame and re-centred on their '
                      'median',
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
          f'references from {len(result.references)} frames around the sharpest, {result.sharpest}')
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
