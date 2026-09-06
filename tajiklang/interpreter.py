"""Интерпретатор — walks the AST and makes it happen.

This is a *tree-walk* interpreter: it visits each node and computes its value
directly, with no bytecode and no compilation step. It is the slowest design
and by far the clearest one, which is the right trade for a teaching language.
"""

from __future__ import annotations

import difflib
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from . import ast_nodes as ast, collation, stdlib
from .errors import (
    KIND_ARGUMENTS,
    KIND_DIVISION,
    KIND_GENERAL,
    KIND_KEY,
    KIND_NAME,
    KIND_RANGE,
    KIND_TYPE,
    BuiltinError,
    RuntimeErrorTJ,
)
from .values import (
    BoundMethod,
    BreakSignal,
    Builtin,
    ContinueSignal,
    Instance,
    TajikClass,
    is_whole,
    number,
    Function,
    Module,
    ReturnSignal,
    equals,
    is_number,
    to_tajik_string,
    type_name,
)

# A loop that runs this many times has almost certainly lost its exit
# condition. Stopping with an explanation beats a frozen terminal — and beats
# a frozen browser tab once the playground exists.
MAX_ITERATIONS = 1_000_000

# How deep function calls may nest before we assume runaway recursion. Kept
# well under Python's own limit so the student gets a Tajik message rather
# than a RecursionError traceback.
MAX_CALL_DEPTH = 200

# How many changes `чаро` remembers per variable.
HISTORY_LIMIT = 200


class Environment:
    """The table of names the program can see.

    Each block and each function call gets one of these, chained to the scope
    around it. A name is looked up here first, then in the parent, and so on
    outwards.

    `is_function_scope` marks where a function body begins. Declarations look
    for a clashing name only as far as that boundary: a block must not shadow
    the variable beside it, but a function must be free to name its own
    variables without knowing what the caller happened to call theirs.
    """

    def __init__(
        self,
        parent: "Environment | None" = None,
        is_function_scope: bool = False,
        is_builtin_scope: bool = False,
    ) -> None:
        self.values: dict[str, Any] = {}
        self.parent = parent
        self.is_function_scope = is_function_scope
        self.is_builtin_scope = is_builtin_scope

    def define(self, name: str, value: Any) -> None:
        """Introduce a new name in *this* scope."""
        self.values[name] = value

    def assign(self, name: str, value: Any) -> bool:
        """Change an existing name, wherever it lives. False if unknown.

        Assignment stops at the builtin scope: `навис = 5` must not silently
        replace printing. Builtins are readable everywhere and shadowable with
        `бигзор`, but never assignable — a bare `=` means "change my variable",
        and a builtin is not the student's variable.
        """
        if self.is_builtin_scope:
            return False
        if name in self.values:
            self.values[name] = value
            return True
        if self.parent is not None:
            return self.parent.assign(name, value)
        return False

    def get(self, name: str) -> Any:
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise KeyError(name)

    def has(self, name: str) -> bool:
        if name in self.values:
            return True
        return self.parent is not None and self.parent.has(name)

    def has_within_function(self, name: str) -> bool:
        """Is the name already taken by the program in this function's scopes?

        Built-in names do not count. The no-shadowing rule exists to stop a
        student clobbering *their own* variable by accident; applying it to
        the standard library would mean every builtin added in a later version
        breaks programs that happened to use that word. `дарозӣ` was a
        perfectly good variable name in 0.2 and became a builtin in 0.7.
        """
        if self.is_builtin_scope:
            return False
        if name in self.values:
            return True
        if self.is_function_scope or self.parent is None:
            return False
        return self.parent.has_within_function(name)

    def visible_names(self) -> list[str]:
        """Every name reachable from here, for "did you mean" suggestions."""
        names = list(self.values)
        if self.parent is not None:
            names.extend(self.parent.visible_names())
        return names


