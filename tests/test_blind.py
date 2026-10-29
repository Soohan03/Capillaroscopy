"""Blind placement (`gui.blind`): the codes recordings show under, and which recordings are listed."""

import unicodedata
from types import SimpleNamespace

from capillary import blinding, datasets, pattern_shift
from gui import blind
from gui.library import Recording
from gui.line_page import ROLE_NAMES, LinePage

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


class _Var:
    """Stands in for a Tk variable."""

    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _Button:
    def __init__(self):
        self.disabled = False

    def state(self, spec):
        self.disabled = spec == ['disabled']


def _line_page(blind_on: bool, role: str):
    """The parts of a Centre line page that `LinePage.keep_blind_role` uses, without a window."""
    page = SimpleNamespace(app=SimpleNamespace(blind=blind_on), role_var=_Var(role), name_var=_Var('set3'),
                           role_buttons={r: _Button() for r in ROLE_NAMES}, recording=object(),
                           existing_names=lambda: ['set1', 'set2'], draw_overlay=lambda: None)
    page.suggest_name = lambda existing: datasets.suggest_dataset_name(existing, ROLE_NAMES[page.role_var.get()])
    return page


def test_blind_placement_saves_every_line_as_a_whole_loop():
    # a recording seen before brings back its line's role (here any stretch, as a try-out line had on 2026-10-29)
    page = _line_page(blind_on=True, role='')
    LinePage.keep_blind_role(page)
    assert blind.ROLE == pattern_shift.WHOLE_LOOP and page.role_var.get() == blind.ROLE
    assert page.name_var.get() == 'loop1'                                     # the name the analysis ranks
    assert [r for r, button in page.role_buttons.items() if not button.disabled] == [blind.ROLE]
    page = _line_page(blind_on=False, role='')                                # outside it, any role
    LinePage.keep_blind_role(page)
    assert page.role_var.get() == '' and page.name_var.get() == 'set3'
    assert not any(button.disabled for button in page.role_buttons.values())


def test_the_aims_recordings_come_from_the_inventory():
    used = blind.aim_recordings()
    assert 'FP01_Qföre_22-Oct-2019_08-16-35' in used                         # aims 1 and 2, control before
    assert 'FP01_Qefter_försök2_22-Oct-2019_09-50-15' in used                # aim 2, control after: the last attempt
    assert 'FP01_Qefter_22-Oct-2019_09-46-17' not in used                    # the attempt before it
