# Чӣ тавр кор мекунад — how TajikLang works

A walk through the four stages, in the order they run. Every section ends with
something to try. Run each stage yourself:

```bash
tajik --tokens examples/шарт.tj
tajik --ast examples/шарт.tj
```

---

## 1. Lexer (лексер) — characters become tokens

The lexer reads left to right and asks one question per character: *what shape
is starting here?* A letter starts a name, a digit starts a number, a `"`
starts a string. It has no idea what a program means.

```
навис("Салом Тоҷикистон!")
```
```
IDENT('навис')@2:1
LPAREN('(')@2:6
STRING('Салом Тоҷикистон!')@2:7
RPAREN(')')@2:26
NEWLINE@2:27
EOF@3:1
```

`@2:1` is line 2, column 1. Every token carries its position, which is the
only reason error messages can draw a caret at the right place later.

### The two Tajik-specific parts

**NFC normalisation.** `ӣ` has two Unicode spellings: one code point (U+04E3),
or `и` + a combining macron. They look identical and compare unequal. The
lexer normalises the whole file first, so the two spellings are one name.

**Unicode identifiers.** `char.isalpha()` is true for `ҳ`, `қ`, `ӯ`, so
`ҳарорат` needs no special handling at all.

### Tokens that are not characters

Indentation is unlike every other token: **the thing you need is not a
character**. "A block opens here" is spelt with the *absence* of something on
the next line. So the lexer manufactures two tokens that appear nowhere in the
source:

```
агар x > 5:                IF IDENT GT NUMBER COLON NEWLINE
    навис("калон")         INDENT IDENT LPAREN STRING RPAREN NEWLINE
навис("тамом")             DEDENT IDENT ...
```

The mechanism is one list:

```python
self.indents = [0]          # widths of every block currently open
```

Deeper than the top → push, emit `INDENT`. Shallower → pop and emit one
`DEDENT` per level closed. At end of file, pop everything, so a file ending
inside a block still closes cleanly.

Three rules, each stricter than Python's, and each deliberate: **spaces only**
(a tab can make a file look right and nest wrong), **exactly four** (one rule
to teach instead of "any consistent width"), and **a dedent must land on an
open level**.

One counter-rule: inside `(`, `[` or `{`, newlines and indentation mean
nothing. Without that, a table of data would have to be written on one
enormous line — exactly where it most wants breaking up.

### Машқ

1. Run `--tokens` on a file containing `навис(3.5, "х")`. How many tokens?
   What column is the comma at?
2. Delete the closing `"` from a string. Which of the three error classes
   fires — луғавӣ, синтаксис, or иҷро? Why that one?
3. Write a list literal spread over four lines. Count the NEWLINE tokens.
   Now do the same without the brackets and explain the difference.

---

## 2. Parser (парсер) — tokens become a tree

The token list is flat; meaning is nested. `навис("Салом")` is not four things
in a row, it is *one call, whose callee is a name, and whose argument is a
string*:

```
Program
  └── ExpressionStatement
        └── CallExpression
              ├── callee: Identifier('навис')
              └── arguments: [StringLiteral('Салом Тоҷикистон!')]
```

The parser is *recursive descent*: one method per grammar rule, and the
methods call each other exactly the way the rules nest. Read `parser.py` next
to the EBNF in `LANGUAGE_SPEC.md` §3 — they are the same thing written twice.

### Precedence is the shape of the grammar

The interpreter has **no** notion of precedence. Look at `2 + 3 * 4`:

```
BinaryOp('+')
  ├── NumberLiteral(2)
  └── BinaryOp('*')        ← deeper, so evaluated first
        ├── NumberLiteral(3)
        └── NumberLiteral(4)
```

That came from two rules being written in terms of each other:

```
term    ::= factor { ("+" | "-") factor }
factor  ::= unary  { ("*" | "/" | "%") unary }
```

`_term()` calls `_factor()` first, `_factor()` grabs the whole `3 * 4` before
`_term()` ever sees the `+`. Adding a precedence level later means inserting
one rule in the chain — never editing a table. The full chain is:

```
ё  <  ва  <  не  <  муқоиса  <  + -  <  * / %  <  -x  <  даъват / [] / .
```

The `{ }` loop in each rule is what makes operators left-associative, so
`10 - 3 - 2` is 5 and not 9. And `comparison` uses `[ ]` instead — at most one
— which makes `1 < 2 < 3` a syntax error rather than the nonsense
`(1 < 2) < 3`.

### Deciding assignment after the fact

`навис(x)`, `x = 1` and `рӯйхат[0] = 1` all go through one rule. The parser
reads an expression, *then* checks for `=`:

```python
expression = self._expression()
if self._check(TokenType.ASSIGN):
    ...
    if isinstance(expression, ast.Identifier):     -> Assignment
    if isinstance(expression, ast.IndexExpression) -> IndexAssignment
    otherwise: error
```

