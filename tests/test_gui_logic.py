"""The GUI's non-visual logic: settings, the recording list, the trash, background jobs.

None of these tests opens a window, so they run headless like the rest of the suite.
"""

import datetime
import os
import threading
import time

import pytest

from capillary import datasets
from gui import library, tasks
from gui.jobs import JobManager
from gui.media import format_time
from gui.settings import DataFolder, Settings


def touch(path, content=b''):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as handle:
        handle.write(content)
    return path


@pytest.fixture
def folder(tmp_path):
    data = DataFolder(str(tmp_path / 'data'))
    data.ensure()
    return data


# ---------------------------------------------------------------------- settings

def test_settings_round_trip_keeps_rows_it_does_not_know(tmp_path):
    path = tmp_path / 'settings.csv'
    path.write_text(',0\nApplication_path,/data\nmm_per_pixel,0.002\nsomething_else,42\n')
    settings = Settings.load(str(path))
    assert (settings.data_folder, settings.mm_per_pixel, settings.box_size) == ('/data', 0.002, 12)
    settings.box_size = 20
    settings.save()
    again = Settings.load(str(path))
    assert (again.data_folder, again.mm_per_pixel, again.box_size) == ('/data', 0.002, 20)
    assert again.extra == {'something_else': '42'}
    assert path.read_text().splitlines()[:3] == [',0', 'Application_path,/data', 'mm_per_pixel,0.002']


def test_settings_first_start_and_unusable_values(tmp_path):
    assert Settings.load(str(tmp_path / 'missing.csv')) is None
    path = tmp_path / 'settings.csv'
    path.write_text(',0\nmm_per_pixel,0.002\n')
    assert Settings.load(str(path)) is None  # no data folder chosen yet
    path.write_text(',0\nApplication_path,/data\nmm_per_pixel,abc\nbox_size,1\n')
    settings = Settings.load(str(path))
    assert settings.mm_per_pixel == pytest.approx(0.001328903654)
    assert settings.box_size == 12


# --------------------------------------------------------------------- the library

def test_scan_groups_the_files_of_each_recording(folder):
    assert not os.path.exists(folder.flows)  # new data folders get no Flows/ any more
    assert library.scan(folder) == []
    touch(os.path.join(folder.recorded, 'FP01.avi'))
    touch(os.path.join(folder.stabilized, 'FP01.avi'))
    touch(os.path.join(folder.recorded, 'FP01_b.avi'))
    touch(os.path.join(folder.stabilized, 'FP02.mp4'))
    touch(os.path.join(folder.stabilized, '.partial', 'FP03.avi'))   # an unfinished job's output
    touch(os.path.join(folder.stabilized, 'notes.txt'))
    for stem, name in (('FP01', 'Test'), ('FP01', 'Test2'), ('FP01_b', 'set1'), ('FP01', 'old___name'),
                       ('FP09', 'orphan')):
        touch(datasets.velocity_dataset_files(folder.statistics, stem, name)['cross_correlation'])

    recordings = {recording.stem: recording for recording in library.scan(folder)}
    assert sorted(recordings) == ['FP01', 'FP01_b', 'FP02']
    fp01 = recordings['FP01']
    assert fp01.video == fp01.stabilized and fp01.raw
    assert fp01.velocity_sets == ['Test', 'Test2', 'old___name'] and fp01.dataset_count == 3
    assert recordings['FP01_b'].velocity_sets == ['set1'] and recordings['FP01_b'].video.endswith('FP01_b.avi')
    assert recordings['FP02'].is_stabilized and recordings['FP02'].dataset_count == 0
    assert all(recording.legacy_flow_files == [] for recording in recordings.values())


def old_flow_files(folder, stem, name):
    """The files the removed optical-flow feature left for `stem`: flow video, summary, one data set."""
    paths = [os.path.join(folder.flows, stem + '.avi'), os.path.join(folder.flows, stem + '.pickle')]
    prefix = f'{stem}___{name}___'
    paths += [os.path.join(folder.statistics, prefix + part) for part in ('flow.pickle', 'mask.pickle')]
    paths += [os.path.join(folder.reports, prefix + part) for part in ('up_and_down_.png', 'omnidirectional_.png')]
    return [touch(path, path.encode()) for path in paths]


def test_old_flow_files_are_not_listed_but_belong_to_their_recording(folder):
    touch(os.path.join(folder.stabilized, 'FP01.avi'))
    old = old_flow_files(folder, 'FP01', 'region')
    old_flow_files(folder, 'FP04', '')   # flow of a recording whose videos are gone

    recordings = library.scan(folder)
    assert [recording.stem for recording in recordings] == ['FP01']
    fp01 = recordings[0]
    assert fp01.velocity_sets == [] and fp01.dataset_count == 0
    assert sorted(fp01.legacy_flow_files) == sorted(old)


# ------------------------------------------------------------------------ the trash

