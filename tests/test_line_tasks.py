"""The Centre line page's background work (`gui.tasks`), end to end on a synthetic recording.

A capillary loop with a known red-cell speed is written as a stabilized video
into a scratch data folder; the measurement runs as the page would run it.
"""

import json
import os
import shutil

import numpy as np
import pandas as pd
import pytest

from capillary import datasets, inventory, pattern_shift, simulate, spacetime, stabilize
from gui import library, tasks
from gui.settings import DataFolder

from .synthetic import write_video

MM_PER_PIXEL = 0.001328903654
STEM = 'FP99_line_06-Oct-2026_12-00-00'


class FakeJob:
    def __init__(self):
        self.progress = []

    def report(self, progress=None, message=None):
        if progress is not None:
            self.progress.append(progress)

    def cancelled(self):
        return False


@pytest.fixture(scope='module')
def recording(tmp_path_factory):
    clip = simulate.simulate(simulate.hairpin(), 240, 1.5, seed=4)
    folder = DataFolder(str(tmp_path_factory.mktemp('data')))
    folder.ensure()
    path = os.path.join(folder.stabilized, STEM + '.avi')
    if not write_video(path, list(clip.frames), clip.fps, fourcc=''):
        pytest.skip('this OpenCV build cannot write uncompressed video')
    line = clip.drawn_line(20, 140, seed=2)
    return folder, path, clip, [tuple(p) for p in line.points]


@pytest.fixture(scope='module')
def measured(recording):
    folder, path, clip, points = recording
    job = FakeJob()
    result = tasks.measure_line_dataset(job, folder=folder, stem=STEM, name='line1', video_path=path, points=points,
                                        start=10, end=229, mm_per_pixel=MM_PER_PIXEL, time_points=[3.0],
                                        observer='SJ')
    return result, job


def test_measurement_finds_the_known_velocity(recording, measured):
    _, _, clip, _ = recording
    result, job = measured
    truth = clip.true_velocity_mm_s(MM_PER_PIXEL)
    summary = result['summary']
    assert result['kind'] == 'line' and result['name'] == 'line1'
    assert summary['median'] == pytest.approx(truth, rel=0.05)
    assert summary['resolved_fraction'] > 0.8
    assert summary['fastest_mm_s'] > truth
    assert job.progress[0] == 0.0 and max(job.progress) <= 1.0
    assert len(result['series']['t']) == len(result['series']['v']) == summary['resolved']


def test_measurement_saves_the_data_set_and_its_report(recording, measured):
    folder, _, _, points = recording
    files = datasets.line_dataset_files(folder.statistics, STEM, 'line1')
    diagram, blocks = datasets.load_line_dataset(folder.statistics, STEM, 'line1')
    assert diagram.shape[0] == 220                               # frames 10..229
    assert blocks.index.min() == 10 + 45                         # the first block is centred 45 frames in
    record = json.load(open(files['provenance'], encoding='utf-8'))
    assert record['kind'] == 'line' and record['frames'] == {'first': 10, 'last': 229, 'count': 220}
    assert [tuple(p) for p in record['line']['points']] == [tuple(round(v, 2) for v in p) for p in points]
    assert record['estimator']['min_snr'] == pytest.approx(8.0)
    assert record['pattern_shift']['bandpass_px'] == [1.0, 4.0]
    assert record['time_points_s'] == [3.0]
    assert record['observer'] == 'SJ'
    assert record['line']['role'] is None and record['summary']['limb_check'] == ''
    assert record['summary']['phase'] == ''                       # this recording has no official times
    assert record['picture'] is None                              # nor a shift file: it was not stabilized here
    for path in datasets.line_report_files(folder.reports, STEM, 'line1').values():
        assert os.path.isfile(path)
    summary_row = pd.read_csv(datasets.line_report_files(folder.reports, STEM, 'line1')['summary'])
    assert summary_row['median'].iloc[0] == pytest.approx(measured[0]['summary']['median'])


def test_the_library_and_the_results_page_see_it(recording, measured):
    folder = recording[0]
    found = {r.stem: r for r in library.scan(folder)}[STEM]
    assert found.line_sets == ['line1'] and found.velocity_sets == []
    info = tasks.dataset_info(folder, STEM, 'line1', 'line')
    assert info['kind'] == 'line' and info['complete']
    assert {role for role, _ in info['images']} == {'line_velocity', 'space_time'}
    assert info['summary']['median'] == pytest.approx(measured[0]['summary']['median'])


