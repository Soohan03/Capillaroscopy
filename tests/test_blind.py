"""Blind placement (`gui.blind`): the codes recordings show under, and which recordings are listed."""

import unicodedata

from capillary import blinding
from gui import blind
from gui.library import Recording

NAMES = ['FP01_Qföre_22-Oct-2019_08-16-35', 'FP01_W_14-Oct-2019_08-36-26', 'FP03_Wföre_21-Oct-2019_08-58-40',
         'ISMOKE_FP02_Sföre_02-Mar-2020_08-30-00']


def test_a_code_hides_the_name_and_is_always_the_same():
    codes = [blind.code(name) for name in NAMES]
    assert all(len(code) == blind.LENGTH and set(code) <= set(blind.ALPHABET) for code in codes)
    assert len(set(codes)) == len(NAMES)
    assert codes == [blind.code(name) for name in NAMES]                         # the same every time
    # macOS spells ö as o + a combining mark; the code is the same
    assert blind.code(unicodedata.normalize('NFD', NAMES[0])) == codes[0]


def test_a_code_two_names_share_is_told_apart(monkeypatch):
    monkeypatch.setattr(blinding, 'code', lambda stem: 'SAME1')
    assert blind.codes(['b', 'a', 'c']) == {'a': 'SAME1', 'b': 'SAME1-2', 'c': 'SAME1-3'}


def test_the_app_and_the_command_line_use_the_same_codes():
    assert blind.code is blinding.code and blind.codes is blinding.codes


def test_only_the_recordings_the_aims_use_are_listed_in_the_order_of_their_codes():
    recordings = [Recording(name) for name in NAMES + ['FP02_Wföre_17-Oct-2019_09-00-00']]
    used = frozenset(unicodedata.normalize('NFC', name) for name in NAMES)
    listed = blind.listed(recordings, used)
    assert [r.stem for r in listed] == sorted(NAMES, key=blind.code)
    assert [r.stem for r in blind.listed(recordings, frozenset())] == sorted(
        [r.stem for r in recordings], key=blind.code)                        # without official times: every one


def test_the_aims_recordings_come_from_the_inventory():
    used = blind.aim_recordings()
    assert 'FP01_Qföre_22-Oct-2019_08-16-35' in used                         # aims 1 and 2, control before
    assert 'FP01_Qefter_försök2_22-Oct-2019_09-50-15' in used                # aim 2, control after: the last attempt
    assert 'FP01_Qefter_22-Oct-2019_09-46-17' not in used                    # the attempt before it
