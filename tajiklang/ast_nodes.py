"""Дарахти синтаксисӣ (AST) — the shape of a program.

Tokens are a flat list. An AST is a tree, and the tree is where meaning lives:

    бигзор натиҷа = 2 + 3 * 4

    Program
      └── VarDeclaration(name='натиҷа')
            └── BinaryOp('+')
                  ├── NumberLiteral(2)
                  └── BinaryOp('*')
                        ├── NumberLiteral(3)
                        └── NumberLiteral(4)

Note that `*` sits *below* `+` in the tree. That nesting is precedence: the
deeper node is evaluated first, so the tree already encodes 2 + (3 * 4) and the
interpreter never has to think about precedence at all.

Every node carries `line`/`column` so runtime errors can point back at source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


@dataclass
class Node:
    line: int
    column: int


# --- expressions: things that produce a value -------------------------------


@dataclass
class StringLiteral(Node):
    value: str


@dataclass
class NumberLiteral(Node):
    value: Union[int, float]


@dataclass
class BooleanLiteral(Node):
    value: bool              # рост / дурӯғ


@dataclass
class NullLiteral(Node):
    pass                     # холӣ


@dataclass
class ListLiteral(Node):
    elements: list["Expression"] = field(default_factory=list)


@dataclass
class DictLiteral(Node):
    pairs: list[tuple["Expression", "Expression"]] = field(default_factory=list)


@dataclass
class Identifier(Node):
    name: str


@dataclass
class UnaryOp(Node):
    operator: str            # "-" or "не"
    operand: "Expression"


@dataclass
class BinaryOp(Node):
    """Arithmetic and comparison: both sides are always evaluated."""

    operator: str            # "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">="
    left: "Expression"
    right: "Expression"


@dataclass
class LogicalOp(Node):
    """`ва` and `ё` — a *different* node from BinaryOp, because the right side
    may never be evaluated at all (short-circuiting). Giving them their own
    node type means the difference is visible in the tree rather than hidden
    inside an `if` in the interpreter."""

    operator: str            # "ва", "ё"
    left: "Expression"
    right: "Expression"


@dataclass
class CallExpression(Node):
    callee: "Expression"
    arguments: list["Expression"] = field(default_factory=list)


@dataclass
class IndexExpression(Node):
    """рӯйхат[0] and луғат["калид"]."""

    target: "Expression"
    index: "Expression"


@dataclass
class MemberExpression(Node):
    """риёзӣ.реша — reaching inside a module."""

    target: "Expression"
    name: str


Expression = Union[
    StringLiteral,
    NumberLiteral,
    BooleanLiteral,
    NullLiteral,
    ListLiteral,
    DictLiteral,
    Identifier,
    UnaryOp,
    BinaryOp,
    LogicalOp,
    CallExpression,
    IndexExpression,
    MemberExpression,
]


# --- statements: things that are *done* -------------------------------------


@dataclass
class VarDeclaration(Node):
    """бигзор ном = қимат — introduces a new name."""

    name: str
    value: Expression


@dataclass
class Assignment(Node):
    """ном = қимат — changes a name that already exists."""

    name: str
    value: Expression


@dataclass
class IndexAssignment(Node):
    """рӯйхат[0] = қимат — changes one element in place."""

    target: Expression
    index: Expression
    value: Expression


@dataclass
class ExpressionStatement(Node):
    expression: Expression


@dataclass
class IfStatement(Node):
    """агар шарт: ... вагарна: ...

    `вагарна агар` needs no node of its own: it is an IfStatement sitting
    alone inside another IfStatement's else branch. One node type, any number
    of branches.
    """

    condition: Expression
    then_branch: list["Statement"] = field(default_factory=list)
    else_branch: list["Statement"] | None = None


@dataclass
class ForRange(Node):
    """барои i аз 1 то 10: — a counted loop, both ends inclusive."""

    variable: str
    start: Expression
    end: Expression
    body: list["Statement"] = field(default_factory=list)


@dataclass
class ForEach(Node):
    """барои x аз рӯйхат: — walk a list, a dictionary's keys, or a string."""

    variable: str
    iterable: Expression
    body: list["Statement"] = field(default_factory=list)


@dataclass
class WhileStatement(Node):
    """то_вақте шарт: ..."""

    condition: Expression
    body: list["Statement"] = field(default_factory=list)


@dataclass
class FunctionDeclaration(Node):
    """функсия ном(a, b): ..."""

    name: str
    parameters: list[str] = field(default_factory=list)
    body: list["Statement"] = field(default_factory=list)


@dataclass
class ReturnStatement(Node):
    """баргардон қимат — or bare `баргардон`, which returns холӣ."""

    value: Expression | None = None


@dataclass
class BreakStatement(Node):
    """шикан — leave the innermost loop."""


@dataclass
class ContinueStatement(Node):
    """давом — skip to the next turn of the innermost loop."""


@dataclass
class CatchClause(Node):
    """One `хато [навъ] [ном]:` arm of a try statement.

    `kind`, when given, matches only that sort of failure. `name`, when given,
    binds the message text. A clause with no kind catches everything, so it
    must come last.
    """

    kind: str | None = None
    name: str | None = None
    body: list["Statement"] = field(default_factory=list)


@dataclass
class TryStatement(Node):
    """кӯшиш: ... хато [навъ] [ном]: ...

    Several `хато` clauses may follow, and the first whose kind matches runs.
    """

    body: list["Statement"] = field(default_factory=list)
    handlers: list[CatchClause] = field(default_factory=list)


@dataclass
class ClassDeclaration(Node):
    """қолиб Ном [мерос Волид]: функсия ...

    A class is a named bag of methods. `оғоз` is the one called when an
    instance is made; `худ` is an ordinary first parameter, not a keyword.
    """

    name: str
    parent: str | None = None
    methods: list["FunctionDeclaration"] = field(default_factory=list)


@dataclass
class MemberAssignment(Node):
    """худ.ном = қимат — setting a field on an object."""

    target: Expression
    name: str
    value: Expression


@dataclass
class ImportStatement(Node):
    """ворид риёзӣ — a built-in module, or a neighbouring .tj file."""

    name: str


Statement = Union[
    VarDeclaration,
    Assignment,
    IndexAssignment,
    ExpressionStatement,
    IfStatement,
    ForRange,
    ForEach,
    WhileStatement,
    FunctionDeclaration,
    ReturnStatement,
    ImportStatement,
    BreakStatement,
    ContinueStatement,
    TryStatement,
    ClassDeclaration,
    MemberAssignment,
]


@dataclass
class Program(Node):
    statements: list[Statement] = field(default_factory=list)
