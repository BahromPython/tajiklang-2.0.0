# TajikLang — Мушаххасоти забон / Language Specification

**Version 2.0** · file extension `.tj` · encoding UTF-8 (NFC)

This document is the contract. Code follows the spec; when they disagree, one
of them is a bug.

---

## 1. Design principles

1. **Tajik words for structure, universal symbols for operators.** `агар`,
   `барои`, `функсия` are Tajik; `+ - * / % == != >= <=` stay as they are
   everywhere else. A student who learns TajikLang should be able to read
   Python, JavaScript or C++ arithmetic on day one.
2. **Errors teach.** Every error names the line, shows the source, points at
   the character, and says what to do. An error message is a lesson.
3. **No hidden magic.** One statement per line, explicit calls, explicit
   blocks, explicit declarations, no truthiness, no silent conversions.
4. **Tajik is not a skin over English.** Where the language actually differs —
   Unicode normalisation, alphabet order — TajikLang does the Tajik thing, not
   the convenient one. See §2.1 and §4.5.
5. **Nothing runs until it has been checked.** Python reports a misspelled
   name only when that line executes. TajikLang reports every problem it is
   certain of before any output appears. See §5.1.
6. **The vocabulary is reserved from day one.** See §7.

---

## 2. Lexical structure

### 2.1 Encoding and normalisation

Source files are UTF-8. The lexer normalises the whole file to **Unicode NFC**
before tokenising.

This is not a detail. `ӣ` can be written as one code point (U+04E3) or as
`и` + combining macron (U+0438 U+0304). The two look identical and compare
unequal. Without normalisation, `мебошӣ` typed on one keyboard would be a
different name from `мебошӣ` typed on another, and the error would be
invisible on screen. NFC makes them one name.

### 2.2 Identifiers (номҳо)

An identifier starts with a letter or `_` and continues with letters, digits
or `_`. "Letter" means any Unicode letter, so all of these are valid:

```
ном            шаҳр           ҳарорат        қимат
синну_сол      натиҷа2        _хусусӣ        x
```

Identifiers are case-sensitive. Reserved words (§7) may not be used as names.

### 2.3 Literals (қиматҳо)

| Kind | Examples |
|---|---|
| Integer | `0`, `42`, `2026` |
| Float | `3.5`, `0.25` |
| String | `"Салом"`, `"Душанбе"` |
| Boolean | `рост`, `дурӯғ` |
| Nothing | `холӣ` |
| List | `[1, 2, 3]`, `[]` |
| Dictionary | `{"ном": "Баҳром"}`, `{}` |

String escapes: `\n`, `\t`, `\r`, `\"`, `\\`. Any other escape is an error.
Strings may not span lines.

`\r` is in the list for a reason worth stating: text files arrive with CRLF
line endings, and a language whose programs cannot name a carriage return
cannot write a lexer for the files people actually have. It was added when the
self-hosting compiler in `худсоз/` needed it — see that folder's README.

### 2.4 Operators

```
+   -   *   /   %              арифметика
==  !=  <   >   <=  >=         муқоиса
ва  ё   не                     мантиқ
=                              додани қимат
(   )   [   ]   {   }   ,  .   гурӯҳбандӣ, рӯйхат, луғат, модул
```

Logical operators are Tajik words; everything else is the symbol used
everywhere else in programming. `&&`, `||`, `!` and `===` are recognised **only**
so the lexer can name the Tajik word to use instead.

### 2.5 Comments (шарҳҳо)

`#` to end of line. There is no block comment.

### 2.6 Statement separation and line joining

A newline ends a statement. Two statements on one line is an error.

**Inside `(`, `[` or `{`, newlines carry no meaning.** A list of records can
be written as a table:

```
бигзор донишҷӯён = [
    {"ном": "Яқубов", "баҳоҳо": [5, 4, 5]},
    {"ном": "Ғафуров", "баҳоҳо": [3, 4, 4]},
]
```

The lexer counts open brackets and skips newlines while any are open.
Indentation inside brackets is ignored too, so the 4-space rule (§2.7) does
not apply to a wrapped literal — otherwise the layout above would be illegal.
A trailing comma is allowed — in list and dictionary literals **and in call
arguments** — which makes adding a row, or an element to a page, a one-line
diff.

### 2.7 Indentation (фосилагузорӣ)

Blocks are marked by indentation. The lexer turns it into two tokens the
parser can use like any other: `INDENT` when a block opens, `DEDENT` when one
closes. It keeps a stack of the widths of every open block; pushing emits an
`INDENT`, popping emits a `DEDENT`.

