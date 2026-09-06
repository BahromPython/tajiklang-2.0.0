# TajikLang

[![Санҷишҳо](https://github.com/BahromPython/tajiklang/actions/workflows/tests.yml/badge.svg)](https://github.com/BahromPython/tajiklang/actions/workflows/tests.yml)
[![Сомона](https://img.shields.io/badge/сомона-bahrompython.github.io%2Ftajiklang-0f7b5f)](https://bahrompython.github.io/tajiklang/)
[![Литсензия](https://img.shields.io/badge/литсензия-MIT-blue)](LICENSE)

**[Санҷед дар браузер →](https://bahrompython.github.io/tajiklang/playground.html)** ·
**[Тоҷикӣ →](README.tg.md)** · **[Дарсҳо →](docs/дарсҳо.md)**

Забони барномасозӣ бо забони тоҷикӣ — a beginner-friendly programming language
whose keywords, error messages and alphabet order are Tajik.

> Making programming education accessible to Tajik-speaking students by letting
> beginners learn programming concepts in their own language.

**Status: version 2.0.** A complete small language — variables, arithmetic,
comparisons, logic, conditionals, loops with `шикан`/`давом`, functions with
closures and recursion, error handling, call stacks in error messages, lists,
dictionaries, modules, file I/O, and **55 built-in functions available with no
import at all**. Plus a `tajik` command with an interactive shell, a browser
playground needing no install, thirteen lessons in Tajik, and a VS Code
extension. **Checks the whole program before running it**, uses **decimal
arithmetic** so `0.1 + 0.2 == 0.3`, and can reach **Python's libraries**
through one marked door, and **build web pages** that run in a browser or
save as HTML — plus **classes**, **typed error handling**, a **pipeline
operator**, and **`чаро`**, which tells a student why a variable holds what it
holds. 420 tests.

```
ворид риёзӣ

бигзор донишҷӯён = [
    {"ном": "Яқубов", "баҳоҳо": [5, 4, 5, 5]},
    {"ном": "Ғафуров", "баҳоҳо": [3, 4, 4, 3]},
]

функсия миёнаи_баҳо(баҳоҳо):
    бигзор ҷамъ = 0
    барои б аз баҳоҳо:
        ҷамъ = ҷамъ + б
    баргардон ҷамъ / дарозӣ(баҳоҳо)

барои д аз донишҷӯён:
    бигзор миёна = миёнаи_баҳо(д["баҳоҳо"])
    агар миёна >= 4.5:
        навис(д["ном"], "— аъло")
    вагарна:
        навис(д["ном"], "—", риёзӣ.гирд(миёна * 100) / 100)
```

## Насб / Install

```bash
pip install git+https://github.com/BahromPython/tajiklang.git
```

```bash
tajik барнома.tj      # run a file
tajik                 # interactive shell
tajik-ide             # the editor
```

## Бе насб / Without installing anything

`playground/index.html` is a single self-contained file that runs the real
interpreter in the browser. Double-click it, or host it anywhere static
(GitHub Pages, emaktab.tj). **No Python needed on the student's machine** —
it loads CPython compiled to WebAssembly, and the whole interpreter is
embedded in the file.

An internet connection is needed the first time, to fetch the Python runtime;
after that the browser caches it. File imports (`ворид асбоб`) do not work
there — there is no filesystem — but the built-in `риёзӣ` module does.

Rebuild it whenever the interpreter changes:

```bash
py tools/build_playground.py
```

## Иҷро / Running locally

```bash
py main.py examples/журнал.tj
```

Or install it, and get the `tajik` command plus an interactive shell:

```bash
pip install -e .
```

```bash
tajik examples/журнал.tj
```

```bash
tajik
```

```
TajikLang 0.9.0 — реҷаи интерактивӣ
>>> бигзор x = 21
>>> x * 2
42
>>> функсия дучанд(n):
...     баргардон n * 2
...
>>> дучанд(50)
100
```

Look inside the pipeline at any time:

```bash
tajik --tokens examples/шарт.tj
```

```bash
tajik --ast examples/шарт.tj
```

## Муҳаррир / The editor

```bash
py -m tajiklang.ide
```

A small IDE built on tkinter, which ships with Python — so a school computer
needs nothing installed beyond Python itself. File list, Tajik syntax
colouring, line numbers, an input pane for `хонед`, **F5** to run and **F6**
to check. The problems panel lists everything the checker is sure of *before*
the program runs; click a problem to jump to its line.

## VS Code

```bash
py tools/build_vsix.py
code --install-extension dist/tajiklang-2.0.0.vsix
```

`tools/build_vsix.py` packages the extension using only the standard library —
no `npm`, no `vsce`, no network — because "install Node first" is a poor answer
for a school in Dushanbe.

You get syntax highlighting for `.tj`, 4-space indentation enforced by the
editor (the language rejects tabs, so this matters), and reserved-but-unimplemented
words shown as errors.

Opening this folder in VS Code also gives you tasks — **Ctrl+Shift+B** runs the
`.tj` file you have open. The others are under *Terminal → Run Task*: tokens,
AST, the interactive shell, the tests, and rebuilding the playground.

## Санҷишҳо / Tests

```bash
py -m unittest discover -s tests -t .
```

## Мисолҳо / Examples

| File | Shows |
|---|---|
| `examples/salom.tj` | the smallest program |
| `examples/тағйирёбанда.tj` | variables and arithmetic |
| `examples/муқоиса.tj` | comparisons, logic, Tajik alphabet order |
| `examples/шарт.tj` | `агар` / `вагарна агар` / `вагарна` |
| `examples/давр.tj` | `барои` and `то_вақте` |
| `examples/функсия.tj` | functions, recursion, closures |
| `examples/рӯйхат.tj` | lists and dictionaries |
| `examples/модул.tj` | `ворид` — built-in and file modules |
| `examples/матн_кор.tj` | the `матн` module — splitting, joining, slicing |
| `examples/саволнома.tj` | `хонед` — asking the reader questions |
| `examples/санҷиш.tj` | `шикан`, `давом`, `кӯшиш`/`хато` — validating input |
| `examples/саҳифа_демо.tj` | `саҳифа` — a web page with working buttons |
| `examples/қолиб.tj` | classes and inheritance |
| `examples/чаро_ва_қувват.tj` | `чаро`, `\|>`, and typed error handling |
| `examples/журнал.tj` | all of it, as a class grade register |
| `examples/хатои_*.tj` | programs that fail on purpose, to show the errors |

## Сохтор / Architecture

```
Source code (.tj, UTF-8)
      ↓  lexer.py       — characters → tokens (+ INDENT/DEDENT)
   Tokens
      ↓  parser.py      — tokens → tree
   AST (ast_nodes.py)
      ↓  interpreter.py — walks the tree and runs it
   Output
```

| File | Job |
|---|---|
| `tajiklang/tokens.py` | token types, the reserved Tajik vocabulary |
| `tajiklang/lexer.py` | text → tokens; NFC; Unicode identifiers; indentation |
| `tajiklang/ast_nodes.py` | the node types a program is made of |
| `tajiklang/parser.py` | recursive-descent parser, one method per grammar rule |
| `tajiklang/interpreter.py` | tree-walk evaluator, scopes, calls, imports |
| `tajiklang/values.py` | runtime values, Tajik type names, printing, equality |
| `tajiklang/stdlib.py` | built-in functions and the `риёзӣ` module |
| `tajiklang/collation.py` | Tajik alphabet order — `Ғафуров` sorts before `Яқубов` |
| `tajiklang/errors.py` | Tajik error messages with line, caret and hint |
| `tajiklang/cli.py` | the `tajik` command and the interactive shell |
| `tools/build_playground.py` | builds `playground/index.html` — regenerate, do not hand-edit |
| `tajiklang/ide.py` | the tkinter editor — checking, colouring, running |
| `tools/collect_messages.py` | builds `docs/ТАРҶУМА.md`, the translation review sheet |
| `tools/build_vsix.py` | packages the VS Code extension without npm |
| `tools/build_site.py` | builds `site/` for GitHub Pages |
| `editors/vscode/` | syntax highlighting extension |
| `LANGUAGE_SPEC.md` | the language contract — read this before changing syntax |

## Хатоҳо / Errors

Errors are the reason this project is worth building. Instead of

```
SyntaxError: unexpected EOF while parsing
```

TajikLang says:

```
Хатои иҷро (сатри 2, сутуни 1):

    нмо = "Далер"
    ^

Номи "нмо" муайян нашудааст.
Маслиҳат: Аввал онро эълон кунед: бигзор нмо = ...
```

Every message names the line and column, shows the source, points at the
character, explains the problem, and — where one exists — says what to change.

## Се чиз, ки Python карда наметавонад / Three things Python cannot do

**1. It checks before it runs.** Python finds a misspelled name only when that
line executes — a typo in a rare branch ships to production. TajikLang reports
every problem it is certain of, all at once, before any output:

```
Хатои санҷиш (сатри 3, сутуни 11):

        навис(нмо)
              ^

Номи "нмо" муайян нашудааст.
Маслиҳат: Оё шумо "ном" -ро дар назар доштед?

Ҳамагӣ 2 хато. Барнома иҷро нашуд.
```

The rule it lives by is **no false alarms** — it mirrors the interpreter's
scope rules exactly, and stays silent about anything it cannot be sure of.

**2. Decimal arithmetic.**

```
навис(0.1 + 0.2)          # 0.3      (Python: 0.30000000000000004)
навис(0.1 + 0.2 == 0.3)   # рост     (Python: False)
```

School arithmetic is decimal, money is decimal, marks are decimal. Binary
floating point is a machine detail that does not belong in lesson 3.

**3. `чаро` — the question no other language answers.**

```
бигзор ҷамъ = 0
барои i аз 1 то 3:
    ҷамъ += i
чаро(ҷамъ)
```
```
Тағйирёбандаи "ҷамъ":
    сатри 1    →  0    (эълон)
    сатри 3    →  1    (ивазкунӣ)
    сатри 3    →  3    (ивазкунӣ)
    сатри 3    →  6    (ивазкунӣ)
```

"Why does my variable hold that?" is the commonest beginner question, and
Python, C, Java and JavaScript all answer it with silence. A tree-walk
interpreter can answer it for almost nothing.

**4. Errors that show how you got there** — call stacks, in Tajik, with a
caret, a suggestion, and the English term in brackets
(`Хатои иҷро (RuntimeError)`) so the vocabulary transfers.

## Web pages, in Tajik

```
ворид саҳифа

саҳифа.нависед(
    саҳифа.сарлавҳа("Журнали синфи 10"),
    саҳифа.ҷадвал(донишҷӯён, ["ном", "баҳо"]),
    саҳифа.тугма("Ҳисоб кун", ҳисоб_кун),
)
```

An HTML page is a tree and TajikLang already has trees, so there is no markup
syntax to learn. In the playground it becomes a live page whose buttons call
your functions; in the terminal `саҳифа.ҳамчун_матн(...)` gives you the HTML
to save with `файл.навиштан`. Styling is a dictionary with Tajik names —
`{"ранг": "green", "андоза": 20}`.

A student who finishes the lessons can build a working web page in Tajik,
in a browser, with nothing installed.

## Python's libraries, through one door

```
ворид питон

бигзор омор = питон.ворид("statistics")
навис(омор.median([3, 1, 4, 1, 5]))
```

Opt-in, one visible prefix, and Python exceptions arrive as ordinary Tajik
errors you can catch with `кӯшиш`. Works in the browser playground too.

## Он чи забон дигар мекунад / What makes it Tajik, not translated

- **NFC normalisation.** `ӣ` has two Unicode spellings that look identical.
  Without normalising, the same name typed on two keyboards is two variables.
- **Tajik alphabet order.** `ғ ӣ қ ӯ ҳ ҷ` sit after `я` in Unicode, so every
  other language sorts a Tajik class list wrongly. `collation.py` fixes it,
  and both `<` and `тартиб` use it.
- **No truthiness, no coercion, no shadowing.** Three sources of invisible
  beginner bugs, each replaced by an error message that teaches the rule.
- **Errors that answer the next question.** `&&` says to use `ва`;
  `1 < 2 < 3` says to use `ва`; a missing dictionary key points at `дорад`;
  and a failure inside a function prints the chain of calls that reached it.

## Ҳуҷҷатҳо бо тоҷикӣ / Tajik documentation

| File | What |
|---|---|
| `README.tg.md` | this README, in Tajik |
| `docs/дарсҳо.md` | **thirteen lessons**, Tajik only, no English needed |
| `docs/чӣ_тавр_кор_мекунад.md` | how the interpreter works, in Tajik |
| `docs/ТАРҶУМА.md` | every one of the 305 Tajik strings, as a review sheet |

`docs/ТАРҶУМА.md` is generated from source by `tools/collect_messages.py`, so
it cannot drift from what the language actually says. **If you read Tajik,
that file is the most useful twenty minutes you can give this project** — the
author does not.

## Роҳи пеш / Roadmap

Everything planned is built. What is left is not code: a Tajik teacher
reading `docs/ТАРҶУМА.md`, and students using it.

## Ҳисса гузоштан / Contributing

The most valuable contribution needs no code: if you read Tajik, open
[`docs/ТАРҶУМА.md`](docs/ТАРҶУМА.md) — every message the language can show a
student, with a column for a better wording. Twenty minutes of a teacher's
time is worth more to this project than any feature.

For code: `python -m unittest discover -s tests -t .` must stay green, and
generated files (`playground/`, `docs/ТАРҶУМА.md`) are rebuilt by their tools
rather than edited — CI checks that they match.

Not planned: a bytecode VM. Tree-walking is slow and it will not matter —
no student program is performance-bound.

See `LANGUAGE_SPEC.md` §8.
