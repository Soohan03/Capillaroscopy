"""Line placement (`capillary.placement`): the same capillary measured by different observers, found and compared."""

import os

import numpy as np
import pandas as pd
import pytest

import Caper
from capillary import datasets, placement
from gui import tasks
from gui.settings import DataFolder

LIMB = [(60.0, 200.0), (63.0, 150.0), (66.0, 100.0), (70.0, 50.0)]           # 150 px up a capillary limb


def shifted(points, dx=0.0, dy=0.0):
    return [(x + dx, y + dy) for x, y in points]


def measurement(recording, dataset, observer, points, median, first=0, last=899, created='2026-10-07T10:00:00'):
    return placement.Measurement(recording=recording, dataset=dataset, observer=observer, points=tuple(points),
                                 first_frame=first, last_frame=last, median_mm_s=median, resolved_fraction=0.6,
                                 created=created)


def test_lines_along_each_other_and_their_direction():
    assert placement.line_overlap(LIMB, LIMB) == (1.0, 1.0, 1)
    covered_a, covered_b, direction = placement.line_overlap(LIMB, list(reversed(shifted(LIMB, dx=2))))
    assert covered_a == 1.0 and covered_b == 1.0 and direction == -1
    other_limb = shifted(LIMB, dx=26)
    assert placement.line_overlap(LIMB, other_limb)[:2] == (0.0, 0.0)
    upper_half = LIMB[2:]                                                     # the top 50 px only
    covered_a, covered_b, _ = placement.line_overlap(LIMB, upper_half)
    assert covered_b == 1.0 and 0.25 < covered_a < 0.5


def test_frames_must_be_mostly_the_same():
    a = measurement('R', 'a', 'SJ', LIMB, 0.02, 0, 899)
    assert placement.frame_overlap(a, measurement('R', 'b', 'AB', LIMB, 0.02, 0, 899)) == 1.0
    assert placement.frame_overlap(a, measurement('R', 'b', 'AB', LIMB, 0.02, 450, 1349)) == pytest.approx(450 / 1350)
    assert placement.match(a, measurement('R', 'b', 'AB', LIMB, 0.02, 2000, 2899)) is None
    assert placement.match(a, measurement('S', 'b', 'AB', LIMB, 0.02)) is None            # another recording
    assert placement.match(a, measurement('R', 'b', 'AB', shifted(LIMB, dx=1.5), 0.02)) == 1


def capillaries():
    """Three recordings; on each, SJ and AB measured the same limb (AB 10% faster), SJ once more the other way."""
    found = []
    for number, truth in enumerate((0.010, 0.020, 0.040)):
        recording = f'FP0{number + 1}'
        found += [
            measurement(recording, 'set1', 'SJ', LIMB, truth, created='2026-10-07T10:00:00'),
            measurement(recording, 'set2', 'AB', shifted(LIMB, dx=1.5), 1.1 * truth, created='2026-10-07T11:00:00'),
            measurement(recording, 'set3', 'SJ', list(reversed(shifted(LIMB, dx=-1))), -0.95 * truth,
                        created='2026-10-08T09:00:00'),
            measurement(recording, 'other', 'AB', shifted(LIMB, dx=26), 0.5 * truth),          # the other limb
            measurement(recording, 'later', 'AB', LIMB, truth, first=3000, last=3899),        # other frames
        ]
    found.append(measurement('FP09', 'old', '', LIMB, 0.03))                                 # no observer
    return found


def test_capillaries_measured_more_than_once_are_grouped_with_their_direction():
    groups = placement.group_measurements(capillaries())
    assert len(groups) == 3
    for group in groups:
        assert [m.dataset for m, _ in group] == ['set1', 'set2', 'set3']
        assert [sign for _, sign in group] == [1, 1, -1]
    per_dataset, per_capillary = placement.placement_tables(groups)
    assert list(per_capillary['capillary']) == ['c01', 'c02', 'c03']
    assert per_capillary['SJ_velocity_mm_s'].to_numpy() == pytest.approx([0.010, 0.020, 0.040])
    assert per_capillary['AB_velocity_mm_s'].to_numpy() == pytest.approx([0.011, 0.022, 0.044])
    assert per_capillary['SJ_repeat_velocity_mm_s'].to_numpy() == pytest.approx([0.0095, 0.019, 0.038])
    assert per_dataset['reversed'].tolist() == [False, False, True] * 3


def test_observers_and_repeats_are_compared():
    _, per_capillary = placement.placement_tables(placement.group_measurements(capillaries()))
    rows = {row['comparison']: row for row in placement.compare_placements(per_capillary)}
    assert list(rows) == ['AB vs SJ', 'SJ: first vs second measurement']
    between = rows['AB vs SJ']
    assert between['kind'] == 'between observers' and between['pairs'] == 3
    assert between['ratio'] == pytest.approx(1.1)                        # AB reads 10% higher
    assert between['ratio_loa_low'] == pytest.approx(1.1) and between['ratio_loa_high'] == pytest.approx(1.1)
    assert between['bias'] == pytest.approx(np.mean([0.001, 0.002, 0.004]))
    assert between['first_column'] == 'AB_velocity_mm_s' and between['second_column'] == 'SJ_velocity_mm_s'
    within = rows['SJ: first vs second measurement']
    assert within['kind'] == 'within observer' and within['pairs'] == 3
    assert within['repeatability_coefficient'] == pytest.approx(1.96 * within['sd'])


def test_no_observers_means_nothing_to_compare():
    found = [measurement('R', 'a', '', LIMB, 0.02), measurement('R', 'b', '', LIMB, 0.03)]
    groups = placement.group_measurements(found)
    assert len(groups) == 1
    _, per_capillary = placement.placement_tables(groups)
    assert placement.compare_placements(per_capillary) == []


def test_the_report_from_saved_data_sets(tmp_path):
    folder = DataFolder(str(tmp_path / 'data'))
    folder.ensure()
    sources = []
    for m in capillaries():
        record = {'kind': 'line', 'dataset': m.dataset, 'recording': m.recording, 'created': m.created,
                  'observer': m.observer or None, 'frames': {'first': m.first_frame, 'last': m.last_frame},
                  'line': {'points': [list(p) for p in m.points]},
                  'summary': {'median': m.median_mm_s, 'resolved_fraction': 0.6}}
        datasets.write_provenance(datasets.line_dataset_files(folder.statistics, m.recording, m.dataset)['provenance'],
                                  record)
        sources.append((m.recording, m.dataset))
    sources.append(('FP01', 'missing'))                                   # no provenance: left out

    class Job:
        def report(self, progress=None, message=None):
            pass

    result = tasks.placement_report(Job(), folder=folder, sources=sources)
    assert result['measurements'] == len(capillaries()) and result['capillaries'] == 3
    for role in ('measurements', 'capillaries', 'summary', 'bland_altman', 'scatter'):
        assert os.path.isfile(result['files'][role])
    summary = pd.read_csv(result['files']['summary'])
    assert list(summary['comparison']) == ['AB vs SJ', 'SJ: first vs second measurement']
    assert os.path.dirname(result['files']['summary']) == os.path.join(folder.validation, 'line_placement')
    Caper.generate_validation_report(os.path.dirname(result['files']['summary']), pd.DataFrame(), [])
    assert not os.path.exists(result['files']['scatter'])
