"""Китобхонаи стандартӣ — the built-in names and modules.

Everything here is available **without `ворид`**, the way Python's builtins
are. The two modules (`риёзӣ`, `матн`) exist as tidy namespaces over the very
same function objects, so `гирд(3.7)` and `риёзӣ.гирд(3.7)` are the same call.

A builtin reports problems by raising `BuiltinError`; the interpreter turns
that into a normal Tajik runtime error with the caller's line and column.

Naming rules followed here, so the library stays predictable:

* a function that *answers a question* is a noun or adjective — `дарозӣ`,
  `навъ`, `калидҳо`;
* a function that *does something* is an imperative — `илова`, `иваз`,
  `хонед`;
* a function that *asks* yes/no ends in a verb — `дорад`, `сар_мешавад`.
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any, Callable

from . import collation
from .errors import BuiltinError
from .values import Builtin, is_number, to_tajik_string, type_name


# ---------------------------------------------------------------------------
# argument checking helpers
# ---------------------------------------------------------------------------
def _arity(name: str, args: tuple[Any, ...], *allowed: int) -> None:
    if len(args) not in allowed:
        wanted = " ё ".join(str(n) for n in allowed)
        raise BuiltinError(
            f'Функсияи "{name}" {wanted} аргумент мехоҳад, вале '
            f"{len(args)} гирифт.",
            hint="Шумораи аргументҳоро санҷед.",
        )


def _need(name: str, value: Any, check: Callable[[Any], bool], expected: str) -> Any:
    if not check(value):
        raise BuiltinError(
            f'Функсияи "{name}" {expected} мехоҳад, вале {type_name(value)} гирифт.'
        )
    return value


def _text(name: str, value: Any) -> str:
    return _need(name, value, lambda v: isinstance(v, str), "матн")


def _list(name: str, value: Any) -> list:
    return _need(name, value, lambda v: isinstance(v, list), "рӯйхат")


def _dict(name: str, value: Any) -> dict:
    return _need(name, value, lambda v: isinstance(v, dict), "луғат")


def _number(name: str, value: Any) -> Any:
    return _need(name, value, is_number, "рақам")


def _whole(name: str, value: Any) -> int:
    if not is_number(value) or (isinstance(value, float) and not value.is_integer()):
        raise BuiltinError(
            f'Функсияи "{name}" рақами бутун мехоҳад, вале '
            f"{type_name(value)} гирифт."
        )
    return int(value)


def _position(name: str, index: Any, length: int, allow_end: bool = False) -> int:
    """A 0-based index, accepting negatives from the end, as `рӯйхат[-1]` does."""
    position = _whole(name, index)
    if position < 0:
        position += length
    limit = length if allow_end else length - 1
    if position < 0 or position > limit:
        raise BuiltinError(
            f"Рақами тартибӣ берун аз ҳудуд аст (дарозӣ {length}).",
            hint=(
                f"Рақамҳои имконпазир: 0 то {limit}, ё -1 то -{length} аз охир."
                if length
                else "Ин холӣ аст."
            ),
        )
    return position


def _ordered(name: str, items: list) -> list:
    """Sorted copy — text by the Tajik alphabet, numbers numerically."""
    if all(isinstance(item, str) for item in items):
        return sorted(items, key=collation.sort_key)
    if all(is_number(item) for item in items):
        return sorted(items)
    raise BuiltinError(
        f'Функсияи "{name}" рӯйхати ҳамаи матнҳо ё ҳамаи рақамҳоро мехоҳад.',
        hint='Барои рӯйхати мураккаб "тартиб_бо" -ро истифода баред.',
    )


# ---------------------------------------------------------------------------
# numbers — also exposed as the `риёзӣ` module
# ---------------------------------------------------------------------------
def _build_math() -> dict[str, Any]:
    def реша(*args: Any) -> float:
        _arity("реша", args, 1)
        value = _number("реша", args[0])
        if value < 0:
            raise BuiltinError(
                "Решаи квадратии рақами манфӣ вуҷуд надорад.",
                hint="Аввал санҷед: агар x >= 0:",
            )
        return math.sqrt(value)

    def дараҷа(*args: Any) -> Any:
        _arity("дараҷа", args, 2)
        return _number("дараҷа", args[0]) ** _number("дараҷа", args[1])

    def мутлақ(*args: Any) -> Any:
        _arity("мутлақ", args, 1)
        return abs(_number("мутлақ", args[0]))

    def гирд(*args: Any) -> Any:
        """Гирд мекунад. Бо аргументи дуюм — то чанд рақами баъди вергул."""
        _arity("гирд", args, 1, 2)
        value = _number("гирд", args[0])
        if len(args) == 1:
            return round(value)
        return round(value, _whole("гирд", args[1]))

    def фарш(*args: Any) -> int:
        _arity("фарш", args, 1)
        return math.floor(_number("фарш", args[0]))

    def сақф(*args: Any) -> int:
        _arity("сақф", args, 1)
        return math.ceil(_number("сақф", args[0]))

    def бутун(*args: Any) -> int:
        """Қисми касриро мепартояд: бутун(3.9) = 3, бутун(-3.9) = -3."""
        _arity("бутун", args, 1)
        value = args[0]
        if isinstance(value, str):
            return int(ба_рақам_text("бутун", value))
        return int(_number("бутун", value))

    def мин(*args: Any) -> Any:
        return _extreme_of("мин", args, biggest=False)

    def макс(*args: Any) -> Any:
        return _extreme_of("макс", args, biggest=True)

    def _extreme_of(name: str, args: tuple[Any, ...], biggest: bool) -> Any:
        """мин(a, b) or мин(рӯйхат) — both read naturally, so both work."""
        if len(args) == 1 and isinstance(args[0], list):
            items = args[0]
            if not items:
                raise BuiltinError(
                    f'Функсияи "{name}" рӯйхати холиро қабул намекунад.',
                    hint="Аввал санҷед: агар дарозӣ(рӯйхат) > 0:",
                )
        elif len(args) == 2:
            items = list(args)
        else:
            raise BuiltinError(
                f'Функсияи "{name}" ду рақам ё як рӯйхат мехоҳад.',
                hint=f"{name}(3, 7) ё {name}([3, 7, 1])",
            )
        ordered = _ordered(name, items)
        return ordered[-1] if biggest else ordered[0]

    def тасодуфӣ(*args: Any) -> int:
        _arity("тасодуфӣ", args, 2)
        low = _whole("тасодуфӣ", args[0])
        high = _whole("тасодуфӣ", args[1])
        if low > high:
            raise BuiltinError(
                "Ҳадди поён аз ҳадди боло калон аст.",
                hint="тасодуфӣ(1, 10) — аввал хурдтарин.",
            )
        return random.randint(low, high)

    def интихоб(*args: Any) -> Any:
        """Як унсури тасодуфӣ аз рӯйхат."""
        _arity("интихоб", args, 1)
        items = _list("интихоб", args[0])
        if not items:
            raise BuiltinError('Функсияи "интихоб" рӯйхати холиро қабул намекунад.')
        return random.choice(items)

    values: dict[str, Any] = {
        name: Builtin(name, fn)
        for name, fn in {
            "реша": реша, "дараҷа": дараҷа, "мутлақ": мутлақ, "гирд": гирд,
            "фарш": фарш, "сақф": сақф, "бутун": бутун, "мин": мин,
            "макс": макс, "тасодуфӣ": тасодуфӣ, "интихоб": интихоб,
        }.items()
    }
    values["ПИ"] = math.pi
    values["Е"] = math.e
    return values


def ба_рақам_text(name: str, value: str) -> Any:
    """Shared by `ба_рақам` and `бутун` so both fail the same way."""
    text = value.strip()
    try:
        return int(text) if text.lstrip("-").isdigit() else float(text)
    except ValueError:
        raise BuiltinError(
            f'Матни "{value}" ба рақам табдил намеёбад.',
            hint='Танҳо матни рақамӣ, масалан "16". Бо "рақам_аст" санҷед.',
        ) from None


def _буриш(*args: Any) -> Any:
    """Пораи матн ё рӯйхат — ҳарду ҳадд дохил мешаванд, мисли «то».

    Module-level so that it can be both a global and `матн.буриш` without
    two copies drifting apart.
    """
    _arity("буриш", args, 3)
    target = args[0]
    if not isinstance(target, (str, list)):
        raise BuiltinError(
            f'Функсияи "буриш" матн ё рӯйхат мехоҳад, вале '
            f"{type_name(target)} гирифт."
        )
    if not target:
        raise BuiltinError('Функсияи "буриш" чизи холиро қабул намекунад.')
    start = _position("буриш", args[1], len(target))
    end = _position("буриш", args[2], len(target))
    if end < start:
        raise BuiltinError(
            "Ҳадди охир аз ҳадди аввал хурд аст.",
            hint="буриш(x, 0, 2) — аввал хурдтарин.",
        )
    return target[start : end + 1]


# ---------------------------------------------------------------------------
# text — also exposed as the `матн` module
# ---------------------------------------------------------------------------
def _build_text() -> dict[str, Any]:
    def калон(*args: Any) -> str:
        _arity("калон", args, 1)
        return _text("калон", args[0]).upper()

    def хурд(*args: Any) -> str:
        _arity("хурд", args, 1)
        return _text("хурд", args[0]).lower()

    def тоза(*args: Any) -> str:
        """Холигиҳои аввал ва охирро мебарорад."""
        _arity("тоза", args, 1)
        return _text("тоза", args[0]).strip()

    def ҷудо(*args: Any) -> list:
        """ҷудо("а,б,в", ",") -> ["а", "б", "в"]"""
        _arity("ҷудо", args, 1, 2)
        text = _text("ҷудо", args[0])
        if len(args) == 1:
            return text.split()
        separator = _text("ҷудо", args[1])
        if separator == "":
            raise BuiltinError(
                "Ҷудокунанда набояд холӣ бошад.",
                hint="Барои ҳарф ба ҳарф: ҳарфҳо(матн)",
            )
        return text.split(separator)

    def пайваст(*args: Any) -> str:
        """пайваст(["а", "б"], "-") -> "а-б" """
        _arity("пайваст", args, 1, 2)
        items = _list("пайваст", args[0])
        separator = _text("пайваст", args[1]) if len(args) == 2 else ""
        for item in items:
            if not isinstance(item, str):
                raise BuiltinError(
                    f'Функсияи "пайваст" рӯйхати матнҳоро мехоҳад, вале дар он '
                    f"{type_name(item)} ҳаст.",
                    hint="Ҳар қиматро бо «ба_матн» табдил диҳед.",
                )
        return separator.join(items)

    def иваз(*args: Any) -> str:
        """иваз(матн, кӯҳна, нав)"""
        _arity("иваз", args, 3)
        text = _text("иваз", args[0])
        old = _text("иваз", args[1])
        new = _text("иваз", args[2])
        if old == "":
            raise BuiltinError("Матни ивазшаванда набояд холӣ бошад.")
        return text.replace(old, new)

    def ёфтан(*args: Any) -> Any:
        """Рақами тартибии аввалин мувофиқат, ё «холӣ» агар ёфт нашавад."""
        _arity("ёфтан", args, 2)
        text = _text("ёфтан", args[0])
        position = text.find(_text("ёфтан", args[1]))
        return None if position < 0 else position

    def сар_мешавад(*args: Any) -> bool:
        _arity("сар_мешавад", args, 2)
        return _text("сар_мешавад", args[0]).startswith(
            _text("сар_мешавад", args[1])
        )

    def тамом_мешавад(*args: Any) -> bool:
        _arity("тамом_мешавад", args, 2)
        return _text("тамом_мешавад", args[0]).endswith(
            _text("тамом_мешавад", args[1])
        )

    def такрор(*args: Any) -> str:
        _arity("такрор", args, 2)
        text = _text("такрор", args[0])
        times = _whole("такрор", args[1])
        if times < 0:
            raise BuiltinError("Шумораи такрор набояд манфӣ бошад.")
        return text * times

    def ҳарфҳо(*args: Any) -> list:
        _arity("ҳарфҳо", args, 1)
        return list(_text("ҳарфҳо", args[0]))

    def рақам_аст(*args: Any) -> bool:
        """Оё ин матнро ба рақам табдил додан мумкин аст?"""
        _arity("рақам_аст", args, 1)
        text = _text("рақам_аст", args[0]).strip()
        if text.lstrip("-").isdigit():
            return True
        try:
            float(text)
            return True
        except ValueError:
            return False

    return {
        name: Builtin(name, fn)
        for name, fn in {
            "калон": калон, "хурд": хурд, "тоза": тоза, "ҷудо": ҷудо,
            "буриш": _буриш,
            "пайваст": пайваст, "иваз": иваз, "ёфтан": ёфтан,
            "сар_мешавад": сар_мешавад, "тамом_мешавад": тамом_мешавад,
            "такрор": такрор, "ҳарфҳо": ҳарфҳо, "рақам_аст": рақам_аст,
        }.items()
    }


# ---------------------------------------------------------------------------
# global builtins
# ---------------------------------------------------------------------------
def build_globals(
    output: Callable[[str], None],
    read_line: Callable[[str], str | None] | None = None,
    call: Callable[[Any, list[Any]], Any] | None = None,
) -> dict[str, Builtin]:
    """Every name a program starts with.

    `read_line` is how `хонед` asks for input — the terminal passes Python's
    `input`, the browser passes an input pane, a test passes canned lines.

    `call` is how a builtin calls back into a TajikLang function, which is
    what `тартиб_бо` needs. The interpreter supplies it; nothing else can.
    """

    # --- output and input ---------------------------------------------------
    def навис(*args: Any) -> None:
        output(" ".join(to_tajik_string(a) for a in args))

    def хонед(*args: Any) -> str:
        """хонед()  ё  хонед("Номи шумо: ")  — always returns матн."""
        _arity("хонед", args, 0, 1)
        prompt = to_tajik_string(args[0]) if args else ""

        if read_line is None:
            raise BuiltinError(
                "Дар ин ҷо маълумот хондан имконнопазир аст.",
                hint="Функсияи «хонед» дар терминал ва майдончаи браузер кор мекунад.",
            )

        line = read_line(prompt)
        if line is None:
            raise BuiltinError(
                "Маълумоти воридотӣ тамом шуд.",
                hint="Барнома чизе интизор буд, вале ҳеҷ чиз ворид нашуд.",
            )
        return line

    # --- conversions and types ---------------------------------------------
    def ба_рақам(*args: Any) -> Any:
        _arity("ба_рақам", args, 1)
        value = args[0]
        if is_number(value):
            return value
        if isinstance(value, str):
            return ба_рақам_text("ба_рақам", value)
        raise BuiltinError(
            f'Функсияи "ба_рақам" матн мехоҳад, вале {type_name(value)} гирифт.'
        )

    def ба_матн(*args: Any) -> str:
        _arity("ба_матн", args, 1)
        return to_tajik_string(args[0])

    def навъ(*args: Any) -> str:
        _arity("навъ", args, 1)
        return type_name(args[0])

    # --- size, membership, copying -----------------------------------------
    def дарозӣ(*args: Any) -> int:
        _arity("дарозӣ", args, 1)
        value = args[0]
        if isinstance(value, (str, list, dict)):
            return len(value)
        raise BuiltinError(
            f'Функсияи "дарозӣ" матн, рӯйхат ё луғат мехоҳад, вале '
            f"{type_name(value)} гирифт."
        )

    def дорад(*args: Any) -> bool:
        _arity("дорад", args, 2)
        container = args[0]
        if isinstance(container, (dict, list)):
            return args[1] in container
        if isinstance(container, str):
            return isinstance(args[1], str) and args[1] in container
        raise BuiltinError(
            f'Функсияи "дорад" луғат, рӯйхат ё матн мехоҳад, вале '
            f"{type_name(container)} гирифт."
        )

    def нусха(*args: Any) -> Any:
        """Нусхаи мустақил. Бе он «бигзор б = а» ҳамон рӯйхатро нишон медиҳад."""
        _arity("нусха", args, 1)
        value = args[0]
        if isinstance(value, list):
            return list(value)
        if isinstance(value, dict):
            return dict(value)
        return value        # numbers, text and booleans cannot be changed anyway

    def холӣ_аст(*args: Any) -> bool:
        _arity("холӣ_аст", args, 1)
        value = args[0]
        if isinstance(value, (str, list, dict)):
            return len(value) == 0
        raise BuiltinError(
            f'Функсияи "холӣ_аст" матн, рӯйхат ё луғат мехоҳад, вале '
            f"{type_name(value)} гирифт."
        )

    # --- list operations ----------------------------------------------------
    def илова(*args: Any) -> list:
        _arity("илова", args, 2)
        target = _list("илова", args[0])
        target.append(args[1])
        return target

    def дарҷ(*args: Any) -> list:
        """Дар ҷои муайян мегузорад: дарҷ(рӯйхат, 0, қимат)."""
        _arity("дарҷ", args, 3)
        target = _list("дарҷ", args[0])
        target.insert(_position("дарҷ", args[1], len(target), allow_end=True), args[2])
        return target

    def хориҷ(*args: Any) -> Any:
        """Унсурро аз рӯйхат мебарорад ва онро бармегардонад."""
        _arity("хориҷ", args, 2)
        target = _list("хориҷ", args[0])
        if not target:
            raise BuiltinError('Функсияи "хориҷ" рӯйхати холиро қабул намекунад.')
        return target.pop(_position("хориҷ", args[1], len(target)))

    def васеъ(*args: Any) -> list:
        """Ҳамаи унсурҳои рӯйхати дуюмро илова мекунад."""
        _arity("васеъ", args, 2)
        target = _list("васеъ", args[0])
        target.extend(_list("васеъ", args[1]))
        return target

    def холӣ_кун(*args: Any) -> list:
        _arity("холӣ_кун", args, 1)
        target = _list("холӣ_кун", args[0])
        target.clear()
        return target

    def ҷои(*args: Any) -> Any:
        """Рақами тартибии аввалин мувофиқат, ё «холӣ»."""
        _arity("ҷои", args, 2)
        items = _list("ҷои", args[0])
        for index, item in enumerate(items):
            if item == args[1] and type_name(item) == type_name(args[1]):
                return index
        return None

    def шумор(*args: Any) -> int:
        _arity("шумор", args, 2)
        container = args[0]
        if isinstance(container, list):
            return sum(
                1 for item in container
                if item == args[1] and type_name(item) == type_name(args[1])
            )
        if isinstance(container, str):
            return container.count(_text("шумор", args[1]))
        raise BuiltinError(
            f'Функсияи "шумор" рӯйхат ё матн мехоҳад, вале '
            f"{type_name(container)} гирифт."
        )

    def рақамҳо(*args: Any) -> list:
        """рақамҳо(1, 5) -> [1, 2, 3, 4, 5] — ҳарду ҳадд дохил мешаванд."""
        _arity("рақамҳо", args, 1, 2)
        if len(args) == 1:
            start, end = 1, _whole("рақамҳо", args[0])
        else:
            start = _whole("рақамҳо", args[0])
            end = _whole("рақамҳо", args[1])
        step = 1 if end >= start else -1
        return list(range(start, end + step, step))

    # --- ordering and aggregation ------------------------------------------
    def тартиб(*args: Any) -> list:
        _arity("тартиб", args, 1)
        return _ordered("тартиб", _list("тартиб", args[0]))

    def тартиб_бо(*args: Any) -> list:
        """тартиб_бо(рӯйхат, функсия) — функсия калиди ҳар унсурро медиҳад.

        Ин ҳамон чизест, ки барои тартиб додани рӯйхати луғатҳо лозим аст:
        тартиб_бо(донишҷӯён, калиди_ном)
        """
        _arity("тартиб_бо", args, 2)
        items = _list("тартиб_бо", args[0])
        key_fn = args[1]

        if call is None or not callable_value(key_fn):
            raise BuiltinError(
                f'Функсияи "тартиб_бо" ҳамчун аргументи дуюм функсия мехоҳад, '
                f"вале {type_name(key_fn)} гирифт."
            )

        keyed = [(call(key_fn, [item]), index, item) for index, item in enumerate(items)]
        keys = [key for key, _, _ in keyed]
        if all(isinstance(key, str) for key in keys):
            keyed.sort(key=lambda triple: (collation.sort_key(triple[0]), triple[1]))
        elif all(is_number(key) for key in keys):
            keyed.sort(key=lambda triple: (triple[0], triple[1]))
        else:
            raise BuiltinError(
                'Функсияи "тартиб_бо" бояд ҳамеша матн ё ҳамеша рақам диҳад.'
            )
        return [item for _, _, item in keyed]

    def баръакс(*args: Any) -> Any:
        _arity("баръакс", args, 1)
        value = args[0]
        if isinstance(value, list):
            return list(reversed(value))
        if isinstance(value, str):
            return value[::-1]
        raise BuiltinError(
            f'Функсияи "баръакс" рӯйхат ё матн мехоҳад, вале '
            f"{type_name(value)} гирифт."
        )

    def ҷамъи(*args: Any) -> Any:
        _arity("ҷамъи", args, 1)
        total: Any = 0
        for item in _list("ҷамъи", args[0]):
            if not is_number(item):
                raise BuiltinError(
                    f'Функсияи "ҷамъи" рӯйхати рақамҳоро мехоҳад, вале дар он '
                    f"{type_name(item)} ҳаст."
                )
            total = total + item
        return total

    def миёна(*args: Any) -> Any:
        _arity("миёна", args, 1)
        items = _list("миёна", args[0])
        if not items:
            raise BuiltinError(
                'Функсияи "миёна" рӯйхати холиро қабул намекунад.',
                hint="Аввал санҷед: агар дарозӣ(рӯйхат) > 0:",
            )
        return ҷамъи(items) / len(items)

    def калонтарин(*args: Any) -> Any:
        _arity("калонтарин", args, 1)
        items = _list("калонтарин", args[0])
        if not items:
            raise BuiltinError(
                'Функсияи "калонтарин" рӯйхати холиро қабул намекунад.',
                hint="Аввал санҷед: агар дарозӣ(рӯйхат) > 0:",
            )
        return _ordered("калонтарин", items)[-1]

    def хурдтарин(*args: Any) -> Any:
        _arity("хурдтарин", args, 1)
        items = _list("хурдтарин", args[0])
        if not items:
            raise BuiltinError(
                'Функсияи "хурдтарин" рӯйхати холиро қабул намекунад.',
                hint="Аввал санҷед: агар дарозӣ(рӯйхат) > 0:",
            )
        return _ordered("хурдтарин", items)[0]

    def ҳама(*args: Any) -> bool:
        """Оё ҳамаи унсурҳо «рост» ҳастанд?"""
        _arity("ҳама", args, 1)
        return all(_booleans("ҳама", _list("ҳама", args[0])))

    def ягон(*args: Any) -> bool:
        """Оё ҳадди аққал яке «рост» аст?"""
        _arity("ягон", args, 1)
        return any(_booleans("ягон", _list("ягон", args[0])))

    def _booleans(name: str, items: list) -> list[bool]:
        for item in items:
            if not isinstance(item, bool):
                raise BuiltinError(
                    f'Функсияи "{name}" рӯйхати қиматҳои мантиқиро мехоҳад, '
                    f"вале дар он {type_name(item)} ҳаст."
                )
        return items

    # --- dictionary operations ---------------------------------------------
    def калидҳо(*args: Any) -> list:
        _arity("калидҳо", args, 1)
        return list(_dict("калидҳо", args[0]))

    def қиматҳо(*args: Any) -> list:
        _arity("қиматҳо", args, 1)
        return list(_dict("қиматҳо", args[0]).values())

    def ҷуфтҳо(*args: Any) -> list:
        """Ҳар ҷуфт ҳамчун рӯйхати [калид, қимат]."""
        _arity("ҷуфтҳо", args, 1)
        return [[key, value] for key, value in _dict("ҷуфтҳо", args[0]).items()]

    def гирифтан(*args: Any) -> Any:
        """гирифтан(луғат, калид, пешфарз) — бе хато, агар калид набошад."""
        _arity("гирифтан", args, 2, 3)
        mapping = _dict("гирифтан", args[0])
        default = args[2] if len(args) == 3 else None
        return mapping.get(args[1], default)

    def нест_кун(*args: Any) -> Any:
        """Калидро аз луғат мебарорад ва қимати онро бармегардонад."""
        _arity("нест_кун", args, 2)
        mapping = _dict("нест_кун", args[0])
        if args[1] not in mapping:
            raise BuiltinError(
                f"Калиди {to_tajik_string(args[1])} дар луғат нест.",
                hint="Бо функсияи «дорад» санҷед: дорад(луғат, калид)",
            )
        return mapping.pop(args[1])

    core = {
        "навис": навис, "хонед": хонед,
        "ба_рақам": ба_рақам, "ба_матн": ба_матн, "навъ": навъ,
        "дарозӣ": дарозӣ, "дорад": дорад, "нусха": нусха, "холӣ_аст": холӣ_аст,
        "илова": илова, "дарҷ": дарҷ, "хориҷ": хориҷ, "васеъ": васеъ,
        "холӣ_кун": холӣ_кун, "ҷои": ҷои, "шумор": шумор, "рақамҳо": рақамҳо,
        "буриш": _буриш,
        "тартиб": тартиб, "тартиб_бо": тартиб_бо, "баръакс": баръакс,
        "ҷамъи": ҷамъи, "миёна": миёна,
        "калонтарин": калонтарин, "хурдтарин": хурдтарин,
        "ҳама": ҳама, "ягон": ягон,
        "калидҳо": калидҳо, "қиматҳо": қиматҳо, "ҷуфтҳо": ҷуфтҳо,
        "гирифтан": гирифтан, "нест_кун": нест_кун,
    }

    names: dict[str, Builtin] = {
        name: Builtin(name, fn) for name, fn in core.items()
    }

    # Everything in the two modules is a global as well, so a beginner never
    # has to `ворид` anything to write an ordinary program. The modules stay
    # as namespaces over the very same objects.
    for module in (_build_math(), _build_text()):
        for name, value in module.items():
            if isinstance(value, Builtin):
                names.setdefault(name, value)

    return names


def callable_value(value: Any) -> bool:
    """Is this something the interpreter can call?"""
    return callable(value) or type_name(value) == "функсия"


# ---------------------------------------------------------------------------
# built-in module: файл
# ---------------------------------------------------------------------------
def _build_file(interpreter: Any) -> dict[str, Any]:
    base_dir = interpreter.base_dir

    """Reading and writing text files, relative to the program's own folder.

    Not global, unlike everything else: touching the disk should be a visible
    decision, so it costs one `ворид файл`.
    """

    def _resolve(name: str, value: Any) -> Path:
        text = _text(name, value)
        path = Path(text)
        if not path.is_absolute():
            path = base_dir / path
        return path

    def мавҷуд(*args: Any) -> bool:
        _arity("мавҷуд", args, 1)
        return _resolve("мавҷуд", args[0]).exists()

    def хондан(*args: Any) -> str:
        """Тамоми файлро ҳамчун матн мехонад."""
        _arity("хондан", args, 1)
        path = _resolve("хондан", args[0])
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise BuiltinError(
                f'Файли "{args[0]}" ёфт нашуд.',
                hint="Бо «файл.мавҷуд» санҷед: агар файл.мавҷуд(ном):",
            ) from None
        except OSError as error:
            raise BuiltinError(f"Файл хонда нашуд: {error.strerror}.") from None

    def сатрҳо(*args: Any) -> list:
        """Файлро ҳамчун рӯйхати сатрҳо мехонад, бе сатрҳои холии охир."""
        _arity("сатрҳо", args, 1)
        return хондан(args[0]).splitlines()

    def навиштан(*args: Any) -> None:
        """Файлро менависад. Агар файл бошад, мазмуни кӯҳна нест мешавад."""
        _arity("навиштан", args, 2)
        _write(args[0], _text("навиштан", args[1]), append=False)

    def илова_кардан(*args: Any) -> None:
        """Ба охири файл илова мекунад."""
        _arity("илова_кардан", args, 2)
        _write(args[0], _text("илова_кардан", args[1]), append=True)

    def _write(name: Any, text: str, append: bool) -> None:
        path = _resolve("навиштан", name)
        try:
            # newline="" so that "\n" is written as "\n" on every platform.
            # Without it Windows silently turns each one into "\r\n", and a
            # program that writes a file byte by byte gets back something it
            # did not ask for — which is exactly how a self-hosting compiler
            # stops matching its own output.
            with path.open(
                "a" if append else "w", encoding="utf-8", newline=""
            ) as handle:
                handle.write(text)
        except OSError as error:
            raise BuiltinError(
                f"Файл навишта нашуд: {error.strerror}.",
                hint="Шояд ҷузвдон вуҷуд надорад ё иҷозат нест.",
            ) from None

    return {
        name: Builtin(name, fn)
        for name, fn in {
            "мавҷуд": мавҷуд, "хондан": хондан, "сатрҳо": сатрҳо,
            "навиштан": навиштан, "илова_кардан": илова_кардан,
        }.items()
    }


# name -> builder. Each builder takes the importing file's folder, which only
# `файл` actually uses.
def _build_python(interpreter: Any) -> dict[str, Any]:
    from . import interop      # imported here so `питон` costs nothing unused

    return interop.build_module()


def _build_page(interpreter: Any) -> dict[str, Any]:
    from . import page

    return page.build_module(interpreter)


def _build_data(interpreter: Any) -> dict[str, Any]:
    from . import extras

    return extras.build_data()


def _build_http(interpreter: Any) -> dict[str, Any]:
    from . import extras

    return extras.build_http()


# name -> builder. Each builder receives the interpreter, which is how `файл`
# learns the program's folder and `саҳифа` learns how to call a click handler.
BUILTIN_MODULES: dict[str, Callable[[Any], dict[str, Any]]] = {
    "риёзӣ": lambda interpreter: _build_math(),
    "матн": lambda interpreter: _build_text(),
    "файл": _build_file,
    "питон": _build_python,
    "саҳифа": _build_page,
    "маълумот": _build_data,
    "интернет": _build_http,
}
