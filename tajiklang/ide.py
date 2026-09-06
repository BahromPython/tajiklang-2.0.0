"""Муҳаррир — a small IDE for TajikLang.

    py -m tajiklang.ide            # open on the examples folder
    py -m tajiklang.ide барнома.tj

Built on tkinter, which ships with Python, so a school computer needs nothing
installed beyond Python itself — no pip, no network, no package manager. That
constraint is the whole design: an IDE that cannot be installed is not an IDE.

What it does, in the order a student meets it:

* a file list on the right, and an editor with line numbers and Tajik syntax
  colouring;
* **F5 runs** the file, with the input pane feeding `хонед`;
* **F6 checks** without running, and the problems panel lists everything the
  checker is sure of — click a problem to jump to its line;
* the output panel shows what the program printed, or the error with its
  caret and hint exactly as the terminal would.

The problems panel is the point. Every other beginner editor tells you a
program failed; this one tells you what is wrong before you run it, and puts
the cursor there.
"""

from __future__ import annotations

import re
import sys
import traceback
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, font as tkfont, messagebox, ttk
except ImportError:  # pragma: no cover - headless machines
    tk = None

from . import __version__
from .checker import check_program
from .errors import TajikLangError
from .interpreter import Interpreter
from .lexer import Lexer
from .parser import Parser
from .tokens import KEYWORD_TOKENS

# --- colouring --------------------------------------------------------------
KEYWORDS = sorted(KEYWORD_TOKENS, key=len, reverse=True)

THEME = {
    "bg": "#12171c",
    "panel": "#181f26",
    "line": "#28313a",
    "ink": "#e6ebf0",
    "soft": "#8d9aa8",
    "keyword": "#7cc4ff",
    "builtin": "#c9a0ff",
    "string": "#8ee08e",
    "number": "#f2c078",
    "comment": "#6b7784",
    "error": "#ff8a80",
    "warning": "#f2c078",
    "accent": "#35b48b",
}


