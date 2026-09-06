"""Майдончаро месозад — builds the single-file browser playground.

    py tools/build_playground.py

Reads every module in `tajiklang/` and every `.tj` in `examples/`, embeds them
into `playground/index.html`, and writes it out. The result is ONE file that
needs no Python installed, no server and no build step to open — it runs the
real interpreter in the browser through Pyodide (CPython compiled to
WebAssembly).

Rebuild it whenever the interpreter changes; the HTML is generated, not
hand-edited.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "tajiklang"
EXAMPLES = ROOT / "examples"
OUTPUT = ROOT / "playground" / "index.html"

# Pyodide release used by the playground. Pinned on purpose: an unpinned CDN
# version means a browser that worked yesterday can break tomorrow.
PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/"

# Modules the CLI needs but the browser does not.
SKIP = {"cli.py", "__main__.py"}

# Examples worth putting in the dropdown, in teaching order.
EXAMPLE_ORDER = [
    ("salom.tj", "1. Салом Тоҷикистон"),
    ("тағйирёбанда.tj", "2. Тағйирёбандаҳо"),
    ("муқоиса.tj", "3. Муқоиса ва мантиқ"),
    ("шарт.tj", "4. Шартҳо"),
    ("давр.tj", "5. Даврҳо"),
    ("функсия.tj", "6. Функсияҳо"),
    ("рӯйхат.tj", "7. Рӯйхат ва луғат"),
    ("матн_кор.tj", "8. Кор бо матн"),
    ("саволнома.tj", "9. Саволнома (хонед)"),
    ("санҷиш.tj", "10. Санҷиш (шикан, кӯшиш)"),
    ("журнал.tj", "11. Журнали баҳоҳо"),
    ("саҳифа_демо.tj", "12. Саҳифаи интернетӣ"),
    ("қолиб.tj", "13. Қолибҳо (синфҳо)"),
    ("чаро_ва_қувват.tj", "14. чаро, |> ва хатоҳо"),
]

# Answers pre-loaded for examples that ask questions, so the very first run
# works even where a prompt dialog is blocked.
EXAMPLE_INPUT = {
    "саволнома.tj": "Баҳром" + chr(10) + "16",
}

# A loop cap low enough that a runaway program cannot lock up a phone. The
# interpreter's own limit is a million, which is fine on a laptop and far too
# slow inside WebAssembly.
BROWSER_MAX_ITERATIONS = 200_000

TEMPLATE = """<!doctype html>
<html lang="tg">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TajikLang — Майдончаи озмоишӣ</title>
<style>
  :root {{
    --ink: #101418;
    --muted: #5b6672;
    --line: #dfe4ea;
    --bg: #f7f8fa;
    --panel: #ffffff;
    --accent: #0f7b5f;
    --accent-ink: #ffffff;
    --error: #b3261e;
    --code: ui-monospace, "Cascadia Code", "Segoe UI Mono", Consolas, monospace;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --ink: #e8ecef; --muted: #9aa5b1; --line: #2b323a;
      --bg: #14181c; --panel: #1b2026; --accent: #2fa37c; --accent-ink: #06120d;
      --error: #ff8a80;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--ink);
    font: 15px/1.5 system-ui, "Segoe UI", Roboto, sans-serif;
  }}
  header {{
    padding: 18px 20px; border-bottom: 1px solid var(--line);
    background: var(--panel);
    display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
  }}
  h1 {{ font-size: 18px; margin: 0; font-weight: 650; letter-spacing: -0.01em; }}
  h1 span {{ color: var(--muted); font-weight: 400; }}
  .spacer {{ flex: 1 1 auto; }}
  select, button {{
    font: inherit; padding: 8px 14px; border-radius: 8px;
    border: 1px solid var(--line); background: var(--panel); color: var(--ink);
  }}
  button.run {{
    background: var(--accent); color: var(--accent-ink);
    border-color: transparent; font-weight: 600; cursor: pointer;
  }}
  button.run:disabled {{ opacity: .55; cursor: progress; }}
  main {{
    display: grid; gap: 14px; padding: 16px 20px 28px;
    grid-template-columns: 1fr 1fr; max-width: 1200px; margin: 0 auto;
  }}
  @media (max-width: 820px) {{ main {{ grid-template-columns: 1fr; }} }}
  section {{ display: flex; flex-direction: column; min-height: 0; }}
  label {{
    font-size: 12px; text-transform: uppercase; letter-spacing: .08em;
    color: var(--muted); margin-bottom: 6px;
  }}
  textarea, pre {{
    font-family: var(--code); font-size: 14px; line-height: 1.6;
    border: 1px solid var(--line); border-radius: 10px;
    background: var(--panel); color: var(--ink);
    padding: 14px; margin: 0; min-height: 58vh; overflow: auto;
  }}
  textarea {{ resize: vertical; tab-size: 4; }}
  label.second {{ margin-top: 12px; }}
  textarea.stdin {{ min-height: 5.5em; }}
  #tajik-page {{
    border: 1px solid var(--line); border-radius: 10px; background: var(--panel);
    padding: 14px; margin: 0; min-height: 6em; overflow: auto;
  }}
  #tajik-page h1 {{ font-size: 22px; margin: 0 0 8px; }}
  #tajik-page h2 {{ font-size: 18px; margin: 0 0 6px; }}
  #tajik-page h3 {{ font-size: 16px; margin: 0 0 6px; }}
  #tajik-page p {{ margin: 6px 0; }}
  #tajik-page table {{ border-collapse: collapse; margin: 10px 0; }}
  #tajik-page th, #tajik-page td {{
    border: 1px solid var(--line); padding: 5px 10px; text-align: right;
  }}
  #tajik-page button, #tajik-page input {{
    font: inherit; padding: 7px 14px; border-radius: 8px;
    border: 1px solid var(--line); background: var(--bg); color: var(--ink);
  }}
  #tajik-page button {{ cursor: pointer; }}
  #tajik-page ul {{ padding-right: 20px; margin: 6px 0; }}
  pre {{ white-space: pre-wrap; word-break: break-word; }}
  pre.error {{ color: var(--error); }}
  footer {{
    padding: 0 20px 28px; max-width: 1200px; margin: 0 auto;
    color: var(--muted); font-size: 13px;
  }}
  kbd {{
    font-family: var(--code); font-size: 12px; border: 1px solid var(--line);
    border-bottom-width: 2px; border-radius: 5px; padding: 1px 5px;
  }}
