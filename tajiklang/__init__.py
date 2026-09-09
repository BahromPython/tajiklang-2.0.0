"""TajikLang — забони барномасозӣ бо забони тоҷикӣ."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .checker import Diagnostic, check_program
from .errors import LexerError, ParseError, RuntimeErrorTJ, TajikLangError
from .interpreter import Interpreter
from .lexer import Lexer
from .parser import Parser

__version__ = "3.0.4"

__all__ = [
    "Lexer",
    "Parser",
    "Interpreter",
    "TajikLangError",
    "CheckFailed",
    "LexerError",
    "ParseError",
    "RuntimeErrorTJ",
    "check_source",
    "Diagnostic",
    "run_source",
    "run_file",
    "__version__",
]


def check_source(source: str, filename: str = "<матн>") -> list[Diagnostic]:
    """Lex, parse and check — without running anything.

    This is what makes TajikLang different from Python at the point a student
    presses Run: problems are reported before any output appears, and all of
    them at once rather than one per attempt.
    """
    lexer = Lexer(source, filename)
    program = Parser(lexer.tokenize(), lexer.lines).parse()
    builtins = set(Interpreter([], lambda _: None).builtins.values)
    return check_program(program, builtins)


def run_source(
    source: str,
    filename: str = "<матн>",
    output: Callable[[str], None] = print,
    base_dir: Path | None = None,
    read_line: Callable[[str], str | None] | None = None,
    check: bool = False,
) -> None:
    """Run TajikLang source text through the whole pipeline.

    source → Lexer → tokens → Parser → AST → [Checker] → Interpreter → output

    `check` is off here so that tests and embedders keep the plain path; the
    `tajik` command and the playground turn it on.
    """
    lexer = Lexer(source, filename)
    tokens = lexer.tokenize()
    parser = Parser(tokens, lexer.lines)
    program = parser.parse()

    interpreter = Interpreter(
        lexer.lines, output, base_dir=base_dir, read_line=read_line
    )

    if check:
        problems = [
            d
            for d in check_program(program, set(interpreter.builtins.values))
            if not d.is_warning
        ]
        if problems:
            raise CheckFailed(problems, lexer.lines)

    interpreter.run(program)


class CheckFailed(Exception):
    """Raised by `run_source(check=True)` when the program cannot be safe to run.

    It carries every problem, not just the first — reporting one error per
    attempt is a Python habit worth breaking.
    """

    def __init__(self, problems: list[Diagnostic], source_lines: list[str]) -> None:
        super().__init__(f"{len(problems)} хато")
        self.problems = problems
        self.source_lines = source_lines

    def format(self) -> str:
        blocks = [problem.format(self.source_lines) for problem in self.problems]
        count = len(self.problems)
        blocks.append(f"Ҳамагӣ {count} хато. Барнома иҷро нашуд.")
        return (chr(10) * 2).join(blocks)


def run_file(
    path: str | Path,
    output: Callable[[str], None] = print,
    read_line: Callable[[str], str | None] | None = None,
    check: bool = False,
) -> None:
    """Run a .tj file. Imports resolve relative to the file's own folder."""
    path = Path(path)
    run_source(
        path.read_text(encoding="utf-8"),
        str(path),
        output,
        base_dir=path.parent,
        read_line=read_line,
        check=check,
    )