Three rules, all stricter than Python's:

1. **Spaces only.** A tab anywhere in indentation is an error. Python 3
   rejects only *inconsistent* tabs, which still lets a file look correct and
   nest wrongly. Forbidding tabs removes the whole class of bug.
2. **Exactly four spaces per level.** Not "consistent" — four. Python accepts
   any consistent width, so two files in the same class can use 2 and 8 and
   both be right. One width means one rule to teach.
3. **A dedent must land on an open level**, and the error names the widths
   that were available.

Blank lines and comment-only lines carry no indentation meaning. Every block
still open when the file ends is closed with a `DEDENT` before `EOF`, so the
parser never treats "ran out of file" as a special case.

---

## 3. Grammar (EBNF)

```
program     ::= { NEWLINE | statement } EOF

statement   ::= if_stmt | for_stmt | while_stmt | func_decl | try_stmt
              | return_stmt | import_stmt | declaration | expr_or_assign
              | "шикан" NEWLINE | "давом" NEWLINE
try_stmt    ::= "кӯшиш" ":" block "хато" [ IDENT ] ":" block
if_stmt     ::= "агар" expression ":" block
                [ "вагарна" ( "агар" ... | ":" block ) ]
for_stmt    ::= "барои" IDENT "аз" expression [ "то" expression ] ":" block
while_stmt  ::= "то_вақте" expression ":" block
func_decl   ::= "функсия" IDENT "(" [ IDENT { "," IDENT } ] ")" ":" block
return_stmt ::= "баргардон" [ expression ] NEWLINE
import_stmt ::= "ворид" IDENT NEWLINE
declaration ::= "бигзор" IDENT "=" expression NEWLINE
expr_or_assign ::= expression [ ( "=" | "+=" | "-=" | "*=" | "/=" | "%=" )
                                expression ] NEWLINE
block       ::= NEWLINE INDENT statement { statement } DEDENT

expression  ::= or_expr
or_expr     ::= and_expr { "ё" and_expr }
and_expr    ::= not_expr { "ва" not_expr }
not_expr    ::= "не" not_expr | comparison
comparison  ::= term [ ("==" | "!=" | "<" | ">" | "<=" | ">=") term ]
term        ::= factor { ("+" | "-") factor }
factor      ::= unary { ("*" | "/" | "%") unary }
unary       ::= "-" unary | postfix
postfix     ::= primary { "(" [ arguments ] ")" | "[" expression "]"
                        | "." IDENT }
primary     ::= NUMBER | STRING | IDENT | "рост" | "дурӯғ" | "холӣ"
              | list_literal | dict_literal | "(" expression ")"
```

**Precedence is the shape of the grammar, not a table.** Each rule is written
in terms of the next one down, so each level binds tighter than the one above:

```
|>  <  ё  <  ва  <  не  <  муқоиса  <  + -  <  * / %  <  -x  <  даъват / [] / .
```

### The pipeline `|>`

```
номҳо |> тартиб |> навис
"а,б" |> ҷудо(",") |> дарозӣ
```

Tajik is verb-final: object first, then what is done to it. Every programming
language is verb-first. `|>` lets a student write either — `а |> f` becomes
`f(а)` and `а |> f(б)` becomes `f(а, б)`, rewritten in the parser, so nothing
downstream learns it exists. It binds loosest of all, so a whole expression
can be piped.

The `{ ... }` loop makes an operator left-associative: `10 - 3 - 2` is
`(10 - 3) - 2`. `comparison` deliberately uses `[ ... ]` — at most one — which
makes comparison **non-associative**: `1 < 2 < 3` is a syntax error rather
than the nonsense `(1 < 2) < 3`.

`x += 1` is rewritten by the parser into `x = x + 1`, so nothing downstream
ever learns that compound assignment exists.

**Assignment is a statement, not an expression**, and its left side is decided
*after* parsing: the parser reads an expression, then checks for `=`. An
`Identifier` becomes an assignment, an `IndexExpression` becomes an element
assignment, anything else is an error. That is why adding indexed assignment
needed no change to the statement dispatcher.

---

## 4. Semantics

### 4.1 Values

`рақам` (int and float), `матн`, `мантиқӣ`, `холӣ`, `рӯйхат`, `луғат`,
`функсия`, `модул`. Those Tajik names are exactly what appears in error
messages, and what `навъ(x)` returns.

Integers stay integers: `2 + 2` is `4`, not `4.0`, and a fraction with no
fractional part prints without it, so `10 / 5` prints `2`.

