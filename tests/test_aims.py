"""The aims from saved data sets (`capillary.aims`): which loops count, each visit's mean, aim 1's statistics."""

import math
import os

import numpy as np
import pandas as pd
import pytest
from scipy import ndimage, stats

from capillary import agreement, aims, blinding, datasets, pattern_shift
from capillary.spacetime import Centreline


@pytest.fixture(autouse=True)
def app_settings(tmp_path, monkeypatch):
    """The app's settings.csv, empty (blind placement off) unless a test writes it: never the real one."""
    path = tmp_path / 'settings.csv'
    monkeypatch.setattr(aims, 'SETTINGS', str(path))
    return path


def loop_points(x):
    """A loop drawn from the base of its left limb, over the apex, to the base of its right limb."""
    return [[x, 100.0], [x, 30.0], [x + 4, 5.0], [x + 10, 0.0], [x + 16, 5.0], [x + 20, 30.0], [x + 20, 100.0]]


def save(statistics, recording, name, velocity=0.1, *, x=0.0, role='whole loop', phase='rest', resolved=True,
         movement=False, observer='SJ', folder='StabilizedVideos', points=None):
    record = {
        'kind': 'line', 'dataset': name, 'recording': recording, 'observer': observer,
        'created': '2026-10-14T10:00:00', 'video': {'folder': folder, 'fps': 30.0},
        'frames': {'first': 60, 'last': 1859, 'count': 1800},
        'line': {'points': points or loop_points(x), 'role': role, 'length_px': 220.0},
        'summary': {'pattern_shift_velocity_mm_s': velocity if resolved else math.nan,
                    'pattern_shift_snr': 12.0 if resolved else 5.0, 'pattern_shift_resolved': resolved,
                    'phase': phase, 'arterial_end': 'start' if velocity > 0 else 'end', 'loop_movement': movement}}
    datasets.write_provenance(datasets.line_dataset_files(statistics, recording, name)['provenance'], record)


def save_measured(statistics, recording, name, speed_px, *, x=0.0, seed=0, frames=900, mm_per_pixel=0.00133):
    """A whole loop measured as the app measures it: a space-time diagram whose pattern moves `speed_px`
    px/frame along the line, the summary computed from it, and both saved."""
    points = loop_points(x)
    line = Centreline.from_points(points)
    width = int(line.length_px) + 1
    rng = np.random.default_rng(seed)
    reach = int(abs(speed_px) * frames)
    texture = ndimage.gaussian_filter1d(rng.normal(size=width + 2 * reach + 20), 1.5)
    start = reach + 10
    diagram = np.array([texture[start - int(round(speed_px * t)):][:width] for t in range(frames)])
    diagram = (diagram + rng.normal(scale=0.2, size=diagram.shape)).astype(np.float32)
    summary = pattern_shift.summarize(diagram, 30.0, mm_per_pixel)
    summary.update(pattern_shift.loop_limbs(diagram, line.apex_arc_px(), 30.0, mm_per_pixel), phase='rest')
    record = {'kind': 'line', 'dataset': name, 'recording': recording, 'observer': 'SJ', 'mm_per_pixel': mm_per_pixel,
              'video': {'folder': 'StabilizedVideos', 'fps': 30.0}, 'frames': {'first': 60, 'last': 959, 'count': 900},
              'line': {'points': points, 'role': 'whole loop', 'length_px': line.length_px}, 'summary': summary}
    files = datasets.line_dataset_files(statistics, recording, name)
    datasets.write_provenance(files['provenance'], record)
    np.save(files['space_time'], diagram, allow_pickle=False)


@pytest.fixture
def statistics(tmp_path):
    folder = str(tmp_path / 'Statistics')
    os.makedirs(folder)
    save(folder, 'A1', 'loop1', 0.10)
    save(folder, 'A1', 'loop2', -0.14, x=50)                    # flow the other way round: its size counts
    save(folder, 'C1', 'loop1', 0.08)
    save(folder, 'C1', 'loop2', 0.08, x=1.5)                    # the same capillary drawn twice
    save(folder, 'A2', 'loop1', 0.20)
    save(folder, 'C2', 'loop1', 0.15)
    save(folder, 'C2', 'loop2', 0.30, x=50, resolved=False)
    save(folder, 'C2', 'loop3', 0.40, x=100, movement=True)
    save(folder, 'C2', 'loop4', 0.50, x=150, phase='occlusion')
    save(folder, 'C2', 'loop5', 0.50, x=200, folder='RecordedVideos')
    save(folder, 'C2', 'limb1', 0.50, x=250, role='arterial limb')
    save(folder, 'A3', 'loop1', 0.05)
    save(folder, 'C3', 'loop1', 0.30, resolved=False)
    save(folder, 'A4', 'loop1', 0.09)
    save(folder, 'C4', 'loop1', 0.11)
    save(folder, 'A1', 'XY_loop1', 0.30, observer='XY')         # another observer's line on the same capillary
    return folder


