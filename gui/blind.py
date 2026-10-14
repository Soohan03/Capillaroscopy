"""Blind placement: lines placed on coded recordings, without seeing what they measure.

The observer chooses the capillaries and places the lines; the app measures.
So that nothing but the anatomy decides where a line goes, blind placement
(switched on in the header, kept in settings.csv as ``blind_placement``)
hides what could steer it:

- the recording list shows only the recordings the aims use
  (`capillary.inventory`), each under a code instead of its name, in the
  order of the codes, so neither the participant, the visit, the exposure
  nor the time of day shows;
- the Centre line page hides the space-time preview and every result, and
  measures the official rest only;
- the pages that show results (Two boxes, Results, Validation) are closed.

A code is the recording's name hashed (`code`): the same on every computer
and every day, and the same name always gets it. The data sets are saved
under the real names, as always.
"""

from __future__ import annotations

import functools
import hashlib
import logging
from typing import Iterable

from capillary import inventory

log = logging.getLogger(__name__)

#: 32 characters without the ones that look alike (0/O, 1/I).
ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
LENGTH = 5
#: The pages closed during blind placement: they show what lines measure.
LOCKED_PAGES = ('analyze', 'results', 'validation')
#: The settings.csv row that keeps it on between sessions.
SETTING = 'blind_placement'


def code(stem: str) -> str:
    """The recording's code: its name (Unicode-normalized, as file systems differ) hashed into `LENGTH` characters."""
    number = int.from_bytes(hashlib.sha256(inventory.nfc(stem).encode('utf-8')).digest()[:8], 'big')
    characters = []
    for _ in range(LENGTH):
        number, digit = divmod(number, len(ALPHABET))
        characters.append(ALPHABET[digit])
    return ''.join(characters)


def codes(stems: Iterable[str]) -> dict:
    """``{stem: code}`` for every stem; a code two names share gets -2, -3 ... on the later names (by name)."""
    out, seen = {}, {}
    for stem in sorted(set(stems), key=inventory.nfc):
        base = code(stem)
        seen[base] = seen.get(base, 0) + 1
        out[stem] = base if seen[base] == 1 else f'{base}-{seen[base]}'
    return out


@functools.lru_cache(maxsize=1)
def aim_recordings() -> frozenset:
    """The names (NFC) of the recordings the aims use; empty if the official times cannot be read."""
    try:
        table = inventory.recordings()
        table = inventory.mark_use(table, inventory.participants(table))
    except (OSError, ValueError, KeyError):
        log.warning('Could not read which recordings the aims use', exc_info=True)
        return frozenset()
    return frozenset(inventory.nfc(name) for name in table.loc[table['used_for'] != '', 'name'])


def listed(recordings: list, used: frozenset = None) -> list:
    """The recordings blind placement lists: those the aims use (`used`, by default `aim_recordings`), by code.

    Every recording is listed when none is known to be used, so that the app stays usable without the
    official times.
    """
    used = aim_recordings() if used is None else used
    chosen = [recording for recording in recordings if inventory.nfc(recording.stem) in used] if used else \
        list(recordings)
    names = codes(recording.stem for recording in chosen)
    return sorted(chosen, key=lambda recording: names[recording.stem])