**Fractions are decimal, not binary.** This is the single most visible break
with Python:

```
навис(0.1 + 0.2)          # 0.3
навис(0.1 + 0.2 == 0.3)   # рост
```

Python, C, Java and JavaScript all answer `0.30000000000000004` and `false`,
because 0.1 has no exact binary form. Every beginner meets that, and no
explanation of binary floating point belongs in lesson 3. School arithmetic is
decimal; money is decimal; marks are decimal. So is this language.

Precision is 20 significant digits — enough that nothing a student writes runs
out, few enough that `1 / 3` does not fill a line. The cost is speed, which is
irrelevant here, and one invariant the implementation must hold: **no float
may ever enter the language.** Decimal and float cannot be mixed in Python
arithmetic, so a single stray float would fail far from its source. Literals,
arithmetic results, builtin return values and Python interop each pass through
`values.number()` at the boundary.

### 4.2 Declaration and assignment

```
бигзор ном = "Баҳром"     # эълон — introduces a new name
ном = "Далер"             # ивазкунӣ — changes an existing name
рӯйхат[0] = 5             # changes one element in place
```

- `бигзор` on a name already visible in the same function is an error.
- Plain assignment to a name that does **not** exist is an error.

**Design note.** If a bare `x = 5` could create variables, this program would
be silently wrong:

```
бигзор ном = "Баҳром"
нмо = "Далер"            # typo — creates a second variable
навис(ном)               # prints Баҳром, and the student has no idea why
```

Misspelling a name left of `=` is the most common beginner bug and the hardest
to see, because nothing fails. Same split as `let` in Rust and Swift, and what
JavaScript recovered with `let`/`const` after `var` proved the point.

### 4.3 Arithmetic

| Operator | Types |
|---|---|
| `+` | number + number, string + string, **or** list + list |
| `-` `*` `/` `%` | numbers only (`/` and `%` reject a zero right side) |
| `-x` | numbers only |

`"синну сол: " + 16` is an error, not a conversion. Silent number-to-string
coercion is how `"2" + 2 === "22"` happens. Students who want mixed output
already have `навис("синну сол:", 16)`, or `ба_матн(16)`.

### 4.4 Equality

`==` and `!=` never fail; values of different kinds are simply unequal.

```
2 == 2.0          рост      # both рақам
рост == 1         дурӯғ
1 == "1"          дурӯғ
[1, 2] == [1, 2]  рост      # element by element, under the same rule
```

Python treats `True == 1` as true; a student who writes `рост == 1` should get
`дурӯғ`, not a coincidence.

### 4.5 Ordering, and the Tajik alphabet

`<` `>` `<=` `>=` require two numbers or two strings. Strings compare by the
**Tajik alphabet**, not by Unicode code point.

This is the one place where the easy thing would have been quietly wrong. The
Tajik alphabet places its own letters beside their base letters:

```
... в  г  ғ  д ...        ғ straight after г
... и  ӣ  й  к  қ ...     ӣ after и, қ after к
```

Unicode does not. `г` is U+0433 in the main Cyrillic block; `ғ` is U+0493, off
in Cyrillic Supplement — so `"ғ" > "я"` by code point, and a naive sort files
every Tajik-specific letter after the entire rest of the alphabet:
`Ғафуров` would sort after `Яқубов`.

`collation.py` builds a sort key from the real 35-letter alphabet. It backs
both the comparison operators and the `тартиб` builtin.

### 4.6 Logic, and the absence of truthiness

`ва`, `ё` and `не` require actual booleans, as do the conditions of `агар` and
`то_вақте`. There is **no truthiness**: `0`, `""` and `холӣ` are not "false",
they are type errors in a logical position.

Truthiness saves one comparison and costs a permanent class of confusion:
`if (0)` and `if ("0")` disagree across languages, and no beginner can predict
which of `[]`, `"0"`, `0.0` is falsy in which language. Requiring
`агар ном != "":` makes the student say what they mean.

**`ва` and `ё` short-circuit**, so `дурӯғ ва 1 / 0 == 1` is `дурӯғ` rather than
a division error. This is why `LogicalOp` is a separate AST node from
`BinaryOp`: for `BinaryOp` both sides are always evaluated, for `LogicalOp`
they are not, and that difference belongs in the tree where it can be seen.

### 4.7 Conditionals

```
агар шарт:
    ...
вагарна агар шарти_дигар:
    ...
вагарна:
    ...
```

