"""Translation-only stabilization of a recording, read from disk twice.

The method is the one the app has always used (it was `Caper.VideoStabilization`
until 2026-10-08):

1. Every frame gets a sharpness score (`quality.calculate_blur`); the three
   sharpest frames are the references.
2. Each frame and each reference is enhanced for the registration only: CLAHE
   (clip limit 7.65, 3 x 3 tiles), then a 7 x 7 median filter. The frame is
   registered against each reference to 1/100 pixel by upsampled
   cross-correlation (Guizar-Sicairos, Thurman & Fienup 2008,
   `capillary.registration`), and its shift is the mean over the references.
3. The original frame (not the enhanced one) is moved by that shift with
   bilinear interpolation, rounded to whole grey levels and written
   uncompressed as 8-bit grey. Edges the move uncovers are black.

How it runs changed on 2026-10-08. The old code held the whole video in memory
twice as float64 (22-37 GB for the 2019 recordings), wrote MPEG-4 (lossy), and
wrote every frame one frame late (frame 0 black, the last frame dropped). Here
the video is read once for the sharpness and once to register and write, so
memory stays at a few frames whatever the length; output frame k is recorded
frame k, losslessly.

Next to the stabilized video go the shift of every frame
(``<stem>___stabilization.csv``) and the settings and a summary
(``<stem>___stabilization_provenance.json``). The CSV's columns:

- ``frame``, ``time_s``: the frame and its time at the video's frame rate;
- ``shift_x_px``, ``shift_y_px``: how far the frame was moved (right and down
  positive). The image itself had moved by minus this, relative to the
  references;
- ``disagreement_px``: how far apart the references' estimates were, after
  removing the offsets between the references themselves (the larger of x and
  y). A large value marks a frame whose shift is unreliable; on FP01_Qföre it
  grows during the occlusion, where the shift is several pixels short (see the
  2026-10-08 DEVLOG entry);
- ``sharpness``: the score the references were chosen by;
- ``reference``: whether the frame is one of the references.

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

from . import registration
from .datasets import SEPARATOR, software_version, write_provenance
from .measure import Cancelled
from .quality import calculate_blur
from .video import VideoInfo, iter_frames, probe_video

#: Registration settings, unchanged from the original stabilizer.
CLAHE_CLIP_LIMIT = 7.65
CLAHE_TILES = (3, 3)
MEDIAN_KERNEL = 7
UPSAMPLING = 100                 # register to 1/100 pixel
REFERENCE_FRAMES = 3

#: Share of the progress bar for the first reading (sharpness); registering and writing take the rest.
SHARPNESS_SHARE = 0.1

ProgressCallback = Optional[Callable[[float, str], None]]
CancelCheck = Optional[Callable[[], bool]]


def enhance(frame: np.ndarray) -> np.ndarray:
    """The frame as the registration sees it: CLAHE, then a 7 x 7 median filter with zero-padded edges.

    Equal to ``scipy.signal.medfilt(clahe(frame), [7, 7])``, the filter used
    before 2026-10-08, but much faster.
    """
    contrast = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILES).apply(frame.astype(np.uint8))
    pad = MEDIAN_KERNEL // 2
    padded = cv2.copyMakeBorder(contrast, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    return cv2.medianBlur(padded, MEDIAN_KERNEL)[pad:-pad, pad:-pad]


def register(enhanced: np.ndarray, references: list) -> np.ndarray:
    """The shift (x, y) that moves `enhanced` onto each of the enhanced `references`, one row each."""
    image = enhanced.astype(np.float64)
    return np.array([registration.register_images(image, reference, usfac=UPSAMPLING)
                     for reference in references], dtype=float)


def shift_frame(frame: np.ndarray, shift) -> np.ndarray:
    """`frame` moved by `shift` = (x, y) pixels: bilinear, rounded to uint8, uncovered edges black."""
    height, width = frame.shape
    matrix = np.float32([[1, 0, shift[0]], [0, 1, shift[1]]])
    moved = cv2.warpAffine(frame.astype(np.float64), matrix, (width, height))
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
    references: list            # frame numbers of the reference frames, sharpest first
    frames: pd.DataFrame

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    def summary(self) -> dict:
        """How much the recording moved and how sure the registration was."""
        shifts = self.frames[['shift_x_px', 'shift_y_px']].to_numpy()
        jumps = np.hypot(*np.diff(shifts, axis=0).T) if len(shifts) > 1 else np.zeros(1)
        disagreement = self.frames['disagreement_px'].to_numpy()
        return {'movement_range_x_px': float(np.ptp(shifts[:, 0])),
                'movement_range_y_px': float(np.ptp(shifts[:, 1])),
                'largest_jump_between_frames_px': float(jumps.max()),
                'median_disagreement_px': float(np.median(disagreement)),
                'largest_disagreement_px': float(disagreement.max()),
                'frames_disagreeing_over_1px': int(np.sum(disagreement > 1.0))}


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

    # first reading: the sharpness of every frame, keeping the sharpest ones as references
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
    enhanced_references = [enhance(frame).astype(np.float64) for _, _, frame in best]
    del best

    # second reading: register each frame, move it and write it
    writer = cv2.VideoWriter(output, 0, info.fps, (width, height), isColor=False)
    if not writer.isOpened():
        writer.release()
        raise OSError(f'cannot write an uncompressed video to {output}')
    per_reference = np.full((count, len(references), 2), np.nan)
    shifts = np.full((count, 2), np.nan)
    written = 0
    try:
        for number, frame in enumerate(iter_frames(source, max_frames=count)):
            _check(should_cancel)
            if number % 25 == 0:
                _report(progress, SHARPNESS_SHARE + (1 - SHARPNESS_SHARE) * number / count,
                        'Aligning and writing frames')
            per_reference[number] = register(enhance(frame), enhanced_references)
            shifts[number] = per_reference[number].mean(axis=0)
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

    # The references lie a few pixels apart, which offsets each one's estimates by a constant (the
    # mean shift carries the mean offset, the same for every frame). The offsets are read on the
    # sharpest reference, which every estimate there measures against itself or a nearby
    # reference; what is left after removing them is how much the references disagree about a
    # frame. It grows where the registration is unreliable, such as far from the references.
    offsets = per_reference[references[0]]
    disagreement = np.ptp(per_reference - offsets[None], axis=1).max(axis=1)

    numbers = np.arange(count)
    frames = pd.DataFrame({'frame': numbers, 'time_s': numbers / info.fps,
                           'shift_x_px': shifts[:, 0], 'shift_y_px': shifts[:, 1],
                           'disagreement_px': disagreement, 'sharpness': sharpness,
                           'reference': np.isin(numbers, references)})
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
    write_provenance(paths['provenance'], {
        'source_video': os.path.basename(result.source),
        'frames': result.frame_count,
        'fps': result.fps,
        'width': result.width,
        'height': result.height,
        'method': {
            'movement': 'translation only, one shift per frame',
            'reference_frames': result.references,
            'reference_choice': f'the {REFERENCE_FRAMES} sharpest frames (capillary.quality.calculate_blur)',
            'enhancement_for_registration': {'clahe_clip_limit': CLAHE_CLIP_LIMIT, 'clahe_tiles': list(CLAHE_TILES),
                                             'median_kernel_px': MEDIAN_KERNEL},
            'registration': f'upsampled cross-correlation to 1/{UPSAMPLING} pixel (Guizar-Sicairos et al. 2008), '
                            'mean over the reference frames',
            'output': 'original frames moved with bilinear interpolation, rounded, uncompressed 8-bit grey AVI; '
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
          f'references {result.references}')
    print(f'  moved over {summary["movement_range_x_px"]:.1f} x {summary["movement_range_y_px"]:.1f} px, '
          f'largest jump {summary["largest_jump_between_frames_px"]:.1f} px; references disagree by a median '
          f'{summary["median_disagreement_px"]:.2f} px, over 1 px on {summary["frames_disagreeing_over_1px"]} frames')
    print(f'  shifts: {final_records["shifts"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
