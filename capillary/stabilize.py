"""Translation-only stabilization of a recording, read from disk four times.

1. Following the movement (since 2026-10-14). Every frame is registered onto
   the frame before it (step 4's search), which gives a path of the picture
   through the recording. A frame that matches the one before it less than
   `STEP_MIN_MATCH` (the picture went dark or blurred, or jumped too far)
   breaks the path, and a new stretch of path begins there.
   - Every frame also gets a sharpness score (`quality.calculate_blur`) and
     its mean grey.
   - The references (step 3) are built around the sharpest frame of those
     that lie where the picture usually is (within `REFERENCE_RADIUS_PX` of
     the median position along the path), whose mean grey is usual (within
     `BRIGHTNESS_FACTOR`), taken from the official rest when the recording has
     official times (`capillary.inventory`), since resting velocity is
     measured there. Until 2026-10-14 it was the sharpest frame of the whole
     recording: on FP01_W that lay in its last, darkening seconds, 200 px from
     where the picture spends most of the recording, and no frame was found.
   - The sharpest frame and the 12 frames on each side of it are read again.
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
     two candidates, the coarse result and where the frame should be, and
     keeps the better match. A parabola through the best offset and its
     neighbours gives the fraction of a pixel.
   - Where the frame should be is the frame before's position plus the step
     between them along the path (step 1); before any frame has been placed,
     its position along the path relative to the references' centre. This
     lets the search track a recording that moves further than the coarse
     search reaches: FP03_Wföre swings by about 200 px with each breath, and
     FP03_Wefter makes excursions of 100-200 px at rest. The coarse result
     finds the frame again where the path broke.
   - The fine search compares the largest part of the frame that stays inside
     the reference.
   - The frame's shift is the mean of the two references' results, after
     removing the fixed offset between the two references.
   - The frame is placed by the references when it matches them at least
     `MIN_MATCH`, the two agree within `MAX_DISAGREEMENT_PX` and the match lies
     inside the search.
5. A frame the references did not place (it shares too little of the picture
   with them, or the picture changed) is carried along the path from the
   placed frames before and after it on its stretch, the path's own drift
   spread evenly between them (`bridge`). A stretch of path with no placed
   frame is lost: its frames get no shift and are written black. FP03_Qföre
   moves about 500 px when the cuff goes on, to a part of the finger the
   references do not show.
6. The shifts are measured from the references' centre. They are re-centred
   on their median over the official rest (or the whole recording), so the
   stabilized picture sits where it is during the rest and loses as little as
   possible at its edges there.
7. The original frame (not the band-passed one) is moved by its shift with
   bicubic interpolation, rounded to whole grey levels and written uncompressed
   as 8-bit grey. Edges the move uncovers are black.

The video is read four times: to follow the movement, for the reference
frames, to register, and to write.
Memory stays at a few dozen frames whatever the length. Output frame k is
recorded frame k, losslessly.

History (see the DEVLOG; on 2026-10-14 the frame-to-frame path, the choice of
the references' centre, the placing of frames the references miss, and the
centring on the rest were added, all above; the rest from 2026-10-08):

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
  positive). The image itself had moved by minus this from its median position
  during the rest. Empty for a lost frame;
- ``placed_by``: 'references' (registered onto them), 'neighbours' (carried
  along the path from frames that were), or 'lost' (written black);
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
- ``step_x_px``, ``step_y_px``, ``step_match``: the shift that moves the
  frame onto the frame before it, and how well they match (empty for the first);
- ``sharpness``: the score the reference frames were chosen by;
- ``mean_grey``: the frame's mean grey level;
- ``reference``: whether the frame was averaged into the references.

A line measured on a stabilized video must stay in the picture in every frame
of its range (`check_picture`, since 2026-10-14): where the picture moved, a
frame shows a black strip along its edge, and a line that reaches the strip
sees its edge move along the line, which reads as flow.

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
#: The frames on each side of the sharpest one that are averaged into the references with it.
REFERENCE_NEIGHBOURS = 12
#: How many times smaller the frames are for the coarse search, which then reaches a third of the frame.
#: Small frames are reduced less.
COARSE_REDUCTION = 4
#: How far the fine search looks around each candidate position (px).
FINE_REACH_PX = 12
#: A frame that matches the frame before it less than this (or only at the edge of the search) breaks the
#: frame-to-frame path: the picture went dark or blurred, or jumped too far. On the recordings neighbouring frames
#: match at 0.45-0.95; FP01_W's last, darkening seconds and FP03_Qföre's jump when the cuff went on fall to 0.05-0.4.
STEP_MIN_MATCH = 0.3
#: A frame is placed by the references when it matches them at least this well, they agree within
#: MAX_DISAGREEMENT_PX and the match lies inside the fine search. Otherwise it is placed by the frame-to-frame path
#: from the frames that were. Where the registration failed on 2026-10-08 the match was 0.08-0.15.
MIN_MATCH = 0.3
MAX_DISAGREEMENT_PX = 2.0
#: The sharpest frame that becomes the references' centre is chosen among frames that lie within this distance
#: (px) of where the picture usually is, so that as much as possible of the recording overlaps the references,
#: and whose mean grey is within this factor of the usual (FP01_W's sharpest frame was in its darkening end).
REFERENCE_RADIUS_PX = 40.0
BRIGHTNESS_FACTOR = 1.5

#: Shares of the progress bar for the readings: following the frames, registration, writing (the reading that
#: collects the reference frames is short).
PROGRESS_SHARES = (0.35, 0.5, 0.15)

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


def rest_window(source: str, fps: float, frame_count: int):
    """The official rest of the recording `source` (its first and last frame), or None without official times.

    The references are built and the picture centred there, since resting
    velocity is measured there (`capillary.inventory`).
    """
    from . import inventory
    phases = inventory.recording_phases(os.path.splitext(os.path.basename(source))[0], fps, frame_count)
    return None if phases is None else phases.windows.get('rest')


def path_stretches(step_ok: np.ndarray) -> np.ndarray:
    """Which stretch of unbroken frame-to-frame path each frame lies on (numbered from 1).

    A new stretch begins at the first frame and wherever a frame does not match
    the frame before it (`step_ok` False).
    """
    ok = np.asarray(step_ok, dtype=bool).copy()
    if ok.size:
        ok[0] = False
    return np.cumsum(~ok)


def path_positions(steps: np.ndarray, stretches: np.ndarray) -> np.ndarray:
    """The shift that moves each frame onto the first frame of its stretch, adding up the frame-to-frame steps.

    ``steps[t]`` moves frame t onto frame t - 1.
    """
    steps = np.nan_to_num(np.asarray(steps, dtype=float))
    out = np.zeros_like(steps)
    for t in range(1, len(steps)):
        out[t] = out[t - 1] + steps[t] if stretches[t] == stretches[t - 1] else 0.0
    return out


def choose_reference(sharpness, brightness, positions, stretches, window=None) -> int:
    """The frame the references are built around: the sharpest of the frames where the picture usually is.

    Frames are taken from `window` (first, last; the official rest when the
    recording has official times) or else from the whole recording. Of those,
    frames whose mean grey lies within `BRIGHTNESS_FACTOR` of the usual, on the
    stretch of unbroken path that holds most of them (`path_stretches`), and
    within `REFERENCE_RADIUS_PX` of their median position along that path.
    """
    sharpness, brightness = np.asarray(sharpness, dtype=float), np.asarray(brightness, dtype=float)
    candidates = np.zeros(len(sharpness), dtype=bool)
    if window is None:
        candidates[:] = True
    else:
        candidates[window[0]:window[1] + 1] = True
    usual = np.median(brightness[candidates])
    good = candidates & (brightness <= usual * BRIGHTNESS_FACTOR) & (brightness >= usual / BRIGHTNESS_FACTOR)
    if not good.any():
        good = candidates
    ids, counts = np.unique(stretches[good], return_counts=True)
    good &= stretches == ids[np.argmax(counts)]
    centre = np.median(positions[good], axis=0)
    near = good & (np.abs(positions - centre).max(axis=1) <= REFERENCE_RADIUS_PX)
    if near.any():
        good = near
    index = np.flatnonzero(good)
    return int(index[np.argmax(sharpness[index])])


def bridge(shifts, placed, positions, stretches) -> tuple:
    """Shifts for the frames the references did not place, from the frame-to-frame path.

    Each such frame is carried along its stretch of path from the nearest
    placed frames before and after it, weighted by how near each is, so the
    path's own drift is spread evenly between them; with a placed frame on one
    side only, from that one. A stretch without any placed frame is lost (NaN).
    Returns the shifts and, per frame, 'references', 'neighbours' or 'lost'.
    """
    shifts = np.array(shifts, dtype=float)
    found_by = np.where(placed, 'references', 'neighbours').astype(object)
    for stretch in np.unique(stretches):
        members = np.flatnonzero(stretches == stretch)
        anchors = members[placed[members]]
        unplaced = members[~placed[members]]
        if not unplaced.size:
            continue
        if not anchors.size:
            shifts[unplaced] = np.nan
            found_by[unplaced] = 'lost'
            continue
        after = np.searchsorted(anchors, unplaced)
        a = anchors[np.clip(after - 1, 0, anchors.size - 1)]
        b = anchors[np.clip(after, 0, anchors.size - 1)]
        from_a = shifts[a] + positions[unplaced] - positions[a]
        from_b = shifts[b] + positions[unplaced] - positions[b]
        weight = np.where(a == b, 0.0, (unplaced - a) / np.maximum(b - a, 1))
        weight = np.where(after == 0, 1.0, np.where(after == anchors.size, 0.0, weight))[:, None]
        shifts[unplaced] = (1 - weight) * from_a + weight * from_b
    return shifts, found_by


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
        placed_by = self.frames['placed_by'].to_numpy()
        return {'movement_range_x_px': float(np.nanmax(shifts[:, 0]) - np.nanmin(shifts[:, 0])),
                'movement_range_y_px': float(np.nanmax(shifts[:, 1]) - np.nanmin(shifts[:, 1])),
                'largest_jump_between_frames_px': float(np.nanmax(jumps)) if np.isfinite(jumps).any() else 0.0,
                'median_match': float(np.median(match)),
                'lowest_match': float(match.min()),
                'median_disagreement_px': float(np.median(disagreement)),
                'largest_disagreement_px': float(disagreement.max()),
                'frames_disagreeing_over_1px': int(np.sum(disagreement > 1.0)),
                'frames_at_search_limit': int(self.frames['at_search_limit'].sum()),
                'frames_placed_by_neighbours': int(np.sum(placed_by == 'neighbours')),
                'frames_lost': int(np.sum(placed_by == 'lost'))}


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

    follow_share, register_share, _ = PROGRESS_SHARES

    # first reading: sharpness, mean grey, and each frame registered onto the frame before it
    sharpness, brightness, steps, step_match, step_ok = [], [], [], [], []
    before = None
    for number, frame in enumerate(iter_frames(source)):
        if number % 25 == 0:
            _check(should_cancel)
            _report(progress, follow_share * number / expected, 'Following the movement')
        sharpness.append(float(calculate_blur(frame)))
        brightness.append(float(frame.mean()))
        enhanced = enhance(frame)
        if before is None:
            steps.append(np.zeros(2))
            step_match.append(np.nan)
            step_ok.append(False)
        else:
            step, matched, at_edge = locate(enhanced, before, steps[-1])
            steps.append(step)
            step_match.append(matched)
            step_ok.append(matched >= STEP_MIN_MATCH and not at_edge)
        before = enhanced
    if not sharpness:
        raise ValueError(f'no frames could be read from {source}')
    count = len(sharpness)
    steps, step_ok = np.array(steps), np.array(step_ok)
    stretches = path_stretches(step_ok)
    positions = path_positions(steps, stretches)
    window = rest_window(source, info.fps, count)
    sharpest = choose_reference(sharpness, brightness, positions, stretches, window)

    # second reading: the sharpest frame and its neighbours make the references
    first = max(0, sharpest - REFERENCE_NEIGHBOURS)
    last = min(count - 1, sharpest + REFERENCE_NEIGHBOURS)
    neighbourhood = [frame.copy() for frame in iter_frames(source, start=first, max_frames=last - first + 1)]
    height, width = neighbourhood[0].shape
    reference_images, used = build_references(neighbourhood, sharpest - first)
    references = [first + index for index in used]
    del neighbourhood

    # third reading: register every frame, the search led by the frame before it and the step between them
    shifts = np.full((count, 2), np.nan)
    match = np.full(count, np.nan)
    disagreement = np.full(count, np.nan)
    at_limit = np.zeros(count, dtype=bool)
    placed = np.zeros(count, dtype=bool)
    estimate = None
    registered = 0
    for number, frame in enumerate(iter_frames(source, max_frames=count)):
        _check(should_cancel)
        if number % 25 == 0:
            _report(progress, follow_share + register_share * number / count, 'Aligning frames')
        if step_ok[number] and estimate is not None:
            guide = estimate + steps[number]
        elif stretches[number] == stretches[sharpest]:
            guide = positions[number] - positions[sharpest]
        else:
            guide = None
        shifts[number], match[number], disagreement[number], at_limit[number] = register(
            enhance(frame), reference_images, guide)
        placed[number] = (not at_limit[number] and match[number] >= MIN_MATCH
                          and disagreement[number] <= MAX_DISAGREEMENT_PX)
        estimate = shifts[number] if placed[number] else guide
        registered += 1
    if registered != count:
        raise OSError(f'{source} gave {count} frames on the first reading but {registered} on the third')
    shifts, found_by = bridge(shifts, placed, positions, stretches)
    lost = found_by == 'lost'
    if lost.all():
        raise ValueError(f'no frame of {source} could be placed')
    centred = ~lost
    if window is not None and centred[window[0]:window[1] + 1].any():
        centred[:window[0]] = False
        centred[window[1] + 1:] = False
    centre = np.median(shifts[centred], axis=0)
    shifts -= centre

    # fourth reading: move every frame and write it; a lost frame is written black
    writer = cv2.VideoWriter(output, 0, info.fps, (width, height), isColor=False)
    if not writer.isOpened():
        writer.release()
        raise OSError(f'cannot write an uncompressed video to {output}')
    written = 0
    try:
        for number, frame in enumerate(iter_frames(source, max_frames=count)):
            _check(should_cancel)
            if number % 25 == 0:
                _report(progress, follow_share + register_share + (1 - follow_share - register_share)
                        * number / count, 'Writing the stabilized video')
            writer.write(np.zeros_like(frame) if lost[number] else shift_frame(frame, shifts[number]))
            written += 1
        writer.release()
        if written != count:
            raise OSError(f'{source} gave {count} frames on the first reading but {written} on the fourth')
    except BaseException:
        writer.release()
        _remove(output)
        raise
    _report(progress, 1.0, 'Writing the stabilized video')

    numbers = np.arange(count)
    frames = pd.DataFrame({'frame': numbers, 'time_s': numbers / info.fps,
                           'shift_x_px': shifts[:, 0], 'shift_y_px': shifts[:, 1], 'placed_by': found_by,
                           'match': match, 'disagreement_px': disagreement, 'at_search_limit': at_limit,
                           'step_x_px': steps[:, 0], 'step_y_px': steps[:, 1], 'step_match': step_match,
                           'sharpness': sharpness, 'mean_grey': brightness,
                           'reference': np.isin(numbers, references)})
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
            'following': f'every frame registered onto the frame before it (the same search); a match below '
                         f'{STEP_MIN_MATCH} breaks the path. The references\' centre: the sharpest frame within '
                         f'{REFERENCE_RADIUS_PX:g} px of the median position along the path and within '
                         f'{BRIGHTNESS_FACTOR:g}x of the usual mean grey, from the official rest if there is one',
            'registration': f'a coarse search on frames reduced up to {COARSE_REDUCTION} times, reaching a third '
                            f'of the frame; then normalized cross-correlation within {FINE_REACH_PX} px of the '
                            'coarse result and of where the frame should be (the frame before\'s position plus '
                            'the step between them), the better match kept, refined by a parabola through the '
                            'peak; the mean over the two references',
            'placing': f'by the references when the match is at least {MIN_MATCH}, they agree within '
                       f'{MAX_DISAGREEMENT_PX:g} px and the match lies inside the search; otherwise carried along '
                       'the frame-to-frame path from the placed frames before and after it; lost (written black) '
                       'where the path holds no placed frame',
            'recentred_by_px': list(result.centre),
            'output': 'original frames moved with bicubic interpolation, rounded, uncompressed 8-bit grey AVI; '
                      'uncovered edges and lost frames black; shifts measured from the references\' centre and '
                      're-centred on their median over the official rest (else the whole recording)',
        },
        'summary': result.summary(),
        'software': software_version(),
    })
    return paths


# ------------------------------------------------------------- where every frame shows the picture

#: How far (px) a line's samples must keep from the black strip a frame's move uncovers. The bicubic move
#: (`shift_frame`) blends black into the pixels beside the strip, and a sample is read between two pixels:
#: samples 2 px from the strip are just clear of it (DEVLOG 2026-10-14), and the third pixel is to spare.
EDGE_MARGIN_PX = 3.0


def read_shifts(video_path: str) -> Optional[pd.DataFrame]:
    """The shift of every frame of a stabilized video (its ``___stabilization.csv``), indexed by frame.

    None when the video has no shift file: it was not stabilized by this module (a raw recording, or a video
    stabilized before 2026-10-08).
    """
    path = record_paths(video_path)['shifts']
    if not os.path.isfile(path):
        return None
    shifts = pd.read_csv(path, index_col='frame')
    if not {'shift_x_px', 'shift_y_px'} <= set(shifts.columns):
        raise ValueError(f'{os.path.basename(path)} holds no shifts')
    return shifts


def _frame_areas(shifts: pd.DataFrame, frame_shape, first: int, last: int, margin_px: float) -> tuple:
    """Where each placed frame of `first`..`last` shows the picture, and the frames the stabilizer lost.

    A frame moved by (dx, dy) shows the recorded picture from x = dx to dx + width - 1 and from y = dy to
    dy + height - 1; within the frame, `margin_px` inside that. Returns ``(areas, lost)``: the placed frames'
    areas as rows of (x0, y0, x1, y1), and the numbers of the lost frames (written black).
    """
    height, width = frame_shape[0], frame_shape[1]
    part = shifts.loc[first:last]
    moves = part[['shift_x_px', 'shift_y_px']].to_numpy(dtype=float)
    lost = ~np.isfinite(moves).all(axis=1)
    if 'placed_by' in part:
        lost |= (part['placed_by'] == 'lost').to_numpy()
    dx, dy = moves[~lost, 0], moves[~lost, 1]
    areas = np.column_stack([np.maximum(0.0, dx + margin_px), np.maximum(0.0, dy + margin_px),
                             np.minimum(width - 1.0, dx + width - 1 - margin_px),
                             np.minimum(height - 1.0, dy + height - 1 - margin_px)])
    return areas, part.index.to_numpy()[lost]


def picture_area(shifts: pd.DataFrame, frame_shape, first: int, last: int,
                 margin_px: float = EDGE_MARGIN_PX) -> Optional[tuple]:
    """(x0, y0, x1, y1): where every placed frame of `first`..`last` shows the picture (`check_picture`).

    None when the stabilizer placed no frame of the range. x0 > x1 (or y0 > y1) when the picture moved
    further than the frame is wide (high), so that no place shows it in every frame.
    """
    return _common_area(_frame_areas(shifts, frame_shape, first, last, margin_px)[0])


def _common_area(areas: np.ndarray) -> Optional[tuple]:
    """The part of every area (rows of x0, y0, x1, y1) that all share; None for none."""
    if not len(areas):
        return None
    return (float(areas[:, 0].max()), float(areas[:, 1].max()), float(areas[:, 2].min()), float(areas[:, 3].min()))


@dataclass(frozen=True)
class PictureCheck:
    """Whether a line's samples lie in the recorded picture in every frame of a range (`check_picture`).

    A stabilized frame is the recorded frame moved back by its shift (`shift_frame`), which leaves a black
    strip along the edge where the picture had moved; a frame the stabilizer lost is black all over. A line
    that reaches the strip sees its edge move along the line as the picture moves, a strong pattern that
    reads as flow (found on FP13_Qföre, DEVLOG 2026-10-14).
    """

    first: int                      # the range checked, frames first..last
    last: int
    box: tuple                      # (x0, y0, x1, y1), the smallest rectangle holding the line's samples
    area: Optional[tuple]           # where every placed frame of the range shows the picture (`picture_area`)
    off_picture: int                # placed frames in which the samples reach the strip or leave the frame
    lost: int                       # frames of the range the stabilizer lost (written black)
    lost_at: str                    # where they lie, e.g. '142.9–150.9 s' ('' when none)
    margin_px: float = EDGE_MARGIN_PX

    @property
    def frames(self) -> int:
        return self.last - self.first + 1

    @property
    def clearance_px(self) -> float:
        """How far the samples keep from the edge of `area`; negative: how far they reach over it."""
        if self.area is None:
            return float('nan')
        return float(min(self._sides().values()))

    @property
    def side(self) -> str:
        """The edge of the picture the line comes nearest: 'left', 'top', 'right' or 'bottom' ('' without area)."""
        sides = self._sides()
        return min(sides, key=sides.get) if sides else ''

    def _sides(self) -> dict:
        if self.area is None:
            return {}
        (x0, y0, x1, y1), (a0, b0, a1, b1) = self.box, self.area
        return {'left': x0 - a0, 'top': y0 - b0, 'right': a1 - x1, 'bottom': b1 - y1}

    def problem(self) -> Optional[str]:
        """Why the line cannot be measured over the range, or None."""
        if self.lost:
            several = self.lost != 1
            return (f'The stabilizer lost {self.lost} frame{"s" if several else ""} of this range ({self.lost_at}), '
                    f'which {"are" if several else "is"} black. Set the range to frames it placed.')
        if self.off_picture:
            reach = (f'In {self.off_picture} of the range\'s {self.frames} frames the line reaches the black strip '
                     'that stabilizing leaves along the edge where the picture moved.')
            (x0, y0, x1, y1), (a0, b0, a1, b1) = self.box, self.area
            if a0 > a1 or b0 > b1:
                return f'{reach} No part of the frame shows the picture in every frame of this range: it moved too far.'
            if x1 - x0 > a1 - a0 or y1 - y0 > b1 - b0:
                return (f'{reach} The line is larger than the part of the frame that shows the picture in every frame '
                        f'of this range ({a1 - a0:.0f} × {b1 - b0:.0f} px).')
            return (f'{reach} Move it at least {max(1, int(np.ceil(-self.clearance_px - 1e-9)))} px away from the '
                    f'{self.side} edge.')
        return None

    def record(self) -> dict:
        """The check as kept in a data set's provenance."""
        return {'rule': ('every frame of the range shows the recorded picture under the line, its samples at least '
                         f'{self.margin_px:g} px from the black strip stabilizing leaves where the picture moved '
                         '(capillary.stabilize.check_picture)'),
                'area_px': [round(value, 2) for value in self.area] if self.area is not None else None,
                'clearance_px': round(self.clearance_px, 2) if self.area is not None else None}


