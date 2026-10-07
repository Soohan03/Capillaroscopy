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
from capillary import datasets, spacetime, validation
from capillary.intensity import extract_traces
from capillary.measure import measure_velocity
from capillary.roi import ROI
from capillary.velocity import (DEFAULT_WINDOWS, lag_and_correlation, resolvable_range, velocity_from_lag,
                                velocity_summary)
from capillary.video import iter_frames, probe_video

from .library import Recording
from .settings import DataFolder

log = logging.getLogger(__name__)

_MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


# ------------------------------------------------------------------------- helpers

def _remove(path: Optional[str]) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            log.warning('Could not remove %s', path, exc_info=True)


def _release(process) -> None:
    """Close the capture and writer a Caper processing object holds."""
    for attribute in ('cap', 'writer'):
        handle = getattr(process, attribute, None)
        if handle is not None:
            try:
                handle.release()
            except Exception:  # noqa: BLE001 - best effort while cleaning up
                pass


def available_memory_bytes() -> Optional[int]:
    """Memory available to new allocations (Linux), or None if unknown."""
    try:
        with open('/proc/meminfo') as handle:
            for line in handle:
                if line.startswith('MemAvailable:'):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def stabilization_memory_bytes(frame_count: int, width: int, height: int) -> int:
    """`Caper.VideoStabilization` holds the raw and the filtered video as float64 arrays."""
    return 2 * frame_count * width * height * 8


def check_stabilization_memory(path: str) -> None:
    """Refuse to start a stabilization that would exhaust memory and take the app down."""
    info = probe_video(path)
    needed = stabilization_memory_bytes(info.frame_count, info.width, info.height)
    available = available_memory_bytes()
    if available is not None and needed > 0.85 * available:
        raise MemoryError(
            f'Stabilizing this video needs about {needed / 1e9:.1f} GB of memory, but only '
            f'{available / 1e9:.1f} GB is available. The stabilizer keeps the whole video in memory '
            f'({info.frame_count} frames); a shorter recording or more memory is needed.')


def recording_name(prefix: str = '', when: Optional[datetime.datetime] = None, time_text: Optional[str] = None) -> str:
    """``<prefix>_05-Oct-2026_14-03-22``: the stem of a recording started at `when`.

    The date format matches the existing recordings (e.g. 22-Oct-2019_09-46-17),
    independent of the system language. `time_text` replaces the time of day
    (for showing the pattern before a recording starts).
    """
    when = when or datetime.datetime.now()
    stamp = f'{when.day:02d}-{_MONTHS[when.month - 1]}-{when.year}_{time_text or f"{when:%H-%M-%S}"}'
    return f'{datasets.safe_file_part(prefix)}_{stamp}' if prefix.strip() else stamp


def new_recording_path(folder: DataFolder, prefix: str = '', extension: str = '.avi') -> str:
    """A fresh file name in RecordedVideos/: ``<prefix>_<05-Oct-2026_14-03-22>.avi``."""
    base = recording_name(prefix)
    path = os.path.join(folder.recorded, base + extension)
    counter = 2
    while os.path.exists(path):
        path = os.path.join(folder.recorded, f'{base}_{counter}{extension}')
        counter += 1
    return path


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


def recording_files(folder: DataFolder, recording: Recording) -> list[str]:
    """Every file that belongs to `recording`: videos, data sets, reports, time points, old flow files."""
    paths = [recording.raw, recording.stabilized]
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
    """Stabilize a raw recording into StabilizedVideos/ (Caper.VideoStabilization)."""
    check_stabilization_memory(raw_path)
    name = os.path.basename(raw_path)
    final = os.path.join(folder.stabilized, name)
    partial_dir = folder.partial(folder.stabilized)
    os.makedirs(partial_dir, exist_ok=True)
    partial = os.path.join(partial_dir, name)

    stages = ('load', 'transform', 'stabilize', 'write')
    labels = {'load': 'Loading frames', 'transform': 'Enhancing contrast',
              'stabilize': 'Registering frames', 'write': 'Writing the stabilized video'}
    job.report(0.0, labels['load'])
    process = Caper.VideoStabilization(path=raw_path)
    process.output_path = partial
    try:
        while process.current_stage != 'finished':
            stage = process.current_stage
            fraction = (stages.index(stage) + process.index / max(1, process.number_of_frames_)) / len(stages)
            job.report(fraction, labels[stage])
            process.update()
        _release(process)
        if os.path.exists(final):
            move_to_trash(folder, [final], f'{os.path.splitext(name)[0]} previous stabilized video')
        os.replace(partial, final)
    finally:
        _release(process)
        _remove(partial)
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


