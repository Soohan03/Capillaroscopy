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

from capillary import spacetime, stabilize
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


def test_no_frame_is_silently_wrong(tmp_path):
    # jumps of up to 60 px, at random, in a 160 x 120 frame where the coarse search reaches 40 px
    frames, movement = jittered_frames(40, seed=9, amplitude=(5, 60))
    write_grey(tmp_path / 'source.avi', frames)
    result = stabilize.stabilize_video(str(tmp_path / 'source.avi'), str(tmp_path / 'stabilized.avi'))
    error = result.frames[['shift_x_px', 'shift_y_px']].to_numpy() + movement
    error = np.abs(error - error[result.sharpest]).max(axis=1)
    marked = (result.frames['at_search_limit'] | (result.frames['match'] < 0.6)).to_numpy()
    away = np.abs(movement - movement[result.sharpest]).max(axis=1)
    assert (away > 44).sum() >= 5
    assert ((error < 0.15) | marked).all()                       # right, or marked as doubtful
    assert (error[away < 36] < 0.15).all() and not marked[away < 36].any()


def test_following_the_previous_frame_reaches_beyond_the_coarse_search():
    # in 240 x 320 the coarse search reaches 80 px; the image drifts 130 px down, as FP03_Wföre swings with breathing
    texture = scene(240, 320, margin=140, seed=6)

    def at(dy):
        matrix = np.float32([[1, 0, -140], [0, 1, dy - 140]])
        return stabilize.enhance(cv2.warpAffine(texture, matrix, (320, 240), flags=cv2.INTER_CUBIC))
    reference = at(0.0)
    references = (reference, reference, np.zeros(2))
    previous = None
    for dy in np.linspace(0, 130, 66):
        shift, match, _, at_limit = stabilize.register(at(dy), references, previous)
        assert abs(shift[1] + dy) < 0.15 and abs(shift[0]) < 0.15 and not at_limit and match > 0.9
        previous = shift
    lost, match, _, _ = stabilize.register(at(130.0), references)          # without the previous frame
    assert abs(lost[1] + 130) > 10 or match < 0.6


def drifting_frames(n: int, drift_y: float, seed: int = 0, size=(HEIGHT, WIDTH)):
    """`n` frames of a scene drifting steadily `drift_y` px down over the clip, with a little jitter."""
    rng = np.random.default_rng(seed + 1)
    height, width = size
    margin = int(np.ceil(abs(drift_y))) + 12
    texture = scene(height, width, margin, seed)
    movement = np.column_stack([rng.uniform(-1, 1, n), np.linspace(0, drift_y, n) + rng.uniform(-1, 1, n)])
    frames = []
    for dx, dy in movement:
        matrix = np.float32([[1, 0, dx - margin], [0, 1, dy - margin]])
        frame = cv2.warpAffine(texture, matrix, (width, height), flags=cv2.INTER_CUBIC)
        frames.append(np.clip(np.rint(frame + rng.normal(0, 1.5, frame.shape)), 0, 255).astype(np.uint8))
    return frames, movement


def sharpen(frame: np.ndarray, seed: int = 1) -> np.ndarray:
    """`frame` with added noise, which makes it the sharpest by `calculate_blur`."""
    noise = np.random.default_rng(seed).normal(0, 6, frame.shape)
    return np.clip(frame + noise, 0, 255).astype(np.uint8)


def test_a_drift_far_beyond_the_coarse_search_is_followed(tmp_path):
    # FP01_W drifts about 200 px, and its sharpest frame was at the far end: the frames far from it were never found
    # (2026-10-08). In 160 x 120 the coarse search reaches 40 px; here the scene drifts 100 px.
    frames, movement = drifting_frames(60, 100.0, seed=3)
    frames[-1] = sharpen(frames[-1])
    write_grey(tmp_path / 'source.avi', frames)
    result = stabilize.stabilize_video(str(tmp_path / 'source.avi'), str(tmp_path / 'stabilized.avi'))
    error = result.frames[['shift_x_px', 'shift_y_px']].to_numpy() + movement
    error -= np.median(error, axis=0)
    placed_by = result.frames['placed_by']
    # the frame furthest from the references overlaps them too little and is carried along from its neighbour
    assert (placed_by == 'references').sum() >= 57 and not (placed_by == 'lost').any()
    assert np.abs(error).max() < 0.15
    # the references are built where the picture usually is, not at the sharp far end
    assert abs(movement[result.sharpest, 1] - np.median(movement[:, 1])) <= stabilize.REFERENCE_RADIUS_PX
    # and the picture is centred there
    assert abs(np.median(result.frames['shift_y_px'])) < 1.0


