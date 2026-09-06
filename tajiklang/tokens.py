"""Токенҳо — the vocabulary of TajikLang.

A token is the smallest meaningful piece of source code: a name, a number,
a string, an operator. The lexer's only job is to turn a stream of characters
into a stream of these.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    # --- literals and names ---
    NUMBER = auto()      # 10, 3.5
    STRING = auto()      # "Салом"
    IDENT = auto()       # навис, ном, ҳарорат
    TRUE = auto()        # рост
    FALSE = auto()       # дурӯғ
    NULL = auto()        # холӣ

    # --- keywords ---
    LET = auto()         # бигзор
    AND = auto()         # ва
    OR = auto()          # ё
    NOT = auto()         # не
    IF = auto()          # агар
    ELSE = auto()        # вагарна
    FOR = auto()         # барои
    FROM = auto()        # аз
    TO = auto()          # то
    WHILE = auto()       # то_вақте
    FUNC = auto()        # функсия
    RETURN = auto()      # баргардон
    IMPORT = auto()      # ворид
    BREAK = auto()       # шикан
    CONTINUE = auto()    # давом
    TRY = auto()         # кӯшиш
    CATCH = auto()       # хато
    CLASS = auto()       # қолиб
    INHERITS = auto()    # мерос

    # --- arithmetic ---
    PLUS = auto()        # +
    MINUS = auto()       # -
    STAR = auto()        # *
    SLASH = auto()       # /
    PERCENT = auto()     # %

    # --- comparison ---
    EQ = auto()          # ==
    NEQ = auto()         # !=
    LT = auto()          # <
    GT = auto()          # >
    LTE = auto()         # <=
    GTE = auto()         # >=

    # --- compound assignment ---
    PLUS_ASSIGN = auto()     # +=
    MINUS_ASSIGN = auto()    # -=
    STAR_ASSIGN = auto()     # *=
    SLASH_ASSIGN = auto()    # /=
    PERCENT_ASSIGN = auto()  # %=

    # --- assignment and punctuation ---
    PIPE = auto()        # |>
    ASSIGN = auto()      # =
    LPAREN = auto()      # (
    RPAREN = auto()      # )
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]
    LBRACE = auto()      # {
    RBRACE = auto()      # }
    COMMA = auto()       # ,
    COLON = auto()       # :
    DOT = auto()         # .

    # --- structure ---
    NEWLINE = auto()     # end of a statement
    INDENT = auto()      # a block opens (4 more spaces)
    DEDENT = auto()      # a block closes
    EOF = auto()         # end of file

    def __str__(self) -> str:
        return self.name


# Keywords that currently mean something. The lexer turns these into their own
# token type, so the parser never has to compare strings.
KEYWORD_TOKENS: dict[str, TokenType] = {
    "бигзор": TokenType.LET,
    "рост": TokenType.TRUE,
    "дурӯғ": TokenType.FALSE,
    "холӣ": TokenType.NULL,
    "ва": TokenType.AND,
    "ё": TokenType.OR,
    "не": TokenType.NOT,
    "агар": TokenType.IF,
    "вагарна": TokenType.ELSE,
    "барои": TokenType.FOR,
    "аз": TokenType.FROM,
    "то": TokenType.TO,
    "то_вақте": TokenType.WHILE,
    "функсия": TokenType.FUNC,
    "баргардон": TokenType.RETURN,
    "ворид": TokenType.IMPORT,
    "шикан": TokenType.BREAK,
    "давом": TokenType.CONTINUE,
    "кӯшиш": TokenType.TRY,
    "хато": TokenType.CATCH,
    "қолиб": TokenType.CLASS,
    "мерос": TokenType.INHERITS,
}


# The full reserved vocabulary. Words absent from KEYWORD_TOKENS are reserved
# but not implemented: the lexer rejects them with a "coming in a later
# version" message, so a program written today cannot break when they land.
KEYWORDS: frozenset[str] = frozenset(KEYWORD_TOKENS) | frozenset({
})

# `худ` (self) and `синф` (class) are deliberately NOT reserved. Python does
# not reserve `self` either, and a school program wants `бигзор синф = 10` on
# its first line — so the class keyword is `қолиб` ("mould"), which is also
# the metaphor: a class is the mould an object is cast from.


# Version each not-yet-implemented keyword is scheduled for.
KEYWORD_VERSIONS: dict[str, str] = {}


# Two-character operators, checked before single characters so that "<=" is
# never read as "<" followed by "=".
TWO_CHAR_OPERATORS: dict[str, TokenType] = {
    "==": TokenType.EQ,
    "!=": TokenType.NEQ,
    "<=": TokenType.LTE,
    ">=": TokenType.GTE,
    "+=": TokenType.PLUS_ASSIGN,
    "-=": TokenType.MINUS_ASSIGN,
    "*=": TokenType.STAR_ASSIGN,
    "/=": TokenType.SLASH_ASSIGN,
    "%=": TokenType.PERCENT_ASSIGN,
    "|>": TokenType.PIPE,
}


# Compound assignment token -> the arithmetic operator it stands for.
# `x += 1` is rewritten by the parser into `x = x + 1`, so the interpreter
# never learns that compound assignment exists.
COMPOUND_OPERATORS: dict[TokenType, str] = {
    TokenType.PLUS_ASSIGN: "+",
    TokenType.MINUS_ASSIGN: "-",
    TokenType.STAR_ASSIGN: "*",
    TokenType.SLASH_ASSIGN: "/",
    TokenType.PERCENT_ASSIGN: "%",
}


# Single characters that form a complete token on their own.
SINGLE_CHARS: dict[str, TokenType] = {
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    ",": TokenType.COMMA,
    ".": TokenType.DOT,
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "%": TokenType.PERCENT,
    "=": TokenType.ASSIGN,
    ":": TokenType.COLON,
    "<": TokenType.LT,
    ">": TokenType.GT,
}


# Operators students arrive with from other languages, and what to write here
# instead. Recognising them costs nothing and turns "unknown character" into a
# usable answer.
WRONG_OPERATORS: dict[str, str] = {
    "&&": 'Дар ин ҷо калимаи "ва" -ро истифода баред.',
    "||": 'Дар ин ҷо калимаи "ё" -ро истифода баред.',
    "!": 'Барои инкор калимаи "не" -ро истифода баред: не (x == 5)',
    "===": 'Барои муқоиса аломати "==" кифоя аст.',
}


@dataclass(frozen=True)
class Token:
    """One token, plus where it came from.

    `line` and `column` are 1-based and are carried all the way through the
    parser and interpreter so that every error message can point at the exact
    character that caused it.
    """

    type: TokenType
    value: Any
    line: int
    column: int

    def __repr__(self) -> str:
        return f"{self.type}({self.value!r})@{self.line}:{self.column}"
