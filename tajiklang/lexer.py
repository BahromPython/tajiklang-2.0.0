"""Лексер — characters in, tokens out.

    бигзор калон = синну_сол >= 18

becomes

    LET  IDENT('калон')  ASSIGN  IDENT('синну_сол')  GTE  NUMBER(18)  NEWLINE  EOF

The lexer knows nothing about what a program *means*. It only recognises
shapes: this run of letters is a name, this run of digits is a number, this
quoted run is a string.
"""

from __future__ import annotations

import unicodedata
from decimal import Decimal

from .errors import LexerError
from .tokens import (
    KEYWORD_TOKENS,
    KEYWORD_VERSIONS,
    KEYWORDS,
    SINGLE_CHARS,
    TWO_CHAR_OPERATORS,
    WRONG_OPERATORS,
    Token,
    TokenType,
)

# Written as chr(92) so that this source file contains no backslash puzzles of
# its own while describing the escape sequences of another language.
_B = chr(92)

# Escape sequences allowed inside "..."
ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",       # real files arrive with CRLF; a program should be able
    '"': '"',        # to say so
    _B: _B,
}

ESCAPE_HINT = (
    "Танҳо " + _B + "n, " + _B + "t, " + _B + "r, " + _B + '" ва ' + _B + _B
    + " иҷозат дода мешаванд."
)

# One block level is exactly this many spaces. See LANGUAGE_SPEC.md §2.7 for
# why the width is fixed rather than merely consistent.
INDENT_WIDTH = 4


