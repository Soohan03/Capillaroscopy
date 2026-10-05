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
from capillary import datasets
from capillary.intensity import extract_traces
from capillary.measure import measure_flow, measure_velocity
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
    """Close the captures and writer a Caper processing object holds."""
    for owner in (process, getattr(process, 'video', None)):
        if owner is None:
            continue
        for attribute in ('cap', 'writer'):
            handle = getattr(owner, attribute, None)
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

    Each file keeps its place relative to the data folder, so the raw,
    stabilized and flow videos of a recording (which share a file name) stay
    apart and can be put back where they were.
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
    """Every file that belongs to `recording`: videos, data sets, reports, time points."""
    paths = [recording.raw, recording.stabilized, recording.flow, recording.flow_summary]
    for name in recording.velocity_sets:
        paths += datasets.dataset_paths(folder.statistics, folder.reports, recording.stem, name, 'velocity')
    for name in recording.flow_sets:
        paths += datasets.dataset_paths(folder.statistics, folder.reports, recording.stem, name, 'flow')
    paths.append(datasets.time_points_file(folder.statistics, recording.stem))
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


def compute_flow(job, folder: DataFolder, stabilized_path: str) -> str:
    """Dense optical flow of a stabilized video into Flows/ (Caper.FlowVideo)."""
    name = os.path.basename(stabilized_path)
    final = os.path.join(folder.flows, name)
    final_summary = os.path.splitext(final)[0] + '.pickle'
    partial_dir = folder.partial(folder.flows)
    os.makedirs(partial_dir, exist_ok=True)
    partial = os.path.join(partial_dir, name)
    partial_summary = os.path.splitext(partial)[0] + '.pickle'

    job.report(0.0, 'Computing optical flow')
    process = Caper.FlowVideo(path=stabilized_path)
    process.output_path = partial
    total = max(1, process.video.number_of_frames_)
    try:
        while process.current_stage != 'finished':
            job.report(max(0, process.video.get_frame_number()) / total, 'Computing optical flow')
            process.update()
        _release(process)
        previous = [path for path in (final, final_summary) if os.path.exists(path)]
        if previous:
            move_to_trash(folder, previous, f'{os.path.splitext(name)[0]} previous optical flow')
        # the summary first: the library lists a flow video only once its summary exists
        os.replace(partial_summary, final_summary)
        os.replace(partial, final)
    finally:
        _release(process)
        _remove(partial)
        _remove(partial_summary)
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


def flow_summary(up, down, both) -> dict:
    def median(values):
        values = np.asarray(values, dtype=float)
        values = values[np.isfinite(values)]
        return float(np.median(values)) if values.size else float('nan')
    return {'frames': int(np.isfinite(np.asarray(both, dtype=float)).sum()),
            'median_up': median(up), 'median_down': median(down), 'median_both': median(both)}


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
    return {'kind': 'velocity', 'stem': stem, 'name': name, 'summary': summary,
            'series': velocity_series(report), 'record': record}


def measure_flow_dataset(job, *, folder: DataFolder, stem: str, name: str, flow_path: str, mask,
                         bounds, start: int, end: int, mm_per_pixel: float) -> dict:
    """Collect the region `bounds` of flow frames ``start..end`` (inclusive), save it, write the report."""
    job.report(0.0, 'Reading flow frames')
    info = probe_video(flow_path)
    flow, mask_regions, frames_read = measure_flow(flow_path, mask, bounds, start, end + 1,
                                                   progress=lambda p: job.report(0.55 * p, 'Reading flow frames'),
                                                   should_cancel=job.cancelled)
    if frames_read == 0:
        raise ValueError('No frames could be read from the flow video in that range.')
    files = datasets.flow_dataset_files(folder.statistics, stem, name)
    try:
        job.report(0.6, 'Saving the data set')
        datasets.write_flow_dataset(folder.statistics, stem, name, flow, mask_regions)
        job.report(0.75, 'Drawing the flow report')
        up, down, both = Caper.generate_flow_report(flow, mask_regions, info.fps, mm_per_pixel,
                                                    datasets.dataset_prefix(folder.reports, stem, name))
        summary = flow_summary(up, down, both)
        x_left, x_right, y_top, y_bottom = (int(v) for v in bounds)
        record = {
            'kind': 'flow',
            'dataset': name,
            'recording': stem,
            'created': datetime.datetime.now().isoformat(timespec='seconds'),
            'video': _video_record(flow_path, info),
            'frames': {'first': start, 'last': start + frames_read - 1, 'count': frames_read},
            'region': {'x_left': x_left, 'x_right': x_right, 'y_top': y_top, 'y_bottom': y_bottom,
                       'width_px': x_right - x_left, 'height_px': y_bottom - y_top,
                       'vessel_pixels': int(np.sum(mask[y_top:y_bottom, x_left:x_right])),
                       'coordinates': 'slice bounds in video pixels: frame[y_top:y_bottom, x_left:x_right]'},
            'mm_per_pixel': mm_per_pixel,
            'units': 'flow per frame: optical-flow displacement summed over the region, in mm, '
                     'divided by the number of vessel pixels in it',
            'summary': summary,
            'software': datasets.software_version(),
        }
        datasets.write_provenance(files['provenance'], record)
    except BaseException:
        for path in datasets.dataset_paths(folder.statistics, folder.reports, stem, name, 'flow'):
            _remove(path)
        raise
    return {'kind': 'flow', 'stem': stem, 'name': name, 'summary': summary, 'record': record,
            'series': {'t': (np.arange(len(both)) / (info.fps or 30)).tolist(), 'v': np.asarray(both).tolist()}}


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


def regenerate_flow_report(job, *, folder: DataFolder, stem: str, name: str, fps: float, mm_per_pixel: float) -> dict:
    job.report(0.0, 'Loading the flow data set')
    flow, mask = datasets.load_flow_dataset(folder.statistics, stem, name)
    job.report(0.4, 'Drawing the flow report')
    up, down, both = Caper.generate_flow_report(flow, mask, fps, mm_per_pixel,
                                                datasets.dataset_prefix(folder.reports, stem, name))
    return {'kind': 'flow', 'stem': stem, 'name': name, 'summary': flow_summary(up, down, both)}


# ------------------------------------------------------------------ results browsing

def dataset_info(folder: DataFolder, stem: str, name: str, kind: str) -> dict:
    """What the Results page shows for one data set (run off the Tk thread)."""
    if kind == 'velocity':
        files = datasets.velocity_dataset_files(folder.statistics, stem, name)
        inputs = [files[part] for part in datasets.VELOCITY_INPUTS]
        images = datasets.velocity_report_files(folder.reports, stem, name)
        images = {role: path for role, path in images.items() if path.endswith('.png')}
    else:
        files = datasets.flow_dataset_files(folder.statistics, stem, name)
        inputs = [files[part] for part in datasets.FLOW_INPUTS]
        images = datasets.flow_report_files(folder.reports, stem, name)
    record = datasets.read_provenance(files['provenance'])
    summary = (record or {}).get('summary')
    if summary is None and kind == 'velocity' and os.path.exists(files['report']):
        try:
            summary = summarize_velocity_report(pd.read_csv(files['report'], index_col=0))
        except Exception:  # noqa: BLE001 - a damaged report just has no summary
            log.warning('Could not read %s', files['report'], exc_info=True)
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
        'report_table': files.get('report') if kind == 'velocity' and os.path.exists(files.get('report', '')) else None,
    }