def check_picture(shifts: pd.DataFrame, frame_shape, box, first: int, last: int,
                  margin_px: float = EDGE_MARGIN_PX) -> PictureCheck:
    """Whether the rectangle `box` = (x0, y0, x1, y1) lies in the picture in every frame `first`..`last`.

    `shifts` is the video's shift file (`read_shifts`), `frame_shape` its frames' (height, width), and `box`
    holds the samples a line reads (`capillary.spacetime.SpaceTimeSampler.bounds`). In each frame the
    samples must keep `margin_px` inside the moved picture, and lie in the frame; no frame may be lost.
    """
    areas, lost = _frame_areas(shifts, frame_shape, first, last, margin_px)
    x0, y0, x1, y1 = (float(value) for value in box)
    off = (x0 < areas[:, 0]) | (y0 < areas[:, 1]) | (x1 > areas[:, 2]) | (y1 > areas[:, 3])
    lost_at = ''
    if len(lost):
        lost_at = (f'{shifts.at[lost[0], "time_s"]:.1f}–{shifts.at[lost[-1], "time_s"]:.1f} s' if 'time_s' in shifts
                   else f'frames {lost[0]}–{lost[-1]}')
    return PictureCheck(first=int(first), last=int(last), box=(x0, y0, x1, y1), area=_common_area(areas),
                        off_picture=int(off.sum()), lost=int(len(lost)), lost_at=lost_at, margin_px=float(margin_px))


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
    if summary['frames_placed_by_neighbours'] or summary['frames_lost']:
        print(f'  {summary["frames_placed_by_neighbours"]} frames placed from their neighbours along the path; '
              f'{summary["frames_lost"]} lost (written black)')
    if summary['frames_at_search_limit']:
        print(f'  WARNING: on {summary["frames_at_search_limit"]} frames the image may have moved further than the '
              'search reaches; check their shifts')
    print(f'  shifts: {final_records["shifts"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