@pytest.fixture
def wanted():
    rows = [('ESMOKE', f'FP0{i}', f'A{i}', f'C{i}') for i in range(1, 5)] + [('ISMOKE', 'FP01', 'IA1', 'IC1')]
    return pd.DataFrame(rows, columns=['study', 'subject', 'active_recording', 'control_recording'])


def test_only_whole_loops_within_the_rest_resolved_without_movement_count(statistics):
    table = aims.loops(aims.collect(statistics))
    assert 'limb1' not in set(table['dataset'])
    c2 = table[(table['recording'] == 'C2') & (table['observer'] == 'SJ')].set_index('dataset')
    assert c2['counted'].to_dict() == {'loop1': True, 'loop2': False, 'loop3': False, 'loop4': False, 'loop5': False}
    assert c2.loc['loop2', 'why_not'] == 'not resolved'
    assert c2.loc['loop3', 'why_not'] == 'limbs moved opposite ways (movement)'
    assert c2.loc['loop4', 'why_not'] == 'not within the official rest'
    assert c2.loc['loop5', 'why_not'] == 'not on a stabilized video'
    a1 = table[(table['recording'] == 'A1') & (table['observer'] == 'SJ')].set_index('dataset')
    assert a1.loc['loop2', 'speed_mm_s'] == pytest.approx(0.14)
    assert a1.loc['loop1', 'seconds'] == pytest.approx(60.0)


def test_one_capillary_drawn_twice_is_flagged_not_removed(statistics):
    table = aims.loops(aims.collect(statistics)).set_index(['observer', 'recording', 'dataset'])
    assert table.loc[('SJ', 'C1', 'loop1'), 'duplicate_of'] == 'loop2'
    assert table.loc[('SJ', 'C1', 'loop2'), 'duplicate_of'] == 'loop1'
    assert table.loc[('SJ', 'A1', 'loop1'), 'duplicate_of'] == ''           # 50 px apart
    assert table.loc[('SJ', 'C1', 'loop2'), 'counted']


def test_each_recording_gets_the_mean_of_its_counted_loops(statistics):
    recordings = aims.per_recording(aims.loops(aims.collect(statistics))).set_index(['observer', 'recording'])
    assert recordings.loc[('SJ', 'A1'), 'mean_mm_s'] == pytest.approx(0.12)
    assert tuple(recordings.loc[('SJ', 'C2'), ['loops_placed', 'loops_counted']]) == (4, 1)   # loop4 is not rest
    assert recordings.loc[('SJ', 'C2'), 'mean_mm_s'] == pytest.approx(0.15)
    assert np.isnan(recordings.loc[('SJ', 'C3'), 'mean_mm_s'])
    assert recordings.loc[('XY', 'A1'), 'mean_mm_s'] == pytest.approx(0.30)


