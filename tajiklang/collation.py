"""Тартиби алифбо — ordering text the way Tajik actually orders it.

Comparing strings by Unicode code point is wrong for Tajik, and wrong in a way
that is invisible until a student sorts a class list.

The Tajik alphabet places its own letters next to their base letters:

    ... в  г  ғ  д ...        ғ comes straight after г
    ... и  ӣ  й  к  қ ...     ӣ after и, қ after к

But Unicode does not. `г` is U+0433, in the main Cyrillic block, while `ғ` is
U+0493, off in Cyrillic Supplement. By code point:

    "ғ" > "я"        # U+0493 > U+044F

so a naive sort puts every Tajik-specific letter after the entire rest of the
alphabet. `Ғафуров` would sort after `Яқубов`.

This module builds a sort key from the real alphabet instead.
"""

from __future__ import annotations

# The Tajik alphabet in its official order — 35 letters.
ALPHABET = "абвгғдеёжзиӣйкқлмнопрстуӯфхҳчҷшъэюя"

# letter -> its position in the alphabet
_POSITION = {letter: index for index, letter in enumerate(ALPHABET)}


def char_key(char: str) -> tuple[int, int, int]:
    """Sort key for a single character.

    Returns a tuple compared left to right:

    1. group — 0 for everything that is not a Tajik letter (spaces, digits,
       punctuation, Latin), 1 for Tajik letters. Non-letters sort first.
    2. position — the alphabet index for Tajik letters, the code point for
       everything else.
    3. case — 0 for upper case, 1 for lower case, so that `Анор` sorts before
       `анор` but the two stay adjacent instead of being split apart the way
       raw code points split them.
    """
    lower = char.lower()
    if lower in _POSITION:
        return (1, _POSITION[lower], 0 if char != lower else 1)
    return (0, ord(char), 0)


def sort_key(text: str) -> list[tuple[int, int, int]]:
    """Sort key for a whole string."""
    return [char_key(char) for char in text]


def compare(left: str, right: str) -> int:
    """-1 if left sorts first, 0 if equal, 1 if right sorts first."""
    a, b = sort_key(left), sort_key(right)
    if a < b:
        return -1
    if a > b:
        return 1
    return 0
