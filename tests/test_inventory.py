"""The study's recordings and which ones the aims use (`capillary.inventory`), on the real metadata."""

import datetime
import unicodedata

import pytest

from capillary import inventory
from capillary.inventory import mark_use, parse_name, participants, recording_phases, recordings, video_stems


@pytest.fixture(scope='module')
def tables():
    table = recordings()
    people = participants(table)
    return mark_use(table, people), people


def test_a_name_says_what_the_recording_is():
    name = parse_name('FP05_Qföre_försök4_23-Oct-2019_09-24-22')
    assert (name.study, name.subject, name.condition, name.role, name.phase, name.attempt) == \
        ('ESMOKE', 'FP05', 'Q', 'control', 'före', 4)
    assert name.started == datetime.datetime(2019, 10, 23, 9, 24, 22)
    ismoke = parse_name('ISMOKE_FP23_Cefter2_09-Dec-2020_09-52-09')
    assert (ismoke.study, ismoke.condition, ismoke.role, ismoke.phase, ismoke.attempt) == \
        ('ISMOKE', 'C', 'control', 'efter', 2)


def test_names_that_bend_the_pattern():
    assert parse_name('FP21Wföre_20-Nov-2019_09-08-03').subject == 'FP21'       # no underscore after the code
    assert parse_name('FP01_W_14-Oct-2019_08-36-26').phase is None             # neither före nor efter
    assert parse_name('FP01_Qföre.avi') is None
    decomposed = unicodedata.normalize('NFD', 'FP03_Qföre_15-Oct-2019_09-15-49')  # how macOS spells file names
    assert parse_name(decomposed).name == 'FP03_Qföre_15-Oct-2019_09-15-49'


def test_every_recording_in_the_metadata_is_understood(tables):
    table, people = tables
    assert len(table) == 124 and len(people) == 30
    assert set(table['phase']) == {'före', 'efter'}


def test_what_does_not_fit_is_flagged(tables):
    table, _ = tables
    issues = table.set_index('name')['issues']
    assert 'taken as före' in issues['FP01_W_14-Oct-2019_08-36-26']
    assert 'two conditions on one day' in issues['ISMOKE_FP02_Sföre_02-Nov-2020_09-19-10']
    assert 'probably an efter' in issues['ISMOKE_FP08_Cföre_10-Nov-2020_10-07-08']
    assert 'rest only 2 s' in issues['ISMOKE_FP04_Sefter_11-Nov-2020_10-27-46']
    assert issues['FP03_Qföre_15-Oct-2019_09-15-49'] == ''


def test_the_last_usable_attempt_is_chosen(tables):
    _, people = tables
    person = people.set_index(['study', 'subject'])
    assert person.loc[('ESMOKE', 'FP05'), 'control_före'] == 'FP05_Qföre_försök4_23-Oct-2019_09-24-22'
    assert 'FP05_Qföre_23-Oct-2019_09-05-51' in person.loc[('ESMOKE', 'FP05'), 'control_före_alternatives']
    assert person.loc[('ESMOKE', 'FP01'), 'active_efter'] == 'FP01_Wefter_14-Oct-2019_10-13-03'
    # ISMOKE FP04's after-exposure recording starts the occlusion at 6.4 s: no rest to measure
    assert person.loc[('ISMOKE', 'FP04'), 'active_efter'] == ''


def test_who_the_aims_can_use(tables):
    _, people = tables
    status = people.set_index(['study', 'subject'])[['aim1', 'aim2']]
    counts = people.groupby('study')[['aim1', 'aim2']].agg(lambda s: dict(s.value_counts()))
    assert counts.loc['ESMOKE', 'aim1'] == {'yes': 13, 'check': 1, 'no': 3}
    assert counts.loc['ESMOKE', 'aim2'] == {'yes': 12, 'check': 1, 'no': 4}
    assert counts.loc['ISMOKE', 'aim1'] == {'yes': 9, 'check': 1, 'no': 3}
    assert counts.loc['ISMOKE', 'aim2'] == {'yes': 8, 'no': 5}
    assert tuple(status.loc[('ESMOKE', 'FP09')]) == ('yes', 'no')        # no efter on the active day
    assert tuple(status.loc[('ESMOKE', 'FP02')]) == ('no', 'no')         # one visit only