def test_each_recording_gets_its_reference_or_else_the_first_backup_that_counts(statistics):
    save(statistics, 'A6', 'loop1', 0.10, resolved=False)
    save(statistics, 'A6', 'loop2', 0.12, x=50)
    save(statistics, 'A6', 'loop3', 0.20, x=100)
    save(statistics, 'A7', 'loop1', 0.10, movement=True)
    save(statistics, 'A7', 'loop2', 0.12, x=50, resolved=False)
    save(statistics, 'A7', 'loop3', -0.20, x=100)
    save(statistics, 'A8', 'loop1', 0.10, resolved=False)
    save(statistics, 'A8', 'loop4', 0.30, x=50)                 # beyond the two backups
    save(statistics, 'A8', 'extra', 0.40, x=100)                # not ranked
    save(statistics, 'A9', 'loop1', 0.10, points=[[0, 100], [20, 0], [20, 100], [0, 0]])       # crosses itself
    save(statistics, 'A9', 'loop2', 0.12, x=50)
    recordings = aims.per_recording(aims.loops(aims.collect(statistics)))
    mine = recordings[recordings['observer'] == 'SJ'].set_index('recording')
    assert (mine.at['A1', 'value_mm_s'], mine.at['A1', 'value_from']) == (pytest.approx(0.10), 'loop1')
    assert mine.at['A1', 'mean_mm_s'] == pytest.approx(0.12)
    assert (mine.at['A6', 'value_mm_s'], mine.at['A6', 'value_from']) == (pytest.approx(0.12), 'loop2')
    assert (mine.at['A7', 'value_mm_s'], mine.at['A7', 'value_from']) == (pytest.approx(0.20), 'loop3')
    assert np.isnan(mine.at['A8', 'value_mm_s']) and mine.at['A8', 'value_from'] == ''
    assert mine.at['A8', 'mean_mm_s'] == pytest.approx(0.35)                 # the secondary value takes every loop
    assert np.isnan(mine.at['A6', 'reference_only_mm_s']) and mine.at['A1', 'reference_only_mm_s'] == pytest.approx(0.1)
    assert np.isnan(mine.at['C3', 'value_mm_s'])
    assert (mine.at['A9', 'value_mm_s'], mine.at['A9', 'value_from']) == (pytest.approx(0.12), 'loop2')
    table = aims.loops(aims.collect(statistics)).set_index(['observer', 'recording', 'dataset'])
    assert table.at[('SJ', 'A9', 'loop1'), 'why_not'] == 'crosses itself (not a candidate)'


def test_aim_1_takes_the_value_asked_for(statistics, wanted):
    recordings = aims.per_recording(aims.loops(aims.collect(statistics)))
    pairs = aims.aim1_pairs(recordings, wanted).set_index(['observer', 'study', 'subject'])
    assert pairs.loc[('SJ', 'ESMOKE', 'FP01'), ['active_mm_s', 'active_from']].tolist() == [pytest.approx(0.10), 'loop1']
    pairs = aims.aim1_pairs(recordings, wanted, 'mean_mm_s').set_index(['observer', 'study', 'subject'])
    assert pairs.loc[('SJ', 'ESMOKE', 'FP01'), ['active_mm_s', 'active_from']].tolist() == [pytest.approx(0.12), 'mean of 2']


def test_aim_1_from_the_visits_of_each_participant(statistics, wanted):
    recordings = aims.per_recording(aims.loops(aims.collect(statistics)))
    pairs = aims.aim1_pairs(recordings, wanted, 'mean_mm_s')
    stats = aims.aim1(pairs).set_index(['observer', 'study'])
    mine = stats.loc[('SJ', 'ESMOKE')]
    assert (mine['participants'], mine['participants_wanted'], mine['one_visit_only'], mine['neither_visit']) == \
        (3, 4, 1, 0)
    a, c = np.array([0.12, 0.20, 0.09]), np.array([0.08, 0.15, 0.11])
    typical = np.std(a - c, ddof=1) / math.sqrt(2)
    assert mine['typical_error_mm_s'] == pytest.approx(typical)
    assert mine['cv_percent'] == pytest.approx(100 * typical / np.r_[a, c].mean())
    assert mine['cv_log_percent'] == pytest.approx(100 * (math.exp(np.std(np.log(a / c), ddof=1) / math.sqrt(2)) - 1))
    assert mine['sdc_mm_s'] == pytest.approx(2.77 * typical)
    assert mine['ba_bias'] == pytest.approx(np.mean(a - c))
    assert mine['icc_a1'] == pytest.approx(agreement.icc(np.column_stack([a, c]))['agreement'])
    assert stats.loc[('SJ', 'ISMOKE'), 'participants'] == 0 and np.isnan(stats.loc[('SJ', 'ISMOKE'), 'cv_percent'])
    assert stats.loc[('XY', 'ESMOKE'), 'participants'] == 0                 # one visit of one participant only


def test_the_command_writes_the_tables(statistics, tmp_path, capsys):
    out = tmp_path / 'aims'
    assert aims.main(['--data', os.path.dirname(statistics), '--out', str(out), '--observer', 'SJ']) == 0
    for name in ('loops.csv', 'recordings.csv', 'aim1_pairs.csv', 'aim1.csv'):
        assert (out / name).is_file()
    printed = capsys.readouterr().out
    assert 'Observer SJ: 14 whole loops in 8 recordings, 9 counted' in printed
    assert 'check: C1 loop1 lies on loop2' in printed
    assert pd.read_csv(out / 'loops.csv')['observer'].eq('SJ').all()


