"""Reading sets and the agreement of observers with the estimator (`capillary.validation`).

Centre-line data sets are made from synthetic diagrams with a known speed
(flow) or none (still), then observers are simulated: they read the true
speed with a little scatter where there is flow and see no streaks where
there is none.
"""

import json
import math
import os

import numpy as np
import pandas as pd
import pytest

import Caper
from capillary import datasets, spacetime, validation

from .test_spacetime import diagram as moving_diagram

FPS, MM_PER_PIXEL = 30.0, 0.0013
STEMS = {'flow': 'FP90_flow_01-Jan-2026_10-00-00', 'slow': 'FP90_slow_01-Jan-2026_10-05-00',
         'still': 'FP91_still_02-Jan-2026_11-00-00'}
SPEEDS = {'flow': 1.0, 'slow': 0.4, 'still': 0.0}           # px/frame, towards the line's last point


def save_line_dataset(statistics, stem, name, diagram, first_frame=100):
    blocks = spacetime.analyze_space_time(diagram, FPS, MM_PER_PIXEL, first_frame=first_frame)
    datasets.write_line_dataset(statistics, stem, name, diagram, blocks)
    record = {'kind': 'line', 'dataset': name, 'recording': stem, 'video': {'fps': FPS},
              'frames': {'first': first_frame, 'last': first_frame + len(diagram) - 1, 'count': len(diagram)},
              'line': {'points': [[10, 10], [10, 129]], 'length_px': float(diagram.shape[1] - 1)},
              'mm_per_pixel': MM_PER_PIXEL}
    datasets.write_provenance(datasets.line_dataset_files(statistics, stem, name)['provenance'], record)
    return blocks


@pytest.fixture(scope='module')
def folders(tmp_path_factory):
    root = tmp_path_factory.mktemp('data')
    statistics, validation_dir = str(root / 'Statistics'), str(root / 'Validation')
    os.makedirs(statistics)
    for number, (kind, stem) in enumerate(STEMS.items()):
        save_line_dataset(statistics, stem, 'line1', moving_diagram(SPEEDS[kind], frames=450, seed=number + 1))
    return statistics, validation_dir


@pytest.fixture(scope='module')
def reading_set(folders):
    statistics, validation_dir = folders
    sources = [(stem, 'line1') for stem in STEMS.values()]
    return validation.create_reading_set(validation_dir, statistics, 'pilot', sources, blocks_per_dataset=4, seed=7)


# ------------------------------------------------------------------------- choosing blocks

def test_blocks_are_drawn_without_overlap_half_of_them_resolved():
    starts = list(range(0, 600, 15))
    resolved = [start < 300 for start in starts]
    chosen = validation.choose_blocks(starts, resolved, 4, 90, True, np.random.default_rng(1))
    assert len(chosen) == 4
    assert all(b - a >= 90 for a, b in zip(chosen, chosen[1:]))
    assert sum(start < 300 for start in chosen) == 2
    again = validation.choose_blocks(starts, resolved, 4, 90, True, np.random.default_rng(1))
    assert again == chosen


def test_a_shortage_of_one_kind_is_made_up_from_the_other():
    starts = list(range(0, 600, 15))
    resolved = [start == 0 for start in starts]            # a single resolved block
    chosen = validation.choose_blocks(starts, resolved, 4, 90, True, np.random.default_rng(2))
    assert len(chosen) == 4 and chosen[0] == 0
    few = validation.choose_blocks(starts[:10], resolved[:10], 6, 90, False, np.random.default_rng(3))
    assert len(few) == 2                                     # 150 frames hold at most two blocks of 90


# ----------------------------------------------------------------------------- the set