class Interpreter:
    def __init__(
        self,
        source_lines: list[str] | None = None,
        output: Callable[[str], None] = print,
        base_dir: Path | None = None,
        module_cache: dict[str, Module] | None = None,
        loading: frozenset[str] | None = None,
        read_line: Callable[[str], str | None] | None = None,
    ) -> None:
        self.source_lines = source_lines or []
        self.output = output

        # How `хонед` asks for input. The terminal passes Python's `input`,
        # the browser passes a JavaScript prompt, a test passes canned lines.
        # The language itself never learns which.
        self.read_line = read_line
        self.base_dir = base_dir or Path.cwd()

        # Shared with the modules this program imports, so a file loaded twice
        # is executed once and `loading` can catch an import cycle.
        self.module_cache = module_cache if module_cache is not None else {}
        self.loading = loading if loading is not None else frozenset()

        # Builtins live in their own scope above the globals, so the program
        # can shadow them (see Environment.has_within_function) while still
        # seeing them everywhere it has not.
        self.builtins = Environment(is_builtin_scope=True)
        self.globals = Environment(self.builtins)
        self.environment = self.globals   # the scope statements run in

        # Which function called which, innermost last. Every error copies it,
        # so a failure two calls deep can show how the program got there.
        self.call_stack: list[tuple[str, int]] = []

        # The call site currently being evaluated. A builtin calling back into
        # TajikLang has no node of its own, so errors borrow this one.
        self._current_node: ast.Node = ast.Program(line=1, column=1)

        # Every change to every variable, for `чаро`. "Why is my variable
        # wrong?" is the commonest question a beginner has, and every other
        # language answers it with silence. A tree-walk interpreter can
        # answer it for almost nothing, because every change already passes
        # through two methods.
        self.history: dict[str, list[tuple[int, Any, str]]] = {}

        # Names that were declared inside a block that has since closed. Kept
        # only so that the "name not defined" error can explain *why*, which
        # is the single most confusing consequence of block scoping.
        self.closed_names: set[str] = set()

        for name, builtin in stdlib.build_globals(
            self.output, self.read_line, self._call_value
        ).items():
            self.builtins.define(name, builtin)

        # `чаро` is a real name in the builtin scope, so the checker sees it
        # and a program can shadow it. The interpreter intercepts the call
        # only when this exact object is what the name resolves to — see
        # `_call`. Reaching the builtin body means the argument was not a
        # plain variable name.
        def _чаро_misused(*args: Any) -> None:
            raise BuiltinError(
                'Функсияи "чаро" номи тағйирёбандаро мехоҳад.',
                hint="Масалан: чаро(ҷамъ) — бе нохунак ва бе ҳисоб.",
            )

        self._char_builtin = Builtin("чаро", _чаро_misused)
        self.builtins.define("чаро", self._char_builtin)

    # ------------------------------------------------------------------
    def _record(self, name: str, line: int, value: Any, note: str) -> None:
        """Remember one change, for `чаро`.

        Capped per name: a loop running a million times must not turn the
        history into the program's largest object.
        """
        entries = self.history.setdefault(name, [])
        if len(entries) < HISTORY_LIMIT:
            entries.append((line, value, note))
        elif len(entries) == HISTORY_LIMIT:
            entries.append((line, value, "…"))

    def _source_line(self, line: int) -> str:
        if 1 <= line <= len(self.source_lines):
            return self.source_lines[line - 1]
        return ""

    def _error(
        self,
        node: ast.Node,
        message: str,
        hint: str = "",
        kind_code: str = KIND_GENERAL,
    ) -> RuntimeErrorTJ:
        return RuntimeErrorTJ(
            message,
            node.line,
            node.column,
            self._source_line(node.line),
            hint,
            call_stack=list(self.call_stack),
            kind_code=kind_code,
        )

    # ------------------------------------------------------------------
    # statements
    # ------------------------------------------------------------------
    def run(self, program: ast.Program, echo: bool = False) -> None:
        """Run a whole program. `echo` prints expression values, for the REPL."""
        for statement in program.statements:
            if echo and isinstance(statement, ast.ExpressionStatement):
                value = self.evaluate(statement.expression)
                if value is not None:
                    self.output(to_tajik_string(value))
                continue
            self.execute(statement)

    def execute(self, statement: ast.Statement) -> None:
        if isinstance(statement, ast.VarDeclaration):
            # Checking the enclosing scopes, not just this one, means a block
            # cannot shadow the variable beside it. The search stops at the
            # function boundary — see Environment.has_within_function.
            if self.environment.has_within_function(statement.name):
                raise self._error(
                    statement,
                    f'Номи "{statement.name}" аллакай муайян шудааст.',
                    hint='Барои иваз кардани қимат "бигзор" -ро нанависед: '
                    f"{statement.name} = ...",
                )
            value = self.evaluate(statement.value)
            self.environment.define(statement.name, value)
            self._record(statement.name, statement.line, value, "эълон")
            return

        if isinstance(statement, ast.Assignment):
            value = self.evaluate(statement.value)
            self._record(statement.name, statement.line, value, "ивазкунӣ")
            if not self.environment.assign(statement.name, value):
                raise self._error(
                    statement,
                    f'Номи "{statement.name}" муайян нашудааст.',
                    hint=f"Аввал онро эълон кунед: бигзор {statement.name} = ...",
                )
            return

        if isinstance(statement, ast.IndexAssignment):
            self._index_assign(statement)
            return

        if isinstance(statement, ast.IfStatement):
            condition = self._as_boolean(
                self.evaluate(statement.condition), statement.condition, 'Шарти "агар"'
            )
            if condition:
                self._execute_block(statement.then_branch)
            elif statement.else_branch is not None:
                self._execute_block(statement.else_branch)
            return

        if isinstance(statement, ast.ForRange):
            self._for_range(statement)
            return

        if isinstance(statement, ast.ForEach):
            self._for_each(statement)
            return

        if isinstance(statement, ast.WhileStatement):
            self._while(statement)
            return

        if isinstance(statement, ast.FunctionDeclaration):
            if self.environment.has_within_function(statement.name):
                raise self._error(
                    statement,
                    f'Номи "{statement.name}" аллакай муайян шудааст.',
                    hint="Барои функсия номи дигар интихоб кунед.",
                )
            self.environment.define(
                statement.name, Function(statement, self.environment)
            )
            return

        if isinstance(statement, ast.ReturnStatement):
            value = None
            if statement.value is not None:
                value = self.evaluate(statement.value)
            raise ReturnSignal(value)

        if isinstance(statement, ast.ClassDeclaration):
            self._declare_class(statement)
            return

        if isinstance(statement, ast.MemberAssignment):
            target = self.evaluate(statement.target)
            if not isinstance(target, Instance):
                raise self._error(
                    statement,
                    f"Ба {type_name(target)} майдон илова кардан мумкин нест.",
                    hint="Танҳо объектҳои синф майдон доранд.",
                    kind_code=KIND_TYPE,
                )
            target.fields[statement.name] = self.evaluate(statement.value)
            return

        if isinstance(statement, ast.BreakStatement):
            raise BreakSignal()

        if isinstance(statement, ast.ContinueStatement):
            raise ContinueSignal()

        if isinstance(statement, ast.TryStatement):
            self._try(statement)
            return

        if isinstance(statement, ast.ImportStatement):
            self._import(statement)
            return

        if isinstance(statement, ast.ExpressionStatement):
            self.evaluate(statement.expression)
            return

        raise self._error(statement, f"Амали нофаҳмо: {type(statement).__name__}.")

    def _execute_block(
        self, statements: list[ast.Statement], scope: Environment | None = None
    ) -> None:
        """Run a block in a fresh scope chained to the current one.

        The scope is restored in a `finally` so that an error — or a
        `баргардон` unwinding out of a function — cannot leave the interpreter
        pointing at a dead environment.
        """
        previous = self.environment
        block = scope if scope is not None else Environment(previous)
        self.environment = block
        try:
            for statement in statements:
                self.execute(statement)
        finally:
            self.closed_names.update(block.values)
            self.environment = previous

    def _declare_class(self, statement: ast.ClassDeclaration) -> None:
        if self.environment.has_within_function(statement.name):
            raise self._error(
                statement,
                f'Номи "{statement.name}" аллакай муайян шудааст.',
                hint="Барои синф номи дигар интихоб кунед.",
            )

        parent = None
        if statement.parent is not None:
            if not self.environment.has(statement.parent):
                raise self._error(
                    statement,
                    f'Синфи волиди "{statement.parent}" муайян нашудааст.',
                    hint="Синфи волидро пеш аз фарзанд эълон кунед.",
                    kind_code=KIND_NAME,
                )
            parent = self.environment.get(statement.parent)
            if not isinstance(parent, TajikClass):
                raise self._error(
                    statement,
                    f'"{statement.parent}" синф нест.',
                    hint="Пас аз «мерос» бояд номи синф бошад.",
                    kind_code=KIND_TYPE,
                )

        methods = {
            method.name: Function(method, self.environment)
            for method in statement.methods
        }
        self.environment.define(
            statement.name, TajikClass(statement.name, parent, methods)
        )

    def _instantiate(
        self, cls: TajikClass, arguments: list[Any], node: ast.Node
    ) -> Instance:
        """Making an object: create it, then run `оғоз` if the class has one."""
        instance = Instance(cls)
        constructor = cls.find("оғоз")

        if constructor is None:
            if arguments:
                raise self._error(
                    node,
                    f'Синфи "{cls.name}" функсияи "оғоз" надорад, пас '
                    "аргумент қабул намекунад.",
                    hint="Функсияи «оғоз(худ, ...)» -ро илова кунед.",
                    kind_code=KIND_ARGUMENTS,
                )
            return instance

        self._call_function(
            constructor, [instance] + arguments, node, method_of=cls.name
        )
        return instance

    def _try(self, statement: ast.TryStatement) -> None:
        """кӯшиш / хато — run a block, and run the handler if it fails.

        Only `RuntimeErrorTJ` is caught. `баргардон`, `шикан` and `давом`
        travel as their own signals and pass straight through, so a
        `баргардон` inside `кӯшиш` still returns from the function.
        """
        try:
            self._execute_block(statement.body)
        except RuntimeErrorTJ as error:
            for clause in statement.handlers:
                if clause.kind is not None and clause.kind != error.kind_code:
                    continue
                scope = Environment(self.environment)
                if clause.name is not None:
                    scope.define(clause.name, error.message)
                self._execute_block(clause.body, scope)
                return
            raise            # no clause wanted this kind — let it travel on

    # ------------------------------------------------------------------
    # loops
    # ------------------------------------------------------------------
    def _loop_scope(self, variable: str, value: Any) -> Environment:
        """A fresh scope per iteration, holding just the loop variable.

        Per-iteration rather than per-loop, so `бигзор` inside the body works
        on every pass instead of colliding with the previous one.
        """
        scope = Environment(self.environment)
        scope.define(variable, value)
        return scope

    def _for_range(self, statement: ast.ForRange) -> None:
        start = self.evaluate(statement.start)
        end = self.evaluate(statement.end)

        for label, value in (("аз", start), ("то", end)):
            if not is_number(value):
                raise self._error(
                    statement,
                    f'Қимати "{label}" бояд рақам бошад, вале {type_name(value)} аст.',
                    hint="Масалан: барои i аз 1 то 10:",
                )

        # `то` is inclusive: `аз 1 то 5` runs five times, with i = 1..5.
        # A backwards range counts down, so `аз 5 то 1` also runs five times.
        step = 1 if end >= start else -1
        current = start
        count = 0

        while (step > 0 and current <= end) or (step < 0 and current >= end):
            count += 1
            self._guard_iterations(count, statement)
            try:
                self._execute_block(
                    statement.body, self._loop_scope(statement.variable, current)
                )
            except BreakSignal:
                return
            except ContinueSignal:
                pass
            current += step

    def _for_each(self, statement: ast.ForEach) -> None:
        iterable = self.evaluate(statement.iterable)

        if isinstance(iterable, list):
            items: list[Any] = list(iterable)
        elif isinstance(iterable, dict):
            items = list(iterable)          # walking a dictionary walks its keys
        elif isinstance(iterable, str):
            items = list(iterable)
        else:
            raise self._error(
                statement,
                f"Аз {type_name(iterable)} гузаштан мумкин нест.",
                hint="Барои шумурдан нависед: барои i аз 1 то 10:",
            )

        for count, item in enumerate(items, start=1):
            self._guard_iterations(count, statement)
            try:
                self._execute_block(
                    statement.body, self._loop_scope(statement.variable, item)
                )
            except BreakSignal:
                return
            except ContinueSignal:
                continue

    def _while(self, statement: ast.WhileStatement) -> None:
        count = 0
        while self._as_boolean(
            self.evaluate(statement.condition),
            statement.condition,
            'Шарти "то_вақте"',
        ):
            count += 1
            self._guard_iterations(count, statement)
            try:
                self._execute_block(statement.body)
            except BreakSignal:
                return
            except ContinueSignal:
                continue

    def _guard_iterations(self, count: int, statement: ast.Node) -> None:
        if count > MAX_ITERATIONS:
            raise self._error(
                statement,
                f"Давр аз {MAX_ITERATIONS} маротиба зиёд такрор шуд.",
                hint="Шояд шарти хотима ҳеҷ гоҳ иҷро намешавад.",
            )

    # ------------------------------------------------------------------
    # imports
    # ------------------------------------------------------------------
    def _import(self, statement: ast.ImportStatement) -> None:
        name = statement.name

        if self.environment.has_within_function(name):
            raise self._error(
                statement,
                f'Номи "{name}" аллакай муайян шудааст.',
                hint="Модул ва тағйирёбанда наметавонанд як ном дошта бошанд.",
            )

        if name in self.module_cache:
            self.environment.define(name, self.module_cache[name])
            return

        if name in stdlib.BUILTIN_MODULES:
            environment = Environment()
            for key, value in stdlib.BUILTIN_MODULES[name](self).items():
                environment.define(key, value)
            module = Module(name, environment)
        else:
            module = self._import_file(statement)

        self.module_cache[name] = module
        self.environment.define(name, module)

    def _import_file(self, statement: ast.ImportStatement) -> Module:
        from .lexer import Lexer          # imported here to avoid a cycle
        from .parser import Parser

        name = statement.name
        path = self.base_dir / (name + ".tj")

        if not path.exists():
            available = ", ".join(sorted(stdlib.BUILTIN_MODULES))
            raise self._error(
                statement,
                f'Модули "{name}" ёфт нашуд.',
                hint=f"На модули дарунсохт ({available}), на файли "
                f'"{name}.tj" дар ин ҷузвдон.',
            )

        key = str(path.resolve())
        if key in self.loading:
            raise self._error(
                statement,
                f'Модули "{name}" худашро ворид мекунад.',
                hint="Ду файл наметавонанд якдигарро ворид кунанд.",
            )

        source = path.read_text(encoding="utf-8")
        lexer = Lexer(source, str(path))
        tokens = lexer.tokenize()
        program = Parser(tokens, lexer.lines).parse()

        inner = Interpreter(
            lexer.lines,
            self.output,
            base_dir=path.parent,
            module_cache=self.module_cache,
            loading=self.loading | {key},
            read_line=self.read_line,
        )
        inner.run(program)
        return Module(name, inner.globals)

    # ------------------------------------------------------------------
    # expressions
    # ------------------------------------------------------------------
    def evaluate(self, node: ast.Expression) -> Any:
        if isinstance(node, (ast.StringLiteral, ast.NumberLiteral)):
            return node.value

        if isinstance(node, ast.BooleanLiteral):
            return node.value

        if isinstance(node, ast.NullLiteral):
            return None

        if isinstance(node, ast.ListLiteral):
            return [self.evaluate(element) for element in node.elements]

        if isinstance(node, ast.DictLiteral):
            result: dict[Any, Any] = {}
            for key_node, value_node in node.pairs:
                key = self.evaluate(key_node)
                if not isinstance(key, str) and not is_number(key):
                    raise self._error(
                        key_node,
                        "Калиди луғат бояд матн ё рақам бошад, вале "
                        f"{type_name(key)} аст.",
                        hint='Масалан: {"ном": "Баҳром"}',
                    )
                result[key] = self.evaluate(value_node)
            return result

        if isinstance(node, ast.Identifier):
            if not self.environment.has(node.name):
                if node.name in self.closed_names:
                    raise self._error(
                        node,
                        f'Номи "{node.name}" дар дохили блок эълон шуда буд ва '
                        "берун аз он дида намешавад.",
                        hint=f"Онро пеш аз блок эълон кунед: бигзор {node.name} = ...",
                    )
                raise self._error(
                    node,
                    f'Номи "{node.name}" муайян нашудааст.',
                    hint=self._suggest(node.name),
                    kind_code=KIND_NAME,
                )
            return self.environment.get(node.name)

        if isinstance(node, ast.UnaryOp):
            if node.operator == "не":
                return not self._as_boolean(
                    self.evaluate(node.operand), node, 'Амали "не"'
                )

            operand = self.evaluate(node.operand)
            if not is_number(operand):
                raise self._error(
                    node,
                    f'Амали "-" барои {type_name(operand)} иҷро намешавад.',
                    hint="Аломати манфӣ танҳо пеши рақам меистад.",
                )
            return number(-operand)

        if isinstance(node, ast.LogicalOp):
            return self._logical(node)

        if isinstance(node, ast.BinaryOp):
            return self._binary(node)

        if isinstance(node, ast.IndexExpression):
            return self._index(node)

        if isinstance(node, ast.MemberExpression):
            return self._member(node)

        if isinstance(node, ast.CallExpression):
            return self._call(node)

        raise self._error(node, f"Ифодаи нофаҳмо: {type(node).__name__}.")

    def call_from_host(self, callee: Any, arguments: list[Any]) -> Any:
        """Call a TajikLang function from outside the interpreter.

        A browser click handler arrives on the JavaScript event loop with no
        statement in progress, so errors are printed rather than raised —
        there is nobody above to catch them.
        """
        try:
            return self._call_value(callee, arguments)
        except RuntimeErrorTJ as error:
            self.output(error.format())
            return None

    def _explain(self, name: str) -> None:
        """`чаро(x)` — print how x came to hold what it holds."""
        entries = self.history.get(name)
        if not entries:
            self.output(f'Тағйирёбандаи "{name}" ҳеҷ гоҳ иваз нашудааст.')
            return

        self.output(f'Тағйирёбандаи "{name}":')
        for line, value, note in entries:
            if note == "…":
                self.output("    …")
                continue
            shown = to_tajik_string(value)
            self.output(f"    сатри {line:<4} →  {shown}    ({note})")

    def _call_value(self, callee: Any, arguments: list[Any]) -> Any:
        """Call a TajikLang value from Python — what `тартиб_бо` needs.

        Builtins receive this as a callback, so a builtin can take a function
        as an argument without knowing anything about the AST.
        """
        if isinstance(callee, BoundMethod):
            return self._call_function(
                callee.function,
                [callee.instance] + arguments,
                self._current_node,
                method_of=callee.instance.cls.name,
            )
        if isinstance(callee, Function):
            return self._call_function(callee, arguments, self._current_node)
        return callee(*arguments)

    # ------------------------------------------------------------------
    # calls
    # ------------------------------------------------------------------
    def _call(self, node: ast.CallExpression) -> Any:
        self._current_node = node

        # `чаро(ҷамъ)` is the single place where a call cares about the *name*
        # of its argument rather than its value, so it is handled before the
        # argument is evaluated. It stays an ordinary shadowable name: if the
        # program defines its own `чаро`, that one wins.
        if (
            isinstance(node.callee, ast.Identifier)
            and node.callee.name == "чаро"
            and self.environment.has("чаро")
            and self.environment.get("чаро") is self._char_builtin
            and len(node.arguments) == 1
            and isinstance(node.arguments[0], ast.Identifier)
        ):
            self._explain(node.arguments[0].name)
            return None

        callee = self.evaluate(node.callee)
        arguments = [self.evaluate(arg) for arg in node.arguments]

        if isinstance(callee, TajikClass):
            return self._instantiate(callee, arguments, node)

        if isinstance(callee, BoundMethod):
            return self._call_function(
                callee.function,
                [callee.instance] + arguments,
                node,
                method_of=callee.instance.cls.name,
            )

        if isinstance(callee, Function):
            return self._call_function(callee, arguments, node)

        if isinstance(callee, Builtin) or callable(callee):
            try:
                return callee(*arguments)
            except BuiltinError as error:
                raise self._error(
                    node, error.message, error.hint, error.kind_code
                ) from None

        raise self._error(
            node,
            f"{type_name(callee).capitalize()} -ро ҳамчун функсия даъват кардан "
            "мумкин нест.",
            hint="Танҳо функсияҳо бо қавсҳо даъват мешаванд.",
        )

    def _call_function(
        self,
        function: Function,
        arguments: list[Any],
        node: ast.Node,
        method_of: str | None = None,
    ) -> Any:
        expected = len(function.parameters)
        if len(arguments) != expected:
            # A method's `худ` is supplied by the language, so the count the
            # student sees must not include it.
            shown = function.parameters[1:] if method_of else function.parameters
            names = ", ".join(shown) or "ҳеҷ"
            raise self._error(
                node,
                (
                    f'Методи "{method_of}.{function.name}" {expected - 1} '
                    f"аргумент мехоҳад, вале {len(arguments) - 1} гирифт."
                    if method_of
                    else f'Функсияи "{function.name}" {expected} аргумент '
                    f"мехоҳад, вале {len(arguments)} гирифт."
                ),
                hint=f"Параметрҳо: {names}",
                kind_code=KIND_ARGUMENTS,
            )

        if len(self.call_stack) >= MAX_CALL_DEPTH:
            raise self._error(
                node,
                f'Функсияи "{function.name}" аз ҳад зиёд худро даъват кард '
                f"({MAX_CALL_DEPTH} маротиба).",
                hint="Ҳар функсияи рекурсивӣ бояд ҳолати хотима дошта бошад.",
            )

        # The closure, not the caller's scope: that is what makes the language
        # lexically scoped.
        scope = Environment(function.closure, is_function_scope=True)
        for name, value in zip(function.parameters, arguments):
            scope.define(name, value)

        previous = self.environment
        self.environment = scope
        label = f"{method_of}.{function.name}" if method_of else function.name
        self.call_stack.append((label, node.line))
        try:
            for statement in function.declaration.body:
                self.execute(statement)
            return None            # a function with no баргардон gives холӣ
        except ReturnSignal as signal:
            return signal.value
        finally:
            self.call_stack.pop()
            self.environment = previous

    # ------------------------------------------------------------------
    # collections
    # ------------------------------------------------------------------
    def _index(self, node: ast.IndexExpression) -> Any:
        target = self.evaluate(node.target)
        index = self.evaluate(node.index)

        if isinstance(target, (list, str)):
            position = self._resolve_index(node, index, len(target))
            if position < 0 or position >= len(target):
                raise self._error(
                    node,
                    f"Рақами тартибӣ берун аз ҳудуд аст (дарозӣ {len(target)}).",
                    hint=(
                        f"Рақамҳои имконпазир: 0 то {len(target) - 1}, "
                        f"ё -1 то -{len(target)} аз охир."
                        if target
                        else "Ин холӣ аст."
                    ),
                    kind_code=KIND_RANGE,
                )
            return target[position]

        if isinstance(target, dict):
            if index not in target:
                raise self._error(
                    node,
                    f"Калиди {to_tajik_string(index)} дар луғат нест.",
                    hint="Бо функсияи «дорад» санҷед: дорад(луғат, калид)",
                    kind_code=KIND_KEY,
                )
            return target[index]

        raise self._error(
            node,
            f"Аз {type_name(target)} унсур гирифтан мумкин нест.",
            hint="Танҳо рӯйхат, луғат ва матн рақами тартибӣ доранд.",
        )

    def _whole_number(self, node: ast.Node, index: Any) -> int:
        if not is_whole(index):
            raise self._error(
                node,
                f"Рақами тартибӣ бояд бутун бошад, вале {type_name(index)} аст.",
                hint="Масалан: рӯйхат[0]",
            )
        return int(index)

    def _resolve_index(self, node: ast.Node, index: Any, length: int) -> int:
        """Turn a possibly-negative index into a real one.

        `рӯйхат[-1]` is the last element, as in Python. Writing
        `рӯйхат[дарозӣ(рӯйхат) - 1]` for something this common is noise.
        """
        position = self._whole_number(node, index)
        if position < 0:
            position += length
        return position

    def _index_assign(self, statement: ast.IndexAssignment) -> None:
        target = self.evaluate(statement.target)
        index = self.evaluate(statement.index)
        value = self.evaluate(statement.value)

        if isinstance(target, list):
            position = self._resolve_index(statement, index, len(target))
            if position < 0 or position >= len(target):
                raise self._error(
                    statement,
                    f"Рақами тартибӣ берун аз ҳудуд аст (дарозӣ {len(target)}).",
                    hint=f"Рақамҳои имконпазир: 0 то {len(target) - 1}, "
                    f"ё -1 то -{len(target)} аз охир. "
                    "Барои илова кардан: илова(рӯйхат, қимат)",
                    kind_code=KIND_RANGE,
                )
            target[position] = value
            return

        if isinstance(target, dict):
            if not isinstance(index, str) and not is_number(index):
                raise self._error(
                    statement,
                    "Калиди луғат бояд матн ё рақам бошад, вале "
                    f"{type_name(index)} аст.",
                )
            target[index] = value
            return

        if isinstance(target, str):
            raise self._error(
                statement,
                "Матнро тағйир додан мумкин нест.",
                hint="Матни нав созед: ном = ном + «...»",
            )

        raise self._error(
            statement,
            f"Ба {type_name(target)} бо рақами тартибӣ қимат додан мумкин нест.",
        )

    def _member(self, node: ast.MemberExpression) -> Any:
        from .interop import PythonModule, PythonObject

        target = self.evaluate(node.target)

        # A Python module resolves names on demand: a big library has
        # thousands of attributes and a program touches three.
        if isinstance(target, PythonModule):
            try:
                return target.namespace.get(node.name)
            except BuiltinError as error:
                raise self._error(
                    node, error.message, error.hint, error.kind_code
                ) from None

        if isinstance(target, PythonObject):
            from .interop import to_tajik
            try:
                value = getattr(target.value, node.name)
            except AttributeError:
                raise self._error(
                    node,
                    f'Объекти питон номи "{node.name}" -ро надорад.',
                    hint="Номро дар ҳуҷҷатҳои Python санҷед.",
                ) from None
            return to_tajik(value, f"{target.path}.{node.name}")

        if isinstance(target, Instance):
            if node.name in target.fields:
                return target.fields[node.name]
            method = target.cls.find(node.name)
            if method is not None:
                return BoundMethod(target, method)
            available = ", ".join(
                sorted(set(list(target.fields) + target.cls.method_names()))
            )
            raise self._error(
                node,
                f'Объекти "{target.cls.name}" номи "{node.name}" -ро надорад.',
                hint=f"Мавҷуд аст: {available}" if available else "",
                kind_code=KIND_NAME,
            )

        if isinstance(target, TajikClass):
            method = target.find(node.name)
            if method is None:
                raise self._error(
                    node,
                    f'Синфи "{target.name}" методи "{node.name}" -ро надорад.',
                    kind_code=KIND_NAME,
                )
            return method

        if isinstance(target, Module):
            if not target.environment.has(node.name):
                available = ", ".join(sorted(target.environment.values))
                raise self._error(
                    node,
                    f'Модули "{target.name}" номи "{node.name}" -ро надорад.',
                    hint=f"Мавҷуд аст: {available}",
                )
            return target.environment.get(node.name)

        raise self._error(
            node,
            f'Аз {type_name(target)} бо "." чизе гирифтан мумкин нест.',
            hint="Аломати «.» танҳо барои модулҳо кор мекунад.",
        )

    # ------------------------------------------------------------------
    # operators
    # ------------------------------------------------------------------
    def _as_boolean(self, value: Any, node: ast.Node, subject: str) -> bool:
        """Require a real boolean. There is no truthiness in TajikLang.

        `агар ном:` meaning "if the name is non-empty" is convenient once and
        confusing thereafter — it is why `if (0)` and `if ("0")` disagree
        across languages. Here the student writes what they mean:
        `агар ном != "":`.
        """
        if isinstance(value, bool):
            return value
        raise self._error(
            node,
            f"{subject} қимати мантиқӣ мехоҳад, вале {type_name(value)} гирифт.",
            hint='Муқоиса нависед, масалан: x > 0, ё қиматҳои "рост" / "дурӯғ".',
            kind_code=KIND_TYPE,
        )

    def _logical(self, node: ast.LogicalOp) -> bool:
        """`ва` and `ё`, with short-circuiting.

        The right side is evaluated only when the left side does not already
        decide the answer. That is why this is not part of `_binary`: for
        `дурӯғ ва (1 / 0)` the division never runs.
        """
        subject = f'Амали "{node.operator}"'
        left = self._as_boolean(self.evaluate(node.left), node, subject)

        if node.operator == "ва" and not left:
            return False
        if node.operator == "ё" and left:
            return True

        return self._as_boolean(self.evaluate(node.right), node, subject)

    def _binary(self, node: ast.BinaryOp) -> Any:
        left = self.evaluate(node.left)
        right = self.evaluate(node.right)
        op = node.operator

        if op == "==":
            return equals(left, right)
        if op == "!=":
            return not equals(left, right)

        if op in ("<", ">", "<=", ">="):
            return self._order(node, op, left, right)

        # "+" is the one operator with more than one meaning.
        if op == "+":
            if is_number(left) and is_number(right):
                return number(left + right)
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            raise self._error(
                node,
                f'Амали "+" байни {type_name(left)} ва {type_name(right)} '
                "иҷро намешавад.",
                hint="Ҳарду бояд рақам бошанд, ё ҳарду матн, ё ҳарду рӯйхат.",
            )

        if not (is_number(left) and is_number(right)):
            raise self._error(
                node,
                f'Амали "{op}" байни {type_name(left)} ва {type_name(right)} '
                "иҷро намешавад.",
                hint=f'Амали "{op}" танҳо барои рақамҳо кор мекунад.',
            )

        if op == "-":
            return number(left - right)
        if op == "*":
            return number(left * right)

        if op in ("/", "%"):
            if right == 0:
                raise self._error(
                    node,
                    "Тақсим ба сифр мумкин нест.",
                    hint="Тақсимкунанда набояд 0 бошад.",
                    kind_code=KIND_DIVISION,
                )
            if op == "%":
                return number(left % right)
            # `/` always produces a fraction, so both sides become Decimal
            return number(Decimal(left) / Decimal(right))

        raise self._error(node, f'Оператори нофаҳмо: "{op}".')

    def _order(self, node: ast.Node, op: str, left: Any, right: Any) -> bool:
        """< > <= >= — ordering, which unlike equality can fail.

        Numbers compare numerically. Strings compare by the **Tajik alphabet**
        (see collation.py), not by Unicode code point, so `"Ғафуров" < "Яқубов"`
        is рост the way a Tajik reader expects.
        """
        if is_number(left) and is_number(right):
            result = (left > right) - (left < right)
        elif isinstance(left, str) and isinstance(right, str):
            result = collation.compare(left, right)
        else:
            raise self._error(
                node,
                f'Амали "{op}" байни {type_name(left)} ва {type_name(right)} '
                "иҷро намешавад.",
                hint=f'Амали "{op}" ҳарду рақам ё ҳарду матн мехоҳад.',
            )

        if op == "<":
            return result < 0
        if op == ">":
            return result > 0
        if op == "<=":
            return result <= 0
        return result >= 0

    def _suggest(self, name: str) -> str:
        visible = self.environment.visible_names()
        matches = difflib.get_close_matches(name, visible, n=1)
        if matches:
            return f'Оё шумо "{matches[0]}" -ро дар назар доштед?'
        return "Номҳои мавҷуда: " + ", ".join(sorted(visible))