def test_aim_2_compares_the_change_on_the_active_visit_with_the_control_visit():
    before_a, after_a = np.array([0.10, 0.08, 0.12, 0.09]), np.array([0.13, 0.08, 0.15, 0.10])
    before_c, after_c = np.array([0.11, 0.09, 0.10, 0.10]), np.array([0.10, 0.10, 0.11, 0.09])
    out = aims.response(np.r_[before_a, 0.1], np.r_[after_a, np.nan], np.r_[before_c, 0.1], np.r_[after_c, 0.1])
    assert out['participants'] == 4                                          # the one without all four is out
    difference = (after_a - before_a) - (after_c - before_c)
    assert out['difference_mm_s'] == pytest.approx(difference.mean())
    half = stats.t.ppf(0.975, 3) * difference.std(ddof=1) / 2
    assert (out['difference_ci_low_mm_s'], out['difference_ci_high_mm_s']) == \
        (pytest.approx(difference.mean() - half), pytest.approx(difference.mean() + half))
    assert out['t_test_p'] == pytest.approx(stats.ttest_rel(after_a - before_a, after_c - before_c).pvalue)
    assert out['wilcoxon_p'] == pytest.approx(stats.wilcoxon(difference).pvalue)
    assert out['change_control_mm_s'] == pytest.approx(np.mean(after_c - before_c))
    ratio = np.log(after_a / before_a) - np.log(after_c / before_c)
    assert out['ratio_of_ratios'] == pytest.approx(math.exp(ratio.mean()))
    assert out['ratio_active'] == pytest.approx(math.exp(np.log(after_a / before_a).mean()))
    assert aims.response([], [], [], [])['participants'] == 0


def test_aim_2_per_study_from_each_participants_four_recordings(statistics):
    save(statistics, 'A1b', 'loop1', 0.13)
    save(statistics, 'C1b', 'loop1', 0.07)
    save(statistics, 'A2b', 'loop1', 0.22)
    save(statistics, 'C2b', 'loop1', 0.16)
    wanted = pd.DataFrame([('ESMOKE', 'FP01', 'A1', 'A1b', 'C1', 'C1b'), ('ESMOKE', 'FP02', 'A2', 'A2b', 'C2', 'C2b'),
                           ('ESMOKE', 'FP03', 'A3', 'A3b', 'C3', 'C3b')],
                          columns=['study', 'subject', *aims.AIM2_RECORDINGS])
    values = aims.aim2_values(aims.per_recording(aims.loops(aims.collect(statistics))), wanted)
    row = aims.aim2(values).set_index(['observer', 'study']).loc[('SJ', 'ESMOKE')]
    assert (row['participants'], row['participants_wanted'], row['incomplete']) == (2, 3, 1)
    assert row['difference_mm_s'] == pytest.approx(np.mean([(0.13 - 0.10) - (0.07 - 0.08), (0.22 - 0.20) - (0.16 - 0.15)]))


def test_aim_2_uses_the_inventory_participants_with_all_four_recordings():
    wanted = aims.aim2_recordings()
    assert wanted.groupby('study').size().to_dict() == {'ESMOKE': 13, 'ISMOKE': 8}       # CLAUDE.md
    assert (wanted[list(aims.AIM2_RECORDINGS)] != '').all().all()
    assert (wanted['active_before_recording'] != wanted['control_before_recording']).all()


def test_a_threshold_sensitivity_recounts_the_loops_from_their_saved_diagrams(statistics):
    save_measured(statistics, 'A9', 'loop1', 3.0)
    save_measured(statistics, 'A9', 'loop2', -2.0, x=50, seed=1)
    table = aims.loops(aims.collect(statistics))
    mine = table[table['recording'] == 'A9'].sort_values('dataset')
    assert mine['counted'].tolist() == [True, True]
    assert mine['speed_mm_s'].tolist() == [pytest.approx(3 * 30 * 0.00133, rel=0.02),
                                           pytest.approx(2 * 30 * 0.00133, rel=0.02)]
    same = aims.recount(mine, statistics, pattern_shift.MIN_SNR)            # the app's threshold: as saved
    assert same['counted'].tolist() == [True, True]
    assert same['velocity_mm_s'].tolist() == pytest.approx(mine['velocity_mm_s'].tolist())
    assert same['snr'].tolist() == pytest.approx(mine['snr'].tolist())
    strict = aims.recount(mine, statistics, 1e9)
    assert not strict['counted'].any() and set(strict['why_not']) == {'not resolved'}
    lost = aims.recount(table[(table['recording'] == 'A1') & (table['observer'] == 'SJ')], statistics, 8.0)
    assert set(lost['why_not']) == {'no space-time diagram saved'} and not lost['counted'].any()


