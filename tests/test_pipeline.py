"""End-to-end: pixels in, mm/s out, checked against a known velocity."""

import pytest

import cv2

from capillary.cli import main, parse_size, read_mm_per_pixel
from capillary.intensity import extract_traces, extract_traces_from_video
from capillary.roi import ROI
from capillary.velocity import analyze_trace, signed_lag
from capillary.video import probe_video

from .synthetic import expected_lag_frames, expected_velocity_mm_s, make_flow_frames

FPS = 30.0
MM_PER_PIXEL = 0.002
VELOCITY_PX_PER_FRAME = 2.5
UPSTREAM_Y, DOWNSTREAM_Y = 60, 160          # pattern travels towards +y
SEPARATION_PX = DOWNSTREAM_Y - UPSTREAM_Y   # 100 px


@pytest.fixture(scope='module')
def frames():
    return make_flow_frames(
        n_frames=500, height=240, width=120,
        velocity_px_per_frame=VELOCITY_PX_PER_FRAME, seed=7,
    )


@pytest.fixture(scope='module')
def rois():
    """Rectangle 1 downstream and rectangle 2 upstream, as the GUI expects."""
    return ROI(60, DOWNSTREAM_Y, 10, 10), ROI(60, UPSTREAM_Y, 10, 10)


def test_traces_are_sampled_once_per_frame(frames, rois):
    roi_a, roi_b = rois
    trace = extract_traces(frames, roi_a, roi_b, fps=FPS)

    assert trace.n_frames == len(frames)
    assert trace.valid_count() == len(frames)
    assert trace.distance_px == pytest.approx(SEPARATION_PX)
    # A moving pattern, not a constant field.
    assert trace.a.std() > 5


def test_lag_between_the_boxes_matches_the_true_transit_time(frames, rois):
    roi_a, roi_b = rois
    trace = extract_traces(frames, roi_a, roi_b, fps=FPS)

    # Rectangle 2 (upstream) sees each feature first, so trace a lags trace b.
    expected = expected_lag_frames(SEPARATION_PX, VELOCITY_PX_PER_FRAME)
    assert signed_lag(trace.a[:301], trace.b[:301]) == pytest.approx(-expected, abs=1)


def test_pipeline_recovers_the_known_velocity(frames, rois):
    roi_a, roi_b = rois
    trace = extract_traces(frames, roi_a, roi_b, fps=FPS)
    report = analyze_trace(trace, mm_per_pixel=MM_PER_PIXEL)

    expected = expected_velocity_mm_s(VELOCITY_PX_PER_FRAME, FPS, MM_PER_PIXEL)
    # Default direction is b -> a, which is the true direction of flow here.
    assert report['velocity'].median() == pytest.approx(expected, rel=0.05)
    assert report['correlation'].median() > 0.9


def test_a_faster_flow_reads_as_a_faster_velocity(rois):
    roi_a, roi_b = rois
    velocities = []
    for speed in (2.0, 4.0):
        trace = extract_traces(
            make_flow_frames(n_frames=400, height=240, width=120,
                             velocity_px_per_frame=speed, seed=3),
            roi_a, roi_b, fps=FPS,
        )
        report = analyze_trace(trace, mm_per_pixel=MM_PER_PIXEL, windows=(201,))
        velocities.append(report['velocity'].median())

    assert velocities[1] > velocities[0]
    assert velocities[1] / velocities[0] == pytest.approx(2.0, rel=0.1)


def test_legacy_lag_overestimates_this_known_velocity(frames, rois):
    """The old formula reports this clip as flowing measurably faster than it is."""
    roi_a, roi_b = rois
    trace = extract_traces(frames, roi_a, roi_b, fps=FPS)
    truth = expected_velocity_mm_s(VELOCITY_PX_PER_FRAME, FPS, MM_PER_PIXEL)

    fixed = analyze_trace(trace, mm_per_pixel=MM_PER_PIXEL, windows=(201,))
    legacy = analyze_trace(trace, mm_per_pixel=MM_PER_PIXEL, windows=(201,), legacy_lag=True)

    assert abs(fixed['velocity'].median() - truth) < abs(legacy['velocity'].median() - truth)
    assert legacy['velocity'].median() > truth


