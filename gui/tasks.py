"""The work the GUI runs in background jobs. No Tk here.

Each function takes the `Job` it runs in (to report progress; that is also
where a cancel takes effect) and returns a plain result for the page.

Videos are written to a hidden ``.partial`` folder and moved into place only
when complete, so a cancelled or failed job never leaves a half-written file
where the library would list it. A data set whose measurement is cancelled or
fails half-way is removed again.
"""

from __future__ import annotations

import datetime
import logging
import os
import shutil
from typing import Iterable, Optional

import numpy as np
import pandas as pd

import Caper
from capillary import datasets, inventory, pattern_shift, placement, spacetime, validation
from capillary import stabilize as stabilizer
from capillary.intensity import extract_traces
from capillary.measure import measure_velocity
from capillary.roi import ROI
from capillary.velocity import (DEFAULT_WINDOWS, lag_and_correlation, resolvable_range, velocity_from_lag,
                                velocity_summary)
from capillary.video import iter_frames, probe_video

from .library import Recording, stem_of, video_files
from .settings import DataFolder

log = logging.getLogger(__name__)


# ------------------------------------------------------------------------- helpers

def _remove(path: Optional[str]) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            log.warning('Could not remove %s', path, exc_info=True)


def check_disk_space(path: str, needed: int) -> None:
    """Refuse to start writing about `needed` bytes into the folder `path` when its disk has less free."""
    free = shutil.disk_usage(path).free
    if needed > free:
        raise OSError(f'Stabilizing this video needs about {needed / 1e9:.1f} GB of free disk space, but only '
                      f'{free / 1e9:.1f} GB is free. The stabilized video is stored uncompressed, about as '
                      'large as the raw recording.')


def relative_path(folder: DataFolder, path: str) -> str:
    """`path` relative to the data folder (``StabilizedVideos/x.avi``), or its file name if outside it."""
    try:
        relative = os.path.relpath(path, folder.root)
    except ValueError:  # another drive on Windows
        return os.path.basename(path)
    return os.path.basename(path) if relative.startswith(os.pardir) else relative


def move_to_trash(folder: DataFolder, paths: Iterable[str], label: str) -> str:
    """Move `paths` into a new, dated folder under ``.trash``; returns that folder.

    Each file keeps its place relative to the data folder, so the raw and
    stabilized videos of a recording (which share a file name) stay apart and
    can be put back where they were.
    """
    stamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    target = os.path.join(folder.trash, f'{stamp}_{datasets.safe_file_part(label)}')
    unique, counter = target, 2
    while os.path.exists(unique):
        unique = f'{target}_{counter}'
        counter += 1
    os.makedirs(unique)
    for path in paths:
        destination = os.path.join(unique, relative_path(folder, path))
        base, extension = os.path.splitext(destination)
        counter = 2
        while os.path.lexists(destination):
            destination = f'{base}_{counter}{extension}'
            counter += 1
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.move(path, destination)
    return unique


def stabilized_files(folder: DataFolder, stem: str) -> list[str]:
    """The stabilized video of `stem` and the shift and provenance files kept next to it."""
    videos = [path for path in video_files(folder.stabilized) if stem_of(path) == stem]
    records = [path for video in videos + [os.path.join(folder.stabilized, f'{stem}.avi')]
               for path in stabilizer.record_paths(video).values()]
    seen, result = set(), []
    for path in videos + records:
        if path not in seen and os.path.exists(path):
            seen.add(path)
            result.append(path)
    return result


def recording_files(folder: DataFolder, recording: Recording) -> list[str]:
    """Every file that belongs to `recording`: videos and their stabilization records, data sets, reports,
    time points, old flow files."""
    paths = [recording.raw, recording.stabilized, *stabilized_files(folder, recording.stem)]
    for kind in datasets.KINDS:
        for name in recording.datasets_of(kind):
            paths += datasets.dataset_paths(folder.statistics, folder.reports, recording.stem, name, kind)
    paths.append(datasets.time_points_file(folder.statistics, recording.stem))
    paths += recording.legacy_flow_files
    seen, result = set(), []
    for path in paths:
        if path and path not in seen and os.path.exists(path):
            seen.add(path)
            result.append(path)
    return result


