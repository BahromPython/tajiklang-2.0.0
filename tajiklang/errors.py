"""Хатоҳо — the error system.

Every error in TajikLang knows four things: what kind of error it is, where it
happened, what the source line looked like, and what the student should do
about it. A message without a fix is only half an error message.
"""

from __future__ import annotations


# Kinds of runtime failure a program can catch by name:
#
#     кӯшиш:
#         ...
#     хато "тақсим_ба_сифр":
#         ...
#
# Only the failures worth handling separately are named. Everything else is
# ХАТОИ_УМУМӢ, which a bare `хато:` catches along with all the rest.
KIND_DIVISION = "тақсим_ба_сифр"
KIND_NAME = "номи_номаълум"
KIND_TYPE = "навъи_нодуруст"
KIND_RANGE = "берун_аз_ҳудуд"
KIND_KEY = "калиди_нест"
KIND_ARGUMENTS = "шумораи_аргумент"
KIND_PYTHON = "хатои_питон"
KIND_FILE = "хатои_файл"
KIND_GENERAL = "умумӣ"

ERROR_KINDS = (
    KIND_DIVISION, KIND_NAME, KIND_TYPE, KIND_RANGE, KIND_KEY,
    KIND_ARGUMENTS, KIND_PYTHON, KIND_FILE, KIND_GENERAL,
)


class TajikLangError(Exception):
    """Base class for every error the language reports to the user."""

    # Overridden by subclasses; shown as the heading of the message.
    kind: str = "Хато"

    def __init__(
        self,
        message: str,
        line: int,
        column: int,
        source_line: str = "",
        hint: str = "",
        call_stack: list[tuple[str, int]] | None = None,
        kind_code: str = KIND_GENERAL,
    ) -> None:
        super().__init__(message)
        self.kind_code = kind_code
        self.message = message
        self.line = line
        self.column = column
        self.source_line = source_line
        self.hint = hint

        # Which function called which, innermost last: [(name, call line)].
        # Without this, an error two calls deep names a line and leaves the
        # student with no idea how the program reached it.
        self.call_stack = call_stack or []

    def format(self) -> str:
        """Render the error the way the student sees it in the terminal."""
        parts = [f"{self.kind} (сатри {self.line}, сутуни {self.column}):", ""]

        if self.source_line:
            stripped = self.source_line.rstrip("\n")
            parts.append("    " + stripped)
            # column is 1-based, so column 1 puts the caret under the first char
            parts.append("    " + " " * max(self.column - 1, 0) + "^")
            parts.append("")

        parts.append(self.message)
        if self.hint:
            parts.append(f"Маслиҳат: {self.hint}")

        # Where the failing line was reached from. Without this, an error two
        # calls deep names a line and leaves the student with no idea how the
        # program got there.
        if self.call_stack:
            parts.append("")
            parts.append("Роҳи даъват:")
            for name, line in reversed(self.call_stack):
                parts.append(f'    дар функсияи "{name}", даъват дар сатри {line}')

        return "\n".join(parts)


# The English term in brackets is deliberate. A student who meets
# `Хатои синтаксис (SyntaxError)` here recognises `SyntaxError` the first time
# they open Python — the Tajik teaches the concept, the bracket carries the
# vocabulary across. It costs one word per class.
class LexerError(TajikLangError):
    """A character or sequence the lexer cannot turn into a token."""

    kind = "Хатои луғавӣ (LexicalError)"


class ParseError(TajikLangError):
    """Tokens that are individually valid but form no legal construct."""

    kind = "Хатои синтаксис (SyntaxError)"


class RuntimeErrorTJ(TajikLangError):
    """A program that parsed fine but failed while running."""

    kind = "Хатои иҷро (RuntimeError)"


class BuiltinError(Exception):
    """Raised inside a built-in function, which has no idea where it was called.

    The interpreter catches it at the call site and turns it into a proper
    `RuntimeErrorTJ` with the line, column and source line filled in. This is
    the only way a builtin can report a problem without knowing about the AST.
    """

    def __init__(
        self, message: str, hint: str = "", kind_code: str = KIND_GENERAL
    ) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.kind_code = kind_code


def internal_report(error: BaseException, where: str = "") -> str:
    """A fault in the language itself — reported in Tajik, never as a traceback.

    A student who meets a crash in the interpreter has done nothing wrong, and
    a wall of English filenames tells them nothing they can act on. So the
    message says, in their language, that this is our bug and how to report
    it — and the technical detail goes to a log file for whoever fixes it.

    This is the only place the implementation can surface, and it does not.
    """
    import traceback

    detail = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )

    log = ""
    try:
        from . import packages

        path = packages.home() / "хатоҳо.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"--- {where or 'иҷро'} ---{chr(10)}{detail}{chr(10)}")
        log = str(path)
    except Exception:       # noqa: BLE001 - logging must never be the failure
        log = ""

    lines = [
        "Хатои дохилии забон.",
        "",
        "Ин хатои барномаи шумо нест — ин камбудии худи TajikLang аст.",
    ]
    if log:
        lines.append(f"Тафсилот дар: {log}")
    lines.append(
        "Лутфан хабар диҳед: "
        "https://github.com/BahromPython/tajiklang/issues"
    )
    return chr(10).join(lines)
