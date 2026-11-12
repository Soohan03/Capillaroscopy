"""The batch command (`capillary.cli`), end to end: pixels in, mm/s out, checked against a known velocity."""

import pytest

from capillary.cli import main, read_mm_per_pixel
from capillary.video import probe_video

from .synthetic import expected_velocity_mm_s, make_flow_frames, write_video

FPS = 30.0
MM_PER_PIXEL = 0.002
VELOCITY_PX_PER_FRAME = 2.5
LINE_TOP_Y, LINE_BOTTOM_Y = 40, 190         # the pattern travels towards +y, along the line
LINE = f'60,{LINE_TOP_Y}; 60,{LINE_BOTTOM_Y}'


@pytest.fixture(scope='module')
def frames():
    return make_flow_frames(
        n_frames=500, height=240, width=120,
        velocity_px_per_frame=VELOCITY_PX_PER_FRAME, seed=7,
    )


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


def test_cli_measures_along_a_line(video_file, tmp_path, capsys):
    import pandas as pd

    out = tmp_path / 'blocks.csv'
    summary = tmp_path / 'summary.csv'
    exit_code = main([
        str(video_file),
        '--line', LINE,
        '--mm-per-pixel', str(MM_PER_PIXEL),
        '--start', '20',
        '--out', str(out),
        '--summary-out', str(summary),
    ])

    assert exit_code == 0
    blocks = pd.read_csv(out, index_col=0)
    assert blocks.index.min() == 20 + 45                      # the first 90-frame block starts at frame 20
    resolved = blocks[blocks['resolved']]
    expected = expected_velocity_mm_s(VELOCITY_PX_PER_FRAME, FPS, MM_PER_PIXEL)
    assert len(resolved) == len(blocks)
    assert resolved['velocity_mm_s'].median() == pytest.approx(expected, rel=0.03)
    assert list(pd.read_csv(summary).columns) == ['frame', 'time_s', 'velocity_mm_s']
    printed = capsys.readouterr().out
    assert 'centre line' in printed and 'pattern shift' in printed


def test_cli_searches_the_slow_range_when_asked(video_file, capsys):
    argv = [str(video_file), '--line', LINE, '--mm-per-pixel', str(MM_PER_PIXEL), '--start', '20']
    printed = []
    for extra in ([], ['--slow-flow']):
        assert main(argv + extra) == 0
        printed.append([line for line in capsys.readouterr().out.splitlines() if 'pattern shift' in line])
    assert printed[0] and printed[0] == printed[1]          # flow faster than 1 px/frame reads the same either way


def test_cli_refuses_a_line_that_reaches_the_black_strip_of_a_stabilized_video(video_file, tmp_path, capsys):
    import shutil

    import numpy as np
    import pandas as pd

    from capillary import stabilize

    video = tmp_path / 'stabilized.mp4'
    shutil.copyfile(video_file, video)
    frames = np.arange(probe_video(video).frame_count)
    moves = np.where((frames >= 200) & (frames < 205), 57.0, 0.0)   # a strip up to x = 57 beside the line at 60
    pd.DataFrame({'frame': frames, 'time_s': frames / FPS, 'shift_x_px': moves, 'shift_y_px': 0.0,
                  'placed_by': 'references'}).to_csv(stabilize.record_paths(str(video))['shifts'], index=False)
    argv = [str(video), '--line', LINE, '--mm-per-pixel', str(MM_PER_PIXEL)]
    assert main(argv + ['--start', '20']) == 1
    assert 'In 5 of the range' in capsys.readouterr().err
    assert main(argv + ['--start', '20', '--max-frames', '180']) == 0     # frames 20-199 keep clear of it


def test_cli_wants_a_line(video_file):
    for argv in ([], ['--line', 'nonsense'], ['--line', '10,10']):
        with pytest.raises(SystemExit):
            main([str(video_file), *argv])


def test_cli_reports_a_missing_file_without_a_traceback(tmp_path, capsys):
    exit_code = main([str(tmp_path / 'missing.mp4'), '--line', '10,10;10,60'])

    assert exit_code == 1
    assert 'error' in capsys.readouterr().err


def test_calibration_is_read_from_settings(tmp_path):
    settings = tmp_path / 'settings.csv'
    settings.write_text(',0\nApplication_path,/somewhere\nmm_per_pixel,0.00123\n')

    assert read_mm_per_pixel(str(settings)) == pytest.approx(0.00123)
    assert read_mm_per_pixel(str(tmp_path / 'absent.csv')) is None