# ---------------------------------------------------------------- video processing

def stabilize(job, folder: DataFolder, raw_path: str) -> str:
    """Stabilize a raw recording into ``StabilizedVideos/<stem>.avi`` (`capillary.stabilize`).

    The shift of every frame and the provenance are saved next to the video. A
    previous stabilized video of the recording goes to the trash with its files.
    """
    stem = stem_of(raw_path)
    final = os.path.join(folder.stabilized, f'{stem}.avi')
    partial_dir = folder.partial(folder.stabilized)
    os.makedirs(partial_dir, exist_ok=True)
    check_disk_space(partial_dir, stabilizer.output_bytes(probe_video(raw_path)))
    partial = os.path.join(partial_dir, f'{stem}.avi')
    partial_records = stabilizer.record_paths(partial)
    job.report(0.0, 'Scoring sharpness')
    try:
        result = stabilizer.stabilize_video(raw_path, partial, progress=job.report, should_cancel=job.cancelled)
        stabilizer.save_record(result)
        previous = stabilized_files(folder, stem)
        if previous:
            move_to_trash(folder, previous, f'{stem} previous stabilized video')
        os.replace(partial, final)
        for key, path in stabilizer.record_paths(final).items():
            os.replace(partial_records[key], path)
    finally:
        for path in (partial, *partial_records.values()):
            _remove(path)
    return final


# -------------------------------------------------------------------- measurements

#: Frames the live preview reads around the playhead: the report's shortest window.
PREVIEW_FRAMES = DEFAULT_WINDOWS[0]


