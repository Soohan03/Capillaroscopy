"""The on-disk layout of saved measurements (`capillary.datasets`)."""

import json
import os

import numpy as np
import pandas as pd
import pytest

from capillary import datasets

STEM = 'FP01_W_14-Oct-2019_08-36-26'


def test_time_points_file_name(tmp_path):
    assert os.path.basename(datasets.time_points_file(str(tmp_path), STEM)) == f'{STEM}_registered_time_points.csv'


def touch(path):
    with open(path, 'w') as handle:
        handle.write('x')


def test_listing_matches_names_exactly(tmp_path):
    for name in ('Test', 'Test2', 'Test_1'):
        touch(datasets.line_dataset_files(str(tmp_path), STEM, name)['velocity'])
    # another recording whose name starts the same way must not be listed
    touch(datasets.line_dataset_files(str(tmp_path), STEM + 'b', 'Other')['velocity'])

    assert datasets.list_line_datasets(str(tmp_path), STEM) == ['Test', 'Test2', 'Test_1']


def test_listing_copes_with_glob_characters_in_the_stem(tmp_path):
    stem = 'odd[1]*name'
    touch(datasets.line_dataset_files(str(tmp_path), stem, 'x')['velocity'])
    assert datasets.list_line_datasets(str(tmp_path), stem) == ['x']


def test_dataset_paths_do_not_mix_up_similar_names(tmp_path):
    statistics, reports = tmp_path / 'Statistics', tmp_path / 'Reports'
    statistics.mkdir()
    reports.mkdir()
    for name in ('Test', 'Test2'):
        for path in datasets.line_dataset_files(str(statistics), STEM, name).values():
            touch(path)
        for path in datasets.line_report_files(str(reports), STEM, name).values():
            touch(path)
    paths = datasets.dataset_paths(str(statistics), str(reports), STEM, 'Test')
    assert len(paths) == 6
    assert not any('Test2' in os.path.basename(p) for p in paths)


def test_line_data_set_files_and_round_trip(tmp_path):
    statistics, reports = tmp_path / 'Statistics', tmp_path / 'Reports'
    statistics.mkdir()
    reports.mkdir()
    files = datasets.line_dataset_files(str(statistics), STEM, 'line1')
    assert os.path.basename(files['space_time']) == f'{STEM}___line1___space_time.npy'
    assert os.path.basename(files['velocity']) == f'{STEM}___line1___line_velocity.csv'
    assert os.path.basename(files['provenance']) == f'{STEM}___line1___line_provenance.json'
    plots = datasets.line_report_files(str(reports), STEM, 'line1')
    assert os.path.basename(plots['space_time']) == f'{STEM}___line1___space_time.png'

    diagram = np.arange(12, dtype=float).reshape(4, 3)
    blocks = pd.DataFrame({'time_s': [1.5], 'speed_px_per_frame': [0.5], 'velocity_mm_s': [0.03], 'snr': [20.0],
                           'coherence': [0.2], 'resolved': [True]}, index=pd.Index([45], name='frame'))
    written = datasets.write_line_dataset(str(statistics), STEM, 'line1', diagram, blocks)
    assert set(written) == {'space_time', 'velocity'}
    loaded_diagram, loaded_blocks = datasets.load_line_dataset(str(statistics), STEM, 'line1')
    assert loaded_diagram.dtype == np.float32
    np.testing.assert_array_equal(loaded_diagram, diagram)
    assert list(loaded_blocks.index) == [45] and bool(loaded_blocks['resolved'].iloc[0])

    assert datasets.list_line_datasets(str(statistics), STEM) == ['line1']
    touch(plots['space_time'])
    paths = datasets.dataset_paths(str(statistics), str(reports), STEM, 'line1')
    assert sorted(os.path.basename(p) for p in paths) == sorted(
        [f'{STEM}___line1___space_time.npy', f'{STEM}___line1___line_velocity.csv', f'{STEM}___line1___space_time.png'])
    assert datasets.dataset_paths(str(statistics), str(reports), STEM, 'line2') == []


@pytest.mark.parametrize('name', ['set1', 'Före test', 'baseline-2.1', 'a b c'])
def test_valid_names(name):
    assert datasets.validate_dataset_name(name) is None


@pytest.mark.parametrize('name', ['', '   ', ' lead', 'trail ', 'a___b', 'x/y', 'a:b', 'what?', 'end.', 'x' * 81])
def test_invalid_names_are_explained(name):
    message = datasets.validate_dataset_name(name)
    assert isinstance(message, str) and message


def test_suggested_name_is_unused():
    assert datasets.suggest_dataset_name([]) == 'set1'
    assert datasets.suggest_dataset_name(['set1', 'set2', 'other']) == 'set3'
    assert datasets.suggest_dataset_name(['loop1'], 'loop') == 'loop2'


def test_observer_codes():
    assert datasets.normalize_observer(' sj ') == 'SJ' and datasets.normalize_observer(None) == ''
    assert datasets.validate_observer('sj') is None and datasets.validate_observer('SJ-R') is None
    assert datasets.validate_observer(' ') and datasets.validate_observer('a b')
    assert datasets.validate_observer('x' * 17)


def test_time_points_round_trip(tmp_path):
    path = str(tmp_path / 'tp.csv')
    datasets.save_time_points(path, [12.5, 3.0])
    assert datasets.load_time_points(path) == [3.0, 12.5]
    # same format the old GUI wrote: header ",0" and one row per point
    assert pd.read_csv(path)['0'].tolist() == [3.0, 12.5]


def test_time_points_tolerate_missing_and_empty_legacy_files(tmp_path):
    assert datasets.load_time_points(str(tmp_path / 'missing.csv')) == []
    empty = tmp_path / 'empty.csv'
    pd.DataFrame([]).to_csv(empty)          # what the old GUI wrote with no points: '""'
    assert datasets.load_time_points(str(empty)) == []


def test_provenance_is_strict_json(tmp_path):
    path = str(tmp_path / 'p.json')
    datasets.write_provenance(path, {'kind': 'line', 'median': float('nan'), 'n': np.int64(3),
                                     'points': [{'x': np.int32(4)}], 'name': 'Före'})
    text = open(path, encoding='utf-8').read()
    assert 'NaN' not in text
    record = json.loads(text)
    assert record['median'] is None and record['n'] == 3 and record['points'][0]['x'] == 4
    assert record['name'] == 'Före' and 'written' in record
    assert datasets.read_provenance(path) == record
    assert datasets.read_provenance(str(tmp_path / 'absent.json')) is None


def test_software_version_reports_a_commit_or_nothing(tmp_path):
    info = datasets.software_version()
    assert set(info) == {'git_commit', 'git_uncommitted_changes'}
    assert datasets.software_version(str(tmp_path)) == {'git_commit': None, 'git_uncommitted_changes': None}