`вагарна агар` needs no node of its own in the AST: it is an `IfStatement`
sitting alone inside another one's else branch.

### 4.8 Loops

```
барои i аз 1 то 5:        # шумурдан — counting
барои x аз рӯйхат:        # гузаштан — walking
то_вақте шарт:            # while
```

**`то` is inclusive.** `аз 1 то 5` runs five times, with `i` = 1, 2, 3, 4, 5.

*Design note.* Exclusive upper bounds (`range(5)` → 0…4) exist because C
counts array offsets from zero, and the convention outlived its reason. "From
1 to 5" means 1 to 5 in Tajik, in English, and in mathematics; a beginner who
must be told it means 1 to 4 is being taught a C artifact, not a concept.
Counting down works too: `аз 5 то 1` runs five times, descending.

**Walking uses `аз`, not a new keyword.** Both forms begin
`барои НОМ аз ...`; the presence of `то` decides which. Reusing `аз` keeps
`дар` — a very common Tajik word — free as an ordinary variable name.

Walking a list gives its values, a string gives its letters, and a dictionary
gives its **keys** (as in Python; the values are one `луғат[калид]` away).

**One scope per iteration.** The loop variable lives in a fresh scope created
for each pass, which is why `бигзор` inside a loop body works on every
iteration instead of colliding with the previous one. The loop variable does
not survive the loop.

**Runaway loops are stopped.** A loop that runs more than 1,000,000 times
raises a Tajik error instead of hanging. A frozen terminal teaches nothing,
and once the browser playground exists it would freeze the tab.

### 4.8.1 Leaving a loop early

```
шикан      # leave the innermost loop
давом      # skip to its next turn
```

Both are rejected at **parse** time outside a loop, and a function body does
not inherit the loop around its declaration — `шикан` inside a function
declared in a loop belongs to no loop and is an error.

### 4.9 Functions

```
функсия ҷамъ(a, b):
    баргардон a + b
```

- A function with no `баргардон`, or a bare `баргардон`, returns `холӣ`.
- `баргардон` outside a function is a **syntax** error, caught while parsing.
- Wrong argument count is a runtime error naming the parameters.
- Functions are values: they can be assigned and passed to other functions.
- Recursion deeper than 200 calls raises a Tajik error rather than a Python
  `RecursionError`, and the hint says what a recursive function needs.

**Closures.** A function captures the environment it was *declared* in, not
the one it is called from. That one choice is what makes TajikLang lexically
scoped — a function always sees the names that surrounded its own text, and
never the caller's locals.

### 4.9.1 Errors that can be handled

```
кӯшиш:
    бигзор n = ба_рақам(хонед())
хато паём:
    навис("Ин рақам нест:", паём)
```

`хато` catches a runtime error from the `кӯшиш` block; naming it binds the
**message text**, so a student can print what went wrong.

**Several `хато` clauses may follow, matched by kind:**

```
кӯшиш:
    бигзор n = ба_рақам(хонед())
    навис(100 / n)
хато "тақсим_ба_сифр":
    навис("Сифр нашавад.")
хато паём:
    навис("Хатои дигар:", паём)
```

The first clause whose kind matches runs; a clause with no kind catches
everything and must come last, which the parser enforces. A failure no clause
wanted travels on, exactly as if there were no `кӯшиш` at all.

The kinds: `тақсим_ба_сифр`, `номи_номаълум`, `навъи_нодуруст`,
`берун_аз_ҳудуд`, `калиди_нест`, `шумораи_аргумент`, `хатои_питон`,
`хатои_файл`, `умумӣ`. Only failures worth handling *differently* are named —
a longer list would be a taxonomy nobody remembers.

`баргардон`, `шикан` and `давом` travel as their own signals and pass
straight through a `кӯшиш`, so a return inside one still returns from the
function. Only failures are caught.

### 4.9.2 Call stacks

A runtime error carries the chain of calls that reached it:

```
Хатои иҷро (сатри 2, сутуни 17):

        баргардон x / 0
                    ^

Тақсим ба сифр мумкин нест.
Маслиҳат: Тақсимкунанда набояд 0 бошад.

Роҳи даъват:
    дар функсияи "дарунӣ", даъват дар сатри 4
    дар функсияи "берунӣ", даъват дар сатри 5
```

Without this, the error names a line inside a function and leaves the student
with no idea how the program got there — which is exactly the moment, around
lesson 7, when they start writing functions.

### 4.9.3 Қолибҳо — classes