def velocity_preview(path: str, box1: ROI, box2: ROI, start: int, count: int, mm_per_pixel: float) -> dict:
    """One-window velocity estimate for the live preview, through the same engine as a measurement.

    Positive velocity means flow from box 2 to box 1, the report's convention.
    """
    info = probe_video(path)
    trace = extract_traces(iter_frames(path, max_frames=count, start=start), box1, box2, fps=info.fps)
    lag, correlation = lag_and_correlation(trace.a, trace.b)
    velocity = -velocity_from_lag(lag, trace.distance_px, info.fps, mm_per_pixel) if np.isfinite(lag) else float('nan')
    return {'start': start, 'a': trace.a, 'b': trace.b, 'lag': lag, 'r': correlation, 'velocity': velocity,
            'fps': info.fps, 'distance_px': trace.distance_px, 'max_lag': trace.n_frames // 2}


def summarize_velocity_report(report: pd.DataFrame) -> dict:
    """Headline numbers of a velocity report table (`Caper.CrossCorrelation`).

    Velocity per row is the mean over the window lengths, as in the report's
    plots, before smoothing; the zero-lag share counts every window estimate.
    """
    columns = [str(c) for c in report.columns]
    velocity = report.loc[:, [c.startswith('velocity') for c in columns]].mean(axis=1)
    correlation = report.loc[:, [c.startswith('correlation') for c in columns]].mean(axis=1)
    lags = report.loc[:, [c.isdigit() for c in columns]].to_numpy(dtype=float)
    summary = velocity_summary(velocity, correlation, lags)
    times = pd.to_numeric(pd.Series(report.index), errors='coerce')
    summary['first_s'] = float(times.min()) if len(times) else float('nan')
    summary['last_s'] = float(times.max()) if len(times) else float('nan')
    return summary


def velocity_series(report: pd.DataFrame, max_points: int = 600) -> dict:
    """Time and smoothed velocity as the report plots them, thinned out for a small chart."""
    columns = [str(c) for c in report.columns]
    velocity = report.loc[:, [c.startswith('velocity') for c in columns]].mean(axis=1)
    smoothed = velocity.rolling(30, min_periods=1).mean()
    step = max(1, int(np.ceil(len(smoothed) / max_points)))
    times = pd.to_numeric(pd.Series(report.index), errors='coerce').to_numpy(dtype=float)
    return {'t': times[::step].tolist(), 'v': smoothed.to_numpy(dtype=float)[::step].tolist()}


def _video_record(path: str, info) -> dict:
    return {'file': os.path.basename(path), 'folder': os.path.basename(os.path.dirname(path)), 'path': path,
            'frame_count': info.frame_count, 'fps': info.fps, 'width': info.width, 'height': info.height}


def range_phase(stem: str, fps: float, frame_count, first: int, last: int) -> str:
    """The official phases frames `first`..`last` of the recording lie in, e.g. 'rest' (`capillary.inventory`).

    '' when the recording has no official times, they do not fit its video, or
    the metadata cannot be read.
    """
    if not frame_count:
        return ''
    try:
        phases = inventory.recording_phases(stem, fps, int(frame_count))
    except (OSError, ValueError, KeyError):
        log.warning('Could not read the official times', exc_info=True)
        return ''
    return phases.phase_of(first, last, fps) if phases is not None else ''


def measure_velocity_dataset(job, *, folder: DataFolder, stem: str, name: str, video_path: str,
                             box1: ROI, box2: ROI, start: int, end: int, mm_per_pixel: float,
                             time_points=(), blur_cache=None, observer: str = '') -> dict:
    """Measure frames ``start..end`` (inclusive), save the data set, and write its report."""
    job.report(0.0, 'Reading frames')
    measurement = measure_velocity(video_path, box1, box2, start, end + 1,
                                   progress=lambda p: job.report(0.5 * p, 'Reading frames'),
                                   should_cancel=job.cancelled, blur_cache=blur_cache)
    if measurement.frames_read < datasets.MIN_VELOCITY_FRAMES:
        raise ValueError(f'Only {measurement.frames_read} frames could be read; the report needs at least '
                         f'{datasets.MIN_VELOCITY_FRAMES}.')
    files = datasets.velocity_dataset_files(folder.statistics, stem, name)
    trace = measurement.trace
    try:
        job.report(0.52, 'Saving the data set')
        datasets.write_velocity_dataset(folder.statistics, stem, name, trace.a, trace.b, trace.distance_px,
                                        measurement.blur, measurement.start_frame, measurement.frame_count)
        report = Caper.CrossCorrelation(fps=measurement.fps, mm_per_pixel=mm_per_pixel).generate_report(
            datasets.dataset_prefix(folder.statistics, stem, name), sorted(time_points),
            report_path=datasets.dataset_prefix(folder.reports, stem, name),
            progress=lambda p: job.report(0.55 + 0.37 * p, 'Computing velocities'))
        job.report(0.97, 'Writing the summary')
        summary = summarize_velocity_report(report)
        summary['phase'] = range_phase(stem, measurement.fps, measurement.frame_count, measurement.start_frame,
                                       measurement.start_frame + measurement.frames_read - 1)
        slowest, fastest = resolvable_range(trace.distance_px, measurement.fps, mm_per_pixel)
        record = {
            'kind': 'velocity',
            'dataset': name,
            'recording': stem,
            'created': datetime.datetime.now().isoformat(timespec='seconds'),
            'observer': observer or None,
            'video': _video_record(video_path, measurement),
            'frames': {'first': measurement.start_frame,
                       'last': measurement.start_frame + measurement.frames_read - 1,
                       'count': measurement.frames_read},
            'boxes': {
                'width_px': box1.width,
                'height_px': box1.height,
                'box1': {'x': box1.center_x, 'y': box1.center_y,
                         'role': 'downstream: the blood reaches it last (column 0 of the data)'},
                'box2': {'x': box2.center_x, 'y': box2.center_y,
                         'role': 'upstream: the blood reaches it first (column 1 of the data)'},
                'coordinates': 'box centre in video pixels, x to the right, y down from the top-left corner',
            },
            'distance_px': trace.distance_px,
            'distance_um': trace.distance_px * mm_per_pixel * 1000.0,
            'mm_per_pixel': mm_per_pixel,
            'resolvable_mm_per_s': {'slowest': slowest, 'fastest': fastest},
            'time_points_s': sorted(float(t) for t in time_points),
            'report': {'windows_frames': [int(w) for w in DEFAULT_WINDOWS],
                       'estimator': 'Caper.CrossCorrelation.calculate_cross_correlation, '
                                    'lags from capillary.velocity.lag_and_correlation',
                       'positive_velocity': 'flow from box 2 towards box 1'},
            'summary': summary,
            'software': datasets.software_version(),
        }
        datasets.write_provenance(files['provenance'], record)
    except BaseException:
        for path in datasets.dataset_paths(folder.statistics, folder.reports, stem, name, 'velocity'):
            _remove(path)
        raise
    return {'kind': 'velocity', 'stem': stem, 'name': name, 'summary': summary, 'series': velocity_series(report),
            'record': record}


def regenerate_velocity_report(job, *, folder: DataFolder, stem: str, name: str, fps: float,
                               mm_per_pixel: float, time_points=()) -> dict:
    """Write the report of a saved velocity data set again (e.g. after adding time points)."""
    job.report(0.0, 'Computing velocities')
    report = Caper.CrossCorrelation(fps=fps, mm_per_pixel=mm_per_pixel).generate_report(
        datasets.dataset_prefix(folder.statistics, stem, name), sorted(time_points),
        report_path=datasets.dataset_prefix(folder.reports, stem, name),
        progress=lambda p: job.report(0.9 * p, 'Computing velocities'))
    summary = summarize_velocity_report(report)
    provenance = datasets.velocity_dataset_files(folder.statistics, stem, name)['provenance']
    record = datasets.read_provenance(provenance)
    if record is not None:
        frames = record.get('frames') or {}
        if 'first' in frames and 'last' in frames:
            summary['phase'] = range_phase(stem, fps, (record.get('video') or {}).get('frame_count'),
                                           int(frames['first']), int(frames['last']))
        record['summary'] = summary
        record['time_points_s'] = sorted(float(t) for t in time_points)
        record['report_regenerated'] = datetime.datetime.now().isoformat(timespec='seconds')
        datasets.write_provenance(provenance, record)
    return {'kind': 'velocity', 'stem': stem, 'name': name, 'summary': summary, 'series': velocity_series(report)}


# ------------------------------------------------------------- centre-line velocity

#: Frames the centre-line preview reads around the playhead (4 s at 30 fps), measured as one block.
LINE_PREVIEW_FRAMES = 120


def line_preview(path: str, points, start: int, count: int, mm_per_pixel: float) -> dict:
    """Space-time diagram of `count` frames from `start` along the line, and one estimate over all of them."""
    info = probe_video(path)
    line = spacetime.Centreline.from_points(points)
    diagram = spacetime.space_time_diagram(iter_frames(path, max_frames=count, start=start), line)
    estimate = spacetime.streak_speed(diagram)
    to_mm_s = info.fps * mm_per_pixel
    return {'start': start, 'diagram': diagram, 'fps': info.fps, 'length_px': line.length_px,
            'speed': estimate.speed_px_per_frame, 'snr': estimate.snr, 'coherence': estimate.coherence,
            'in_range': estimate.in_range, 'resolved': estimate.resolved,
            'velocity': estimate.speed_px_per_frame * to_mm_s if estimate.resolved else float('nan'),
            'limits_mm_s': tuple(v * to_mm_s for v in spacetime.speed_limits(diagram.shape[1], diagram.shape[0]))}


def line_series(blocks: pd.DataFrame) -> dict:
    """Time and velocity of the resolved blocks, for the result chart."""
    resolved = blocks[blocks['resolved'].astype(bool)]
    return {'t': resolved['time_s'].astype(float).tolist(), 'v': resolved['velocity_mm_s'].astype(float).tolist()}


def summarize_line_blocks(blocks: pd.DataFrame, length_px: float, fps: float, mm_per_pixel: float) -> dict:
    """Headline numbers of a centre-line measurement, plus its measurable range."""
    summary = spacetime.space_time_summary(blocks)
    slowest, fastest = spacetime.resolvable_speeds(length_px, fps, mm_per_pixel)
    times = blocks['time_s'].astype(float)
    summary.update(first_s=float(times.min()) if len(times) else float('nan'),
                   last_s=float(times.max()) if len(times) else float('nan'),
                   slowest_mm_s=slowest, fastest_mm_s=fastest)
    return summary


def summarize_line(diagram, blocks: pd.DataFrame, length_px: float, fps: float, mm_per_pixel: float,
                   role: Optional[str] = None, phase: str = '', apex_px: Optional[float] = None) -> dict:
    """Everything a centre-line data set reports: its 3-s blocks, the pattern shift pooled over the range
    (`capillary.pattern_shift.summarize`), what the line follows and, for an arterial limb, which limb the
    direction of the pooled flow shows; `phase` is the official phase of the range ('' if unknown).

    For a whole loop (`apex_px` from `Centreline.apex_arc_px`): which end of the line lies on the arterial
    limb (`arterial_end`), and each limb's own pattern shift with ``loop_movement``
    (`capillary.pattern_shift.loop_limbs`)."""
    summary = summarize_line_blocks(blocks, length_px, fps, mm_per_pixel)
    summary.update(pattern_shift.summarize(diagram, fps, mm_per_pixel))
    velocity = summary['pattern_shift_velocity_mm_s']
    summary['line_role'] = role or ''
    summary['limb_check'] = pattern_shift.limb_from_direction(velocity) if role == pattern_shift.ARTERIAL_LIMB else ''
    summary['arterial_end'] = pattern_shift.loop_from_direction(velocity) if role == pattern_shift.WHOLE_LOOP else ''
    if role == pattern_shift.WHOLE_LOOP and apex_px is not None:
        summary.update(pattern_shift.loop_limbs(diagram, apex_px, fps, mm_per_pixel))
    summary['phase'] = phase
    return summary


def _apex_px(points, role: Optional[str]) -> Optional[float]:
    """The apex's distance along a whole-loop line (None for other lines, or without points)."""
    if role != pattern_shift.WHOLE_LOOP or not points or len(points) < 2:
        return None
    return spacetime.Centreline.from_points(points).apex_arc_px()


def _estimator_record() -> dict:
    return {'method': 'capillary.spacetime: slope of the streaks in the space-time diagram (Radon transform '
                      'evaluated in the Fourier domain, mirror line subtracted)',
            'block_frames': spacetime.DEFAULT_BLOCK_FRAMES, 'step_frames': spacetime.DEFAULT_STEP_FRAMES,
            'min_snr': spacetime.MIN_SNR, 'min_coherence': spacetime.MIN_COHERENCE, 'k_max': spacetime.K_MAX,
            'omega_taper': [spacetime.TAPER_START, spacetime.MAX_OMEGA],
            'fastest_fraction': spacetime.FASTEST_FRACTION, 'half_width_px': spacetime.DEFAULT_HALF_WIDTH_PX}


def _pattern_shift_record() -> dict:
    return {'method': 'capillary.pattern_shift: the shift of the pattern along the line between a frame and the '
                      f'next 1-{pattern_shift.MAX_LAG} (below 1 px/frame, the frames the pattern takes to move '
                      f'1-{pattern_shift.MAX_LAG} px), pooled over all 3-s blocks of the range, and of each half',
            'block_frames': pattern_shift.BLOCK_FRAMES, 'max_lag': pattern_shift.MAX_LAG,
            'bandpass_px': list(pattern_shift.BANDPASS_PX), 'min_snr': pattern_shift.MIN_SNR,
            'min_speed_px_per_frame': pattern_shift.MIN_SPEED, 'min_shift_px': pattern_shift.MIN_SHIFT_PX,
            'centred_beyond_max_lag': pattern_shift.CENTRED, 'slow_refine_top_px_per_frame': pattern_shift.REFINE_TOP,
            'min_half_blocks': pattern_shift.MIN_HALF_BLOCKS}


def picture_check(video_path: str, sampler: spacetime.SpaceTimeSampler, frame_shape, first: int,
                  last: int) -> Optional[stabilizer.PictureCheck]:
    """Whether the line of `sampler` stays in the picture in frames `first`..`last` of a stabilized video
    (`capillary.stabilize.check_picture`); None for a video without a shift file."""
    shifts = stabilizer.read_shifts(video_path)
    if shifts is None:
        return None
    return stabilizer.check_picture(shifts, frame_shape, sampler.bounds, first, last)


def measure_line_dataset(job, *, folder: DataFolder, stem: str, name: str, video_path: str, points,
                         start: int, end: int, mm_per_pixel: float, time_points=(), observer: str = '',
                         role: Optional[str] = None) -> dict:
    """Measure frames ``start..end`` (inclusive) along the centre line, save the data set, write its report.

    `role` is `capillary.pattern_shift.ARTERIAL_LIMB` for a line drawn along a capillary loop's arterial
    limb, from its base to the apex; `capillary.pattern_shift.WHOLE_LOOP` for a line round a whole loop,
    from the base of one limb over the apex to the base of the other; None for any other line.

    On a stabilized video the line must stay in the picture in every frame of the range (`picture_check`);
    otherwise nothing is measured.
    """
    info = probe_video(video_path)
    line = spacetime.Centreline.from_points(points)
    sampler = spacetime.SpaceTimeSampler(line)
    picture = picture_check(video_path, sampler, (info.height, info.width), start, end)
    if picture is not None and picture.problem() is not None:
        raise ValueError(picture.problem())
    wanted = end - start + 1
    rows = []
    job.report(0.0, 'Reading frames')
    for offset, frame in enumerate(iter_frames(video_path, max_frames=wanted, start=start)):
        rows.append(sampler.row(frame))
        if offset % 25 == 0:
            job.report(0.5 * offset / wanted, 'Reading frames')
    if len(rows) < spacetime.DEFAULT_BLOCK_FRAMES:
        raise ValueError(f'Only {len(rows)} frames could be read; a measurement needs at least '
                         f'{spacetime.DEFAULT_BLOCK_FRAMES}.')
    diagram = np.asarray(rows, dtype=np.float32)
    blocks = spacetime.analyze_space_time(diagram, info.fps, mm_per_pixel, first_frame=start,
                                          progress=lambda p: job.report(0.5 + 0.35 * p, 'Measuring the streaks'))
    job.report(0.86, 'Pooling the pattern shift')
    last = start + len(rows) - 1
    summary = summarize_line(diagram, blocks, line.length_px, info.fps, mm_per_pixel, role,
                             range_phase(stem, info.fps, info.frame_count, start, last), _apex_px(line.points, role))
    files = datasets.line_dataset_files(folder.statistics, stem, name)
    try:
        job.report(0.92, 'Saving the data set')
        datasets.write_line_dataset(folder.statistics, stem, name, diagram, blocks)
        Caper.generate_line_report(datasets.dataset_prefix(folder.reports, stem, name), diagram, blocks, info.fps,
                                   mm_per_pixel, start, sorted(time_points), summary)
        record = {
            'kind': 'line',
            'dataset': name,
            'recording': stem,
            'created': datetime.datetime.now().isoformat(timespec='seconds'),
            'observer': observer or None,
            'video': _video_record(video_path, info),
            'frames': {'first': start, 'last': last, 'count': len(rows)},
            'line': {'points': [[round(x, 2), round(y, 2)] for x, y in line.points],
                     'length_px': line.length_px,
                     'length_um': line.length_px * mm_per_pixel * 1000.0,
                     'coordinates': 'clicked points in video pixels, x to the right, y down from the top-left '
                                    'corner; positive velocity runs from the first point towards the last',
                     'role': role,
                     'roles': f'"{pattern_shift.ARTERIAL_LIMB}": drawn along a capillary loop\'s arterial limb '
                              f'from its base to the apex; "{pattern_shift.WHOLE_LOOP}": drawn round a whole loop, '
                              'from the base of one limb over the apex to the base of the other; null: any '
                              'other line'},
            'picture': picture.record() if picture is not None else None,
            'mm_per_pixel': mm_per_pixel,
            'resolvable_mm_per_s': {'slowest': summary['slowest_mm_s'], 'fastest': summary['fastest_mm_s']},
            'time_points_s': sorted(float(t) for t in time_points),
            'estimator': _estimator_record(),
            'pattern_shift': _pattern_shift_record(),
            'summary': summary,
            'software': datasets.software_version(),
        }
        datasets.write_provenance(files['provenance'], record)
    except BaseException:
        for path in datasets.dataset_paths(folder.statistics, folder.reports, stem, name, 'line'):
            _remove(path)
        raise
    return {'kind': 'line', 'stem': stem, 'name': name, 'summary': summary, 'series': line_series(blocks),
            'record': record}


def regenerate_line_report(job, *, folder: DataFolder, stem: str, name: str, fps: float, mm_per_pixel: float,
                           time_points=()) -> dict:
    """Measure a saved centre-line diagram again and rewrite its report (no video needed)."""
    job.report(0.0, 'Loading the space-time diagram')
    diagram, old_blocks = datasets.load_line_dataset(folder.statistics, stem, name)
    files = datasets.line_dataset_files(folder.statistics, stem, name)
    record = datasets.read_provenance(files['provenance'])
    frames = (record or {}).get('frames') or {}
    if 'first' in frames:
        first = int(frames['first'])
    else:
        first = int(old_blocks.index.min()) - spacetime.DEFAULT_BLOCK_FRAMES // 2 if len(old_blocks) else 0
    blocks = spacetime.analyze_space_time(diagram, fps, mm_per_pixel, first_frame=first,
                                          progress=lambda p: job.report(0.1 + 0.7 * p, 'Measuring the streaks'))
    blocks.to_csv(files['velocity'])
    line = (record or {}).get('line') or {}
    length = line.get('length_px') or float(diagram.shape[1] - 1)
    job.report(0.82, 'Pooling the pattern shift')
    frame_count = ((record or {}).get('video') or {}).get('frame_count')
    summary = summarize_line(diagram, blocks, length, fps, mm_per_pixel, line.get('role'),
                             range_phase(stem, fps, frame_count, first, first + diagram.shape[0] - 1),
                             _apex_px(line.get('points'), line.get('role')))
    job.report(0.9, 'Drawing the report')
    Caper.generate_line_report(datasets.dataset_prefix(folder.reports, stem, name), diagram, blocks, fps,
                               mm_per_pixel, first, sorted(time_points), summary)
    if record is not None:
        record.update(summary=summary, estimator=_estimator_record(), pattern_shift=_pattern_shift_record(),
                      mm_per_pixel=mm_per_pixel, time_points_s=sorted(float(t) for t in time_points),
                      report_regenerated=datetime.datetime.now().isoformat(timespec='seconds'))
        datasets.write_provenance(files['provenance'], record)
    return {'kind': 'line', 'stem': stem, 'name': name, 'summary': summary, 'series': line_series(blocks)}


# ------------------------------------------------------------ validation (reading sets)

def create_reading_set(job, *, folder: DataFolder, name: str, sources, blocks_per_dataset: int, balanced: bool,
                       seed: Optional[int], mm_per_pixel: float) -> str:
    """Draw a reading set from centre-line data sets (`capillary.validation`); returns its name."""
    job.report(0.0, 'Drawing blocks')
    reading_set = validation.create_reading_set(
        folder.validation, folder.statistics, name, sources, blocks_per_dataset=blocks_per_dataset,
        balanced=balanced, seed=seed, fallback_mm_per_pixel=mm_per_pixel,
        progress=lambda p: job.report(0.95 * p, 'Drawing blocks'))
    return reading_set.name


def agreement_report(job, *, folder: DataFolder, name: str) -> dict:
    """Measure every block of a reading set again, compare it with the readings, write tables and plots."""
    job.report(0.0, 'Measuring the blocks')
    reading_set = validation.load_reading_set(folder.validation, name)
    readings = reading_set.readings()
    estimates = validation.estimate_items(reading_set, progress=lambda p: job.report(0.8 * p, 'Measuring the blocks'))
    table = validation.agreement_table(reading_set, readings, estimates)
    comparisons = validation.compare(table, readings)
    job.report(0.82, 'Writing the tables')
    files = validation.write_report_tables(reading_set, table, comparisons, readings)
    job.report(0.86, 'Drawing the plots')
    files.update(Caper.generate_validation_report(reading_set.report_dir, table, comparisons))
    return {'name': name, 'comparisons': comparisons, 'files': files, 'readings': len(readings)}


def placement_report(job, *, folder: DataFolder, sources) -> dict:
    """Find the capillaries measured more than once and compare their velocities (`capillary.placement`)."""
    job.report(0.0, 'Reading the data sets')
    measurements = placement.load_measurements(folder.statistics, sources)
    job.report(0.2, 'Matching the lines')
    groups = placement.group_measurements(measurements)
    per_dataset, capillaries = placement.placement_tables(groups)
    comparisons = placement.compare_placements(capillaries)
    job.report(0.6, 'Writing the tables')
    report_dir = os.path.join(folder.validation, placement.REPORT_DIR)
    files = placement.write_report_tables(report_dir, per_dataset, capillaries, comparisons)
    job.report(0.7, 'Drawing the plots')
    files.update(Caper.generate_validation_report(report_dir, capillaries, comparisons, unit='capillaries'))
    return {'measurements': len(measurements), 'capillaries': len(groups), 'comparisons': comparisons,
            'files': files}


# ------------------------------------------------------------------ results browsing

def dataset_info(folder: DataFolder, stem: str, name: str, kind: str = 'velocity') -> dict:
    """What the Results page shows for one data set (run off the Tk thread)."""
    if kind == 'line':
        files = datasets.line_dataset_files(folder.statistics, stem, name)
        inputs = [files['space_time'], files['velocity']]
        images = datasets.line_report_files(folder.reports, stem, name)
        table = files['velocity']
    else:
        files = datasets.velocity_dataset_files(folder.statistics, stem, name)
        inputs = [files[part] for part in datasets.VELOCITY_INPUTS]
        images = datasets.velocity_report_files(folder.reports, stem, name)
        table = files['report']
    images = {role: path for role, path in images.items() if path.endswith('.png')}
    record = datasets.read_provenance(files['provenance'])
    summary = (record or {}).get('summary')
    if summary is None and os.path.exists(table):
        try:
            frame = pd.read_csv(table, index_col=0)
            summary = spacetime.space_time_summary(frame) if kind == 'line' else summarize_velocity_report(frame)
        except Exception:  # noqa: BLE001 - a damaged report just has no summary
            log.warning('Could not read %s', table, exc_info=True)
    existing_inputs = [path for path in inputs if os.path.exists(path)]
    modified = max((os.path.getmtime(path) for path in existing_inputs), default=None)
    return {
        'kind': kind,
        'name': name,
        'record': record,
        'summary': summary,
        'complete': len(existing_inputs) == len(inputs),
        'images': [(role, path) for role, path in images.items() if os.path.exists(path)],
        'modified': datetime.datetime.fromtimestamp(modified) if modified else None,
        'report_table': table if os.path.exists(table) else None,
    }
