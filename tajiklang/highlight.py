"""Рангкунӣ — deciding what colour each piece of source is.

One definition, used by the editor and by the website. Two highlighters that
disagree about what counts as a keyword is a small bug that shows up in the
two places a newcomer looks first, so there is only one.

`spans(source)` returns non-overlapping `(kind, start, end)` triples in source
order. Everything not covered is plain text.
"""

from __future__ import annotations

import re

from .tokens import KEYWORD_TOKENS

# Longest first, so `то_вақте` is never matched as `то` plus rubbish.
_KEYWORDS = sorted(KEYWORD_TOKENS, key=len, reverse=True)

# A word boundary that understands Cyrillic. `\b` and `\w` are ASCII-minded in
# some engines, and `тоза` must never light up the `то` inside it.
_LETTER = r"[^\W\d_]"
_WORD = rf"(?<!{_LETTER})({{}})(?!{_LETTER})"

_COMMENT = re.compile(r"#[^\n]*")
_STRING = re.compile(r'"(?:[^"\\\n]|\\.)*"')
_KEYWORD = re.compile(_WORD.format("|".join(_KEYWORDS)))
_CALL = re.compile(rf"(?<!{_LETTER})([^\W\d_][\w_]*)(?=\s*\()")
_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")

KINDS = ("comment", "string", "keyword", "builtin", "number")


def spans(source: str, builtins: set[str] | None = None) -> list[tuple[str, int, int]]:
    """Where each coloured region starts and ends.

    Comments and strings are matched first and claim their whole span, so a
    `#` inside a string, or a keyword inside a comment, is left alone.
    """
    found: list[tuple[str, int, int]] = []
    taken: list[tuple[int, int]] = []

    def free(start: int) -> bool:
        return not any(a <= start < b for a, b in taken)

    for pattern, kind in ((_COMMENT, "comment"), (_STRING, "string")):
        for match in pattern.finditer(source):
            if free(match.start()):
                found.append((kind, match.start(), match.end()))
                taken.append(match.span())

    for match in _KEYWORD.finditer(source):
        if free(match.start()):
            found.append(("keyword", match.start(), match.end()))

    if builtins:
        for match in _CALL.finditer(source):
            if free(match.start()) and match.group(1) in builtins:
                found.append(("builtin", match.start(), match.end()))

    for match in _NUMBER.finditer(source):
        if free(match.start()):
            found.append(("number", match.start(), match.end()))

    found.sort(key=lambda item: item[1])
    return found


def to_html(source: str, builtins: set[str] | None = None) -> str:
    """Source as HTML, with each coloured region in a `<span class="tj-…">`."""
    def escape(text: str) -> str:
        return (
            text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

    pieces: list[str] = []
    cursor = 0
    for kind, start, end in spans(source, builtins):
        if start < cursor:            # keyword sitting inside a longer span
            continue
        pieces.append(escape(source[cursor:start]))
        pieces.append(f'<span class="tj-{kind}">{escape(source[start:end])}</span>')
        cursor = end
    pieces.append(escape(source[cursor:]))
    return "".join(pieces)