```
қолиб Донишҷӯ:
    функсия оғоз(худ, ном, баҳо):
        худ.ном = ном
        худ.баҳо = баҳо

    функсия хулоса(худ):
        агар худ.баҳо >= 4.5:
            баргардон "аъло"
        баргардон "хуб"

бигзор д = Донишҷӯ("Аҳмадов", 4.75)
навис(д.ном, д.хулоса())
```

A class is a named bag of methods. `оғоз` runs when an object is made; calling
the class makes one. A class body holds **only** functions — fields are set in
`оғоз`, where they can be seen.

`қолиб Фарзанд мерос Волид:` inherits: a method not found on the child is
looked up on its parent, and redefining one replaces it.

**`худ` is an ordinary first parameter, not a keyword.** The language supplies
it on every method call, so `д.хулоса()` takes no arguments even though
`хулоса(худ)` declares one — and argument-count errors count what the student
wrote, not what the language added.

**Design note — why the keyword is `қолиб` and not `синф`.** `синф` is the
word for a school class, and `бигзор синф = 10` belongs on the first line of a
school register program. Spending it on a keyword would be a poor trade.
`қолиб` means *mould* — which is also the metaphor: a class is the mould an
object is cast from. Same reasoning left `худ` unreserved: Python does not
reserve `self` either.

`навъ(объект)` returns the class name, and an object prints as
`Донишҷӯ(ном: "Аҳмадов", баҳо: 4.75)`, so `навис(д)` while debugging shows
something worth reading.

### 4.10 Scope

Every block and every function call is a scope, chained to the one around it.
Lookup walks outwards; assignment finds the name wherever it lives; `бигзор`
always declares locally.

```
бигзор натиҷа = ""          # declare outside
агар синну_сол >= 16:
    натиҷа = "наврас"       # assign inside — works
навис(натиҷа)
```

Declaring inside a block and reading outside does not:

```
Номи "натиҷа" дар дохили блок эълон шуда буд ва берун аз он дида намешавад.
Маслиҳат: Онро пеш аз блок эълон кунед: бигзор натиҷа = ...
```

Python has no block scope, which is why "variable might be undefined" is a
whole genre of Python bug — the variable exists only if a branch happened to
run. Block scoping makes that impossible; the interpreter keeps a
`closed_names` set purely so it can explain the one case where that costs the
student something.

**No shadowing — up to the function boundary.** `бигзор` fails if the name is
already visible *in the same function*. A block must not shadow the variable
beside it; a function must be free to name its own variables without knowing
what the caller called theirs. So this is fine:

```
бигзор ҳисоб = 1
функсия санҷиш():
    бигзор ҳисоб = 99      # a different function, a different name
    баргардон ҳисоб
```

and this is not:

```
бигзор x = 1
агар рост:
    бигзор x = 2           # same function, shadowing — rejected
```

**Built-in names are exempt.** `бигзор дарозӣ = 7.5` is legal even though
`дарозӣ` is a builtin. The no-shadowing rule exists to stop a student
clobbering *their own* variable by accident; applying it to the standard
library would mean every builtin added in a later version breaks programs that
happened to use that word — `дарозӣ` was a perfectly good variable name in 0.2
and became a builtin in 0.7.

Builtins are therefore readable everywhere, shadowable with `бигзор`, and
**not assignable**: a bare `навис = 5` is an error, because `=` means "change
my variable" and a builtin is not the student's variable. They live in their
own scope above the globals, which is the whole implementation of all three
rules.

### 4.11 Collections

```
бигзор рӯйхат = [1, 2, 3]
рӯйхат[0]                  # 1 — indexes start at 0
рӯйхат[0] = 9
рӯйхат + [4]               # joins, giving a new list

бигзор луғат = {"ном": "Баҳром"}
луғат["ном"]
луғат["шаҳр"] = "Душанбе"  # assigning a new key adds it
```

Indexes are 0-based (unlike `барои`, which counts inclusively — see §4.8) and
must be whole numbers. **Negative indexes count from the end**, so `рӯйхат[-1]`
is the last element; writing `рӯйхат[дарозӣ(рӯйхат) - 1]` for something this
common is noise. Out-of-range says what the valid range was, in both
directions. A
missing dictionary key points at `дорад`. Dictionary keys must be strings or
numbers. Strings can be indexed but not modified.

### 4.12 Modules

```
ворид риёзӣ                # a built-in module
ворид асбоб                # асбоб.tj, next to the importing file
навис(риёзӣ.реша(16))
```

`ворид ном` looks for a built-in module first, then `ном.tj` in the same
folder as the file doing the importing — not the folder the shell happens to
be in, so a program keeps working wherever it is run from.