class Lexer:
    def __init__(self, source: str, filename: str = "<матн>") -> None:
        # Normalise to NFC before anything else.
        #
        # Tajik letters such as ӣ and ӯ can be typed two different ways: as one
        # code point (U+04E3), or as и + a combining macron (U+0438 U+0304).
        # They look identical on screen. Without this line, `ҳарорат` typed on
        # one keyboard would be a *different variable* from `ҳарорат` typed on
        # another, and nobody would ever work out why.
        self.source = unicodedata.normalize("NFC", source)
        self.filename = filename
        self.lines = self.source.splitlines()

        self.pos = 0        # index into self.source
        self.line = 1       # 1-based
        self.column = 1     # 1-based

        # The indentation stack: the width of every block currently open.
        # [0] means "at the outermost level". Pushing is an INDENT, popping is
        # a DEDENT. This is the whole of block structure, in one list.
        self.indents = [0]

        # How many brackets are open. While any are, newlines and indentation
        # carry no meaning — see the newline rule in tokenize().
        self.bracket_depth = 0

    # ------------------------------------------------------------------
    # low-level cursor helpers
    # ------------------------------------------------------------------
    def _at_end(self) -> bool:
        return self.pos >= len(self.source)

    def _peek(self, offset: int = 0) -> str:
        index = self.pos + offset
        if index >= len(self.source):
            return ""
        return self.source[index]

    def _advance(self) -> str:
        char = self.source[self.pos]
        self.pos += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _source_line(self, line: int) -> str:
        if 1 <= line <= len(self.lines):
            return self.lines[line - 1]
        return ""

    def _error(self, message: str, line: int, column: int, hint: str = "") -> LexerError:
        return LexerError(message, line, column, self._source_line(line), hint)

    def _wrong_operator(self, text: str, line: int, column: int) -> LexerError:
        for _ in text:
            self._advance()
        return self._error(
            f'Оператори "{text}" дар TajikLang вуҷуд надорад.',
            line,
            column,
            hint=WRONG_OPERATORS[text],
        )

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []

        # Indentation is only meaningful at the start of a line, so it is
        # handled there and nowhere else.
        self._start_of_line(tokens)

        while not self._at_end():
            char = self._peek()
            line, column = self.line, self.column

            # Inside a line, spaces and tabs only separate tokens.
            if char in " \t\r":
                self._advance()
                continue

            # comments run to the end of the line
            if char == "#":
                while not self._at_end() and self._peek() != "\n":
                    self._advance()
                continue

            if char == "\n":
                self._advance()

                # Implicit line joining: a newline inside (), [] or {} is just
                # whitespace. Without this a table of data has to be written on
                # one enormous line, which is exactly where a student most
                # wants to break it up.
                if self.bracket_depth > 0:
                    continue

                tokens.append(Token(TokenType.NEWLINE, "newline", line, column))
                self._start_of_line(tokens)
                continue

            # Operator matching, longest first, alternating between real
            # operators and the ones students bring from other languages.
            #
            # The order matters: "===" must be caught before "==" leaves a
            # stray "=" behind, but "!=" must be matched before the lone "!"
            # rule fires, or a valid comparison would be reported as a mistake.
            three = char + self._peek(1) + self._peek(2)
            two = char + self._peek(1)

            if three in WRONG_OPERATORS:
                raise self._wrong_operator(three, line, column)

            if two in TWO_CHAR_OPERATORS:
                self._advance()
                self._advance()
                tokens.append(Token(TWO_CHAR_OPERATORS[two], two, line, column))
                continue

            if two in WRONG_OPERATORS:
                raise self._wrong_operator(two, line, column)

            if char in WRONG_OPERATORS:
                raise self._wrong_operator(char, line, column)

            if char in SINGLE_CHARS:
                self._advance()
                if char in "([{":
                    self.bracket_depth += 1
                elif char in ")]}":
                    self.bracket_depth = max(0, self.bracket_depth - 1)
                tokens.append(Token(SINGLE_CHARS[char], char, line, column))
                continue

            if char == '"':
                tokens.append(self._read_string())
                continue

            if char.isdigit():
                tokens.append(self._read_number())
                continue

            if char.isalpha() or char == "_":
                tokens.append(self._read_identifier())
                continue

            self._advance()
            raise self._error(
                f'Рамзи ношинос: "{char}".',
                line,
                column,
                hint="Шояд ин рамз тасодуфан навишта шудааст.",
            )

        # A file that does not end in a newline still ends a statement.
        if tokens and tokens[-1].type is not TokenType.NEWLINE:
            tokens.append(Token(TokenType.NEWLINE, "newline", self.line, self.column))

        # Every block still open at the end of the file closes here, so the
        # parser never has to treat "ran out of file" as a special case.
        while len(self.indents) > 1:
            self.indents.pop()
            tokens.append(Token(TokenType.DEDENT, 0, self.line, self.column))

        tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return tokens

    # ------------------------------------------------------------------
    # indentation
    # ------------------------------------------------------------------
    def _start_of_line(self, tokens: list[Token]) -> None:
        """Measure the indentation of the line we are about to read.

        Emits INDENT when a block opens and one DEDENT per block that closes.
        Blank lines and comment-only lines are skipped entirely: their
        indentation means nothing, and treating it as meaningful is a classic
        way to make a lexer reject perfectly good files.
        """
        line, column = self.line, self.column
        width = 0

        while True:
            char = self._peek()
            if char == " ":
                width += 1
                self._advance()
            elif char == "\t":
                tab_line, tab_column = self.line, self.column
                self._advance()
                raise self._error(
                    "Дар фосилагузорӣ рамзи tab истифода шудааст.",
                    tab_line,
                    tab_column,
                    hint=f"Танҳо холигӣ (space) истифода баред — {INDENT_WIDTH} "
                    "холигӣ барои ҳар сатҳ.",
                )
            else:
                break

        # blank line, comment-only line, or end of file
        if self._at_end() or self._peek() in ("\n", "\r", "#"):
            return

        current = self.indents[-1]

        if width == current:
            return

        if width > current:
            if width != current + INDENT_WIDTH:
                raise self._error(
                    f"Фосилаи нодуруст: {width} холигӣ.",
                    line,
                    width + 1,   # under the first real character of the line
                    hint=f"Ҳар сатҳи нав бояд маҳз {current + INDENT_WIDTH} "
                    "холигӣ дошта бошад.",
                )
            self.indents.append(width)
            tokens.append(Token(TokenType.INDENT, width, line, column))
            return

        # width < current: close every block deeper than this line
        while len(self.indents) > 1 and width < self.indents[-1]:
            self.indents.pop()
            tokens.append(Token(TokenType.DEDENT, width, line, column))

        if width != self.indents[-1]:
            raise self._error(
                f"Фосилаи {width} холигӣ ба ҳеҷ блоки кушода мувофиқ намеояд.",
                line,
                width + 1,   # under the first real character of the line
                hint="Сатҳҳои кушода: "
                + ", ".join(str(level) for level in self.indents),
            )

    # ------------------------------------------------------------------
    # token readers
    # ------------------------------------------------------------------
    def _read_string(self) -> Token:
        line, column = self.line, self.column
        self._advance()  # consume the opening quote

        chars: list[str] = []
        while True:
            if self._at_end() or self._peek() == "\n":
                raise self._error(
                    "Сатри матн пӯшида нашудааст.",
                    line,
                    column,
                    hint='Дар охири матн аломати " -ро илова кунед.',
                )

            char = self._advance()

            if char == '"':
                return Token(TokenType.STRING, "".join(chars), line, column)

            if char == _B:
                esc_line, esc_column = self.line, self.column
                if self._at_end():
                    continue  # the unterminated-string check above will fire
                escape = self._advance()
                if escape not in ESCAPES:
                    raise self._error(
                        'Рамзи гурезии номаълум: "' + _B + escape + '".',
                        esc_line,
                        esc_column - 1,
                        hint=ESCAPE_HINT,
                    )
                chars.append(ESCAPES[escape])
                continue

            chars.append(char)

    def _read_number(self) -> Token:
        line, column = self.line, self.column
        digits: list[str] = []

        while not self._at_end() and self._peek().isdigit():
            digits.append(self._advance())

        # a decimal point only counts if a digit follows it
        if self._peek() == "." and self._peek(1).isdigit():
            digits.append(self._advance())
            while not self._at_end() and self._peek().isdigit():
                digits.append(self._advance())
            # Decimal, not float: see the note at the top of values.py.
            return Token(
                TokenType.NUMBER, Decimal("".join(digits)), line, column
            )

        return Token(TokenType.NUMBER, int("".join(digits)), line, column)

    def _read_identifier(self) -> Token:
        line, column = self.line, self.column
        chars: list[str] = []

        # `isalnum()` is true for Cyrillic letters and for Tajik-specific ones
        # such as ӣ ӯ қ ғ ҳ ҷ, so identifiers like `шаҳр` need no special case.
        while not self._at_end() and (self._peek().isalnum() or self._peek() == "_"):
            chars.append(self._advance())

        name = "".join(chars)

        if name in KEYWORD_TOKENS:
            return Token(KEYWORD_TOKENS[name], name, line, column)

        if name in KEYWORDS:
            version = KEYWORD_VERSIONS.get(name, "оянда")
            raise self._error(
                f'Калимаи калидии "{name}" ҳанӯз дастгирӣ намешавад.',
                line,
                column,
                hint=f"Ин калима барои версияи {version} захира шудааст.",
            )

        return Token(TokenType.IDENT, name, line, column)