def test_the_report_can_be_regenerated_without_the_video(recording, measured, tmp_path):
    folder, path, clip, _ = recording
    result = tasks.regenerate_line_report(FakeJob(), folder=folder, stem=STEM, name='line1', fps=clip.fps,
                                          mm_per_pixel=MM_PER_PIXEL, time_points=[2.0, 5.0])
    assert result['summary']['median'] == pytest.approx(measured[0]['summary']['median'])
    pooled = measured[0]['summary']['pattern_shift_velocity_mm_s']
    assert result['summary']['pattern_shift_velocity_mm_s'] == pytest.approx(pooled, rel=1e-4)    # float32 on disk
    record = datasets.read_provenance(datasets.line_dataset_files(folder.statistics, STEM, 'line1')['provenance'])
    assert record['time_points_s'] == [2.0, 5.0] and 'report_regenerated' in record


def test_an_arterial_limb_is_checked_by_the_direction_of_its_flow(recording, monkeypatch):
    folder, path, clip, points = recording
    # official times that put the occlusion 5 s and the release 6 s into this 8-s recording
    monkeypatch.setattr(inventory, '_times_by_name', lambda _folder: {STEM: (5.0, 6.0)})
    results = {}
    for name, line in (('limb', points), ('from_apex', points[::-1])):      # the line runs up the arterial limb
        results[name] = tasks.measure_line_dataset(
            FakeJob(), folder=folder, stem=STEM, name=name, video_path=path, points=line, start=10, end=229,
            mm_per_pixel=MM_PER_PIXEL, role=pattern_shift.ARTERIAL_LIMB)
    summary = results['limb']['summary']
    assert summary['pattern_shift_velocity_mm_s'] == pytest.approx(clip.true_velocity_mm_s(MM_PER_PIXEL), rel=0.05)
    assert (summary['line_role'], summary['limb_check']) == ('arterial limb', 'arterial')
    assert results['from_apex']['summary']['limb_check'] == 'venous'     # against the flow, as in a venous limb
    assert summary['phase'] == 'rest + occlusion + after release'
    record = datasets.read_provenance(datasets.line_dataset_files(folder.statistics, STEM, 'limb')['provenance'])
    assert record['line']['role'] == 'arterial limb' and record['summary']['limb_check'] == 'arterial'
    row = pd.read_csv(datasets.line_report_files(folder.reports, STEM, 'limb')['summary'])
    assert row['pattern_shift_velocity_mm_s'].iloc[0] == pytest.approx(summary['pattern_shift_velocity_mm_s'])
    assert row['limb_check'].iloc[0] == 'arterial' and row['phase'].iloc[0] == 'rest + occlusion + after release'
    regenerated = tasks.regenerate_line_report(FakeJob(), folder=folder, stem=STEM, name='limb', fps=clip.fps,
                                               mm_per_pixel=MM_PER_PIXEL)
    assert regenerated['summary']['limb_check'] == 'arterial'           # the role is kept from the provenance


def test_a_whole_loop_names_its_arterial_end_and_measures_each_limb(recording):
    folder, path, clip, _ = recording
    total = clip.centreline.length_px
    results = {}
    for name, (start, end) in (('loop', (20, total - 20)), ('loop_back', (total - 20, 20))):
        points = [tuple(p) for p in clip.drawn_line(start, end, seed=2).points]
        results[name] = tasks.measure_line_dataset(
            FakeJob(), folder=folder, stem=STEM, name=name, video_path=path, points=points, start=10, end=229,
            mm_per_pixel=MM_PER_PIXEL, role=pattern_shift.WHOLE_LOOP)
    summary = results['loop']['summary']
    truth = clip.true_velocity_mm_s(MM_PER_PIXEL)
    assert summary['pattern_shift_velocity_mm_s'] == pytest.approx(truth, rel=0.05)
    assert (summary['line_role'], summary['arterial_end'], summary['limb_check']) == ('whole loop', 'start', '')
    for limb in ('start_limb', 'end_limb'):                    # each limb on its own, along the line
        assert summary[f'pattern_shift_{limb}_mm_s'] == pytest.approx(truth, rel=0.1)
    assert summary['loop_movement'] is False
    assert results['loop_back']['summary']['arterial_end'] == 'end'
    record = datasets.read_provenance(datasets.line_dataset_files(folder.statistics, STEM, 'loop')['provenance'])
    assert record['line']['role'] == 'whole loop' and record['summary']['arterial_end'] == 'start'
    regenerated = tasks.regenerate_line_report(FakeJob(), folder=folder, stem=STEM, name='loop', fps=clip.fps,
                                               mm_per_pixel=MM_PER_PIXEL)
    assert regenerated['summary']['arterial_end'] == 'start'           # the role and the line from the provenance
    assert regenerated['summary']['pattern_shift_start_limb_mm_s'] == pytest.approx(
        summary['pattern_shift_start_limb_mm_s'], rel=1e-4)