def test_empty_input_is_rejected(rois):
    roi_a, roi_b = rois
    with pytest.raises(ValueError, match='no frames'):
        extract_traces([], roi_a, roi_b)


def write_video(path, frames, fps=FPS):
    """Encode frames to `path`; returns False if this build cannot encode."""
    height, width = frames[0].shape
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    if not writer.isOpened():
        return False
    for frame in frames:
        writer.write(cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR))
    writer.release()
    return True


@pytest.fixture(scope='module')
def video_file(tmp_path_factory, frames):
    path = tmp_path_factory.mktemp('videos') / 'synthetic_flow.mp4'
    if not write_video(path, frames):
        pytest.skip('this OpenCV build cannot write mp4v')
    return path


def test_probe_reads_container_metadata(video_file, frames):
    info = probe_video(video_file)

    assert (info.width, info.height) == (120, 240)
    assert info.fps == pytest.approx(FPS, rel=0.01)
    assert info.frame_count == len(frames)


def test_missing_video_is_reported_clearly(tmp_path):
    with pytest.raises(FileNotFoundError):
        probe_video(tmp_path / 'not_here.mp4')


def test_decoded_video_gives_the_same_velocity_as_the_raw_frames(video_file, rois):
    roi_a, roi_b = rois
    trace = extract_traces_from_video(video_file, roi_a, roi_b)
    report = analyze_trace(trace, mm_per_pixel=MM_PER_PIXEL, windows=(201,))

    expected = expected_velocity_mm_s(VELOCITY_PX_PER_FRAME, FPS, MM_PER_PIXEL)
    assert report['velocity'].median() == pytest.approx(expected, rel=0.05)


def test_max_frames_limits_the_read(video_file, rois):
    roi_a, roi_b = rois
    trace = extract_traces_from_video(video_file, roi_a, roi_b, max_frames=120)
    assert trace.n_frames == 120


def test_cli_writes_a_report(video_file, tmp_path, capsys):
    import pandas as pd

    out = tmp_path / 'report.csv'
    summary = tmp_path / 'summary.csv'
    exit_code = main([
        str(video_file),
        '--roi1', f'60,{DOWNSTREAM_Y}',
        '--roi2', f'60,{UPSTREAM_Y}',
        '--mm-per-pixel', str(MM_PER_PIXEL),
        '--windows', '201',
        '--step', '5',
        '--out', str(out),
        '--summary-out', str(summary),
    ])

    assert exit_code == 0
    report = pd.read_csv(out)
    expected = expected_velocity_mm_s(VELOCITY_PX_PER_FRAME, FPS, MM_PER_PIXEL)
    assert report['velocity'].median() == pytest.approx(expected, rel=0.05)

    assert list(pd.read_csv(summary).columns) == ['frame', 'time_s', 'velocity', 'correlation']
    assert 'velocity' in capsys.readouterr().out


def test_cli_reports_a_missing_file_without_a_traceback(tmp_path, capsys):
    exit_code = main([str(tmp_path / 'missing.mp4'), '--roi1', '10,10', '--roi2', '10,20'])

    assert exit_code == 1
    assert 'error' in capsys.readouterr().err


def test_cli_rejects_a_malformed_roi(video_file):
    with pytest.raises(SystemExit):
        main([str(video_file), '--roi1', 'nope', '--roi2', '10,20'])


def test_size_parsing():
    assert parse_size('10x20') == (10, 20)
    assert parse_size('12') == (12, 12)


def test_calibration_is_read_from_settings(tmp_path):
    settings = tmp_path / 'settings.csv'
    settings.write_text(',0\nApplication_path,/somewhere\nmm_per_pixel,0.00123\n')

    assert read_mm_per_pixel(str(settings)) == pytest.approx(0.00123)
    assert read_mm_per_pixel(str(tmp_path / 'absent.csv')) is None