A module's file runs once; its top-level names become its members. `.` works
only on modules. Importing a name that already exists is an error, and a file
that imports itself is caught rather than looping forever.

Built-in module **`риёзӣ`**: `реша`, `дараҷа`, `мутлақ`, `гирд`, `мин`,
`макс`, `тасодуфӣ`, and the constant `ПИ`.

### 4.13 Built-in functions

**All of these are global — no `ворид` is needed for any of them**, the way
Python's builtins work. The two library modules are namespaces over the very
same objects, so `гирд(3.7)` and `риёзӣ.гирд(3.7)` are the same call.

**Output and input**

| Function | Does |
|---|---|
| `навис(...)` | prints its arguments, space-separated |
| `хонед([савол])` | reads one line — **always returns матн** |

**Types and conversion** — `ба_рақам`, `ба_матн`, `навъ`, `бутун`

**Size, membership, copying** — `дарозӣ`, `дорад`, `холӣ_аст`, `нусха`

**Lists** — `илова`, `дарҷ`, `хориҷ`, `васеъ`, `холӣ_кун`, `ҷои`, `шумор`,
`рақамҳо`, `буриш`

**Ordering and aggregation** — `тартиб`, `тартиб_бо`, `баръакс`, `ҷамъи`,
`миёна`, `калонтарин`, `хурдтарин`, `ҳама`, `ягон`

**Dictionaries** — `калидҳо`, `қиматҳо`, `ҷуфтҳо`, `гирифтан`, `нест_кун`

**Numbers** (also `риёзӣ`) — `реша`, `дараҷа`, `мутлақ`, `гирд`, `фарш`,
`сақф`, `бутун`, `мин`, `макс`, `тасодуфӣ`, `интихоб`, `ПИ`, `Е`

**Text** (also `матн`) — `калон`, `хурд`, `тоза`, `ҷудо`, `пайваст`, `иваз`,
`буриш`, `ёфтан`, `сар_мешавад`, `тамом_мешавад`, `такрор`, `ҳарфҳо`,
`рақам_аст`

Naming rules, so the library stays predictable: a function that *answers a
question* is a noun (`дарозӣ`, `навъ`, `калидҳо`); one that *does something*
is an imperative (`илова`, `иваз`, `хонед`); one that *asks* yes/no ends in a
verb (`дорад`, `сар_мешавад`).

**`хонед` always returns text**, even when the reader types digits — the
conversion is `ба_рақам(хонед())`, written out where the student can see it.
Where the line comes from is not the language's business: the terminal passes
Python's `input`, the playground an input pane, a test a canned list.

**`тартиб_бо(рӯйхат, функсия)`** sorts by whatever the function returns for
each element, which is what sorting records by a field needs:

```
функсия номи(д):
    баргардон д["ном"]

барои д аз тартиб_бо(донишҷӯён, номи):
    навис(д["ном"])
```

Text keys use the Tajik alphabet (§4.5), and the sort is stable. Without it,
`журнал.tj` needed a nested O(n²) loop to put four names in order.

**`нусха`** exists because lists are references: `бигзор б = а` makes both
names see one list, so `илова(б, 3)` changes `а` too. That is correct and
matches every mainstream language, and it is a classic beginner trap — hence
one builtin and a paragraph in lesson 8.

A builtin raises `BuiltinError`, which the interpreter converts into a normal
Tajik error carrying the *caller's* line and column. That is the only way a
builtin can report a problem without knowing anything about the AST. A builtin
that takes a function (`тартиб_бо`) gets a callback from the interpreter for
the same reason.

### 4.14 The `питон` module — one door to Python's libraries

```
ворид питон

бигзор омор = питон.ворид("statistics")
навис(омор.median([3, 1, 4, 1, 5]))
```

TajikLang is a small language; Python has thirty years of libraries. This is
how an advanced program reaches them without the language growing a second
personality. Four rules keep the door from leaking:

1. **One visible prefix.** Everything arrives through `питон.ворид(...)`, so
   an English name in a listing is always traceable to that line.
2. **Errors come home.** A Python exception becomes an ordinary Tajik runtime
   error with the caller's line, caret and hint, and can be caught with
   `кӯшиш`. A student never sees a bare `ValueError` with no position.
3. **Values convert at the boundary.** Numbers, text, booleans, lists and
   dictionaries pass through; Python floats become decimals (§4.1); anything
   else stays wrapped and prints as `<объекти питон>`.