def measure_velocity_dataset(job, *, folder: DataFolder, stem: str, name: str, video_path: str,
                             box1: ROI, box2: ROI, start: int, end: int, mm_per_pixel: float,
                             time_points=(), blur_cache=None) -> dict:
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
        slowest, fastest = resolvable_range(trace.distance_px, measurement.fps, mm_per_pixel)
        record = {
            'kind': 'velocity',
            'dataset': name,
            'recording': stem,
            'created': datetime.datetime.now().isoformat(timespec='seconds'),
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


def _estimator_record() -> dict:
    return {'method': 'capillary.spacetime: slope of the streaks in the space-time diagram (Radon transform '
                      'evaluated in the Fourier domain, mirror line subtracted)',
            'block_frames': spacetime.DEFAULT_BLOCK_FRAMES, 'step_frames': spacetime.DEFAULT_STEP_FRAMES,
            'min_snr': spacetime.MIN_SNR, 'min_coherence': spacetime.MIN_COHERENCE, 'k_max': spacetime.K_MAX,
            'omega_taper': [spacetime.TAPER_START, spacetime.MAX_OMEGA],
            'fastest_fraction': spacetime.FASTEST_FRACTION, 'half_width_px': spacetime.DEFAULT_HALF_WIDTH_PX}


def measure_line_dataset(job, *, folder: DataFolder, stem: str, name: str, video_path: str, points,
                         start: int, end: int, mm_per_pixel: float, time_points=()) -> dict:
    """Measure frames ``start..end`` (inclusive) along the centre line, save the data set, write its report."""
    info = probe_video(video_path)
    line = spacetime.Centreline.from_points(points)
    sampler = spacetime.SpaceTimeSampler(line)
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
                                          progress=lambda p: job.report(0.5 + 0.4 * p, 'Measuring the streaks'))
    files = datasets.line_dataset_files(folder.statistics, stem, name)
    try:
        job.report(0.92, 'Saving the data set')
        datasets.write_line_dataset(folder.statistics, stem, name, diagram, blocks)
        summary = summarize_line_blocks(blocks, line.length_px, info.fps, mm_per_pixel)
        Caper.generate_line_report(datasets.dataset_prefix(folder.reports, stem, name), diagram, blocks, info.fps,
                                   mm_per_pixel, start, sorted(time_points), summary)
        record = {
            'kind': 'line',
            'dataset': name,
            'recording': stem,
            'created': datetime.datetime.now().isoformat(timespec='seconds'),
            'video': _video_record(video_path, info),
            'frames': {'first': start, 'last': start + len(rows) - 1, 'count': len(rows)},
            'line': {'points': [[round(x, 2), round(y, 2)] for x, y in line.points],
                     'length_px': line.length_px,
                     'length_um': line.length_px * mm_per_pixel * 1000.0,
                     'coordinates': 'clicked points in video pixels, x to the right, y down from the top-left '
                                    'corner; positive velocity runs from the first point towards the last'},
            'mm_per_pixel': mm_per_pixel,
            'resolvable_mm_per_s': {'slowest': summary['slowest_mm_s'], 'fastest': summary['fastest_mm_s']},
            'time_points_s': sorted(float(t) for t in time_points),
            'estimator': _estimator_record(),
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
                                          progress=lambda p: job.report(0.1 + 0.75 * p, 'Measuring the streaks'))
    blocks.to_csv(files['velocity'])
    length = ((record or {}).get('line') or {}).get('length_px') or float(diagram.shape[1] - 1)
    summary = summarize_line_blocks(blocks, length, fps, mm_per_pixel)
    job.report(0.9, 'Drawing the report')
    Caper.generate_line_report(datasets.dataset_prefix(folder.reports, stem, name), diagram, blocks, fps,
                               mm_per_pixel, first, sorted(time_points), summary)
    if record is not None:
        record.update(summary=summary, estimator=_estimator_record(), mm_per_pixel=mm_per_pixel,
                      time_points_s=sorted(float(t) for t in time_points),
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
