"""Санҷанда — checks a program before a single line of it runs.

This is the thing Python cannot do. Python finds a misspelled name only when
that line executes, so a typo inside a branch that runs once a month is a bug
that ships. TajikLang builds a complete AST before executing anything, so it
can walk that tree first and report **every** problem it is sure about, all at
once, before any output appears.

What it reports, and never guesses about:

* a name used but never declared
* assignment to a name that was never declared
* a call to a known function with the wrong number of arguments
* code after `баргардон`, `шикан` or `давом` that can never run
* `бигзор` on a name already taken in the same function

and, as warnings that do not stop the program:

* a variable declared and never read

The rule this file lives by: **no false alarms**. A checker that cries wolf is
worse than no checker, because students learn to ignore it. Anything it cannot
be certain of, it says nothing about.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ast_nodes as ast


@dataclass
class Diagnostic:
    """One problem found before running."""

    message: str
    line: int
    column: int
    hint: str = ""
    is_warning: bool = False

    @property
    def kind(self) -> str:
        return "Огоҳӣ (Warning)" if self.is_warning else "Хатои санҷиш (CheckError)"

    def format(self, source_lines: list[str]) -> str:
        """Rendered exactly like a runtime error, so students see one style."""
        parts = [f"{self.kind} (сатри {self.line}, сутуни {self.column}):", ""]
        if 1 <= self.line <= len(source_lines):
            parts.append("    " + source_lines[self.line - 1].rstrip())
            parts.append("    " + " " * max(self.column - 1, 0) + "^")
            parts.append("")
        parts.append(self.message)
        if self.hint:
            parts.append(f"Маслиҳат: {self.hint}")
        return chr(10).join(parts)


class _Scope:
    def __init__(
        self,
        parent: "_Scope | None",
        is_function: bool = False,
        is_builtin: bool = False,
    ) -> None:
        self.names: dict[str, ast.Node] = {}
        self.read: set[str] = set()
        self.parent = parent
        self.is_function = is_function
        self.is_builtin = is_builtin

    def declare(self, name: str, node: ast.Node) -> None:
        self.names[name] = node

    def has(self, name: str) -> bool:
        if name in self.names:
            return True
        return self.parent is not None and self.parent.has(name)

    def mark_read(self, name: str) -> None:
        scope: _Scope | None = self
        while scope is not None:
            if name in scope.names:
                scope.read.add(name)
                return
            scope = scope.parent

    def taken_in_function(self, name: str) -> bool:
        """Mirrors Environment.has_within_function exactly.

        Including the part that matters most: builtins do not count, because
        the runtime lets a program shadow them. A checker that disagrees with
        the interpreter is worse than no checker.
        """
        if self.is_builtin:
            return False
        if name in self.names:
            return True
        if self.is_function or self.parent is None:
            return False
        return self.parent.taken_in_function(name)


class Checker:
    def __init__(self, program: ast.Program, builtin_names: set[str]) -> None:
        self.program = program
        self.builtins = builtin_names
        self.diagnostics: list[Diagnostic] = []

        # name -> parameter count, for user functions we can see
        self.arities: dict[str, int] = {}

    # ------------------------------------------------------------------
    def check(self) -> list[Diagnostic]:
        # Builtins sit in their own scope above the globals, mirroring the
        # interpreter, so that `бигзор дарозӣ = 7.5` is allowed here too.
        builtins = _Scope(None, is_builtin=True)
        for name in self.builtins:
            builtins.declare(name, self.program)
            builtins.read.add(name)

        globals_ = _Scope(builtins, is_function=True)
        self._block(self.program.statements, globals_, report_unused=False)
        self.diagnostics.sort(key=lambda d: (d.line, d.column))
        return self.diagnostics

    def _error(self, node: ast.Node, message: str, hint: str = "") -> None:
        self.diagnostics.append(Diagnostic(message, node.line, node.column, hint))

    def _warn(self, node: ast.Node, message: str, hint: str = "") -> None:
        self.diagnostics.append(
            Diagnostic(message, node.line, node.column, hint, is_warning=True)
        )

    # ------------------------------------------------------------------
    def _block(
        self,
        statements: list[ast.Statement],
        scope: _Scope,
        report_unused: bool = True,
    ) -> None:
        # Functions first. At runtime a function body does not run until it is
        # called, by which time a function declared further down exists — so
        # mutual recursion is legal and must not be reported.
        for statement in statements:
            if isinstance(statement, ast.FunctionDeclaration):
                scope.declare(statement.name, statement)
                self.arities[statement.name] = len(statement.parameters)
            elif isinstance(statement, ast.ClassDeclaration):
                scope.declare(statement.name, statement)
                scope.read.add(statement.name)
                # A class is called to make an object, and its argument count
                # is `оғоз` minus the `худ` the language supplies.
                for method in statement.methods:
                    if method.name == "оғоз":
                        self.arities[statement.name] = max(
                            0, len(method.parameters) - 1
                        )

        stopped: ast.Node | None = None
        for statement in statements:
            if stopped is not None:
                self._error(
                    statement,
                    "Ин сатр ҳеҷ гоҳ иҷро намешавад.",
                    hint=f'Пеш аз он дар сатри {stopped.line} "'
                    f'{self._jump_word(stopped)}" ҳаст.',
                )
                stopped = None      # one message per block is enough
            self._statement(statement, scope)
            if isinstance(
                statement,
                (ast.ReturnStatement, ast.BreakStatement, ast.ContinueStatement),
            ):
                stopped = statement

        if report_unused:
            for name, node in scope.names.items():
                if name not in scope.read:
                    self._warn(
                        node,
                        f'Тағйирёбандаи "{name}" сохта шуд, вале ҳеҷ ҷо '
                        "истифода нашуд.",
                        hint="Шояд онро нест кардан мумкин аст.",
                    )

    @staticmethod
    def _jump_word(node: ast.Node) -> str:
        if isinstance(node, ast.BreakStatement):
            return "шикан"
        if isinstance(node, ast.ContinueStatement):
            return "давом"
        return "баргардон"

    # ------------------------------------------------------------------
    def _statement(self, statement: ast.Statement, scope: _Scope) -> None:
        if isinstance(statement, ast.VarDeclaration):
            self._expression(statement.value, scope)
            if scope.taken_in_function(statement.name):
                self._error(
                    statement,
                    f'Номи "{statement.name}" аллакай муайян шудааст.',
                    hint='Барои иваз кардани қимат "бигзор" -ро нанависед: '
                    f"{statement.name} = ...",
                )
            scope.declare(statement.name, statement)
            return

        if isinstance(statement, ast.Assignment):
            self._expression(statement.value, scope)
            if not scope.has(statement.name):
                self._error(
                    statement,
                    f'Номи "{statement.name}" муайян нашудааст.',
                    hint=f"Аввал онро эълон кунед: бигзор {statement.name} = ...",
                )
            else:
                scope.mark_read(statement.name)
            return

        if isinstance(statement, ast.IndexAssignment):
            self._expression(statement.target, scope)
            self._expression(statement.index, scope)
            self._expression(statement.value, scope)
            return

        if isinstance(statement, ast.ExpressionStatement):
            self._expression(statement.expression, scope)
            return

        if isinstance(statement, ast.IfStatement):
            self._expression(statement.condition, scope)
            self._block(statement.then_branch, _Scope(scope))
            if statement.else_branch is not None:
                self._block(statement.else_branch, _Scope(scope))
            return

        if isinstance(statement, ast.ForRange):
            self._expression(statement.start, scope)
            self._expression(statement.end, scope)
            self._loop_body(statement.variable, statement.body, scope)
            return

        if isinstance(statement, ast.ForEach):
            self._expression(statement.iterable, scope)
            self._loop_body(statement.variable, statement.body, scope)
            return

        if isinstance(statement, ast.WhileStatement):
            self._expression(statement.condition, scope)
            self._block(statement.body, _Scope(scope))
            return

        if isinstance(statement, ast.FunctionDeclaration):
            # already declared by the hoisting pass above
            inner = _Scope(scope, is_function=True)
            for parameter in statement.parameters:
                inner.declare(parameter, statement)
                inner.read.add(parameter)   # a parameter is never "unused"
            self._block(statement.body, inner)
            return

        if isinstance(statement, ast.ReturnStatement):
            if statement.value is not None:
                self._expression(statement.value, scope)
            return

        if isinstance(statement, ast.TryStatement):
            self._block(statement.body, _Scope(scope))
            for clause in statement.handlers:
                handler = _Scope(scope)
                if clause.name is not None:
                    handler.declare(clause.name, clause)
                    handler.read.add(clause.name)   # binding it is enough
                self._block(clause.body, handler)
            return

        if isinstance(statement, ast.ClassDeclaration):
            scope.declare(statement.name, statement)
            scope.read.add(statement.name)
            for method in statement.methods:
                inner = _Scope(scope, is_function=True)
                for parameter in method.parameters:
                    inner.declare(parameter, method)
                    inner.read.add(parameter)
                # A method may call its siblings through `худ`, and member
                # access is not a name lookup, so nothing else to declare.
                self._block(method.body, inner)
            return

        if isinstance(statement, ast.MemberAssignment):
            self._expression(statement.target, scope)
            self._expression(statement.value, scope)
            return

        if isinstance(statement, ast.ImportStatement):
            scope.declare(statement.name, statement)
            scope.read.add(statement.name)   # a module is never "unused"
            return

        # шикан / давом carry nothing to check
        return

    def _loop_body(
        self, variable: str, body: list[ast.Statement], scope: _Scope
    ) -> None:
        inner = _Scope(scope)
        inner.declare(variable, body[0] if body else scope.names.get(variable, None) or _dummy())
        inner.read.add(variable)             # a loop variable is never "unused"
        self._block(body, inner)

    # ------------------------------------------------------------------
    def _expression(self, node: ast.Expression, scope: _Scope) -> None:
        if isinstance(node, ast.Identifier):
            if not scope.has(node.name):
                self._error(
                    node,
                    f'Номи "{node.name}" муайян нашудааст.',
                    hint=self._suggest(node.name, scope),
                )
            else:
                scope.mark_read(node.name)
            return

        if isinstance(node, ast.UnaryOp):
            self._expression(node.operand, scope)
            return

        if isinstance(node, (ast.BinaryOp, ast.LogicalOp)):
            self._expression(node.left, scope)
            self._expression(node.right, scope)
            return

        if isinstance(node, ast.ListLiteral):
            for element in node.elements:
                self._expression(element, scope)
            return

        if isinstance(node, ast.DictLiteral):
            for key, value in node.pairs:
                self._expression(key, scope)
                self._expression(value, scope)
            return

        if isinstance(node, ast.IndexExpression):
            self._expression(node.target, scope)
            self._expression(node.index, scope)
            return

        if isinstance(node, ast.MemberExpression):
            self._expression(node.target, scope)
            return

        if isinstance(node, ast.CallExpression):
            self._expression(node.callee, scope)
            for argument in node.arguments:
                self._expression(argument, scope)

            # Arity is only checked for functions declared in this file and
            # called by their plain name — anything else, stay quiet.
            if isinstance(node.callee, ast.Identifier):
                expected = self.arities.get(node.callee.name)
                if expected is not None and len(node.arguments) != expected:
                    self._error(
                        node,
                        f'Функсияи "{node.callee.name}" {expected} аргумент '
                        f"мехоҳад, вале {len(node.arguments)} гирифт.",
                        hint="Шумораи аргументҳоро санҷед.",
                    )
            return

        # literals carry nothing to check
        return

    def _suggest(self, name: str, scope: _Scope) -> str:
        import difflib

        visible: list[str] = []
        current: _Scope | None = scope
        while current is not None:
            visible.extend(current.names)
            current = current.parent

        matches = difflib.get_close_matches(name, visible, n=1)
        if matches:
            return f'Оё шумо "{matches[0]}" -ро дар назар доштед?'
        return f"Аввал онро эълон кунед: бигзор {name} = ..."


def _dummy() -> ast.Node:
    return ast.Program(line=1, column=1)


def check_program(
    program: ast.Program, builtin_names: set[str]
) -> list[Diagnostic]:
    """Check a whole program and return every problem, in source order."""
    return Checker(program, builtin_names).check()