def test_dark_frames_are_lost_not_misplaced(tmp_path):
    # FP01_W goes dark in its last seconds (mean grey 70 -> 9); its sharpest frame was there
    frames, movement = drifting_frames(50, 10.0, seed=4)
    rng = np.random.default_rng(5)
    for i in range(42, 50):
        frames[i] = np.clip(rng.normal(8, 6, frames[i].shape), 0, 255).astype(np.uint8)   # dark, noisy, "sharp"
    write_grey(tmp_path / 'source.avi', frames)
    result = stabilize.stabilize_video(str(tmp_path / 'source.avi'), str(tmp_path / 'stabilized.avi'))
    placed_by = result.frames['placed_by'].to_numpy()
    assert result.sharpest < 42
    assert (placed_by[:42] == 'references').all() and (placed_by[42:] == 'lost').all()
    assert result.frames.loc[42:, 'shift_x_px'].isna().all()
    written = list(iter_frames(result.output))
    assert all(frame.max() == 0 for frame in written[42:])                   # written black
    error = result.frames[['shift_x_px', 'shift_y_px']].to_numpy()[:42] + movement[:42]
    assert np.abs(error - np.median(error, axis=0)).max() < 0.15
    summary = result.summary()
    assert summary['frames_lost'] == 8 and np.isfinite(summary['movement_range_x_px'])


