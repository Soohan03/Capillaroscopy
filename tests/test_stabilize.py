"""The stabilizer (`capillary.stabilize`) and the Stabilize job (`gui.tasks.stabilize`).

A textured scene is moved by known sub-pixel amounts, written losslessly and
stabilized; the shifts have to undo the movement frame for frame, and every
frame has to come out in its place, unchanged apart from the shift.
"""

import json
import os
import tracemalloc
from types import SimpleNamespace

import cv2
import numpy as np
import pandas as pd
import pytest

from capillary import stabilize
from capillary.measure import Cancelled
from capillary.video import iter_frames, probe_video
from gui import library, tasks
from gui.settings import DataFolder

STEM = 'FP99_stab_08-Oct-2026_12-00-00'
HEIGHT, WIDTH = 120, 160


def scene(height: int, width: int, margin: int, seed: int = 0) -> np.ndarray:
    """A smooth random texture, `margin` larger than a frame on every side, so a moved frame never shows its edge."""
    rng = np.random.default_rng(seed)
    texture = cv2.GaussianBlur(rng.normal(size=(height + 2 * margin, width + 2 * margin)), (0, 0), 2.5)
    return 40 + 175 * (texture - texture.min()) / np.ptp(texture)


def lighting(height: int, width: int) -> np.ndarray:
    """Uneven lighting that stays with the camera: darker towards the corners and to the left."""
    y, x = np.mgrid[0:height, 0:width].astype(float)
    corners = ((x - width / 2) / (width / 2)) ** 2 + ((y - height / 2) / (height / 2)) ** 2
    return (1 - 0.15 * corners) * (1 + 0.25 * (x / width - 0.5))


def jittered_frames(n: int, seed: int = 0, amplitude=(5.0, 5.0), size=(HEIGHT, WIDTH), uneven_light: bool = False):
    """`n` frames of the scene, each moved by a known (x, y) up to `amplitude`; returns the frames and the movement."""
    rng = np.random.default_rng(seed + 1)
    height, width = size
    margin = int(np.ceil(max(amplitude))) + 8
    texture = scene(height, width, margin, seed)
    light = lighting(height, width) if uneven_light else 1.0
    movement = rng.uniform(-1, 1, size=(n, 2)) * np.asarray(amplitude, dtype=float)
    frames = []
    for dx, dy in movement:
        matrix = np.float32([[1, 0, dx - margin], [0, 1, dy - margin]])
        frame = cv2.warpAffine(texture, matrix, (width, height), flags=cv2.INTER_CUBIC) * light
        frames.append(np.clip(np.rint(frame + rng.normal(0, 1.5, frame.shape)), 0, 255).astype(np.uint8))
    return frames, movement


def write_grey(path, frames, fps: float = 30.0) -> None:
    """Uncompressed 8-bit grey, like the recordings from DynCap."""
    writer = cv2.VideoWriter(str(path), 0, fps, (frames[0].shape[1], frames[0].shape[0]), isColor=False)
    assert writer.isOpened()
    for frame in frames:
        writer.write(frame)
    writer.release()


@pytest.fixture(scope='module')
def jittered(tmp_path_factory):
    folder = tmp_path_factory.mktemp('stabilize')
    frames, movement = jittered_frames(60)
    write_grey(folder / 'source.avi', frames, fps=25.0)
    result = stabilize.stabilize_video(str(folder / 'source.avi'), str(folder / 'stabilized.avi'))
    return frames, movement, result


def test_the_enhancement_moves_with_the_image_and_drops_the_lighting():
    # the CLAHE used until 2026-10-08 worked on a fixed grid of tiles, so it changed as the image moved
    texture = scene(240, 320, margin=10, seed=4)
    frame = texture[10:250, 10:330]
    moved = texture[17:257, 5:325]                      # the same scene moved 7 px up and 5 px right
    a, b = stabilize.enhance(frame), stabilize.enhance(moved)
    np.testing.assert_allclose(b[70:-70, 70:-70], a[77:-63, 65:-75], atol=0.01)

    light = lighting(240, 320)
    lit = stabilize.enhance(frame * light)
    assert np.corrcoef(lit[70:-70, 70:-70].ravel(), a[70:-70, 70:-70].ravel())[0, 1] > 0.95
    flat = stabilize.enhance(np.full((240, 320), 120.0) * light)
    assert np.abs(flat[70:-70, 70:-70]).max() < 0.1 * a.std()