def test_each_recording_is_marked_with_its_use(tables):
    table, _ = tables
    use = table.set_index('name')['used_for']
    assert use['FP03_Qföre_15-Oct-2019_09-15-49'] == 'aims 1, 2: control före'
    assert use['FP03_Wefter_21-Oct-2019_10-21-58'] == 'aim 2: active efter'
    assert use['FP09_Wföre_23-Oct-2019_08-20-37'] == 'aim 1: active före'
    assert use['FP02_Wföre_15-Oct-2019_08-29-10'] == ''
    assert (table['used_for'] != '').sum() == 90


def test_downloaded_videos_are_matched_whatever_the_spelling(tmp_path):
    (tmp_path / unicodedata.normalize('NFD', 'FP03_Qföre_15-Oct-2019_09-15-49.avi')).touch()
    (tmp_path / 'notes.txt').touch()
    assert video_stems(str(tmp_path)) == {'FP03_Qföre_15-Oct-2019_09-15-49'}
    assert video_stems(str(tmp_path / 'missing')) == set()


def test_the_official_phases_as_frames_of_a_video():
    # FP01_Qföre: occlusion at 68.3 s, release at 130.5 s; a 180-s video at 30 fps
    phases = recording_phases('FP01_Qföre_22-Oct-2019_08-16-35', 30.0, 5400)
    assert phases.windows == {'rest': (60, 1988), 'occlusion': (2109, 3854), 'after release': (3975, 5339)}
    assert phases.notes == ()
    assert phases.phase_of(60, 1988, 30.0) == 'rest'
    assert phases.phase_of(2000, 2100, 30.0) == 'rest + occlusion'
    assert phases.phase_of(0, 5399, 30.0) == 'rest + occlusion + after release'
    decomposed = unicodedata.normalize('NFD', 'FP01_Qföre_22-Oct-2019_08-16-35')
    assert recording_phases(decomposed, 30.0, 5400).windows == phases.windows


def test_phases_without_a_release_or_that_do_not_fit_the_video():
    no_release = recording_phases('FP01_Qefter_22-Oct-2019_09-46-17', 30.0, 5400)       # occlusion 66.5 s
    assert list(no_release.windows) == ['rest'] and 'only the rest' in no_release.notes[0]
    assert no_release.phase_of(2100, 2200, 30.0) == 'occlusion or later'
    short = recording_phases('ISMOKE_FP04_Sefter_11-Nov-2020_10-27-46', 30.0, 5400)     # occlusion at 6.4 s
    assert short.windows['rest'] == (60, 131) and 'Only 2 s of rest' in short.notes[0]
    # occlusion at 158.5 s and release at 230.1 s, but the 3435 frames last 114.5 s at 30 fps
    late = recording_phases('FP01_Wefter_14-Oct-2019_10-07-49', 30.0, 3435)
    assert late.windows == {} and 'do not fit' in late.notes[0] and late.phase_of(0, 100, 30.0) == ''
    assert recording_phases('FP99_Qföre_01-Jan-2020_10-00-00', 30.0, 5400) is None      # not in the metadata


def test_the_command_line(tmp_path, capsys):
    (tmp_path / 'videos').mkdir()
    (tmp_path / 'videos' / 'FP03_Qföre_15-Oct-2019_09-15-49.avi').touch()
    assert inventory.main(['--out', str(tmp_path / 'out'), '--have', str(tmp_path / 'videos')]) == 0
    assert sorted(p.name for p in (tmp_path / 'out').iterdir()) == ['participants.csv', 'recordings.csv',
                                                                    'to_download.csv']
    printed = capsys.readouterr().out
    assert '124 recordings of 30 participants' in printed and 'still to download: 89' in printed
