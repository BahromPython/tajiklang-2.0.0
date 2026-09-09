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

import sys
import threading
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, font as tkfont, messagebox, ttk
except ImportError:  # pragma: no cover - headless machines
    tk = None

from . import __version__, highlight
from .checker import check_program
from .errors import TajikLangError, internal_report
from .interpreter import Interpreter
from .lexer import Lexer
from .parser import Parser

# --- colouring --------------------------------------------------------------
THEME = {
    "bg": "#0b1020",
    "panel": "#111a2d",
    "panel_raised": "#17233a",
    "line": "#263650",
    "ink": "#edf3fb",
    "soft": "#9baac0",
    "keyword": "#86c5ff",
    "builtin": "#d2b6ff",
    "string": "#9be4a8",
    "number": "#ffd084",
    "comment": "#728198",
    "error": "#ff9a9a",
    "warning": "#ffd084",
    "accent": "#3dd6a3",
    "accent_dark": "#123f36",
}


class IDE:
    def __init__(self, root: "tk.Tk", target: Path | None = None) -> None:
        self.root = root
        self.path: Path | None = None
        self.folder = Path.cwd()

        interpreter = Interpreter([], lambda _: None)
        self.builtin_names = set(interpreter.builtins.values)
        self.problems: list[tuple[int, str]] = []

        root.title(f"TajikLang Studio {__version__}")
        root.geometry("1240x800")
        root.minsize(940, 620)
        root.configure(bg=THEME["bg"])
        self._set_window_icon()

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
    def _set_window_icon(self) -> None:
        """A compact TajikLang mark, visible in the taskbar and title bar."""
        icon = tk.PhotoImage(width=64, height=64)
        icon.put("#10213b", to=(0, 0, 64, 64))
        icon.put(THEME["accent"], to=(6, 6, 58, 58))
        icon.put("#dffcf2", to=(16, 15, 48, 23))
        icon.put("#dffcf2", to=(28, 21, 36, 50))
        icon.put("#dffcf2", to=(18, 45, 46, 53))
        self._window_icon = icon  # keep a reference; tkinter otherwise drops it
        self.root.iconphoto(True, icon)

    def _button(self, parent, label: str, command, *, primary: bool = False) -> None:
        background = THEME["accent"] if primary else THEME["panel_raised"]
        foreground = "#06241c" if primary else THEME["ink"]
        active = "#67e7bd" if primary else THEME["line"]
        tk.Button(
            parent, text=label, command=command, font=("Segoe UI", 10, "bold"),
            relief="flat", bg=background, fg=foreground, activebackground=active,
            activeforeground=foreground, padx=13, pady=8, cursor="hand2",
            borderwidth=0, highlightthickness=0,
        ).pack(side="left", padx=(0, 7))

    def _build_layout(self) -> None:
        mono = tkfont.Font(family="Cascadia Code", size=12)
        ui = tkfont.Font(family="Segoe UI", size=10)
        self.mono = mono

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TNotebook", background=THEME["panel"], borderwidth=0)
        style.configure("TNotebook.Tab", background=THEME["panel"], foreground=THEME["soft"],
                        padding=(14, 7), font=("Segoe UI", 9), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", THEME["bg"])],
                  foreground=[("selected", THEME["ink"])])

        # A familiar professional workbench: command bar, activity rail,
        # Explorer, editor tab/breadcrumb, bottom panel and status bar.
        command_bar = tk.Frame(self.root, bg="#101828", height=38)
        command_bar.pack(fill="x")
        command_bar.pack_propagate(False)
        tk.Label(command_bar, text="Т", font=("Segoe UI", 13, "bold"), width=3,
                 bg="#101828", fg=THEME["accent"]).pack(side="left")
        tk.Label(command_bar, text="TajikLang Studio", font=("Segoe UI", 9, "bold"),
                 bg="#101828", fg=THEME["ink"]).pack(side="left", padx=(3, 28))
        search = tk.Entry(command_bar, font=("Segoe UI", 9), relief="flat",
                          bg="#1b2940", fg=THEME["soft"], insertbackground=THEME["ink"])
        search.insert(0, "Ҷустуҷӯ дар лоиҳа")
        search.pack(side="left", fill="x", expand=True, padx=(0, 28), pady=7, ipady=2)
        tk.Label(command_bar, text="◌  ◫  □", font=("Segoe UI", 10), bg="#101828",
                 fg=THEME["soft"]).pack(side="right", padx=14)

        body = tk.Frame(self.root, bg=THEME["line"])
        body.pack(fill="both", expand=True)

        activity = tk.Frame(body, bg="#101828", width=48)
        activity.pack(side="left", fill="y")
        activity.pack_propagate(False)
        for label, command in (("▤", self._refresh_files), ("⌕", self.open_dialog),
                               ("⑂", self.show_packages), ("▷", self.run),
                               ("▧", self.open_blocks)):
            tk.Button(activity, text=label, command=command, font=("Segoe UI Symbol", 18),
                      relief="flat", bg="#101828", fg=THEME["soft"],
                      activebackground="#1b2940", activeforeground=THEME["accent"],
                      borderwidth=0, cursor="hand2", pady=10).pack(fill="x")
        tk.Label(activity, text="⚙", font=("Segoe UI Symbol", 16), bg="#101828",
                 fg=THEME["soft"]).pack(side="bottom", pady=10)

        files_frame = tk.Frame(body, bg=THEME["panel"], width=250)
        files_frame.pack(side="left", fill="y")
        files_frame.pack_propagate(False)
        explorer_header = tk.Frame(files_frame, bg=THEME["panel"])
        explorer_header.pack(fill="x", pady=(10, 4))
        tk.Label(explorer_header, text="ФАЙЛҲО", anchor="w", font=("Segoe UI", 9, "bold"),
                 bg=THEME["panel"], fg=THEME["soft"]).pack(side="left", padx=14)
        tk.Button(explorer_header, text="＋", command=self._new, relief="flat", bg=THEME["panel"],
                  fg=THEME["soft"], activebackground=THEME["line"], borderwidth=0).pack(side="right", padx=8)
        tk.Label(files_frame, text="⌄  ЛОИҲАИ КУШОДА", anchor="w", font=("Segoe UI", 9, "bold"),
                 bg=THEME["panel"], fg=THEME["ink"], pady=7).pack(fill="x", padx=9)
        self.file_list = tk.Listbox(files_frame, borderwidth=0, font=mono, activestyle="none",
                                    background=THEME["panel"], foreground=THEME["ink"],
                                    selectbackground="#214a59", selectforeground=THEME["ink"],
                                    highlightthickness=0)
        self.file_list.pack(fill="both", expand=True)
        self.file_list.bind("<Double-Button-1>", self._open_selected)
        self.file_list.bind("<Return>", self._open_selected)

        # --- editor + panels -------------------------------------------
        left = tk.PanedWindow(body, orient="vertical", bg=THEME["line"], sashwidth=4, borderwidth=0)
        left.pack(side="left", fill="both", expand=True)
        editor_shell = tk.Frame(left, bg=THEME["bg"])
        left.add(editor_shell, stretch="always", height=460)
        tabs = tk.Frame(editor_shell, bg=THEME["panel"], height=36)
        tabs.pack(fill="x")
        tabs.pack_propagate(False)
        tk.Label(tabs, text="  ◆  барномаи нав.tj    ×", font=("Segoe UI", 9),
                 bg=THEME["bg"], fg=THEME["ink"], padx=12, pady=9).pack(side="left")
        actions = tk.Frame(tabs, bg=THEME["panel"])
        actions.pack(side="right", padx=7, pady=4)
        self._button(actions, "▶ Иҷро", self.run, primary=True)
        self._button(actions, "✓ Санҷиш", self.check)
        breadcrumb = tk.Label(editor_shell, text="  ЛОИҲА  ›  мисолҳо  ›  барномаи нав.tj",
                              anchor="w", font=("Segoe UI", 8), bg=THEME["bg"], fg=THEME["soft"], pady=5)
        breadcrumb.pack(fill="x")
        editor_frame = tk.Frame(editor_shell, bg=THEME["bg"])
        editor_frame.pack(fill="both", expand=True)

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

        for name in highlight.KINDS:
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

        status_bar = tk.Frame(self.root, bg="#0d8270", height=23)
        status_bar.pack(fill="x")
        status_bar.pack_propagate(False)
        self.status = tk.Label(status_bar, text="✓ Омода", font=("Segoe UI", 8),
                               bg="#0d8270", fg="#e8fffb", padx=9)
        self.status.pack(side="left")
        tk.Label(status_bar, text="TajikLang   UTF-8   .tj", font=("Segoe UI", 8),
                 bg="#0d8270", fg="#e8fffb", padx=9).pack(side="right")

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
        """Colour the editor using the same rules the website uses."""
        text = self.editor.get("1.0", "end-1c")
        for kind in highlight.KINDS:
            self.editor.tag_remove(kind, "1.0", "end")

        for kind, begin, finish in highlight.spans(text, self.builtin_names):
            self.editor.tag_add(kind, f"1.0+{begin}c", f"1.0+{finish}c")

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
        self.root.title(f"TajikLang Studio — {path.name}")
        self._after_edit()
        self._say(f"Кушода шуд: {path.name}")

    def _new(self) -> None:
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", 'навис("Салом Тоҷикистон!")\n')
        self.path = None
        self.root.title(f"TajikLang Studio — файли нав")
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

    def open_blocks(self) -> None:
        """Open the visual editor without leaving TajikLang's own IDE."""
        from .blocks import start_blocks

        def serve() -> None:
            try:
                start_blocks()
            except OSError:
                self.root.after(0, lambda: self._say("TajikBlocks аллакай кушода аст"))

        threading.Thread(target=serve, daemon=True).start()
        self._say("TajikBlocks кушода мешавад…")

    def preview_website(self) -> None:
        """Build the nearest TajikWeb project and open its localhost preview."""
        from . import web
        from .blocks import start_preview

        def serve() -> None:
            try:
                result = web.build_project(self.folder)
                start_preview(result.output)
            except (web.WebError, OSError) as error:
                self.root.after(0, lambda: self._say(str(error)))

        threading.Thread(target=serve, daemon=True).start()
        self._say("Пешнамоиши сомона кушода мешавад…")

    def show_packages(self) -> None:
        from . import environment, packages

        project = environment.find(self.folder)
        found = packages.installed(project)
        text = "Бастаҳои лоиҳа:\n" if project else "Бастаҳои умумӣ:\n"
        text += "\n".join(f"• {name} {meta.get('нусха', '?')}" for name, meta in found.items())
        self._write(text if found else text + "Ҳоло баста насб нашудааст.")
        self.panels.select(0)

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
        except Exception as error:              # noqa: BLE001 - our bug, not theirs
            self._write(internal_report(error, "муҳаррир"), error=True)
            self._say("Хатои дохилӣ")
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
