"""Фармон — the `tajik` command, and the interactive shell behind it.

    tajik барнома.tj          run a file
    tajik                     start the interactive shell
    tajik --tokens барнома.tj show what the lexer produced
    tajik --ast барнома.tj    show what the parser produced
    tajik --version
"""

from __future__ import annotations

import sys
from pathlib import Path

from . import __version__
from .checker import check_program
from .errors import TajikLangError, internal_report
from .interpreter import Interpreter
from .lexer import Lexer
from .parser import Parser

USAGE = """TajikLang {version}

Истифода:
    tajik <файл.tj>            барномаро иҷро мекунад
    tajik                      реҷаи интерактивӣ
    tajik --санҷиш <файл.tj>   барномаро месанҷад, вале иҷро намекунад
    tajik --бе-санҷиш <файл.tj> бе санҷиш иҷро мекунад
    tajik --tokens <файл.tj>   токенҳоро нишон медиҳад
    tajik --ast <файл.tj>      дарахти синтаксисиро нишон медиҳад
    tajik --version            версияро нишон медиҳад

Бастаҳо:
    tajik муҳаррир             муҳаррирро мекушояд
    tajik ҷустуҷӯ              бастаҳои мавҷударо нишон медиҳад
    tajik гирифтан <ном>       бастаро насб мекунад
    tajik бастаҳо              бастаҳои насбшударо нишон медиҳад
    tajik нест <ном>           бастаро нест мекунад
"""

BANNER = """TajikLang {version} — реҷаи интерактивӣ
Барои баромадан: `хуруҷ` ё Ctrl+D
"""

EXIT_WORDS = {"хуруҷ", "баромадан", "exit", "quit"}

# Exit codes follow the BSD sysexits convention, so shell scripts and CI can
# tell a bad program from a missing file from bad usage.
EX_USAGE = 64
EX_DATAERR = 65
EX_NOINPUT = 66
EX_SOFTWARE = 70


