"""Саҳифа — building web pages from TajikLang.

The idea that makes this small instead of enormous: an HTML page is a **tree**,
and TajikLang already has trees. So `саҳифа` does not invent a markup syntax,
a template language, or a compiler to JavaScript. It builds a tree of values:

    ворид саҳифа

    саҳифа.нависед(
        саҳифа.сарлавҳа("Журнали синфи 10"),
        саҳифа.ҷадвал(сатрҳо, ["Ном", "Баҳо"]),
        саҳифа.тугма("Аз нав ҳисоб кун", ҳисоб_кун),
    )

Because the tree is plain data, the *same program* has two destinations:

* in a browser (the playground) it becomes real DOM, with `тугма` handlers
  wired to ordinary TajikLang functions;
* in the terminal `саҳифа.ҳамчун_матн(...)` returns the HTML as text, which
  `файл.навиштан` saves — so a student can generate a real web page from the
  command line with no browser at all.

Styling is a dictionary, with Tajik names for the properties a beginner
actually reaches for. Unknown names pass through untouched, so anyone who
knows CSS is not fenced in.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .errors import BuiltinError
from .values import Builtin, to_tajik_string, type_name

# Tajik name -> CSS property. Anything not listed passes through as written,
# so knowing CSS is a bonus rather than a requirement.
STYLE_NAMES = {
    "ранг": "color",
    "замина": "background",
    "андоза": "font-size",
    "фосила": "padding",
    "ҳошия": "margin",
    "васеъӣ": "width",
    "баландӣ": "height",
    "канор": "border",
    "гӯшаҳо": "border-radius",
    "ҳарф": "font-family",
    "ғафсӣ": "font-weight",
    "ҷойгиршавӣ": "text-align",
}

# Properties whose bare numbers mean pixels.
PIXEL_PROPERTIES = {
    "font-size", "padding", "margin", "width", "height", "border-radius",
}

VOID_TAGS = {"img", "input", "br", "hr"}


def escape(text: str) -> str:
    """Text going into HTML. Without this a program could inject markup."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class Element:
    """One node of the page. Plain data — no browser needed to build it."""

    def __init__(
        self,
        tag: str,
        text: str | None = None,
        children: list["Element"] | None = None,
        attributes: dict[str, str] | None = None,
        style: dict[str, str] | None = None,
        handler: Any = None,
    ) -> None:
        self.tag = tag
        self.text = text
        self.children = children or []
        self.attributes = attributes or {}
        self.style = style or {}
        self.handler = handler

    def __repr__(self) -> str:
        return f"<унсури {self.tag}>"

    # ------------------------------------------------------------------
    def style_text(self) -> str:
        return "; ".join(f"{name}: {value}" for name, value in self.style.items())

    def to_html(self, indent: int = 0, interactive: bool = False) -> str:
        pad = "  " * indent
        attributes = dict(self.attributes)
        if not interactive:
            # A static site must stay a normal HTML file.  TajikWeb App adds
            # this private attribute only while a live interpreter exists.
            attributes.pop("data-tajik-action", None)
        if self.style:
            attributes["style"] = self.style_text()

        rendered = "".join(
            f' {name}="{escape(str(value))}"' for name, value in attributes.items()
        )

        if self.tag in VOID_TAGS:
            return f"{pad}<{self.tag}{rendered}>"

        inner = escape(self.text) if self.text is not None else ""
        if not self.children:
            return f"{pad}<{self.tag}{rendered}>{inner}</{self.tag}>"

        lines = [f"{pad}<{self.tag}{rendered}>"]
        if inner:
            lines.append("  " * (indent + 1) + inner)
        for child in self.children:
            lines.append(child.to_html(indent + 1, interactive))
        lines.append(f"{pad}</{self.tag}>")
        return chr(10).join(lines)


