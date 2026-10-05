"""The GUI's Measure button: fixed boxes over a frame range (`capillary.measure`)."""

import numpy as np
import pytest

from capillary import datasets
from capillary.flow import crop_box
from capillary.intensity import extract_traces_from_video
from capillary.measure import Cancelled, flow_region_size_bytes, measure_flow, measure_velocity
from capillary.quality import calculate_blur
from capillary.roi import ROI
from capillary.video import iter_frames

from .synthetic import expected_velocity_mm_s, make_flow_frames, write_video

FPS = 30.0
MM_PER_PIXEL = 0.002
VELOCITY_PX_PER_FRAME = 2.5
N_FRAMES = 420
ROI_DOWNSTREAM = ROI(60, 160, 12, 12)   # box 1: the blood reaches it last
ROI_UPSTREAM = ROI(60, 60, 12, 12)      # box 2: the blood reaches it first


@pytest.fixture(scope='module')
def frames():
    return make_flow_frames(n_frames=N_FRAMES, height=240, width=120,
                            velocity_px_per_frame=VELOCITY_PX_PER_FRAME, seed=11)


@pytest.fixture(scope='module', params=['mp4v', 'raw'])
def video_file(request, tmp_path_factory, frames):
    """The same clip compressed (like recordings) and uncompressed (like stabilized videos)."""
    folder = tmp_path_factory.mktemp('measure')
    if request.param == 'raw':
        path = folder / 'clip.avi'
        ok = write_video(path, frames, FPS, fourcc='')
    else:
        path = folder / 'clip.mp4'
        ok = write_video(path, frames, FPS)
    if not ok:
        pytest.skip(f'this OpenCV build cannot write {request.param} video')
    return str(path)


def test_iter_frames_can_start_mid_video(video_file):
    everything = list(iter_frames(video_file))
    part = list(iter_frames(video_file, start=100, max_frames=7))
    assert len(part) == 7
    for got, expected in zip(part, everything[100:107]):
        np.testing.assert_array_equal(got, expected)


def test_measurement_samples_exactly_what_the_cli_samples(video_file):
    measurement = measure_velocity(video_file, ROI_DOWNSTREAM, ROI_UPSTREAM, 0, N_FRAMES)
    reference = extract_traces_from_video(video_file, ROI_DOWNSTREAM, ROI_UPSTREAM)

    np.testing.assert_array_equal(measurement.trace.a, reference.a)
    np.testing.assert_array_equal(measurement.trace.b, reference.b)
    assert measurement.trace.distance_px == reference.distance_px == pytest.approx(100.0)
    assert measurement.fps == pytest.approx(FPS)
    assert measurement.frames_read == measurement.frame_count == N_FRAMES


def test_a_range_measures_only_those_frames(video_file):
    reference = extract_traces_from_video(video_file, ROI_DOWNSTREAM, ROI_UPSTREAM)
    measurement = measure_velocity(video_file, ROI_DOWNSTREAM, ROI_UPSTREAM, 50, 160)

    assert measurement.start_frame == 50 and measurement.frames_read == 110
    np.testing.assert_array_equal(measurement.trace.a, reference.a[50:160])
    np.testing.assert_array_equal(measurement.trace.b, reference.b[50:160])


def test_sharpness_is_the_same_score_frame_by_frame(video_file):
    measurement = measure_velocity(video_file, ROI_DOWNSTREAM, ROI_UPSTREAM, 10, 40)
    expected = [calculate_blur(frame) for frame in iter_frames(video_file, start=10, max_frames=30)]
    assert measurement.blur.tolist() == expected


def test_sharpness_cache_is_filled_and_reused(video_file):
    cache = {}
    first = measure_velocity(video_file, ROI_DOWNSTREAM, ROI_UPSTREAM, 0, 30, blur_cache=cache)
    assert sorted(cache) == list(range(30))
    np.testing.assert_array_equal(first.blur, [cache[i] for i in range(30)])

    cache[5] = -1.0  # a cached value is used as is
    second = measure_velocity(video_file, ROI_DOWNSTREAM, ROI_UPSTREAM, 0, 30, blur_cache=cache)
    assert second.blur[5] == -1.0


def test_progress_runs_up_to_one(video_file):
    seen = []
    measure_velocity(video_file, ROI_DOWNSTREAM, ROI_UPSTREAM, 0, 200, progress=seen.append)
    assert seen[-1] == 1.0
    assert seen == sorted(seen)


def test_cancelling_stops_the_measurement(video_file):
    calls = []

    def should_cancel():
        calls.append(1)
        return len(calls) > 20

    with pytest.raises(Cancelled):
        measure_velocity(video_file, ROI_DOWNSTREAM, ROI_UPSTREAM, 0, N_FRAMES, should_cancel=should_cancel)


@pytest.mark.parametrize('start,stop', [(-1, 10), (10, 10), (20, 5)])
def test_invalid_ranges_are_rejected(video_file, start, stop):
    with pytest.raises(ValueError):
        measure_velocity(video_file, ROI_DOWNSTREAM, ROI_UPSTREAM, start, stop)


@pytest.fixture(scope='module')
def flow_video(tmp_path_factory):
    """A 3-channel clip standing in for a flow video, uncompressed so every value survives."""
    rng = np.random.default_rng(5)
    clip = [rng.integers(0, 256, (48, 64, 3), dtype=np.uint8) for _ in range(40)]
    path = tmp_path_factory.mktemp('flow') / 'flow.avi'
    if not write_video(path, clip, FPS, fourcc=''):
        pytest.skip('this OpenCV build cannot write uncompressed video')
    return str(path)


def test_flow_measurement_collects_the_region_of_each_frame(flow_video):
    mask = (np.arange(48 * 64).reshape(48, 64) % 3 == 0).astype(np.uint8)
    bounds = (10, 30, 5, 25)
    flow, mask_regions, frames_read = measure_flow(flow_video, mask, bounds, 12, 20)

    decoded = list(iter_frames(flow_video, single_channel=False))
    assert frames_read == 8
    assert len(flow) == len(mask_regions) == 40
    for i in range(40):
        if 12 <= i < 20:
            np.testing.assert_array_equal(flow[i], crop_box(decoded[i], bounds))
            np.testing.assert_array_equal(mask_regions[i], crop_box(mask, bounds))
        else:
            assert str(flow[i]) == 'nan' and str(mask_regions[i]) == 'nan'


def test_flow_measurement_can_be_cancelled(flow_video):
    mask = np.ones((48, 64), dtype=np.uint8)
    with pytest.raises(Cancelled):
        measure_flow(flow_video, mask, (0, 10, 0, 10), 0, 40, should_cancel=lambda: True)


def test_flow_memory_estimate():
    assert flow_region_size_bytes((0, 10, 0, 20), 100) == 10 * 20 * 4 * 100