def _force_utf8_streams() -> None:
    """Windows defaults to a codepage that cannot carry Tajik text.

    Output: without this, `навис("Салом")` raises UnicodeEncodeError on a
    default Windows console instead of printing anything.

    Input: piped stdin is decoded with the locale codepage, so
    `echo навис("Салом") | tajik` arrives as mojibake and the lexer rejects
    characters the user never typed. Both ends have to be UTF-8.
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def terminal_input(prompt: str) -> str | None:
    """How `хонед` reads a line in the terminal. None at end of input."""
    try:
        return input(prompt)
    except EOFError:
        return None


def run_file(path: Path, mode: str = "run") -> int:
    source = path.read_text(encoding="utf-8")
    try:
        lexer = Lexer(source, str(path))
        tokens = lexer.tokenize()
        if mode == "tokens":
            for token in tokens:
                print(token)
            return 0

        program = Parser(tokens, lexer.lines).parse()
        if mode == "ast":
            print(program)
            return 0

        interpreter = Interpreter(
            lexer.lines, base_dir=path.parent, read_line=terminal_input
        )

        # Check before running, unless asked not to. Every problem is reported
        # at once and nothing executes — the opposite of finding a typo after
        # forty lines of output.
        if mode != "no-check":
            found = check_program(program, set(interpreter.builtins.values))
            errors = [d for d in found if not d.is_warning]
            warnings = [d for d in found if d.is_warning]

            for warning in warnings:
                print(warning.format(lexer.lines), file=sys.stderr)
                print(file=sys.stderr)

            if errors:
                for problem in errors:
                    print(problem.format(lexer.lines), file=sys.stderr)
                    print(file=sys.stderr)
                print(
                    f"Ҳамагӣ {len(errors)} хато. Барнома иҷро нашуд.",
                    file=sys.stderr,
                )
                return EX_DATAERR

            if mode == "check":
                print("Тоза — хато ёфт нашуд.")
                return 0

        interpreter.run(program)
        return 0
    except TajikLangError as error:
        print(error.format(), file=sys.stderr)
        return EX_DATAERR
    except RecursionError:
        print("Рекурсия аз ҳад чуқур шуд.", file=sys.stderr)
        return EX_DATAERR
    except Exception as error:              # noqa: BLE001 - our bug, not theirs
        print(internal_report(error, str(path)), file=sys.stderr)
        return EX_SOFTWARE


def opens_block(line: str) -> bool:
    """Does this line start a block the shell must keep reading?

    A block is only finished when a line at column 0 follows it, and in a
    shell that line has not been typed yet. So the rule is: a line ending in
    ":" starts collecting, and a blank line stops.
    """
    stripped = line.strip()
    return stripped.endswith(":") and not stripped.startswith("#")


def repl() -> int:
    """The interactive shell.

    One `Interpreter` for the whole session, so names survive between lines —
    which is the entire point of a shell for learning a language.
    """
    print(BANNER.format(version=__version__))
    interpreter = Interpreter(
        [], print, base_dir=Path.cwd(), read_line=terminal_input
    )

    buffer: list[str] = []
    while True:
        prompt = "... " if buffer else ">>> "
        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not buffer and line.strip() in EXIT_WORDS:
            return 0

        buffer.append(line)

        if len(buffer) == 1:
            if opens_block(line):
                continue            # a block starts here — keep reading
        elif line.strip():
            continue                # still inside the block

        source = "\n".join(buffer)
        buffer = []
        if not source.strip():
            continue

        try:
            lexer = Lexer(source, "<реҷаи интерактивӣ>")
            program = Parser(lexer.tokenize(), lexer.lines).parse()
            interpreter.source_lines = lexer.lines
            interpreter.run(program, echo=True)
        except TajikLangError as error:
            print(error.format(), file=sys.stderr)
        except RecursionError:
            print("Рекурсия аз ҳад чуқур шуд.", file=sys.stderr)
        except Exception as error:          # noqa: BLE001 - our bug, not theirs
            print(internal_report(error, "реҷаи интерактивӣ"), file=sys.stderr)

    return 0


def packages_command(args: list[str]) -> int:
    """The `tajik` subcommands that manage packages, all in Tajik."""
    from . import packages

    command, rest = args[0], args[1:]

    try:
        if command == "ҷустуҷӯ":
            found = packages.catalogue()
            if not found:
                print("Феҳрист холӣ аст.")
                return 0
            have = packages.installed()
            print("Бастаҳои мавҷуда:")
            for name, entry in sorted(found.items()):
                mark = "✓" if name in have else " "
                print(f"  {mark} {name:<12} {entry.get('нусха', '?'):<8} "
                      f"{entry.get('тавсиф', '')}")
            print()
            print("Барои насб: tajik гирифтан <ном>")
            return 0

        if command == "бастаҳо":
            have = packages.installed()
            if not have:
                print("Ҳеҷ баста насб нашудааст.")
                print("Барои дидани бастаҳои мавҷуда: tajik ҷустуҷӯ")
                return 0
            print(f"Насбшуда ({packages.library()}):")
            for name, meta in sorted(have.items()):
                print(f"  {name:<12} {meta.get('нусха', '?'):<8} "
                      f"{meta.get('тавсиф', '')}")
            return 0

        if command == "гирифтан":
            if not rest:
                print("Номи баста лозим аст: tajik гирифтан <ном>", file=sys.stderr)
                return EX_USAGE
            for name in rest:
                meta = packages.install(name)
                print(f"✓ {name} {meta['нусха']} насб шуд "
                      f"({meta['файлҳо']} файл)")
                print(f"  Истифода: ворид {name}")
            return 0

        if command == "нест":
            if not rest:
                print("Номи баста лозим аст: tajik нест <ном>", file=sys.stderr)
                return EX_USAGE
            for name in rest:
                packages.remove(name)
                print(f"✓ {name} нест шуд")
            return 0

    except packages.PackageError as error:
        print(error.message, file=sys.stderr)
        if error.hint:
            print(f"Маслиҳат: {error.hint}", file=sys.stderr)
        return EX_DATAERR

    return EX_USAGE


def main(argv: list[str] | None = None) -> int:
    _force_utf8_streams()
    args = list(sys.argv[1:] if argv is None else argv)

    if args and args[0] in ("муҳаррир", "ide"):
        from .ide import main as ide_main

        return ide_main(args[1:])

    if args and args[0] in ("ҷустуҷӯ", "гирифтан", "бастаҳо", "нест"):
        return packages_command(args)

    if args and args[0] in ("--version", "-v"):
        print(f"TajikLang {__version__}")
        return 0

    if args and args[0] in ("--help", "-h"):
        print(USAGE.format(version=__version__))
        return 0

    FLAGS = {
        "--tokens": "tokens",
        "--ast": "ast",
        "--санҷиш": "check",
        "--check": "check",
        "--бе-санҷиш": "no-check",
        "--no-check": "no-check",
    }
    mode = "run"
    if args and args[0] in FLAGS:
        mode = FLAGS[args.pop(0)]

    if not args:
        if mode != "run":
            print(USAGE.format(version=__version__))
            return EX_USAGE
        return repl()

    if len(args) != 1:
        print(USAGE.format(version=__version__))
        return EX_USAGE

    path = Path(args[0])
    if not path.exists():
        print(f'Файли "{path}" ёфт нашуд.', file=sys.stderr)
        return EX_NOINPUT

    return run_file(path, mode)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