class IDE:
    def __init__(self, root: "tk.Tk", target: Path | None = None) -> None:
        self.root = root
        self.path: Path | None = None
        self.folder = Path.cwd()

        interpreter = Interpreter([], lambda _: None)
        self.builtin_names = set(interpreter.builtins.values)
        self.problems: list[tuple[int, str]] = []

        root.title(f"TajikLang {__version__} — Муҳаррир")
        root.geometry("1180x760")
        root.configure(bg=THEME["bg"])

        self._build_layout()
        self._bind_keys()

        if target is not None and target.is_file():
            self.folder = target.parent
            self._open(target)
        else:
            self.folder = target or (Path(__file__).resolve().parent.parent / "examples")
            self._new()
        self._refresh_files()

    # ------------------------------------------------------------------
    # layout
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        mono = tkfont.Font(family="Consolas", size=12)
        ui = tkfont.Font(family="Segoe UI", size=10)
        self.mono = mono

        bar = tk.Frame(self.root, bg=THEME["panel"])
        bar.pack(fill="x")
        for label, command in (
            ("▶  Иҷро (F5)", self.run),
            ("✓  Санҷиш (F6)", self.check),
            ("Нав", self._new),
            ("Кушодан", self.open_dialog),
            ("Нигоҳ доштан (Ctrl+S)", self.save),
        ):
            tk.Button(
                bar, text=label, command=command, font=ui, relief="flat",
                bg=THEME["panel"], fg=THEME["ink"], activebackground=THEME["line"],
                activeforeground=THEME["ink"], padx=12, pady=7, cursor="hand2",
                borderwidth=0,
            ).pack(side="left")

        self.status = tk.Label(
            bar, text="", font=ui, bg=THEME["panel"], fg=THEME["soft"], padx=12
        )
        self.status.pack(side="right")

        body = tk.PanedWindow(
            self.root, orient="horizontal", bg=THEME["line"], sashwidth=4,
            borderwidth=0,
        )
        body.pack(fill="both", expand=True)

        # --- editor + panels -------------------------------------------
        left = tk.PanedWindow(
            body, orient="vertical", bg=THEME["line"], sashwidth=4, borderwidth=0
        )
        body.add(left, stretch="always", width=860)

        editor_frame = tk.Frame(left, bg=THEME["bg"])
        left.add(editor_frame, stretch="always", height=460)

        self.gutter = tk.Text(
            editor_frame, width=5, padx=8, takefocus=0, borderwidth=0,
            background=THEME["panel"], foreground=THEME["soft"], font=mono,
            state="disabled", cursor="arrow",
        )
        self.gutter.pack(side="left", fill="y")

        self.editor = tk.Text(
            editor_frame, wrap="none", undo=True, borderwidth=0, font=mono,
            background=THEME["bg"], foreground=THEME["ink"],
            insertbackground=THEME["accent"], selectbackground=THEME["line"],
            tabs=(mono.measure(" " * 4),),
        )
        self.editor.pack(side="left", fill="both", expand=True)

        scroll = tk.Scrollbar(editor_frame, command=self._scroll_both)
        scroll.pack(side="right", fill="y")
        self.editor.configure(yscrollcommand=self._on_scroll)
        self._scrollbar = scroll

        for name in ("keyword", "builtin", "string", "number", "comment"):
            self.editor.tag_configure(name, foreground=THEME[name])
        self.editor.tag_configure("problem", background="#3a2226")

        panels = ttk.Notebook(left)
        left.add(panels, height=250)

        self.output = self._make_text(panels, THEME["ink"])
        panels.add(self.output.master, text="  Натиҷа  ")

        self.stdin = self._make_text(panels, THEME["ink"], editable=True)
        panels.add(self.stdin.master, text="  Маълумоти воридотӣ  ")

        problems_frame = tk.Frame(panels, bg=THEME["panel"])
        self.problem_list = tk.Listbox(
            problems_frame, borderwidth=0, font=mono, activestyle="none",
            background=THEME["panel"], foreground=THEME["ink"],
            selectbackground=THEME["line"], selectforeground=THEME["ink"],
            highlightthickness=0,
        )
        self.problem_list.pack(fill="both", expand=True)
        self.problem_list.bind("<<ListboxSelect>>", self._goto_problem)
        panels.add(problems_frame, text="  Хатоҳо  ")
        self.panels = panels
        self.problems_tab = 2

        # --- file list --------------------------------------------------
        files_frame = tk.Frame(body, bg=THEME["panel"])
        body.add(files_frame, width=250)

        tk.Label(
            files_frame, text="  Файлҳо", anchor="w", font=("Segoe UI", 10, "bold"),
            bg=THEME["panel"], fg=THEME["soft"], pady=8,
        ).pack(fill="x")

        self.file_list = tk.Listbox(
            files_frame, borderwidth=0, font=mono, activestyle="none",
            background=THEME["panel"], foreground=THEME["ink"],
            selectbackground=THEME["line"], selectforeground=THEME["ink"],
            highlightthickness=0,
        )
        self.file_list.pack(fill="both", expand=True)
        self.file_list.bind("<Double-Button-1>", self._open_selected)
        self.file_list.bind("<Return>", self._open_selected)

    def _make_text(self, parent, colour: str, editable: bool = False) -> "tk.Text":
        frame = tk.Frame(parent, bg=THEME["bg"])
        widget = tk.Text(
            frame, wrap="word", borderwidth=0, font=self.mono,
            background=THEME["bg"], foreground=colour,
            insertbackground=THEME["accent"], highlightthickness=0,
        )
        widget.pack(fill="both", expand=True, padx=10, pady=8)
        if not editable:
            widget.configure(state="disabled")
        widget.tag_configure("error", foreground=THEME["error"])
        return widget

    def _bind_keys(self) -> None:
        self.root.bind("<F5>", lambda _e: self.run())
        self.root.bind("<F6>", lambda _e: self.check())
        self.root.bind("<Control-s>", lambda _e: self.save())
        self.root.bind("<Control-o>", lambda _e: self.open_dialog())
        self.root.bind("<Control-n>", lambda _e: self._new())
        self.editor.bind("<KeyRelease>", lambda _e: self._after_edit())
        self.editor.bind("<Return>", self._auto_indent)

    # ------------------------------------------------------------------
    # editing
    # ------------------------------------------------------------------
    def _scroll_both(self, *args) -> None:
        self.editor.yview(*args)
        self.gutter.yview(*args)

    def _on_scroll(self, first: str, last: str) -> None:
        self._scrollbar.set(first, last)
        self.gutter.yview_moveto(first)

    def _auto_indent(self, _event) -> str:
        """A line ending in ':' opens a block, so indent the next one for them."""
        line = self.editor.get("insert linestart", "insert")
        indent = len(line) - len(line.lstrip(" "))
        if line.rstrip().endswith(":"):
            indent += 4
        self.editor.insert("insert", "\n" + " " * indent)
        self._after_edit()
        return "break"

    def _after_edit(self) -> None:
        self._highlight()
        self._numbers()

    def _numbers(self) -> None:
        count = int(self.editor.index("end-1c").split(".")[0])
        self.gutter.configure(state="normal")
        self.gutter.delete("1.0", "end")
        self.gutter.insert("1.0", "\n".join(f"{n:>4}" for n in range(1, count + 1)))
        self.gutter.configure(state="disabled")
        self.gutter.yview_moveto(self.editor.yview()[0])

    def _highlight(self) -> None:
        text = self.editor.get("1.0", "end-1c")
        for tag in ("keyword", "builtin", "string", "number", "comment"):
            self.editor.tag_remove(tag, "1.0", "end")

        # Comments and strings win over everything inside them, so they are
        # matched first and their spans skipped by the later passes.
        taken: list[tuple[int, int]] = []

        for match in re.finditer(r"#[^\n]*", text):
            self._tag("comment", match)
            taken.append(match.span())
        for match in re.finditer(r'"(?:[^"\\\n]|\\.)*"', text):
            if any(a <= match.start() < b for a, b in taken):
                continue
            self._tag("string", match)
            taken.append(match.span())

        def free(match: re.Match) -> bool:
            return not any(a <= match.start() < b for a, b in taken)

        word = r"(?<![^\W\d_])({})(?![^\W\d_])"
        for match in re.finditer(word.format("|".join(KEYWORDS)), text):
            if free(match):
                self._tag("keyword", match)
        for match in re.finditer(
            r"(?<![^\W\d_])([^\W\d_][\w_]*)(?=\s*\()", text
        ):
            if free(match) and match.group(1) in self.builtin_names:
                self._tag("builtin", match)
        for match in re.finditer(r"(?<![\w.])\d+(\.\d+)?", text):
            if free(match):
                self._tag("number", match)

    def _tag(self, name: str, match: re.Match) -> None:
        start = f"1.0+{match.start()}c"
        end = f"1.0+{match.end()}c"
        self.editor.tag_add(name, start, end)

    # ------------------------------------------------------------------
    # files
    # ------------------------------------------------------------------
    def _refresh_files(self) -> None:
        self.file_list.delete(0, "end")
        self.files = sorted(self.folder.glob("*.tj")) if self.folder.is_dir() else []
        for path in self.files:
            self.file_list.insert("end", "  " + path.name)

    def _open_selected(self, _event=None) -> None:
        selection = self.file_list.curselection()
        if selection:
            self._open(self.files[selection[0]])

    def _open(self, path: Path) -> None:
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", path.read_text(encoding="utf-8"))
        self.path = path
        self.folder = path.parent
        self.root.title(f"TajikLang {__version__} — {path.name}")
        self._after_edit()
        self._say(f"Кушода шуд: {path.name}")

    def _new(self) -> None:
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", 'навис("Салом Тоҷикистон!")\n')
        self.path = None
        self.root.title(f"TajikLang {__version__} — файли нав")
        self._after_edit()

    def open_dialog(self) -> None:
        name = filedialog.askopenfilename(
            filetypes=[("Барномаи TajikLang", "*.tj"), ("Ҳама файлҳо", "*.*")]
        )
        if name:
            self._open(Path(name))
            self._refresh_files()

    def save(self) -> bool:
        if self.path is None:
            name = filedialog.asksaveasfilename(
                defaultextension=".tj",
                filetypes=[("Барномаи TajikLang", "*.tj")],
            )
            if not name:
                return False
            self.path = Path(name)
            self.folder = self.path.parent

        self.path.write_text(self.editor.get("1.0", "end-1c"), encoding="utf-8")
        self.root.title(f"TajikLang {__version__} — {self.path.name}")
        self._refresh_files()
        self._say(f"Нигоҳ дошта шуд: {self.path.name}")
        return True

    # ------------------------------------------------------------------
    # running
    # ------------------------------------------------------------------
    def _say(self, message: str) -> None:
        self.status.configure(text=message)

    def _write(self, text: str, error: bool = False) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text, ("error",) if error else ())
        self.output.configure(state="disabled")

    def _analyse(self) -> tuple[object | None, list, list[str]]:
        """Lex, parse and check. Returns (program, diagnostics, source lines)."""
        source = self.editor.get("1.0", "end-1c")
        lexer = Lexer(source, str(self.path or "<муҳаррир>"))
        program = Parser(lexer.tokenize(), lexer.lines).parse()
        return program, check_program(program, self.builtin_names), lexer.lines

    def check(self) -> bool:
        """F6 — report every problem without running anything."""
        self.problem_list.delete(0, "end")
        self.problems = []
        self.editor.tag_remove("problem", "1.0", "end")

        try:
            _program, found, lines = self._analyse()
        except TajikLangError as error:
            self._show_single_problem(error)
            return False

        if not found:
            self.problem_list.insert("end", "  Тоза — хато ёфт нашуд.")
            self._say("Тоза")
            return True

        errors = 0
        for diagnostic in found:
            mark = "✕" if not diagnostic.is_warning else "!"
            errors += 0 if diagnostic.is_warning else 1
            self.problem_list.insert(
                "end", f"  {mark} сатри {diagnostic.line}: {diagnostic.message}"
            )
            self.problems.append((diagnostic.line, diagnostic.message))
            self.editor.tag_add(
                "problem", f"{diagnostic.line}.0", f"{diagnostic.line}.end"
            )

        self.panels.select(self.problems_tab)
        self._say(f"{errors} хато, {len(found) - errors} огоҳӣ")
        return errors == 0

    def _show_single_problem(self, error: TajikLangError) -> None:
        self.problem_list.insert(
            "end", f"  ✕ сатри {error.line}: {error.message}"
        )
        self.problems = [(error.line, error.message)]
        self.editor.tag_add("problem", f"{error.line}.0", f"{error.line}.end")
        self.panels.select(self.problems_tab)
        self._write(error.format(), error=True)
        self._say("1 хато")

    def _goto_problem(self, _event) -> None:
        selection = self.problem_list.curselection()
        if not selection or selection[0] >= len(self.problems):
            return
        line = self.problems[selection[0]][0]
        self.editor.mark_set("insert", f"{line}.0")
        self.editor.see(f"{line}.0")
        self.editor.focus_set()

    def run(self) -> None:
        """F5 — check, then run, with the input pane feeding `хонед`."""
        if not self.check():
            self._write(
                "Барнома иҷро нашуд — аввал хатоҳоро дар панели «Хатоҳо» "
                "ислоҳ кунед.",
                error=True,
            )
            return

        lines: list[str] = []
        supplied = iter(
            [line for line in self.stdin.get("1.0", "end-1c").split("\n")]
        )

        try:
            program, _found, source_lines = self._analyse()
            interpreter = Interpreter(
                source_lines,
                lines.append,
                base_dir=self.folder,
                read_line=lambda _prompt: next(supplied, None),
            )
            interpreter.run(program)
            self._write("\n".join(lines) or "(бе натиҷа)")
            self._say("Иҷро шуд")
        except TajikLangError as error:
            self._write("\n".join(lines + ["", error.format()]), error=True)
            self._say("Хатои иҷро")
        except RecursionError:
            self._write("Рекурсия аз ҳад чуқур шуд.", error=True)
        except Exception:                       # noqa: BLE001 - show, never hide
            self._write(traceback.format_exc(), error=True)
        finally:
            self.panels.select(0)


def main(argv: list[str] | None = None) -> int:
    if tk is None:
        print(
            "Муҳаррир кор намекунад: tkinter насб нашудааст.\n"
            "Дар Linux: sudo apt install python3-tk",
            file=sys.stderr,
        )
        return 1

    args = list(sys.argv[1:] if argv is None else argv)
    target = Path(args[0]) if args else None

    root = tk.Tk()
    IDE(root, target)
    root.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
