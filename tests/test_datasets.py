"""The on-disk layout of saved measurements (`capillary.datasets`)."""

import json
import os

import numpy as np
import pandas as pd
import pytest

from capillary import datasets

STEM = 'FP01_W_14-Oct-2019_08-36-26'


def test_file_names_follow_the_legacy_layout(tmp_path):
    files = datasets.velocity_dataset_files(str(tmp_path), STEM, 'set1')
    assert os.path.basename(files['cross_correlation']) == f'{STEM}___set1___cross_correlation.csv'
    assert os.path.basename(files['distance_vector']) == f'{STEM}___set1___distance_vector.csv'
    assert os.path.basename(files['blur_vector']) == f'{STEM}___set1___blur_vector.csv'
    assert os.path.basename(files['report']) == f'{STEM}___set1___report.csv'

    reports = datasets.velocity_report_files(str(tmp_path), STEM, 'set1')
    assert os.path.basename(reports['velocity']) == f'{STEM}___set1velocity.png'
    assert os.path.basename(reports['summary']) == f'{STEM}___set1___report_summary.csv'
    assert os.path.basename(datasets.time_points_file(str(tmp_path), STEM)) == f'{STEM}_registered_time_points.csv'


def touch(path):
    with open(path, 'w') as handle:
        handle.write('x')


def test_listing_matches_names_exactly(tmp_path):
    for name in ('Test', 'Test2', 'Test_1'):
        touch(datasets.velocity_dataset_files(str(tmp_path), STEM, name)['cross_correlation'])
    # another recording whose name starts the same way must not be listed
    touch(datasets.velocity_dataset_files(str(tmp_path), STEM + 'b', 'Other')['cross_correlation'])

    assert datasets.list_velocity_datasets(str(tmp_path), STEM) == ['Test', 'Test2', 'Test_1']


def test_listing_copes_with_glob_characters_in_the_stem(tmp_path):
    stem = 'odd[1]*name'
    touch(datasets.velocity_dataset_files(str(tmp_path), stem, 'x')['cross_correlation'])
    assert datasets.list_velocity_datasets(str(tmp_path), stem) == ['x']


def test_dataset_paths_do_not_mix_up_similar_names(tmp_path):
    statistics, reports = tmp_path / 'Statistics', tmp_path / 'Reports'
    statistics.mkdir()
    reports.mkdir()
    for name in ('Test', 'Test2'):
        for path in datasets.velocity_dataset_files(str(statistics), STEM, name).values():
            touch(path)
        for path in datasets.velocity_report_files(str(reports), STEM, name).values():
            touch(path)
    paths = datasets.dataset_paths(str(statistics), str(reports), STEM, 'Test')
    assert len(paths) == 10
    assert not any('Test2' in os.path.basename(p) for p in paths)


def test_old_flow_data_sets_are_found_with_their_plots(tmp_path):
    statistics, reports = tmp_path / 'Statistics', tmp_path / 'Reports'
    statistics.mkdir()
    reports.mkdir()
    # the names an optical-flow data set had before 2026-10-06, including one saved without a name
    for name in ('', 'Test_1', 'Test_12'):
        for part in ('flow.pickle', 'mask.pickle'):
            touch(statistics / f'{STEM}___{name}___{part}')
    for part in ('up_and_down_.png', 'omnidirectional_.png'):
        touch(reports / f'{STEM}___Test_1___{part}')
    touch(statistics / f'{STEM}___Test_1___flow_provenance.json')

    paths = datasets.legacy_flow_dataset_paths(str(statistics), str(reports), STEM, 'Test_1')
    assert sorted(os.path.basename(p) for p in paths) == sorted(
        f'{STEM}___Test_1___{part}' for part in ('flow.pickle', 'mask.pickle', 'flow_provenance.json',
                                                  'up_and_down_.png', 'omnidirectional_.png'))
    assert [os.path.basename(p) for p in datasets.legacy_flow_dataset_paths(
        str(statistics), str(reports), STEM, '')] == [f'{STEM}______flow.pickle', f'{STEM}______mask.pickle']


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


def test_velocity_dataset_layout(tmp_path):
    a = np.linspace(10, 20, 5)
    b = np.linspace(30, 40, 5)
    blur = np.arange(5) / 10
    written = datasets.write_velocity_dataset(str(tmp_path), STEM, 'set1', a, b, 29.5, blur,
                                              start_frame=3, frame_count=10)
    assert set(written) == {'cross_correlation', 'distance_vector', 'blur_vector'}

    # two rows (box 1, box 2) by one column per frame, NaN outside the range
    intensity = pd.read_csv(written['cross_correlation'], index_col=0)
    assert intensity.shape == (2, 10)
    assert list(intensity.columns) == [str(i) for i in range(10)]
    np.testing.assert_allclose(intensity.iloc[0, 3:8], a)
    np.testing.assert_allclose(intensity.iloc[1, 3:8], b)
    assert intensity.iloc[:, :3].isna().all().all() and intensity.iloc[:, 8:].isna().all().all()

    distance = pd.read_csv(written['distance_vector'], index_col=0)['0']
    assert distance.iloc[3:8].tolist() == [29.5] * 5
    assert distance.iloc[:3].isna().all()

    sharpness = pd.read_csv(written['blur_vector'], index_col=0)['0']
    np.testing.assert_allclose(sharpness.iloc[3:8], blur)


def test_provenance_is_strict_json(tmp_path):
    path = str(tmp_path / 'p.json')
    datasets.write_provenance(path, {'kind': 'velocity', 'median': float('nan'), 'n': np.int64(3),
                                     'boxes': [{'x': np.int32(4)}], 'name': 'Före'})
    text = open(path, encoding='utf-8').read()
    assert 'NaN' not in text
    record = json.loads(text)
    assert record['median'] is None and record['n'] == 3 and record['boxes'][0]['x'] == 4
    assert record['name'] == 'Före' and 'written' in record
    assert datasets.read_provenance(path) == record
    assert datasets.read_provenance(str(tmp_path / 'absent.json')) is None


def test_software_version_reports_a_commit_or_nothing(tmp_path):
    info = datasets.software_version()
    assert set(info) == {'git_commit', 'git_uncommitted_changes'}
    assert datasets.software_version(str(tmp_path)) == {'git_commit': None, 'git_uncommitted_changes': None}