def test_moving_a_recording_to_the_trash_keeps_every_file(folder):
    stem = 'FP01_W_14-Oct-2019_08-36-26'
    videos = {path: path.encode() for path in (
        os.path.join(folder.recorded, stem + '.avi'),
        os.path.join(folder.stabilized, stem + '.avi'))}
    for path, content in videos.items():
        touch(path, content)
    old = old_flow_files(folder, stem, 'Test_1')
    videos[old[0]] = old[0].encode()     # the old flow video shares the file name too
    files = datasets.velocity_dataset_files(folder.statistics, stem, 'Test')
    for part in datasets.VELOCITY_INPUTS:
        touch(files[part], part.encode())
    datasets.save_time_points(datasets.time_points_file(folder.statistics, stem), [12.5])

    recording = library.scan(folder)[0]
    paths = tasks.recording_files(folder, recording)
    assert len(paths) == 2 + 3 + 1 + len(old)
    target = tasks.move_to_trash(folder, paths, recording.stem)

    assert os.path.dirname(target) == folder.trash
    # the three videos share a file name; each must survive in its own subfolder
    for path, content in videos.items():
        assert not os.path.exists(path)
        with open(os.path.join(target, tasks.relative_path(folder, path)), 'rb') as handle:
            assert handle.read() == content
    assert os.path.isfile(os.path.join(target, 'Statistics', os.path.basename(files['cross_correlation'])))
    for path in old:
        assert not os.path.exists(path)
        assert os.path.isfile(os.path.join(target, tasks.relative_path(folder, path)))
    assert library.scan(folder) == []


def test_trash_folders_never_collide(folder):
    first = tasks.move_to_trash(folder, [touch(os.path.join(folder.reports, 'a.png'))], 'same label')
    second = tasks.move_to_trash(folder, [touch(os.path.join(folder.reports, 'a.png'))], 'same label')
    assert first != second
    assert os.path.isfile(os.path.join(first, 'Reports', 'a.png'))
    assert os.path.isfile(os.path.join(second, 'Reports', 'a.png'))


def test_relative_path(folder, tmp_path):
    assert tasks.relative_path(folder, os.path.join(folder.stabilized, 'x.avi')) == \
        os.path.join('StabilizedVideos', 'x.avi')
    assert tasks.relative_path(folder, str(tmp_path / 'elsewhere' / 'x.avi')) == 'x.avi'


# --------------------------------------------------------------------- recording names

def test_recording_names_match_the_existing_recordings():
    when = datetime.datetime(2026, 10, 5, 14, 3, 22)
    assert tasks.recording_name('FP03_Wföre', when) == 'FP03_Wföre_05-Oct-2026_14-03-22'
    assert tasks.recording_name('', when) == '05-Oct-2026_14-03-22'
    assert tasks.recording_name('a/b', when, time_text='hh-mm-ss') == 'a_b_05-Oct-2026_hh-mm-ss'


def test_a_new_recording_never_overwrites_one(folder, monkeypatch):
    monkeypatch.setattr(tasks, 'recording_name', lambda prefix='': 'FP03')
    first = tasks.new_recording_path(folder)
    assert first == os.path.join(folder.recorded, 'FP03.avi')
    touch(first)
    assert tasks.new_recording_path(folder) == os.path.join(folder.recorded, 'FP03_2.avi')


def test_format_time():
    assert format_time(59.9996) == '1:00.000'
    assert format_time(3725.5) == '1:02:05.500'
    assert format_time(-1.5) == '-0:01.500'
    assert format_time(61.9, precise=False) == '1:01'
    assert format_time(float('nan')) == '–'


# ------------------------------------------------------------------- background jobs

class FakeTk:
    """Stands in for the widget the job manager schedules its polling on."""

    def __init__(self):
        self.errors = []

    def after(self, ms, callback, *args):
        return None

    def _root(self):
        return self

    def report_callback_exception(self, exc_type, value, traceback_):
        self.errors.append(value)


def poll_until(manager, condition, timeout=10.0):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, 'timed out'
        manager._poll()
        time.sleep(0.005)


def test_jobs_report_results_errors_and_cancellation():
    tk = FakeTk()
    manager = JobManager(tk)
    outcome = {}

    def endless(job):
        while True:
            job.report(0.5, 'working')
            time.sleep(0.005)

    done = manager.submit('done', lambda job: 42, on_done=lambda result: outcome.update(done=result))
    failed = manager.submit('failed', lambda job: 1 / 0, on_error=lambda exc: outcome.update(failed=exc))
    running = manager.submit('cancelled', endless, lane='processing', key=('x', 1),
                             on_cancel=lambda: outcome.update(cancelled=True))
    assert manager.submit('again', endless, lane='processing', key=('x', 1)) is None  # same key: refused
    poll_until(manager, lambda: running.state == 'running')
    running.cancel()
    poll_until(manager, lambda: len(outcome) == 3)

    assert outcome['done'] == 42 and done.state == 'done'
    assert isinstance(outcome['failed'], ZeroDivisionError) and failed.state == 'failed'
    assert outcome['cancelled'] and running.state == 'cancelled'
    assert manager.active() == [] and tk.errors == []
    assert manager.close(timeout=5)


def test_lanes_run_side_by_side_and_close_waits_for_the_workers():
    manager = JobManager(FakeTk())
    release = threading.Event()
    slow = manager.submit('slow', lambda job: release.wait(5), lane='processing')
    quick = manager.submit('quick', lambda job: 'ok', lane='analysis')
    poll_until(manager, lambda: quick.state == 'done' and slow.state == 'running')
    assert not slow.finished  # the quick job did not wait for it
    release.set()
    assert manager.close(timeout=5)
    assert not any(thread.is_alive() for thread in manager._threads)