def test_the_shifts_undo_the_movement(jittered):
    _, movement, result = jittered
    shifts = result.frames[['shift_x_px', 'shift_y_px']].to_numpy()
    error = shifts + movement                 # one offset for the whole video is allowed
    error -= np.median(error, axis=0)
    assert movement.std(axis=0).min() > 2.5
    assert np.abs(error).max() < 0.15


def test_large_movements_under_uneven_lighting(tmp_path):
    # the registration used until 2026-10-08 fell 3-5.6 px short on FP01_Qföre where the image had moved 15-20 px
    frames, movement = jittered_frames(40, seed=2, amplitude=(10, 25), size=(240, 320), uneven_light=True)
    write_grey(tmp_path / 'source.avi', frames)
    result = stabilize.stabilize_video(str(tmp_path / 'source.avi'), str(tmp_path / 'stabilized.avi'))
    error = result.frames[['shift_x_px', 'shift_y_px']].to_numpy() + movement
    error -= np.median(error, axis=0)
    assert np.ptp(movement[:, 1]) > 40
    assert np.abs(error).max() < 0.15
    assert not result.frames['at_search_limit'].any()


def test_a_frame_beyond_the_search_is_marked(tmp_path):
    frames, movement = jittered_frames(40, seed=9, amplitude=(5, 45))      # in 160 x 120 the search reaches 30 px
    write_grey(tmp_path / 'source.avi', frames)
    result = stabilize.stabilize_video(str(tmp_path / 'source.avi'), str(tmp_path / 'stabilized.avi'))
    away = np.abs(movement - movement[result.references[0]]).max(axis=1)
    marked = (result.frames['at_search_limit'] | (result.frames['match'] < 0.6)).to_numpy()
    assert (away > 31).sum() >= 5 and marked[away > 31].all()
    assert not marked[away < 28].any()


def test_every_frame_is_written_in_place_and_losslessly(jittered):
    frames, _, result = jittered
    shifts = result.frames[['shift_x_px', 'shift_y_px']].to_numpy()
    written = list(iter_frames(result.output))
    assert len(written) == len(frames)
    for frame, out, shift in zip(frames, written, shifts):
        assert np.array_equal(out, stabilize.shift_frame(frame, shift))
    assert written[0].mean() > 30                # frame 0 was black before 2026-10-08
    info = probe_video(result.output)
    assert (info.fps, info.width, info.height) == (25.0, WIDTH, HEIGHT)


def test_the_stabilized_frames_line_up(jittered):
    frames, _, result = jittered
    inner = (slice(None), slice(12, -12), slice(12, -12))      # clear of the black edges the shifts uncover
    before = np.array(frames, dtype=float)[inner]
    after = np.array(list(iter_frames(result.output)), dtype=float)[inner]
    moving = np.abs(before - before[0]).mean()
    still = np.abs(after - after[0]).mean()
    assert still < 4 and moving > 4 * still


def test_the_references_are_the_sharpest_frames(jittered):
    _, _, result = jittered
    frames = result.frames
    sharpest = frames['sharpness'].sort_values(ascending=False, kind='stable').index
    assert result.references == list(sharpest[:stabilize.REFERENCE_FRAMES])
    assert frames.loc[frames['reference'], 'frame'].tolist() == sorted(result.references)
    assert frames['disagreement_px'].median() < 0.05
    assert frames['match'].min() > 0.9


def test_memory_does_not_grow_with_the_length(tmp_path):
    peaks = {}
    for n in (30, 150):
        frames, _ = jittered_frames(n, seed=5)
        write_grey(tmp_path / f'{n}.avi', frames)
        tracemalloc.start()
        stabilize.stabilize_video(str(tmp_path / f'{n}.avi'), str(tmp_path / f'{n}_stabilized.avi'))
        peaks[n] = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    # holding the 120 extra frames would add 2.3 MB as uint8, 18 MB as float64 (as before 2026-10-08)
    assert peaks[150] - peaks[30] < 1_000_000


def test_the_record_is_saved_next_to_the_video(jittered):
    _, _, result = jittered
    paths = stabilize.save_record(result)
    assert paths == stabilize.record_paths(result.output)
    shifts = pd.read_csv(paths['shifts'])
    assert list(shifts.columns) == ['frame', 'time_s', 'shift_x_px', 'shift_y_px', 'match', 'disagreement_px',
                                    'at_search_limit', 'sharpness', 'reference']
    assert len(shifts) == 60 and shifts['reference'].sum() == stabilize.REFERENCE_FRAMES
    assert shifts['time_s'].iloc[25] == pytest.approx(1.0)
    np.testing.assert_allclose(shifts['shift_x_px'], result.frames['shift_x_px'])
    with open(paths['provenance'], encoding='utf-8') as handle:
        provenance = json.load(handle)
    assert provenance['source_video'] == 'source.avi' and provenance['frames'] == 60
    assert provenance['method']['reference_frames'] == result.references
    assert provenance['summary']['movement_range_x_px'] > 5


