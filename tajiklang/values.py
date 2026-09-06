"""Қиматҳо — the runtime values of TajikLang, and how they are described.

Everything a TajikLang program can hold lives here: the Python types it reuses
(int, float, str, bool, None, list, dict) plus the three it needs of its own —
built-in functions, user functions and modules.
"""

from __future__ import annotations

from decimal import Decimal, getcontext
from typing import TYPE_CHECKING, Any, Callable

# TajikLang uses **decimal** arithmetic, not binary floating point.
#
# In Python — and C, and Java, and JavaScript — `0.1 + 0.2` is
# 0.30000000000000004, because 0.1 has no exact binary form. Every beginner
# meets that, and no explanation of it belongs in lesson 3. School arithmetic
# is decimal, money is decimal, marks are decimal; so is this language.
#
# 20 significant digits: enough that nothing a student writes runs out, few
# enough that 1/3 does not fill a line.
getcontext().prec = 20

if TYPE_CHECKING:  # pragma: no cover - typing only
    from . import ast_nodes as ast


class Builtin:
    """A function implemented in Python and exposed to TajikLang."""

    def __init__(self, name: str, fn: Callable[..., Any]) -> None:
        self.name = name
        self.fn = fn

    def __call__(self, *args: Any) -> Any:
        return number(self.fn(*args))

    def __repr__(self) -> str:
        return f"<функсияи дарунсохт {self.name}>"


class Function:
    """A function written in TajikLang.

    `closure` is the environment the function was *declared* in, not the one it
    is called from. That single choice is what makes TajikLang lexically
    scoped: a function always sees the names that surrounded its own text.
    """

    def __init__(self, declaration: "ast.FunctionDeclaration", closure: Any) -> None:
        self.declaration = declaration
        self.closure = closure

    @property
    def name(self) -> str:
        return self.declaration.name

    @property
    def parameters(self) -> list[str]:
        return self.declaration.parameters

    def __repr__(self) -> str:
        params = ", ".join(self.parameters)
        return f"<функсияи {self.name}({params})>"


class TajikClass:
    """A class: a name, an optional parent, and a bag of methods."""

    def __init__(
        self,
        name: str,
        parent: "TajikClass | None",
        methods: dict[str, "Function"],
    ) -> None:
        self.name = name
        self.parent = parent
        self.methods = methods

    def find(self, name: str) -> "Function | None":
        """Look here, then up the chain of parents."""
        if name in self.methods:
            return self.methods[name]
        if self.parent is not None:
            return self.parent.find(name)
        return None

    def method_names(self) -> list[str]:
        names = list(self.methods)
        if self.parent is not None:
            names.extend(self.parent.method_names())
        return names

    def __repr__(self) -> str:
        return f"<синфи {self.name}>"


class Instance:
    """One object made from a class."""

    def __init__(self, cls: TajikClass) -> None:
        self.cls = cls
        self.fields: dict[str, Any] = {}

    def __repr__(self) -> str:
        return f"<{self.cls.name}>"


class BoundMethod:
    """A method with its object already attached, so `худ` is filled in."""

    def __init__(self, instance: Instance, function: "Function") -> None:
        self.instance = instance
        self.function = function

    @property
    def name(self) -> str:
        return self.function.name

    @property
    def parameters(self) -> list[str]:
        return self.function.parameters[1:]      # `худ` is supplied for you

    def __repr__(self) -> str:
        return f"<методи {self.instance.cls.name}.{self.function.name}>"


class Module:
    """A namespace: either a built-in module or another .tj file."""

    def __init__(self, name: str, environment: Any) -> None:
        self.name = name
        self.environment = environment

    def __repr__(self) -> str:
        return f"<модули {self.name}>"


class ReturnSignal(Exception):
    """`баргардон` unwinding the Python stack back to the call site.

    A tree-walk interpreter runs a `баргардон` deep inside nested `execute`
    calls, and there is no way to hand a value back up through them all except
    to raise. This is a control-flow signal, not an error — nothing catches it
    but `Function.call`.
    """

    def __init__(self, value: Any) -> None:
        super().__init__("баргардон")
        self.value = value


