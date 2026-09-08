"""Useful standard modules that keep their public vocabulary in Tajik."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Any

from .errors import BuiltinError
from .values import Builtin, to_tajik_string, type_name


def build_data() -> dict[str, Any]:
    def ба_json(*args: Any) -> str:
        if len(args) != 1:
            raise BuiltinError('Функсияи "маълумот.ба_json" 1 аргумент мехоҳад.')
        try:
            return json.dumps(args[0], ensure_ascii=False, default=to_tajik_string)
        except (TypeError, ValueError) as error:
            raise BuiltinError(f"Қимат ба JSON табдил нашуд: {error}.") from None

    def аз_json(*args: Any) -> Any:
        if len(args) != 1 or not isinstance(args[0], str):
            raise BuiltinError('Функсияи "маълумот.аз_json" як матни JSON мехоҳад.')
        try:
            return json.loads(args[0], parse_float=Decimal)
        except json.JSONDecodeError as error:
            raise BuiltinError(
                f"JSON дуруст нест: сатри {error.lineno}, сутуни {error.colno}.",
                hint="Матн бояд бо {, [, нохунак ва вергулҳои дуруст бошад.",
            ) from None

    return {"ба_json": Builtin("ба_json", ба_json), "аз_json": Builtin("аз_json", аз_json)}


def build_http() -> dict[str, Any]:
    def хондан(*args: Any) -> str:
        if len(args) != 1 or not isinstance(args[0], str):
            raise BuiltinError('Функсияи "интернет.хондан" як суроғаи матнӣ мехоҳад.')
        if not args[0].startswith(("https://", "http://")):
            raise BuiltinError("Суроға бояд бо https:// ё http:// оғоз шавад.")
        try:
            with urllib.request.urlopen(args[0], timeout=15) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, OSError, UnicodeDecodeError) as error:
            raise BuiltinError(
                f"Суроға хонда нашуд: {error}.",
                hint="Интернет ва суроғаро санҷед.",
            ) from None

    return {"хондан": Builtin("хондан", хондан)}