Deciding afterwards is simpler than looking ahead, and it is why adding
indexed assignment needed no change to the statement dispatcher at all.

### Машқ

1. Draw the tree for `-2 * 3 + 4` before running `--ast`. Where does the unary
   minus end up, and why does `unary` sit below `factor`?
2. Add `**` (тавон). It must bind tighter than `*` and be **right**-
   associative: `2 ** 3 ** 2` is 512, not 64. Which rule does it go in, and
   how does a rule become right-associative? (Compare the loop in `_factor`
   with the recursion in `_unary`.)
3. `1 < 2 < 3` is a syntax error here, legal in Python (meaning
   `1 < 2 ва 2 < 3`), and legal in C (meaning `(1 < 2) < 3` → `1 < 3` → true,
   for the wrong reason). Which design would you defend to a teacher?

---

## 3. AST (дарахти синтаксисӣ) — the shape of the program

The tree is the boundary between "what was written" and "what should happen".
Everything after this point works on the tree and never looks at the text
again. That is why adding a new statement means adding one node type and one
branch in `execute` — not rewriting anything.

Two node types are worth looking at, because both exist to make a difference
*visible* rather than hidden:

**`LogicalOp` is not `BinaryOp`.** `2 + 3` and `рост ва дурӯғ` have the same
shape — operator, left, right. But `BinaryOp` always evaluates both sides, and
`LogicalOp` may evaluate only one:

```python
left = self._as_boolean(self.evaluate(node.left), node, subject)
if node.operator == "ва" and not left:
    return False          # node.right is never evaluated
```

That is a real difference in what the program *does*, so it gets a real
difference in the tree. `дурӯғ ва 1 / 0 == 1` returns `дурӯғ` instead of
dividing by zero.

**`вагарна агар` has no node at all.** It is an `IfStatement` sitting alone
inside another one's else branch. One node type, any number of branches.

---

## 4. Interpreter (интерпретатор) — the tree runs

A *tree-walk* interpreter visits each node and computes it directly. This is
the slowest possible design and the clearest one. Real compilers emit bytecode
or machine code — a version 2.0 conversation, and only if speed ever becomes a
real problem for students.

### Scopes are one class and a parent pointer

```python
class Environment:
    def __init__(self, parent=None, is_function_scope=False): ...
```

Every block and every function call makes one, chained outwards. Lookup walks
up the chain; `бигзор` always defines locally. Three consequences fall out of
that single structure:

**A loop body gets a fresh scope per iteration**, which is why `бигзор` inside
a loop works on every pass instead of colliding with the previous one.

**A closure is just the environment a function was declared in:**

```python
scope = Environment(function.closure, is_function_scope=True)
```

`function.closure`, not the caller's scope. That one word is what makes the
language lexically scoped — a function always sees the names that surrounded
its own text, never the caller's locals.

**`is_function_scope` marks where shadowing rules stop.** A block must not
shadow the variable beside it; a function must be free to name its own
variables without knowing what the caller called theirs. So
`has_within_function` walks up only as far as the function boundary.

### `баргардон` raises

A tree-walk interpreter runs a `баргардон` deep inside nested `execute` calls,
and there is no way to hand a value back up through them all except to raise:

```python
class ReturnSignal(Exception):
    def __init__(self, value): self.value = value
```

It is a control-flow signal, not an error. Nothing catches it but
`_call_function`. This is how nearly every tree-walk interpreter does it,
including the one in *Crafting Interpreters*.

### Limits that produce lessons instead of hangs

```python
MAX_ITERATIONS = 1_000_000
MAX_CALL_DEPTH = 200
```

A runaway loop gets a Tajik error naming the count; runaway recursion gets one
saying that a recursive function needs a base case. A frozen terminal teaches
nothing — and once the browser playground exists, it would freeze the tab.

### Машқ

1. What does `навис(1 == 1.0)` print? What about `навис(рост == 1)`? Explain
   the difference using `type_name` in `values.py`.
2. `не` rejects `не 0`. Write the three-line change that would make `0`, `""`
   and `холӣ` count as `дурӯғ` — then write down two programs that get harder
   to debug if you ship it. Do not ship it.
3. Sort these by hand in Tajik order, then check with `collation.sort_key`:
   `Ҳакимов, Аҳмадов, Ҷӯраев, Ғафуров, Иброҳимов, Ӣсоев`
4. Write a recursive `фибоначчи(n)`. At what `n` does it get noticeably slow,
   and why? (This is the honest answer to "when would a tree-walk interpreter
   stop being enough".)
5. Add a `хона` module with a `салом(ном)` function, in a file next to your
   program, and import it. Then make two modules import each other and read
   the error you get.
6. Harder: add `шикан` (break). You need a reserved word (already reserved), a
   token type, an AST node, a signal class like `ReturnSignal`, and a `try`
   in each of the three loop methods. Where should the parser reject `шикан`
   outside a loop — and what does `_return_statement` already do that you can
   copy?
