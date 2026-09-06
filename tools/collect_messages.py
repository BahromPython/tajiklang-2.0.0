"""Ҳамаи матнҳои тоҷикиро ҷамъ мекунад — builds the translation review sheet.

    py tools/collect_messages.py

Walks every module with Python's own `ast`, pulls out every string literal
containing Cyrillic, and writes `docs/ТАРҶУМА.md` — a checklist a Tajik
teacher can go through without reading any code.

Regenerate it after changing any message, so the review sheet cannot drift
away from what the language actually says.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "tajiklang"
OUTPUT = ROOT / "docs" / "ТАРҶУМА.md"

CYRILLIC = re.compile(r"[Ѐ-ӿ]")

# Strings that are code, not prose: type names, keywords, the alphabet.
# They are listed separately in the header rather than as messages to reword.
SKIP_EXACT = {
    "рост", "дурӯғ", "холӣ", "рақам", "матн", "мантиқӣ", "рӯйхат", "луғат",
    "функсия", "модул", "номаълум", "ва", "ё", "не", "агар", "вагарна",
    "бигзор", "барои", "аз", "то", "то_вақте", "баргардон", "ворид",
    "шикан", "давом", "синф", "кӯшиш", "хато", "риёзӣ", "newline",
}

HEADER = """# ТАРҶУМА — саҳифаи санҷиши матнҳои тоҷикӣ

Ин рӯйхат **ҳамаи** матнҳои тоҷикиест, ки забон ба донишҷӯ нишон медиҳад:
хатогиҳо, маслиҳатҳо ва навиштаҷоти фармон.

## Ба муаллим

Ин файл барои шумост. Барномасозиро донистан лозим нест.

Ҳар сатрро хонед ва аз худ пурсед:

1. Оё ин ҷумла ба забони тоҷикии дуруст навишта шудааст?
2. Оё хонандаи синфи 8–11 онро аз як бор хондан мефаҳмад?
3. Оё калимаи беҳтаре ҳаст?

Дар сутуни охирин варианти беҳтарро нависед. Агар ҳама чиз хуб бошад, онро
холӣ гузоред.

Матнҳо аз рӯи файл гурӯҳбандӣ шудаанд, вале ин барои шумо муҳим нест —
онҳоро танҳо аз боло ба поён хонед.

## Калимаҳои калидии забон

Инҳо худи калимаҳои забонанд. Иваз кардани онҳо барномаҳои кӯҳнаро вайрон
мекунад, аз ин рӯ агар яке нодуруст бошад, ҳозир бигӯед.

| Калима | Маъно | Дуруст аст? |
|---|---|---|
| `бигзор` | сохтани тағйирёбандаи нав | |
| `навис` | чоп кардан | |
| `хонед` | маълумот гирифтан аз корбар | |
| `агар` | шарт | |
| `вагарна` | дар акси ҳол | |
| `вагарна агар` | шарти дигар | |
| `барои` | давр (шумурдан ва гузаштан) | |
| `аз` … `то` | ҳудуди давр | |
| `то_вақте` | давр бо шарт | |
| `функсия` | функсия | |
| `баргардон` | натиҷаро бармегардонад | |
| `ворид` | модулро меорад | |
| `рост` / `дурӯғ` | ҳа / не | |
| `холӣ` | ҳеҷ чиз | |
| `ва` / `ё` / `не` | мантиқ | |
| `шикан` / `давом` | (ҳанӯз нест, барои оянда) | |

## Номи навъҳо

Инҳо дар ҳамаи хатогиҳо пайдо мешаванд («… вале **матн** гирифт»).

| Ном | Маъно | Дуруст аст? |
|---|---|---|
| `рақам` | number | |
| `матн` | text | |
| `мантиқӣ` | true/false | |
| `холӣ` | nothing | |
| `рӯйхат` | list | |
| `луғат` | dictionary | |
| `функсия` | function | |
| `модул` | module | |

## Номи функсияҳои тайёр

| Ном | Кор | Дуруст аст? |
|---|---|---|
| `дарозӣ` | шумораи унсурҳо ё ҳарфҳо | |
| `илова` | ба рӯйхат илова мекунад | |
| `хориҷ` | аз рӯйхат мебарорад | |
| `тартиб` | тартиб медиҳад | |
| `баръакс` | чаппа мекунад | |
| `ҷамъи` | ҷамъи рақамҳо | |
| `калонтарин` / `хурдтарин` | | |
| `калидҳо` / `қиматҳо` | аз луғат | |
| `дорад` | оё ҳаст? | |
| `ба_рақам` / `ба_матн` | табдил | |
| `навъ` | навъи қимат | |
| `матн.калон` / `матн.хурд` | ҳарфи калон / хурд | |
| `матн.тоза` | холигиҳоро мебарорад | |
| `матн.ҷудо` / `матн.пайваст` | | |
| `матн.иваз` / `матн.буриш` | | |
| `матн.ёфтан` | ҷустуҷӯ | |
| `матн.сар_мешавад` / `матн.тамом_мешавад` | | |
| `матн.такрор` / `матн.ҳарфҳо` / `матн.рақам_аст` | | |
| `риёзӣ.реша` | решаи квадратӣ | |
| `риёзӣ.дараҷа` / `риёзӣ.мутлақ` | | |
| `риёзӣ.гирд` / `риёзӣ.фарш` / `риёзӣ.сақф` / `риёзӣ.бутун` | | |
| `риёзӣ.мин` / `риёзӣ.макс` / `риёзӣ.тасодуфӣ` | | |

---

# Матнҳое, ки донишҷӯ мебинад

"""


def collect(path: Path) -> list[str]:
    """Every Cyrillic-bearing string literal in one file, in source order."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        text = node.value.strip()
        if not text or not CYRILLIC.search(text):
            continue
        if text in SKIP_EXACT:
            continue
        if "\n" in text:            # docstrings, not messages
            continue
        if text not in found:
            found.append(text)

    return found


def _utf8_stdout() -> None:
    """Windows consoles default to a codepage that cannot print Tajik.

    Without this the tool does its job and then crashes on its own success
    message — the same trap the `tajik` command has to avoid.
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    _utf8_stdout()
    sections: list[str] = []
    total = 0

    for path in sorted(PACKAGE.glob("*.py")):
        messages = collect(path)
        if not messages:
            continue
        total += len(messages)

        lines = [f"## {path.name}", "", "| № | Матн | Варианти беҳтар |", "|---|---|---|"]
        for index, text in enumerate(messages, start=1):
            safe = text.replace("|", "\\|")
            lines.append(f"| {index} | {safe} | |")
        sections.append("\n".join(lines))

    body = HEADER + "\n\n".join(sections) + "\n"
    body += f"\n---\n\nҲамагӣ {total} матн.\n"

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(body, encoding="utf-8")
    print(f"{OUTPUT.relative_to(ROOT)} — {total} messages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