</style>
</head>
<body>
<header>
  <h1>TajikLang <span>— майдончаи озмоишӣ</span></h1>
  <div class="spacer"></div>
  <select id="examples" aria-label="Мисолҳо"></select>
  <button class="run" id="run" disabled>Иҷро</button>
</header>

<main>
  <section>
    <label for="code">Барнома</label>
    <textarea id="code" spellcheck="false" autocapitalize="off"
      autocorrect="off"></textarea>
    <label for="stdin" class="second">Маълумоти воридотӣ — ҳар ҷавоб дар як
      сатр (барои «хонед»)</label>
    <textarea id="stdin" class="stdin" spellcheck="false"
      autocapitalize="off" autocorrect="off"></textarea>
  </section>
  <section>
    <label for="output">Натиҷа</label>
    <pre id="output">Пайвастшавӣ… (бори аввал каме вақт мегирад)</pre>
    <label class="second" id="page-label" hidden>Саҳифа</label>
    <div id="tajik-page" hidden></div>
  </section>
</main>

<footer>
  <kbd>Ctrl</kbd> + <kbd>Enter</kbd> — иҷро.
  Ин саҳифа интерпретатори аслии TajikLang -ро дар браузер иҷро мекунад;
  Python дар компютери шумо лозим нест.
</footer>

<script src="{pyodide}pyodide.js"></script>
<script>
const MODULES = {modules};
const EXAMPLES = {examples};
const MAX_ITERATIONS = {max_iterations};

const codeEl = document.getElementById("code");
const stdinEl = document.getElementById("stdin");
const pageEl = document.getElementById("tajik-page");
const pageLabelEl = document.getElementById("page-label");
const outEl = document.getElementById("output");
const runEl = document.getElementById("run");
const pickEl = document.getElementById("examples");

for (const [name, label] of EXAMPLES.order) {{
  const option = document.createElement("option");
  option.value = name;
  option.textContent = label;
  pickEl.appendChild(option);
}}

function loadExample(name) {{
  codeEl.value = EXAMPLES.sources[name] || "";
  stdinEl.value = EXAMPLES.stdin[name] || "";
  outEl.textContent = "";
  outEl.className = "";
}}
pickEl.addEventListener("change", () => loadExample(pickEl.value));
loadExample(EXAMPLES.order[0][0]);

let pyodide = null;
let runProgram = null;

// Input for `хонед`. Lines typed in the input box are used first; only when
// they run out do we fall back to a prompt dialog — which sandboxed frames
// and some browsers refuse outright, so it can never be the only route.
let inputLines = [];
let inputIndex = 0;

window.tajikReadLine = function (promptText) {{
  if (inputIndex < inputLines.length) {{
    return inputLines[inputIndex++];
  }}
  try {{
    return window.prompt(promptText || "Маълумот ворид кунед:");
  }} catch (err) {{
    return null;    // prompt() unavailable — treat as end of input
  }}
}};