class BreakSignal(Exception):
    """`шикан` unwinding out to the nearest loop. Control flow, not an error."""


class ContinueSignal(Exception):
    """`давом` unwinding out to the nearest loop. Control flow, not an error."""


def is_number(value: Any) -> bool:
    # bool is a subclass of int in Python; booleans must not silently behave
    # as 1 and 0 in arithmetic.
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


def is_whole(value: Any) -> bool:
    """Is this number a whole one? Works for int, Decimal and float alike."""
    if isinstance(value, bool) or not is_number(value):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, Decimal):
        return value == value.to_integral_value()
    return float(value).is_integer()


def number(value: Any) -> Any:
    """Every number entering the language becomes int or Decimal, never float.

    Applied at each boundary — literals, arithmetic results, builtin return
    values, Python interop — because Decimal and float cannot be mixed in
    arithmetic, so a single stray float would fail far from its source.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return Decimal(repr(value))
    if isinstance(value, list):
        return [number(item) for item in value]
    if isinstance(value, dict):
        return {key: number(item) for key, item in value.items()}
    return value


def type_name(value: Any) -> str:
    """The Tajik name of a value's type, for error messages."""
    if isinstance(value, bool):
        return "мантиқӣ"
    if is_number(value):
        return "рақам"
    if isinstance(value, str):
        return "матн"
    if value is None:
        return "холӣ"
    if isinstance(value, list):
        return "рӯйхат"
    if isinstance(value, dict):
        return "луғат"
    if isinstance(value, Module):
        return "модул"
    if isinstance(value, TajikClass):
        return "синф"
    if isinstance(value, Instance):
        return value.cls.name          # `навъ(д)` naming the class is useful
    if isinstance(value, BoundMethod):
        return "функсия"
    if isinstance(value, (Function, Builtin)) or callable(value):
        return "функсия"
    return "номаълум"


def to_tajik_string(value: Any) -> str:
    """How a value looks when printed."""
    if isinstance(value, bool):
        return "рост" if value else "дурӯғ"
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return str(int(value))          # 4.0 prints as 4
        text = format(value.normalize(), "f")
        return text
    if isinstance(value, float) and value.is_integer():
        return str(int(value))  # 4.0 prints as 4
    if value is None:
        return "холӣ"
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "[" + ", ".join(_repr_inside(item) for item in value) + "]"
    if isinstance(value, dict):
        inner = ", ".join(
            f"{_repr_inside(key)}: {_repr_inside(item)}" for key, item in value.items()
        )
        return "{" + inner + "}"
    if isinstance(value, Instance):
        # An object prints as its class plus its fields, so `навис(д)` during
        # debugging shows something worth reading.
        inner = ", ".join(
            f"{key}: {_repr_inside(item)}" for key, item in value.fields.items()
        )
        return f"{value.cls.name}(" + inner + ")"
    return str(value)


def _repr_inside(value: Any) -> str:
    """Like `to_tajik_string`, but strings keep their quotes.

    `навис("а")` prints `а`, but `навис(["а"])` prints `["а"]` — otherwise a
    list of strings and a list of names look identical.
    """
    if isinstance(value, str):
        return '"' + value + '"'
    return to_tajik_string(value)


def equals(left: Any, right: Any) -> bool:
    """Equality that never fails — different kinds are simply unequal.

    The kind check matters because Python treats `True == 1` as true, and a
    student who writes `рост == 1` should get `дурӯғ`, not a surprise. Lists
    and dictionaries compare element by element under the same rule.
    """
    if type_name(left) != type_name(right):
        return False

    if isinstance(left, list):
        return len(left) == len(right) and all(
            equals(a, b) for a, b in zip(left, right)
        )

    if isinstance(left, dict):
        if set(left) != set(right):
            return False
        return all(equals(left[key], right[key]) for key in left)

    return left == right