def test_a_jump_away_from_the_references_is_not_silently_wrong(tmp_path):
    # FP03_Qföre moves about 500 px when the cuff goes on, to a part of the finger the references do not show
    texture = scene(HEIGHT, WIDTH, margin=200, seed=7)
    rng = np.random.default_rng(8)

    def at(dx, dy):
        matrix = np.float32([[1, 0, dx - 200], [0, 1, dy - 200]])
        frame = cv2.warpAffine(texture, matrix, (WIDTH, HEIGHT), flags=cv2.INTER_CUBIC)
        return np.clip(np.rint(frame + rng.normal(0, 1.5, frame.shape)), 0, 255).astype(np.uint8)
    movement = [(rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(30)] + [(150.0, 110.0)] * 15
    write_grey(tmp_path / 'source.avi', [at(*m) for m in movement])
    result = stabilize.stabilize_video(str(tmp_path / 'source.avi'), str(tmp_path / 'stabilized.avi'))
    placed_by = result.frames['placed_by'].to_numpy()
    assert (placed_by[:30] == 'references').all()
    assert (placed_by[30:] == 'lost').all()


def test_frames_the_references_miss_are_carried_along_the_path():
    # the path between placed frames 0 and 4 has drifted 0.4 px, which is spread evenly over the frames between
    positions = np.array([[0.0, 0], [10, 0], [20, 0], [30, 0], [40.4, 0], [50.4, 0], [0, 0], [5, 0]])
    stretches = np.array([1, 1, 1, 1, 1, 1, 2, 2])
    placed = np.array([True, False, False, False, True, False, False, False])
    shifts = np.full((8, 2), np.nan)
    shifts[0], shifts[4] = (100.0, 5.0), (140.0, 5.0)
    bridged, found_by = stabilize.bridge(shifts, placed, positions, stretches)
    np.testing.assert_allclose(bridged[:6, 0], [100, 109.9, 119.8, 129.7, 140, 150])
    np.testing.assert_allclose(bridged[:6, 1], 5.0)
    assert list(found_by) == ['references', 'neighbours', 'neighbours', 'neighbours', 'references', 'neighbours',
                              'lost', 'lost']
    assert np.isnan(bridged[6:]).all()


def test_the_path_breaks_where_neighbouring_frames_do_not_match():
    stretches = stabilize.path_stretches(np.array([True, True, False, True, True]))
    assert list(stretches) == [1, 1, 2, 2, 2]
    steps = np.array([[9.0, 9], [1, 0], [50, 50], [1, 1], [1, 1]])
    np.testing.assert_allclose(stabilize.path_positions(steps, stretches), [[0, 0], [1, 0], [0, 0], [1, 1], [2, 2]])


def test_the_reference_is_the_sharpest_frame_where_the_picture_usually_is():
    n = 100
    positions = np.zeros((n, 2))
    positions[80:, 1] = 200.0                             # the picture moved far away for the last 20 frames
    stretches = np.ones(n, dtype=int)
    brightness = np.full(n, 70.0)
    brightness[60:70] = 9.0                               # dark
    sharpness = np.arange(n, dtype=float)                 # the later, the sharper
    assert stabilize.choose_reference(sharpness, brightness, positions, stretches) == 79
    assert stabilize.choose_reference(sharpness, brightness, positions, stretches, window=(0, 50)) == 50
    stretches[:40] = 2                                    # most usable frames are now on the first stretch... of 40
    assert stabilize.choose_reference(sharpness, brightness, positions, stretches) == 79


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
    sharpest = int(frames['sharpness'].idxmax())
    reach = stabilize.REFERENCE_NEIGHBOURS
    assert result.sharpest == sharpest
    assert result.references == list(range(max(0, sharpest - reach), min(len(frames), sharpest + reach + 1)))
    assert frames.loc[frames['reference'], 'frame'].tolist() == result.references
    assert frames['disagreement_px'].median() < 0.05
    assert frames['match'].min() > 0.9


def test_memory_does_not_grow_with_the_length(tmp_path):
    peaks = {}
    for n in (60, 180):
        frames, _ = jittered_frames(n, seed=5)
        noise = np.random.default_rng(1).normal(0, 6, frames[30].shape)
        frames[30] = np.clip(frames[30] + noise, 0, 255).astype(np.uint8)     # the sharpest, in both videos
        write_grey(tmp_path / f'{n}.avi', frames)
        tracemalloc.start()
        stabilize.stabilize_video(str(tmp_path / f'{n}.avi'), str(tmp_path / f'{n}_stabilized.avi'))
        peaks[n] = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    # holding the 120 extra frames would add 2.3 MB as uint8, 18 MB as float64 (as before 2026-10-08)
    assert peaks[180] - peaks[60] < 500_000


def test_the_record_is_saved_next_to_the_video(jittered):
    _, _, result = jittered
    paths = stabilize.save_record(result)
    assert paths == stabilize.record_paths(result.output)
    shifts = pd.read_csv(paths['shifts'])
    assert list(shifts.columns) == ['frame', 'time_s', 'shift_x_px', 'shift_y_px', 'placed_by', 'match',
                                    'disagreement_px', 'at_search_limit', 'step_x_px', 'step_y_px', 'step_match',
                                    'sharpness', 'mean_grey', 'reference']
    assert (shifts['placed_by'] == 'references').all()
    assert len(shifts) == 60 and shifts['reference'].sum() == len(result.references)
    assert shifts['time_s'].iloc[25] == pytest.approx(1.0)
    np.testing.assert_allclose(shifts['shift_x_px'], result.frames['shift_x_px'])
    with open(paths['provenance'], encoding='utf-8') as handle:
        provenance = json.load(handle)
    assert provenance['source_video'] == 'source.avi' and provenance['frames'] == 60
    assert provenance['method']['reference_frames'] == result.references
    assert provenance['summary']['movement_range_x_px'] > 5


def test_the_shift_file_is_read_back_by_frame(jittered, tmp_path):
    _, _, result = jittered
    stabilize.save_record(result)
    shifts = stabilize.read_shifts(result.output)
    assert shifts.index.name == 'frame' and list(shifts.index) == list(range(60))
    np.testing.assert_allclose(shifts['shift_x_px'], result.frames['shift_x_px'])
    assert stabilize.read_shifts(str(tmp_path / 'raw.avi')) is None            # no shift file: not stabilized here
    odd = stabilize.record_paths(str(tmp_path / 'odd.avi'))['shifts']
    pd.DataFrame({'frame': [0], 'match': [0.9]}).to_csv(odd, index=False)
    with pytest.raises(ValueError, match='no shifts'):
        stabilize.read_shifts(str(tmp_path / 'odd.avi'))


# ------------------------------------------------------------- where every frame shows the picture

def shift_table(moves, fps: float = 30.0) -> pd.DataFrame:
    """A shift file as `read_shifts` gives it: each frame's move (x, y), NaN for a frame the stabilizer lost."""
    moves = np.asarray(moves, dtype=float)
    frames = np.arange(len(moves))
    return pd.DataFrame({'time_s': frames / fps, 'shift_x_px': moves[:, 0], 'shift_y_px': moves[:, 1],
                         'placed_by': np.where(np.isnan(moves).any(axis=1), 'lost', 'references')},
                        index=pd.Index(frames, name='frame'))


def test_the_area_every_frame_of_a_range_shows():
    shifts = shift_table([(5.0, -4.0), (-3.0, 2.0), (0.5, 0.5), (np.nan, np.nan)])
    shape = (HEIGHT, WIDTH)
    # moved right by 5: the strip covers x < 5, then 3 px; moved down by 2: y < 2 plus 3; and so on
    assert stabilize.picture_area(shifts, shape, 0, 2) == pytest.approx((8, 5, WIDTH - 1 - 6, HEIGHT - 1 - 7))
    assert stabilize.picture_area(shifts, shape, 1, 2) == pytest.approx((3.5, 5, WIDTH - 1 - 6, HEIGHT - 1 - 2.5))
    assert stabilize.picture_area(shifts, shape, 3, 3) is None                  # lost: no picture at all

    inside = stabilize.check_picture(shifts, shape, (10, 10, 150, 110), 0, 2)
    assert (inside.off_picture, inside.lost, inside.problem()) == (0, 0, None)
    assert inside.clearance_px == pytest.approx(2.0)                            # 10 - 8 on the left, 112 - 110 below
    assert inside.record()['area_px'] == [8.0, 5.0, 153.0, 112.0] and inside.record()['clearance_px'] == 2.0

    near = stabilize.check_picture(shifts, shape, (6, 10, 100, 50), 0, 2)
    assert (near.off_picture, near.side, near.clearance_px) == (1, 'left', pytest.approx(-2.0))
    assert near.problem() == ("In 1 of the range's 3 frames the line reaches the black strip that stabilizing leaves "
                              'along the edge where the picture moved. Move it at least 2 px away from the left edge.')

    lost = stabilize.check_picture(shifts, shape, (10, 10, 150, 110), 1, 3)
    assert lost.lost == 1 and lost.problem() == ('The stabilizer lost 1 frame of this range (0.1–0.1 s), which is '
                                                 'black. Set the range to frames it placed.')
    nothing = stabilize.check_picture(shifts, shape, (10, 10, 150, 110), 3, 3)
    assert nothing.area is None and np.isnan(nothing.clearance_px) and nothing.record()['area_px'] is None

    # the picture moved so far that no place shows it in every frame, or too little for the line: no move helps
    swing = stabilize.check_picture(shift_table([(0.0, 100.0), (0.0, -100.0)]), shape, (10, 50, 20, 60), 0, 1)
    assert swing.problem().endswith('No part of the frame shows the picture in every frame of this range: it moved '
                                    'too far.')
    sway = stabilize.check_picture(shift_table([(0.0, 30.0), (0.0, -30.0)]), shape, (10, 30, 20, 90), 0, 1)
    assert sway.problem().endswith('The line is larger than the part of the frame that shows the picture in every '
                                   'frame of this range (153 × 53 px).')


def test_a_line_passes_only_where_it_reads_the_recorded_picture():
    """Where the check passes, a line near the edge of a stabilized frame reads exactly what it would read had
    the camera seen beyond the frame: neither the black strip nor the pixels the bicubic move blends with it.
    Without the margin, frames whose blend reaches the line would pass."""
    margin = 24
    texture = np.clip(np.rint(scene(HEIGHT, WIDTH, margin, seed=3)), 0, 255).astype(np.uint8)
    recorded = texture[margin:margin + HEIGHT, margin:margin + WIDTH]
    moves = [(dx, 0.37) for dx in np.arange(-12.0, 12.0, 0.29)]
    shifts = shift_table(moves)
    lines = {name: spacetime.Centreline.from_points([(x, 30.0), (x, 90.0)])
             for name, x in (('left', 10.0), ('right', WIDTH - 11.0), ('right, between pixels', WIDTH - 10.7))}
    for name, line in lines.items():
        sampler = spacetime.SpaceTimeSampler(line)
        x0, _, x1, _ = sampler.bounds
        passed, needed = [], []
        for frame, move in enumerate(moves):
            stabilized = stabilize.shift_frame(recorded, move)
            beyond = stabilize.shift_frame(texture, (move[0] - margin, move[1] - margin))[:HEIGHT, :WIDTH]
            clean = np.abs(sampler.row(stabilized) - sampler.row(beyond)).max() < 0.01      # the same pixels
            check = stabilize.check_picture(shifts, recorded.shape, sampler.bounds, frame, frame)
            assert clean or check.off_picture, f'{name} line, move {move[0]:.2f} px: passed but reads the strip'
            unguarded = stabilize.check_picture(shifts, recorded.shape, sampler.bounds, frame, frame, margin_px=0)
            if not clean and not unguarded.off_picture:
                needed.append(frame)
            if not check.off_picture:
                passed.append(move[0])
        assert needed, f'{name} line: the margin was never needed'
        # and no stricter than that: a move passes when the samples keep the margin inside the moved picture
        margin_px = stabilize.EDGE_MARGIN_PX
        assert passed == [dx for dx, _ in moves if dx + margin_px <= x0 and x1 <= dx + WIDTH - 1 - margin_px]
        assert len(passed) > len(moves) / 2


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
    assert [message for _, message in job.reports][-1] == 'Writing the stabilized video'
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
