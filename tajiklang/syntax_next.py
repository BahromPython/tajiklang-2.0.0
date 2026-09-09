"""TajikLang Next surface syntax.

The interpreter's AST is intentionally independent of spelling.  This module
turns the newer, brace-based TajikLang notation into the stable core grammar
while the parser migration is underway.  Students write the new syntax; the
runtime still receives the same well-tested AST.
"""

from __future__ import annotations

import re


_DECLARE = re.compile(r"^дода\s+([\w]+)\s*<-\s*(.+)$", re.UNICODE)
_UPDATE = re.compile(r"^тағйир\s+([\w]+)\s*<-\s*(.+)$", re.UNICODE)
_SHOW = re.compile(r"^нишон\s+(.+)$", re.UNICODE)
_IF = re.compile(r"^агар\s+(.+?)\s*\{$", re.UNICODE)
_ELSE_IF = re.compile(r"^дигар\s+агар\s+(.+?)\s*\{$", re.UNICODE)


def is_next_syntax(source: str) -> bool:
    """Avoid changing existing programs unless they use a Next-only form."""
    return "<-" in source or bool(re.search(
        r"(?m)^\s*(?:дода|тағйир|нишон)\b|^\s*(?:агар|дигар)\b.*\{\s*$",
        source,
    ))


def normalize(source: str) -> str:
    """Convert concise TajikLang Next statements to the core source grammar.

    Blocks use braces because a missing indentation level should never change a
    student's program.  Opening braces must end a line; closing braces may be
    followed by ``дигар {`` or ``дигар агар ... {``.
    """
    if not is_next_syntax(source):
        return source

    depth = 0
    result: list[str] = []
    for number, raw in enumerate(source.splitlines(), start=1):
        text = raw.strip()
        if not text or text.startswith("#"):
            result.append(text)
            continue

        if text.startswith("}"):
            depth -= 1
            if depth < 0:
                raise ValueError(f"сатри {number}: қавси '}}' зиёдатӣ аст")
            text = text[1:].strip()
            if not text:
                continue
            if text == "дигар {":
                result.append("    " * depth + "вагарна:")
                depth += 1
                continue
            else_if = _ELSE_IF.match(text)
            if else_if:
                result.append("    " * depth + f"вагарна агар {else_if.group(1)}:")
                depth += 1
                continue
            raise ValueError(f"сатри {number}: пас аз '}}' танҳо 'дигар' иҷозат дорад")

        if text == "дигар {":
            result.append("    " * depth + "вагарна:")
            depth += 1
            continue

        if_match = _IF.match(text)
        if if_match:
            result.append("    " * depth + f"агар {if_match.group(1)}:")
            depth += 1
            continue

        declaration = _DECLARE.match(text)
        update = _UPDATE.match(text)
        shown = _SHOW.match(text)
        if declaration:
            text = f"бигзор {declaration.group(1)} = {declaration.group(2)}"
        elif update:
            text = f"{update.group(1)} = {update.group(2)}"
        elif shown:
            text = f"навис({shown.group(1)})"
        elif "<-" in text:
            raise ValueError(
                f"сатри {number}: барои қимати нав 'дода ном <- қимат' "
                "ва барои тағйир 'тағйир ном <- қимат' нависед"
            )

        result.append("    " * depth + text)

    if depth:
        raise ValueError("блок бо '}' баста нашудааст")
    return "\n".join(result) + ("\n" if source.endswith("\n") else "")