def test_the_preview_measures_the_frames_around_the_playhead(recording):
    _, path, clip, points = recording
    preview = tasks.line_preview(path, points, 60, 120, MM_PER_PIXEL)
    assert preview['diagram'].shape[0] == 120
    assert preview['resolved']
    assert preview['velocity'] == pytest.approx(clip.true_velocity_mm_s(MM_PER_PIXEL), rel=0.08)
    slowest, fastest = preview['limits_mm_s']
    assert slowest < preview['velocity'] < fastest


def test_a_failed_measurement_leaves_nothing_behind(recording):
    folder, path, _, points = recording

    class Failing(FakeJob):
        def report(self, progress=None, message=None):
            if message == 'Saving the data set':
                raise RuntimeError('disk full')

    with pytest.raises(RuntimeError):
        tasks.measure_line_dataset(Failing(), folder=folder, stem=STEM, name='broken', video_path=path,
                                   points=points, start=0, end=150, mm_per_pixel=MM_PER_PIXEL)
    assert datasets.dataset_paths(folder.statistics, folder.reports, STEM, 'broken', 'line') == []


def test_a_line_that_reaches_the_black_strip_is_refused(recording):
    """On a stabilized video, a line is measured only over frames that all show the picture under it."""
    folder, path, clip, points = recording
    stem = 'FP99_edge_06-Oct-2026_12-00-00'
    video = os.path.join(folder.stabilized, stem + '.avi')
    shutil.copyfile(path, video)
    x0, y0, x1, y1 = spacetime.SpaceTimeSampler(spacetime.Centreline.from_points(points)).bounds
    moves = np.zeros((len(clip.frames), 2))
    moves[100:110, 0] = x0 - 1                     # the picture had moved left: a black strip up to x0 - 1
    frames = np.arange(len(clip.frames))
    pd.DataFrame({'frame': frames, 'time_s': frames / clip.fps, 'shift_x_px': moves[:, 0], 'shift_y_px': moves[:, 1],
                  'placed_by': 'references'}).to_csv(stabilize.record_paths(video)['shifts'], index=False)
    with pytest.raises(ValueError, match="In 10 of the range's 220 frames the line reaches the black strip"):
        tasks.measure_line_dataset(FakeJob(), folder=folder, stem=stem, name='edge', video_path=video,
                                   points=points, start=10, end=229, mm_per_pixel=MM_PER_PIXEL)
    assert datasets.dataset_paths(folder.statistics, folder.reports, stem, 'edge', 'line') == []

    tasks.measure_line_dataset(FakeJob(), folder=folder, stem=stem, name='clear', video_path=video, points=points,
                               start=110, end=229, mm_per_pixel=MM_PER_PIXEL)
    record = datasets.read_provenance(datasets.line_dataset_files(folder.statistics, stem, 'clear')['provenance'])
    height, width = clip.frames[0].shape
    assert record['picture']['area_px'] == [3.0, 3.0, width - 4.0, height - 4.0]   # no move: 3 px off the frame's edge
    nearest = min(x0 - 3.0, y0 - 3.0, width - 4.0 - x1, height - 4.0 - y1)
    assert record['picture']['clearance_px'] == pytest.approx(nearest, abs=0.01) and nearest > 0


def test_too_short_a_range_is_refused(recording):
    folder, path, _, points = recording
    with pytest.raises(ValueError, match='at least'):
        tasks.measure_line_dataset(FakeJob(), folder=folder, stem=STEM, name='short', video_path=path,
                                   points=points, start=0, end=40, mm_per_pixel=MM_PER_PIXEL)
    assert not np.any([os.path.exists(p) for p in datasets.line_dataset_files(folder.statistics, STEM,
                                                                              'short').values()])