DOCUMENT = """<!doctype html>
<html lang="tg">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ margin: 0; padding: 24px; font: 16px/1.6 system-ui, sans-serif;
         color: #16191d; background: #fbfbfc; }}
  h1, h2, h3 {{ line-height: 1.25; }}
  table {{ border-collapse: collapse; margin: 12px 0; }}
  th, td {{ border: 1px solid #dfe3e8; padding: 6px 12px; text-align: right; }}
  th {{ background: #f2f4f6; }}
  button {{ font: inherit; padding: 8px 16px; border-radius: 8px;
            border: 1px solid #cdd3d9; background: #fff; cursor: pointer; }}
  input {{ font: inherit; padding: 8px 10px; border-radius: 8px;
           border: 1px solid #cdd3d9; }}
  ul {{ padding-right: 20px; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def _text_of(value: Any) -> str:
    return to_tajik_string(value)


def _elements(name: str, values: tuple[Any, ...]) -> list[Element]:
    """Arguments that should each be an element — with plain text allowed."""
    result: list[Element] = []
    for value in values:
        if isinstance(value, Element):
            result.append(value)
        elif isinstance(value, (str, int, Decimal)) or value is None:
            result.append(Element("p", text=_text_of(value)))
        elif isinstance(value, list):
            result.extend(_elements(name, tuple(value)))
        else:
            raise BuiltinError(
                f'Функсияи "саҳифа.{name}" унсур ё матн мехоҳад, вале '
                f"{type_name(value)} гирифт.",
                hint="Унсурҳоро бо саҳифа.сарлавҳа, саҳифа.матн ва ғайра созед.",
            )
    return result


def _style(name: str, value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise BuiltinError(
            f'Услуби "саҳифа.{name}" бояд луғат бошад, вале '
            f"{type_name(value)} аст.",
            hint='Масалан: {"ранг": "кабуд", "андоза": 20}',
        )

    style: dict[str, str] = {}
    for key, raw in value.items():
        if not isinstance(key, str):
            raise BuiltinError("Номи услуб бояд матн бошад.")
        css = STYLE_NAMES.get(key, key)
        if isinstance(raw, (int, Decimal)) and not isinstance(raw, bool):
            style[css] = f"{to_tajik_string(raw)}px" if css in PIXEL_PROPERTIES \
                else to_tajik_string(raw)
        else:
            style[css] = to_tajik_string(raw)
    return style


def build_module(interpreter: Any) -> dict[str, Any]:
    """The `саҳифа` module. `interpreter` is needed to call click handlers."""

    # What `нависед` produced, kept so the terminal can print or save it.
    written: list[Element] = []
    # TajikWeb App keeps the interpreter alive and calls these ordinary
    # TajikLang functions when a browser presses a button.
    actions: dict[str, Any] = {}
    action_number = 0

    # --- building blocks ---------------------------------------------------
    def сарлавҳа(*args: Any) -> Element:
        if not 1 <= len(args) <= 3:
            raise BuiltinError('Функсияи "саҳифа.сарлавҳа" 1-3 аргумент мехоҳад.')
        level = 1
        style = None
        if len(args) >= 2 and isinstance(args[1], (int, Decimal)):
            level = max(1, min(3, int(args[1])))
            style = args[2] if len(args) == 3 else None
        elif len(args) >= 2:
            style = args[1]
        return Element(
            f"h{level}", text=_text_of(args[0]), style=_style("сарлавҳа", style)
        )

    def матн(*args: Any) -> Element:
        if not args:
            raise BuiltinError('Функсияи "саҳифа.матн" ҳадди аққал 1 аргумент мехоҳад.')
        style = None
        values = args
        if isinstance(args[-1], dict):
            values, style = args[:-1], args[-1]
        return Element(
            "p",
            text=" ".join(_text_of(v) for v in values),
            style=_style("матн", style),
        )

    def қуттӣ(*args: Any) -> Element:
        """Унсурҳоро зери ҳам мегузорад."""
        values, style = _split_style(args)
        return Element("div", children=_elements("қуттӣ", values),
                       style=_style("қуттӣ", style))

    def қатор(*args: Any) -> Element:
        """Унсурҳоро паҳлӯи ҳам мегузорад."""
        values, style = _split_style(args)
        base = {"display": "flex", "gap": "12px", "align-items": "center"}
        base.update(_style("қатор", style))
        return Element("div", children=_elements("қатор", values), style=base)

    def _split_style(args: tuple[Any, ...]) -> tuple[tuple[Any, ...], Any]:
        if args and isinstance(args[-1], dict):
            return args[:-1], args[-1]
        return args, None

    def рӯйхат(*args: Any) -> Element:
        if not 1 <= len(args) <= 2:
            raise BuiltinError('Функсияи "саҳифа.рӯйхат" 1 ё 2 аргумент мехоҳад.')
        items = args[0]
        if not isinstance(items, list):
            raise BuiltinError(
                f'Функсияи "саҳифа.рӯйхат" рӯйхат мехоҳад, вале '
                f"{type_name(items)} гирифт."
            )
        children = [Element("li", text=_text_of(item)) for item in items]
        style = args[1] if len(args) == 2 else None
        return Element("ul", children=children, style=_style("рӯйхат", style))

    def ҷадвал(*args: Any) -> Element:
        """ҷадвал(сатрҳо, [сарлавҳаҳо]) — сатрҳо рӯйхати рӯйхатҳо ё луғатҳо."""
        if not 1 <= len(args) <= 2:
            raise BuiltinError('Функсияи "саҳифа.ҷадвал" 1 ё 2 аргумент мехоҳад.')
        rows = args[0]
        if not isinstance(rows, list):
            raise BuiltinError(
                f'Функсияи "саҳифа.ҷадвал" рӯйхат мехоҳад, вале '
                f"{type_name(rows)} гирифт."
            )
        headers = args[1] if len(args) == 2 else None

        # a list of dictionaries: the headers name the columns to take
        if rows and isinstance(rows[0], dict):
            if headers is None:
                headers = list(rows[0])
            body = [[row.get(column) for column in headers] for row in rows]
        else:
            body = [row if isinstance(row, list) else [row] for row in rows]

        children: list[Element] = []
        if headers:
            children.append(
                Element("tr", children=[
                    Element("th", text=_text_of(h)) for h in headers
                ])
            )
        for row in body:
            children.append(
                Element("tr", children=[
                    Element("td", text=_text_of(cell)) for cell in row
                ])
            )
        return Element("table", children=children)

    def тугма(*args: Any) -> Element:
        """тугма(матн, функсия) — функсия ҳангоми пахш даъват мешавад."""
        if not 2 <= len(args) <= 3:
            raise BuiltinError('Функсияи "саҳифа.тугма" 2 ё 3 аргумент мехоҳад.')
        handler = args[1]
        if not callable(handler) and type_name(handler) != "функсия":
            raise BuiltinError(
                f'Функсияи "саҳифа.тугма" ҳамчун аргументи дуюм функсия '
                f"мехоҳад, вале {type_name(handler)} гирифт.",
                hint="Аввал функсия эълон кунед, баъд номи онро диҳед.",
            )
        style = args[2] if len(args) == 3 else None
        nonlocal action_number
        action_number += 1
        action_name = f"амал_{action_number}"
        actions[action_name] = handler
        interpreter.page_actions = actions
        return Element(
            "button", text=_text_of(args[0]), handler=handler,
            attributes={"data-tajik-action": action_name},
            style=_style("тугма", style),
        )

    def майдон(*args: Any) -> Element:
        """майдон(ном, [пешфарз]) — ҷои воридкунии матн."""
        if not 1 <= len(args) <= 2:
            raise BuiltinError('Функсияи "саҳифа.майдон" 1 ё 2 аргумент мехоҳад.')
        name = _text_of(args[0])
        attributes = {"data-ном": name}
        if len(args) == 2:
            attributes["value"] = _text_of(args[1])
        return Element("input", attributes=attributes)

    def расм(*args: Any) -> Element:
        if not 1 <= len(args) <= 2:
            raise BuiltinError('Функсияи "саҳифа.расм" 1 ё 2 аргумент мехоҳад.')
        attributes = {"src": _text_of(args[0])}
        attributes["alt"] = _text_of(args[1]) if len(args) == 2 else ""
        return Element("img", attributes=attributes)

    def услуб(*args: Any) -> Element:
        """Ба унсури тайёр услуб илова мекунад."""
        if len(args) != 2 or not isinstance(args[0], Element):
            raise BuiltinError(
                'Функсияи "саҳифа.услуб" унсур ва луғати услуб мехоҳад.',
                hint='Масалан: саҳифа.услуб(сарлавҳа, {"ранг": "кабуд"})',
            )
        element = args[0]
        element.style.update(_style("услуб", args[1]))
        return element

    # --- destinations ------------------------------------------------------
    def _as_html(elements: list[Element], interactive: bool = False) -> str:
        body = chr(10).join(element.to_html(0, interactive) for element in elements)
        title = "TajikLang"
        for element in elements:
            if element.tag.startswith("h") and element.text:
                title = element.text
                break
        return DOCUMENT.format(title=escape(title), body=body)

    def ҳамчун_матн(*args: Any) -> str:
        """Саҳифаро ҳамчун матни HTML бармегардонад."""
        elements = _elements("ҳамчун_матн", args) if args else list(written)
        return _as_html(elements)

    # A deliberately private bridge for TajikWeb App.  It is set on the
    # interpreter, not exposed as a new English-looking language feature.
    interpreter.page_html = lambda: _as_html(list(written), interactive=True)

    def нависед(*args: Any) -> None:
        """Унсурҳоро ба саҳифа мегузорад (дар браузер) ё нигоҳ медорад."""
        elements = _elements("нависед", args)
        written.extend(elements)
        _render(elements)

    def тоза_кун(*args: Any) -> None:
        written.clear()
        target = _target(required=False)
        if target is not None:
            target.innerHTML = ""

    def қимат(*args: Any) -> str:
        """Он чи корбар ба майдон навиштааст."""
        if len(args) != 1:
            raise BuiltinError('Функсияи "саҳифа.қимат" 1 аргумент мехоҳад.')
        document = _document(
            'Функсияи "саҳифа.қимат" танҳо дар браузер кор мекунад.'
        )
        name = _text_of(args[0])
        found = document.querySelector('[data-ном="' + name + '"]')
        if found is None:
            raise BuiltinError(
                f'Майдони "{name}" дар саҳифа нест.',
                hint="Аввал онро созед: саҳифа.майдон(«ном»)",
            )
        return str(found.value)

    # --- browser plumbing --------------------------------------------------
    def _document(message: str) -> Any:
        try:
            from js import document          # type: ignore
        except ImportError:
            raise BuiltinError(
                message,
                hint="Дар терминал «саҳифа.ҳамчун_матн» -ро истифода баред ва "
                "натиҷаро бо «файл.навиштан» нигоҳ доред.",
            ) from None
        return document

    def _target(required: bool = True) -> Any:
        try:
            from js import document          # type: ignore
        except ImportError:
            if required:
                raise BuiltinError(
                    'Функсияи "саҳифа.нависед" танҳо дар браузер кор мекунад.',
                    hint="Дар терминал «саҳифа.ҳамчун_матн» -ро истифода баред.",
                ) from None
            return None
        return document.getElementById("tajik-page") or document.body

    def _render(elements: list[Element]) -> None:
        target = _target(required=False)
        if target is None:
            return                      # terminal: kept for ҳамчун_матн
        for element in elements:
            target.appendChild(_to_dom(element))

    def _to_dom(element: Element) -> Any:
        from js import document           # type: ignore

        node = document.createElement(element.tag)
        for name, value in element.attributes.items():
            node.setAttribute(name, str(value))
        if element.style:
            node.setAttribute("style", element.style_text())
        if element.text is not None:
            node.textContent = element.text
        for child in element.children:
            node.appendChild(_to_dom(child))

        if element.handler is not None:
            from pyodide.ffi import create_proxy    # type: ignore

            handler = element.handler

            def clicked(_event: Any) -> None:
                interpreter.call_from_host(handler, [])

            node.addEventListener("click", create_proxy(clicked))

        return node

    names = {
        "сарлавҳа": сарлавҳа, "матн": матн, "қуттӣ": қуттӣ, "қатор": қатор,
        "рӯйхат": рӯйхат, "ҷадвал": ҷадвал, "тугма": тугма, "майдон": майдон,
        "расм": расм, "услуб": услуб,
        "нависед": нависед, "ҳамчун_матн": ҳамчун_матн, "тоза_кун": тоза_кун,
        "қимат": қимат,
    }
    return {name: Builtin(name, fn) for name, fn in names.items()}