4. **Opt-in.** No program touches Python without `ворид питон`.

Names are resolved lazily, so `питон.ворид("pandas")` does not walk thousands
of attributes to reach three.

A consequence in the parser: **after a `.`, a keyword is just a name**, so
`питон.ворид(...)` parses even though `ворид` opens an import statement.

### 4.15 The `саҳифа` module — web pages

```
ворид саҳифа

саҳифа.нависед(
    саҳифа.сарлавҳа("Журнали синфи 10"),
    саҳифа.ҷадвал(донишҷӯён, ["ном", "баҳо"]),
    саҳифа.тугма("Ҳисоб кун", ҳисоб_кун),
)
```

**An HTML page is a tree, and TajikLang already has trees.** So this module
invents no markup syntax, no template language and no compiler to JavaScript.
It builds a tree of ordinary values, and because that tree is plain data the
same program has two destinations:

* **In a browser** it becomes real DOM, and a `тугма` handler is an ordinary
  TajikLang function called on click — the same callback path `тартиб_бо`
  uses.
* **In the terminal** `саҳифа.ҳамчун_матн(...)` returns the page as text,
  which `файл.навиштан` saves. A student can generate a real web page from the
  command line with no browser at all.

Elements: `сарлавҳа` (1–3), `матн`, `қуттӣ` (stacked), `қатор` (side by side),
`рӯйхат`, `ҷадвал`, `тугма`, `майдон`, `расм`. Composition: `услуб` adds
styling to any element; plain text used where an element is expected becomes a
paragraph, so `саҳифа.қуттӣ("салом")` works.

`ҷадвал(сатрҳо, [сарлавҳаҳо])` takes either a list of lists, or a list of
dictionaries — in which case the headers name the columns to show, so a table
is one line from the data a program already has.

**Styling is a dictionary with Tajik property names**: `ранг`, `замина`,
`андоза`, `фосила`, `ҳошия`, `васеъӣ`, `баландӣ`, `канор`, `гӯшаҳо`, `ҳарф`,
`ғафсӣ`, `ҷойгиршавӣ`. Bare numbers become pixels where that is what is meant.
Any name not on the list passes through unchanged, so knowing CSS is a bonus
rather than a requirement.

**All text and attributes are escaped.** A program cannot inject markup into
its own page, deliberately or by accident.

Reading input back: `саҳифа.майдон("ном")` creates a field and
`саҳифа.қимат("ном")` reads it. That one is browser-only, and says so.

### 4.16 The `файл` module

```
ворид файл

агар файл.мавҷуд("номҳо.txt"):
    барои сатр аз файл.сатрҳо("номҳо.txt"):
        навис(сатр)

файл.навиштан("натиҷа.txt", "тамом")
файл.илова_кардан("натиҷа.txt", " — дуруст")
```

`мавҷуд`, `хондан`, `сатрҳо`, `навиштан`, `илова_кардан`. Relative paths
resolve against **the program's own folder**, not the shell's working
directory, so a program keeps working wherever it is run from.

This is the one part of the library that is *not* global. Touching the disk
should be a visible decision, and it costs exactly one `ворид файл`.

---

## 5. Errors and checking

| Class | Heading | When |
|---|---|---|
| `LexerError` | `Хатои луғавӣ` | the text cannot be turned into tokens |
| `ParseError` | `Хатои синтаксис` | the tokens form no legal construct |
| `RuntimeErrorTJ` | `Хатои иҷро` | the program parsed but failed while running |

Every message contains: heading, line, column, the source line, a caret under
the offending character, an explanation, and — where one exists — a `Маслиҳат:`
telling the student what to change. Errors point at the operator or name that
failed, not the start of the statement.

Exit status: `65` for any of the three, `66` for a missing file, `64` for bad
command-line usage.

### 5.1 `чаро` — why is my variable this?

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

"Why does my variable hold that?" is the commonest question a beginner has,
and every mainstream language answers it with silence. A tree-walk interpreter
can answer it for almost nothing, because every change already passes through
`define` and `assign`. History is capped at 200 entries per name, so a long
loop cannot turn it into the program's largest object.

`чаро` is the one call that cares about its argument's **name** rather than
its value, so the interpreter intercepts it before evaluating. It stays an
ordinary builtin name: a program that declares its own `чаро` gets that one,
and calling it with anything but a plain name explains what it wants.

### 5.2 Checking before running

`tajik барнома.tj` checks the whole program before executing a single line,
and reports **everything** it is certain of at once:

```
Хатои санҷиш (сатри 3, сутуни 11):

        навис(нмо)
              ^

Номи "нмо" муайян нашудааст.
Маслиҳат: Оё шумо "ном" -ро дар назар доштед?

Хатои санҷиш (сатри 4, сутуни 11):

    навис(ҷамъ(1))
              ^

Функсияи "ҷамъ" 2 аргумент мехоҳад, вале 1 гирифт.

Ҳамагӣ 2 хато. Барнома иҷро нашуд.
```

Reported as errors: a name used or assigned but never declared; a call to a
function declared in this file with the wrong argument count; code after
`баргардон` / `шикан` / `давом` that can never run; `бигзор` on a name already
taken in the same function.

Reported as warnings, which do not stop the program: a variable declared
inside a function or block and never read.

**The rule the checker lives by is no false alarms.** A checker that cries
wolf teaches students to ignore it, so anything it cannot be certain of, it
says nothing about. Two consequences worth knowing:

* Function declarations are collected before the block is walked, so mutual
  recursion is legal and silent — at the cost of not catching the rare case
  where a function really is called before its declaration runs.
* The checker mirrors `Environment` exactly, builtin scope included, so
  `бигзор дарозӣ = 7.5` is as legal here as at runtime. A checker that
  disagrees with the interpreter is worse than none.

`tajik --санҷиш файл.tj` checks without running. `tajik --бе-санҷиш файл.tj`
runs without checking.

---

## 6. The `tajik` command

```
tajik барнома.tj           run a file
tajik                      interactive shell
tajik --tokens барнома.tj  what the lexer produced
tajik --ast барнома.tj     what the parser produced
tajik --version
```

The shell keeps one interpreter for the session, so names survive between
lines. A line ending in `:` starts collecting a block; a blank line runs it.
Expression values print themselves, so `1 + 1` answers `2`.

Both input and output streams are forced to UTF-8. On Windows the default
codepage cannot carry Tajik in either direction: output raises
`UnicodeEncodeError`, and piped input arrives as characters the student never
typed.

---

## 7. Reserved vocabulary

| Tajik | Meaning | Version |
|---|---|---|
| `бигзор` | variable declaration | 0.2 |
| `рост` `дурӯғ` `холӣ` | true, false, nothing | 0.3 |
| `ва` `ё` `не` | and, or, not | 0.3 |
| `агар` `вагарна` | if, else | 0.4 |
| `барои` `аз` `то` | for, from, to | 0.5 |
| `то_вақте` | while | 0.5 |
| `функсия` `баргардон` | function, return | 0.6 |
| `ворид` | import | 0.8 |
| `шикан` `давом` | break, continue | 1.1 |
| `кӯшиш` `хато` | try, catch | 1.1 |
| `қолиб` `мерос` | class, inherits | 2.0 |

Reserved-but-unimplemented words are rejected with the version they are
scheduled for, so a program written today cannot break when they land.

`худ` (self) and `синф` (school class) are deliberately **not** reserved —
both are words a school program needs. See §4.9.3.

Every reserved word is now implemented; nothing is waiting for a later
version. The staged-rollout mechanism remains for whatever comes next.

---

## 8. Version history

| Version | Contents | Status |
|---|---|---|
| 0.1 | strings, numbers, calls, `навис`, Tajik errors | done |
| 0.2 | `бигзор`, variables, assignment, arithmetic | done |
| 0.3 | comparisons, booleans, `ва`/`ё`/`не`, Tajik collation | done |
| 0.4 | `INDENT`/`DEDENT`, blocks and scopes, `агар` / `вагарна` | done |
| 0.5 | `барои`, `то_вақте`, per-iteration scope, loop guard | done |
| 0.6 | `функсия`, `баргардон`, closures, recursion limit | done |
| 0.7 | lists, dictionaries, indexing, `тартиб` and friends | done |
| 0.8 | `ворид`, built-in and file modules, `риёзӣ` | done |
| 0.9 | `tajik` command, interactive shell, packaging | done |
| 1.0 | browser playground, `хонед`, `матн` module, Tajik lessons, VS Code | done |
| 1.1 | `шикан`/`давом`, `кӯшиш`/`хато`, call stacks, `+=`, negative indexes, `файл`, 55 global builtins | done |
| 1.2 | checking before running, decimal arithmetic, Python interop | **done** |
| 1.3 | `саҳифа` — building web pages from TajikLang | done |
| 2.0 | `қолиб` (classes) and `мерос`, typed `хато`, `чаро`, `\|>`, bilingual error terms | **done** |