def test_the_set_holds_copies_of_the_blocks_the_estimator_measured(folders, reading_set):
    statistics, validation_dir = folders
    assert validation.list_reading_sets(validation_dir) == ['pilot']
    assert len(reading_set.items) == 12 and len({item.id for item in reading_set.items}) == 12
    loaded = validation.load_reading_set(validation_dir, 'pilot')
    for item in loaded.items:
        diagram, blocks = datasets.load_line_dataset(statistics, item.recording, item.dataset)
        block = loaded.block(item.id)
        np.testing.assert_array_equal(block, diagram[item.start_row:item.start_row + item.frames])
        assert item.first_frame == 100 + item.start_row
        saved = blocks.loc[item.first_frame + item.frames // 2]
        assert item.estimate['resolved'] == bool(saved['resolved'])
        assert item.estimate['speed_px_per_frame'] == pytest.approx(saved['speed_px_per_frame'])
        assert item.mm_s_per_px_frame == pytest.approx(FPS * MM_PER_PIXEL)
    record = json.load(open(os.path.join(validation_dir, 'pilot', validation.SET_FILE), encoding='utf-8'))
    assert record['seed'] == 7 and record['sampling']['balanced'] is True
    assert {source['recording'] for source in record['sources']} == set(STEMS.values())
    assert not os.path.exists(os.path.join(validation_dir, '.partial'))


def test_the_same_seed_draws_the_same_set(folders, reading_set, tmp_path):
    statistics, _ = folders
    other = validation.create_reading_set(str(tmp_path), statistics, 'again',
                                          [(stem, 'line1') for stem in reversed(list(STEMS.values()))],
                                          blocks_per_dataset=4, seed=7)
    assert [item.as_record() for item in other.items] == [item.as_record() for item in reading_set.items]


def test_bad_names_and_existing_sets_are_refused(folders, reading_set):
    statistics, validation_dir = folders
    sources = [(STEMS['flow'], 'line1')]
    with pytest.raises(FileExistsError):
        validation.create_reading_set(validation_dir, statistics, 'pilot', sources)
    for name in ('', 'a/b', 'a___b', '.hidden'):
        with pytest.raises(ValueError):
            validation.create_reading_set(validation_dir, statistics, name, sources)
    with pytest.raises(ValueError):
        validation.create_reading_set(validation_dir, statistics, 'empty', [])


# ------------------------------------------------------------------------------ readings

def test_every_observer_and_session_gets_its_own_order(reading_set):
    ids = [item.id for item in reading_set.items]
    first = validation.reading_order(ids, 7, 'sj', 1)
    assert sorted(first) == sorted(ids)
    assert first == validation.reading_order(ids, 7, 'SJ', 1)            # codes are not case-sensitive
    assert first != validation.reading_order(ids, 7, 'SJ', 2)
    assert first != validation.reading_order(ids, 7, 'AB', 1)


def test_the_slope_of_a_block_is_the_mean_slope_of_its_lines():
    lines = [(0, 10, 50, 60), (80, 40, 10, 5)]                           # 1.0 and 0.5 px/frame
    assert validation.line_speed(lines) == pytest.approx(0.75)
    assert validation.line_speed([(0, 10, 2, 90)]) != validation.line_speed([(0, 10, 2, 90)])  # NaN: too flat
    assert validation.line_speed([(0, 60, 40, 40)]) == pytest.approx(-0.5)                   # against the line


def test_a_reading_is_saved_after_every_block_and_resumes(reading_set):
    reading = reading_set.open_reading('xy', 1)
    assert reading.observer == 'XY' and not os.path.exists(reading.path)
    first, second = reading.order[:2]
    reading.record_lines(first, [(0, 0, 60, 30), (20, 50, 80, 80), (0, 0, 1, 50)], seconds=12.34)
    reading.record_no_streaks(second, seconds=3)
    with pytest.raises(ValueError):
        reading.record_lines(reading.order[2], [(0, 0, 1, 50)])        # no usable line
    again = reading_set.open_reading('XY', 1)
    assert again.order == reading.order
    assert again.outcome(first) == validation.SLOPE and len(again.lines(first)) == 2
    assert again.speed(first) == pytest.approx(0.5)
    assert again.seconds(first) == pytest.approx(12.3)
    assert again.outcome(second) == validation.NO_STREAKS and math.isnan(again.speed(second))
    assert again.first_unread() == 2 and again.read_count == 2 and not again.is_complete
    assert reading_set.next_session('xy') == 1                           # unfinished: continue it
    again.clear(second)
    assert validation.Reading.load(again.path).outcome(second) is None
    os.remove(again.path)


def test_observer_codes():
    assert validation.validate_observer('sj') is None
    assert validation.validate_observer(' ') and validation.validate_observer('a b')
    assert validation.validate_observer('x' * 17)


# ----------------------------------------------------------------------------- agreement

def simulate_reading(reading_set, observer, session, scatter, seed):
    """An observer who reads the true slope with `scatter` (relative SD) and sees nothing without flow."""
    rng = np.random.default_rng(seed)
    reading = reading_set.open_reading(observer, session)
    truth = {stem: SPEEDS[kind] for kind, stem in STEMS.items()}
    for item_id in reading.order:
        item = reading_set.item(item_id)
        speed = truth[item.recording]
        if speed == 0:
            reading.record_no_streaks(item_id, seconds=5)
        else:
            read = speed * (1 + rng.normal(0, scatter))
            reading.record_lines(item_id, [(0, 10, 60, 10 + 60 * read)], seconds=20)
    return reading


@pytest.fixture(scope='module')
def agreement(reading_set):
    readings = [simulate_reading(reading_set, 'SJ', 1, 0.05, 1), simulate_reading(reading_set, 'AB', 1, 0.05, 2),
                simulate_reading(reading_set, 'SJ', 2, 0.05, 3)]
    estimates = validation.estimate_items(reading_set)
    table = validation.agreement_table(reading_set, reading_set.readings(), estimates)
    comparisons = validation.compare(table, reading_set.readings())
    return readings, estimates, table, comparisons


def test_the_estimate_is_measured_again_and_matches_the_data_set(reading_set, agreement):
    _, estimates, table, _ = agreement
    for item in reading_set.items:
        assert bool(estimates.loc[item.id, 'resolved']) == item.estimate['resolved']
        assert estimates.loc[item.id, 'speed_px_per_frame'] == pytest.approx(item.estimate['speed_px_per_frame'])
    flow = table[table['recording'] == STEMS['flow']]
    assert flow['auto_resolved'].all()
    assert flow['auto_velocity_mm_s'].to_numpy() == pytest.approx(1.0 * FPS * MM_PER_PIXEL, rel=0.05)
    assert flow['SJ_s1_velocity_mm_s'].to_numpy() == pytest.approx(1.0 * FPS * MM_PER_PIXEL, rel=0.25)
    still = table[table['recording'] == STEMS['still']]
    assert (still['AB_s1_outcome'] == validation.NO_STREAKS).all()
    assert still['observers_readable'].eq(0).all()


def test_the_comparisons(agreement):
    _, _, table, comparisons = agreement
    by_name = {row['comparison']: row for row in comparisons}
    assert list(by_name) == ['Automatic vs AB, session 1', 'Automatic vs SJ, session 1', 'Automatic vs SJ, session 2',
                             'Automatic vs mean of observers (AB, SJ)', 'AB, session 1 vs SJ, session 1',
                             'SJ: session 1 vs session 2']
    readable = int((table['recording'] != STEMS['still']).sum())
    automatic = by_name['Automatic vs SJ, session 1']
    assert automatic['kind'] == 'automatic vs observer' and automatic['judged_by_both'] == len(table)
    assert automatic['pairs'] == int((table['auto_resolved'] & (table['recording'] != STEMS['still'])).sum())
    assert automatic['pairs'] >= readable - 1
    assert abs(automatic['bias']) < 0.1 * FPS * MM_PER_PIXEL
    assert automatic['loa_low'] < automatic['bias'] < automatic['loa_high']
    assert automatic['ratio'] == pytest.approx(1.0, abs=0.1)
    assert automatic['same_direction'] == 1.0
    assert automatic['readable_both'] + automatic['readable_neither'] + automatic['readable_first_only'] \
        + automatic['readable_second_only'] == len(table)
    between = by_name['AB, session 1 vs SJ, session 1']
    assert between['kind'] == 'between observers' and between['pairs'] == readable
    assert between['icc_agreement'] > 0.8 and between['kappa'] == pytest.approx(1.0)
    within = by_name['SJ: session 1 vs session 2']
    assert within['kind'] == 'within observer'
    assert within['repeatability_coefficient'] == pytest.approx(1.96 * within['sd'])
    assert 'repeatability_coefficient' not in between


def test_three_observers_add_the_icc_of_all_of_them(reading_set, agreement):
    readings = list(agreement[0]) + [simulate_reading(reading_set, 'CD', 1, 0.05, 4)]
    try:
        table = validation.agreement_table(reading_set, readings, agreement[1])
        rows = validation.compare(table, readings)
        everyone = [row for row in rows if row['comparison'].startswith('All observers')]
        assert len(everyone) == 1 and everyone[0]['icc_agreement'] > 0.8
        assert sum(row['kind'] == 'between observers' for row in rows) == 4      # three pairs and all
    finally:
        os.remove(readings[-1].path)


def test_the_report_is_written_and_read_back(reading_set, agreement):
    readings, _, table, comparisons = agreement
    files = validation.write_report_tables(reading_set, table, comparisons, reading_set.readings())
    files.update(Caper.generate_validation_report(reading_set.report_dir, table, comparisons))
    for role in ('items', 'summary', 'readings', 'bland_altman', 'scatter'):
        assert os.path.isfile(files[role])
    summary = pd.read_csv(files['readings'])
    assert list(summary['observer']) == ['AB', 'SJ', 'SJ'] and (summary['read'] == len(table)).all()
    loaded = validation.load_comparisons(reading_set)
    assert [row['comparison'] for row in loaded] == [row['comparison'] for row in comparisons]
    assert loaded[0]['bias'] == pytest.approx(comparisons[0]['bias'])
    # nothing to plot: stale plots are removed
    Caper.generate_validation_report(reading_set.report_dir, table, [])
    assert not os.path.exists(files['bland_altman'])