def test_a_cancelled_stabilization_leaves_nothing(tmp_path):
    frames, _ = jittered_frames(40)
    write_grey(tmp_path / 'source.avi', frames)
    calls = []

    def cancel_after_ten_checks():
        calls.append(None)
        return len(calls) > 10

    with pytest.raises(Cancelled):
        stabilize.stabilize_video(str(tmp_path / 'source.avi'), str(tmp_path / 'stabilized.avi'),
                                  should_cancel=cancel_after_ten_checks)
    assert sorted(os.listdir(tmp_path)) == ['source.avi']


def test_only_avi_is_written(tmp_path):
    with pytest.raises(ValueError, match='.avi'):
        stabilize.stabilize_video(str(tmp_path / 'source.avi'), str(tmp_path / 'stabilized.mp4'))


def test_the_command_line(tmp_path, capsys):
    frames, _ = jittered_frames(30)
    (tmp_path / 'RecordedVideos').mkdir()
    write_grey(tmp_path / 'RecordedVideos' / 'clip.avi', frames)
    out = tmp_path / 'StabilizedVideos' / 'clip.avi'
    assert stabilize.main([str(tmp_path / 'RecordedVideos' / 'clip.avi'), '--out', str(out)]) == 0
    assert sorted(os.listdir(out.parent)) == ['clip.avi', 'clip___stabilization.csv',
                                              'clip___stabilization_provenance.json']
    assert '30 frames, 160x120' in capsys.readouterr().out


# ------------------------------------------------------------------------- the GUI job

class FakeJob:
    def __init__(self, cancel_after=None):
        self.reports = []
        self.cancel_after = cancel_after

    def report(self, progress=None, message=None):
        self.reports.append((progress, message))
        if self.cancel_after is not None and len(self.reports) > self.cancel_after:
            raise Cancelled()

    def cancelled(self):
        return False


@pytest.fixture
def data_folder(tmp_path):
    folder = DataFolder(str(tmp_path))
    folder.ensure()
    frames, _ = jittered_frames(30)
    write_grey(os.path.join(folder.recorded, f'{STEM}.avi'), frames)
    return folder


def _files_under(path):
    return sorted(name for _, _, names in os.walk(path) for name in names)


def test_the_stabilize_job_files_the_video_and_its_record(data_folder):
    raw = os.path.join(data_folder.recorded, f'{STEM}.avi')
    job = FakeJob()
    final = tasks.stabilize(job, folder=data_folder, raw_path=raw)
    assert final == os.path.join(data_folder.stabilized, f'{STEM}.avi')
    assert [message for _, message in job.reports][-1] == 'Aligning and writing frames'
    record = stabilize.record_paths(final)
    assert all(os.path.exists(path) for path in record.values())
    assert _files_under(data_folder.partial(data_folder.stabilized)) == []

    recording, = library.scan(data_folder)
    assert recording.stabilized == final
    assert set(tasks.recording_files(data_folder, recording)) == {raw, final, *record.values()}

    # stabilizing again moves the previous video and its record to the trash
    tasks.stabilize(FakeJob(), folder=data_folder, raw_path=raw)
    assert _files_under(data_folder.trash) == sorted(os.path.basename(path) for path in [final, *record.values()])
    assert all(os.path.exists(path) for path in [final, *record.values()])


def test_a_cancelled_job_leaves_nothing(data_folder):
    raw = os.path.join(data_folder.recorded, f'{STEM}.avi')
    with pytest.raises(Cancelled):
        tasks.stabilize(FakeJob(cancel_after=3), folder=data_folder, raw_path=raw)
    assert _files_under(data_folder.stabilized) == []


def test_too_little_disk_space_is_refused(data_folder, monkeypatch):
    raw = os.path.join(data_folder.recorded, f'{STEM}.avi')
    monkeypatch.setattr(tasks.shutil, 'disk_usage', lambda path: SimpleNamespace(free=1000))
    with pytest.raises(OSError, match='free disk space'):
        tasks.stabilize(FakeJob(), folder=data_folder, raw_path=raw)
    assert _files_under(data_folder.stabilized) == []
