"""The codes recordings show under during blind placement (`gui.blind`, `capillary.aims --progress`).

A code is the recording's name hashed (`code`): the same on every computer
and every day, and the same name always gets it, so a progress report can
name recordings the way the app lists them without showing which is which.
"""

from __future__ import annotations

import hashlib
from typing import Iterable

from . import inventory

#: 32 characters without the ones that look alike (0/O, 1/I).
ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
LENGTH = 5


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