def test_a_loop_ranks_by_its_name():
    assert [aims.rank(name) for name in ('loop1', 'loop2', 'loop12')] == [1, 2, 12]
    assert all(np.isnan(aims.rank(name)) for name in ('set1', 'ref', 'loop', 'Loop1', 'loop1b', ''))


def test_progress_lists_codes_names_and_what_to_fix_but_no_result(statistics):
    save(statistics, 'A5', 'loop1', 0.10)
    save(statistics, 'A5', 'loop3', 0.12, x=50)                 # loop2 left out
    save(statistics, 'C5', 'loop2', 0.10)                       # no reference
    save(statistics, 'C5', 'ref', 0.10, x=50)                   # a name the protocol does not rank
    save(statistics, 'C6', 'loop1', 0.10)
    save(statistics, 'C6', 'loop2', 0.10, points=[[60, 100], [80, 0], [80, 100], [60, 0]])     # limbs cross
    studies = {'A1': 'ESMOKE', 'C1': 'ESMOKE', 'C2': 'ESMOKE', 'A5': 'ESMOKE', 'C5': 'ESMOKE', 'C6': 'ESMOKE',
               'IA1': 'ISMOKE'}
    table = aims.collect(statistics)
    printed = aims.progress(table[table['observer'] == 'SJ'], studies)
    lines = {line.split()[0]: line for line in printed.splitlines() if line.startswith('  ')}
    code = blinding.codes(studies)
    assert set(lines) == {code[name] for name in ('A1', 'C1', 'C2', 'A5', 'C5', 'C6')}
    assert lines[code['C6']].endswith('<- crosses itself: loop2')
    assert lines[code['A1']].split() == [code['A1'], 'loop1', 'loop2']             # nothing to fix
    assert 'loop1 and loop2 lie on the same capillary' in lines[code['C1']]
    c2 = lines[code['C2']]
    assert 'not a whole loop: limb1' in c2 and 'more than 3 loops: loop4, loop5' in c2
    assert 'not over the official rest: loop4' in c2 and 'not on the stabilized video: loop5' in c2
    assert 'loop2 missing' in lines[code['A5']]
    assert 'no loop1 (the reference)' in lines[code['C5']] and 'not named loop1-loop3: ref' in lines[code['C5']]
    assert 'ESMOKE: 6 of 6 recordings have lines' in printed and 'ISMOKE: 0 of 1' in printed
    assert f'No lines yet (1): {code["IA1"]}' in printed
    assert 'recordings with something to fix: 5' in printed
    for hidden in ('0.', 'mm/s', 'snr', 'count', 'A1 ', 'C2 '):            # no result, no real name
        assert hidden not in printed


def test_results_stay_hidden_while_the_app_is_in_blind_placement(statistics, tmp_path, app_settings, capsys,
                                                                 monkeypatch):
    app_settings.write_text('Application_path,/somewhere\nobserver,sj\nblind_placement,1\n', encoding='utf-8')
    monkeypatch.setattr(aims, 'aims_studies', lambda: {'A1': 'ESMOKE', 'C1': 'ESMOKE'})
    data, out = os.path.dirname(statistics), str(tmp_path / 'aims')
    assert aims.main(['--data', data, '--out', out]) == 2
    captured = capsys.readouterr()
    assert captured.out == '' and '--unblind' in captured.err and not os.path.exists(out)
    assert aims.main(['--data', data, '--progress']) == 0                   # the app's observer, upper case
    printed = capsys.readouterr().out
    assert printed.startswith('Observer SJ:') and 'ESMOKE: 2 of 2 recordings have lines' in printed
    assert '0.' not in printed and not os.path.exists(out)
    assert aims.main(['--data', data, '--out', out, '--unblind']) == 0
    assert 'counted' in capsys.readouterr().out
