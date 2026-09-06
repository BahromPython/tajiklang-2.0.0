"""Пайванд бо Python — the one door out of TajikLang.

TajikLang is a small language. Python has thirty years of libraries. This
module lets an advanced program reach them without the language growing a
second personality:

    ворид питон

    бигзор омор = питон.ворид("statistics")
    навис(омор.median([3, 1, 4, 1, 5]))

Four rules keep the door from leaking:

1. **One visible prefix.** Everything arrives through `питон.ворид(...)`, so
   an English name in a listing is always traceable to that line. The core
   language stays Tajik.
2. **Errors come home.** A Python exception is turned into an ordinary Tajik
   runtime error carrying the caller's line, caret and hint. A student must
   never see a bare `ValueError: math domain error` with no position.
3. **Values convert at the boundary.** Numbers, text, booleans, lists and
   dictionaries pass through as themselves. Anything else stays wrapped and
   prints as `<объекти питон>` rather than pretending to be a TajikLang value.
4. **It is opt-in.** No program touches Python unless it says `ворид питон`.
"""

from __future__ import annotations

import importlib
from decimal import Decimal
from typing import Any

from .errors import BuiltinError
from .values import Builtin, Module


class PythonObject:
    """A Python value with no TajikLang equivalent, kept at arm's length.

    Attribute access and calling both work, so `питон` feels like the rest of
    the language; everything else about it is deliberately opaque.
    """

    def __init__(self, value: Any, path: str) -> None:
        self.value = value
        self.path = path            # e.g. "statistics.median", for messages

    def __repr__(self) -> str:
        return f"<объекти питон: {self.path}>"


def to_tajik(value: Any, path: str) -> Any:
    """A Python value on its way into TajikLang."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        # Floats become decimals so that Python's 0.30000000000000004 does not
        # walk in through the back door — see LANGUAGE_SPEC.md §4.1.
        return Decimal(repr(value))
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (list, tuple)):
        return [to_tajik(item, path) for item in value]
    if isinstance(value, dict):
        return {
            key: to_tajik(item, path)
            for key, item in value.items()
            if isinstance(key, (str, int, float, Decimal))
        }
    if callable(value):
        return _wrap_callable(value, path)
    return PythonObject(value, path)


def to_python(value: Any) -> Any:
    """A TajikLang value on its way out to Python."""
    if isinstance(value, PythonObject):
        return value.value
    if isinstance(value, Decimal):
        # Most libraries want a float; Decimal would raise on arithmetic.
        return float(value)
    if isinstance(value, list):
        return [to_python(item) for item in value]
    if isinstance(value, dict):
        return {key: to_python(item) for key, item in value.items()}
    return value


def _wrap_callable(fn: Any, path: str) -> Builtin:
    def call(*args: Any) -> Any:
        try:
            result = fn(*[to_python(a) for a in args])
        except BuiltinError:
            raise
        except Exception as error:      # noqa: BLE001 - any library may raise
            raise BuiltinError(
                f'Функсияи питони "{path}" хато дод: '
                f"{type(error).__name__}: {error}",
                hint="Ин хатои китобхонаи Python аст, на хатои TajikLang.",
            ) from None
        return to_tajik(result, path)

    return Builtin(path, call)


class _PythonNamespace:
    """What `питон.ворид("math")` gives back: a module you can reach into."""

    def __init__(self, module: Any, name: str) -> None:
        self.module = module
        self.name = name

    def get(self, attribute: str) -> Any:
        if attribute.startswith("_"):
            raise BuiltinError(
                f'Номи "{attribute}" дар питон хусусӣ аст.',
                hint="Номҳое, ки бо _ сар мешаванд, дастрас нестанд.",
            )
        try:
            value = getattr(self.module, attribute)
        except AttributeError:
            raise BuiltinError(
                f'Модули питони "{self.name}" номи "{attribute}" -ро надорад.',
                hint="Номро дар ҳуҷҷатҳои Python санҷед.",
            ) from None
        return to_tajik(value, f"{self.name}.{attribute}")


class PythonModule(Module):
    """A Python module dressed as a TajikLang module, resolved lazily.

    Lazily because a big library has thousands of attributes and a student
    only ever touches three; walking them all at import time would make
    `питон.ворид("pandas")` take seconds for nothing.
    """

    def __init__(self, module: Any, name: str) -> None:
        super().__init__(name, None)
        self.namespace = _PythonNamespace(module, name)

    def __repr__(self) -> str:
        return f"<модули питони {self.name}>"


def build_module() -> dict[str, Any]:
    """The `питон` module itself."""

    def ворид(*args: Any) -> PythonModule:
        if len(args) != 1 or not isinstance(args[0], str):
            raise BuiltinError(
                'Функсияи "питон.ворид" номи модулро ҳамчун матн мехоҳад.',
                hint='Масалан: питон.ворид("math")',
            )
        name = args[0]
        try:
            module = importlib.import_module(name)
        except ImportError:
            raise BuiltinError(
                f'Модули питони "{name}" ёфт нашуд.',
                hint="Шояд он насб нашудааст.",
            ) from None
        return PythonModule(module, name)

    def даъват(*args: Any) -> Any:
        """питон.даъват(объект, "ном", аргументҳо...) — call a method."""
        if len(args) < 2 or not isinstance(args[1], str):
            raise BuiltinError(
                'Функсияи "питон.даъват" объект ва номи метод мехоҳад.',
                hint='Масалан: питон.даъват(объект, "sort")',
            )
        target = to_python(args[0])
        name = args[1]
        try:
            method = getattr(target, name)
        except AttributeError:
            raise BuiltinError(
                f'Объект методи "{name}" -ро надорад.'
            ) from None
        return _wrap_callable(method, name)(*args[2:])

    return {
        "ворид": Builtin("ворид", ворид),
        "даъват": Builtin("даъват", даъват),
    }