async function boot() {{
  pyodide = await loadPyodide({{ indexURL: "{pyodide}" }});

  pyodide.FS.mkdir("/lib/tajiklang");
  for (const [name, source] of Object.entries(MODULES)) {{
    pyodide.FS.writeFile("/lib/tajiklang/" + name, source);
  }}

  runProgram = pyodide.runPython(`
import sys
sys.path.insert(0, "/lib")

from tajiklang import Lexer, Parser, Interpreter, TajikLangError
from tajiklang import interpreter as _interpreter
from tajiklang.checker import check_program
from js import tajikReadLine as _js_read_line

# A phone must not be able to lock itself up on a runaway loop.
_interpreter.MAX_ITERATIONS = ${{MAX_ITERATIONS}}

# chr(10) rather than a backslash escape: this Python sits inside a JS
# template literal inside a Python format string, and a backslash would be
# eaten by whichever of those three layers got to it first.
_NL = chr(10)

# How хонед reads input in the browser: a JS prompt box, None if cancelled.
#
# No docstring and no backticks in this block. It is Python inside a JS
# template literal inside a Python string: a triple quote would end the outer
# string, and a backtick would end the template literal.
def _read_line(text):
    answer = _js_read_line(text)
    return None if answer is None else str(answer)

def _run(source):
    lines = []
    try:
        lexer = Lexer(source, "<майдонча>")
        program = Parser(lexer.tokenize(), lexer.lines).parse()
        interp = Interpreter(lexer.lines, lines.append, read_line=_read_line)

        # Check before running: every problem at once, before any output.
        found = check_program(program, set(interp.builtins.values))
        errors = [d for d in found if not d.is_warning]
        if errors:
            report = []
            for problem in errors:
                report.append(problem.format(lexer.lines))
            report.append("Ҳамагӣ " + str(len(errors)) + " хато. Барнома иҷро нашуд.")
            return ((_NL * 2).join(report), True)

        interp.run(program)
    except TajikLangError as error:
        return (_NL.join(lines + ["", error.format()]), True)
    except RecursionError:
        return (_NL.join(lines + ["", "Хатои иҷро: рекурсия аз ҳад чуқур шуд."]), True)
    return (_NL.join(lines), False)

_run
`);

  runEl.disabled = false;
  outEl.textContent = "Тайёр. Тугмаи «Иҷро» -ро пахш кунед.";
}}

function run() {{
  if (!runProgram) return;
  outEl.textContent = "Иҷро…";
  outEl.className = "";
  // Split on newlines without writing a backslash: TEMPLATE is a plain
  // Python string, so an escape here would become a real control
  // character and the regex literal would not survive the trip.
  const CR = String.fromCharCode(13);
  const LF = String.fromCharCode(10);
  inputLines = stdinEl.value === ""
    ? []
    : stdinEl.value.split(CR).join("").split(LF);
  inputIndex = 0;

  // The page pane belongs to the run that drew it, so it is emptied first
  // and revealed only if this program actually wrote something.
  pageEl.innerHTML = "";
  pageEl.hidden = true;
  pageLabelEl.hidden = true;
  // let the browser paint "Иҷро…" before the interpreter blocks the thread
  setTimeout(() => {{
    try {{
      const result = runProgram(codeEl.value);
      const [text, failed] = result.toJs();
      result.destroy();
      const drew = pageEl.childElementCount > 0;
      pageEl.hidden = !drew;
      pageLabelEl.hidden = !drew;
      outEl.textContent =
        text.trim() === "" ? (drew ? "(саҳифа сохта шуд)" : "(бе натиҷа)") : text;
      outEl.className = failed ? "error" : "";
    }} catch (err) {{
      outEl.textContent = "Хатои дохилӣ: " + err;
      outEl.className = "error";
    }}
  }}, 10);
}}

runEl.addEventListener("click", run);
document.addEventListener("keydown", (event) => {{
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {{
    event.preventDefault();
    run();
  }}
}});

boot().catch((err) => {{
  outEl.textContent = "Пайвастшавӣ нашуд: " + err +
    "\\n\\nБарои кор кардан интернет лозим аст (бори аввал).";
  outEl.className = "error";
}});
</script>
</body>
</html>
"""


def _utf8_stdout() -> None:
    """Windows consoles default to a codepage that cannot print Tajik.

    Without this the tool does its job and then crashes on its own success
    message — the same trap the `tajik` command has to avoid.
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    _utf8_stdout()
    modules = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(PACKAGE.glob("*.py"))
        if path.name not in SKIP
    }

    sources = {}
    order = []
    for filename, label in EXAMPLE_ORDER:
        path = EXAMPLES / filename
        if not path.exists():
            print(f"skipped missing example: {filename}")
            continue
        sources[filename] = path.read_text(encoding="utf-8")
        order.append([filename, label])

    html = TEMPLATE.format(
        pyodide=PYODIDE,
        modules=json.dumps(modules, ensure_ascii=False),
        examples=json.dumps(
            {"order": order, "sources": sources, "stdin": EXAMPLE_INPUT},
            ensure_ascii=False,
        ),
        max_iterations=BROWSER_MAX_ITERATIONS,
        options="",
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")

    size = OUTPUT.stat().st_size / 1024
    print(f"{OUTPUT.relative_to(ROOT)} — {len(modules)} modules, "
          f"{len(order)} examples, {size:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
