"""Парсер — tokens in, AST out.

This is a *recursive descent* parser: one small method per grammar rule, and
the methods call each other the same way the rules nest. It is the easiest kind
of parser to read, to debug, and to extend.

Grammar of version 0.9 (EBNF):

    program     ::= { NEWLINE | statement } EOF

    statement   ::= if_stmt | for_stmt | while_stmt | func_decl
                  | return_stmt | import_stmt | declaration | expr_or_assign
    if_stmt     ::= "агар" expression ":" block
                    [ "вагарна" ( "агар" ... | ":" block ) ]
    for_stmt    ::= "барои" IDENT "аз" expression [ "то" expression ] ":" block
    while_stmt  ::= "то_вақте" expression ":" block
    func_decl   ::= "функсия" IDENT "(" [ IDENT { "," IDENT } ] ")" ":" block
    return_stmt ::= "баргардон" [ expression ] NEWLINE
    import_stmt ::= "ворид" IDENT NEWLINE
    declaration ::= "бигзор" IDENT "=" expression NEWLINE
    expr_or_assign ::= expression [ "=" expression ] NEWLINE
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
    arguments   ::= expression { "," expression }
    primary     ::= NUMBER | STRING | IDENT | "рост" | "дурӯғ" | "холӣ"
                  | list_literal | dict_literal | "(" expression ")"
    list_literal ::= "[" [ expression { "," expression } [","] ] "]"
    dict_literal ::= "{" [ pair { "," pair } [","] ] "}"
    pair         ::= expression ":" expression

Precedence lives in the *shape* of those rules: `or_expr` is written in terms
of `and_expr`, which is written in terms of `not_expr`, and so on down to
`primary`. Each level down binds tighter, with no precedence table anywhere.

`comparison` uses `[ ... ]` — at most one — rather than `{ ... }`. That makes
comparison non-associative, so `1 < 2 < 3` is a syntax error instead of the
nonsense `(1 < 2) < 3`.
"""

from __future__ import annotations

from . import ast_nodes as ast
from .errors import ParseError
from .tokens import COMPOUND_OPERATORS, KEYWORD_TOKENS, Token, TokenType

# operator token -> the string stored on the AST node
TERM_OPERATORS = {
    TokenType.PLUS: "+",
    TokenType.MINUS: "-",
}

FACTOR_OPERATORS = {
    TokenType.STAR: "*",
    TokenType.SLASH: "/",
    TokenType.PERCENT: "%",
}

COMPARISON_OPERATORS = {
    TokenType.EQ: "==",
    TokenType.NEQ: "!=",
    TokenType.LT: "<",
    TokenType.GT: ">",
    TokenType.LTE: "<=",
    TokenType.GTE: ">=",
}


class Parser:
    def __init__(self, tokens: list[Token], source_lines: list[str]) -> None:
        self.tokens = tokens
        self.source_lines = source_lines
        self.pos = 0
        self.function_depth = 0   # so `баргардон` outside a function is caught
        self.loop_depth = 0       # so `шикан` / `давом` outside a loop is caught

    # ------------------------------------------------------------------
    # low-level cursor helpers
    # ------------------------------------------------------------------
    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _check(self, type_: TokenType) -> bool:
        return self._current().type is type_

    def _advance(self) -> Token:
        token = self.tokens[self.pos]
        if token.type is not TokenType.EOF:
            self.pos += 1
        return token

    def _match(self, type_: TokenType) -> bool:
        if self._check(type_):
            self._advance()
            return True
        return False

    def _source_line(self, line: int) -> str:
        if 1 <= line <= len(self.source_lines):
            return self.source_lines[line - 1]
        return ""

    def _error(self, token: Token, message: str, hint: str = "") -> ParseError:
        return ParseError(
            message, token.line, token.column, self._source_line(token.line), hint
        )

    def _expect(self, type_: TokenType, message: str, hint: str = "") -> Token:
        if self._check(type_):
            return self._advance()

        # A stray "=" where an expression was supposed to end means the student
        # wrote an assignment inside an expression — `навис(x = 1)`. Saying
        # "closing bracket not found" there would send them hunting for the
        # wrong thing, so that case gets its own message.
        #
        # This does not apply when we were expecting a *name* (`бигзор = 10`),
        # where the missing name is the real problem.
        if self._current().type is TokenType.ASSIGN and type_ in (
            TokenType.RPAREN,
            TokenType.RBRACKET,
            TokenType.COMMA,
            TokenType.NEWLINE,
        ):
            raise self._error(
                self._current(),
                'Аломати "=" дар ин ҷо истифода намешавад.',
                hint="Додани қимат амали алоҳида аст: бигзор ном = қимат",
            )

        raise self._error(self._current(), message, hint)

    def _end_statement(self) -> None:
        if self._check(TokenType.EOF):
            return
        self._expect(
            TokenType.NEWLINE,
            f'Пас аз ин амал сатри нав интизор мешуд, вале "{self._current().value}" ёфт шуд.',
            hint="Ҳар амал бояд дар сатри алоҳида навишта шавад.",
        )

    # ------------------------------------------------------------------
    # grammar rules — statements
    # ------------------------------------------------------------------
    def parse(self) -> ast.Program:
        program = ast.Program(line=1, column=1, statements=[])

        while not self._check(TokenType.EOF):
            if self._match(TokenType.NEWLINE):
                continue  # blank lines are not statements

            if self._check(TokenType.INDENT):
                raise self._error(
                    self._current(),
                    "Ин сатр бе сабаб фосила дорад.",
                    hint='Фосила танҳо баъд аз "агар", "барои", "функсия" ва '
                    "монанди онҳо истифода мешавад.",
                )

            program.statements.append(self._statement())

        return program

    def _statement(self) -> ast.Statement:
        if self._check(TokenType.IF):
            return self._if_statement()

        if self._check(TokenType.FOR):
            return self._for_statement()

        if self._check(TokenType.WHILE):
            return self._while_statement()

        if self._check(TokenType.FUNC):
            return self._function_declaration()

        if self._check(TokenType.RETURN):
            return self._return_statement()

        if self._check(TokenType.IMPORT):
            return self._import_statement()

        if self._check(TokenType.CLASS):
            return self._class_declaration()

        if self._check(TokenType.TRY):
            return self._try_statement()

        if self._check(TokenType.BREAK):
            return self._loop_jump(TokenType.BREAK, "шикан", ast.BreakStatement)

        if self._check(TokenType.CONTINUE):
            return self._loop_jump(TokenType.CONTINUE, "давом", ast.ContinueStatement)

        if self._check(TokenType.CATCH):
            raise self._error(
                self._current(),
                '"хато" бе "кӯшиш" истифода шудааст.',
                hint='Ҳар "хато" бояд пас аз блоки "кӯшиш" ояд.',
            )

        if self._check(TokenType.ELSE):
            raise self._error(
                self._current(),
                '"вагарна" бе "агар" истифода шудааст.',
                hint='Ҳар "вагарна" бояд ба як "агар" тааллуқ дошта бошад '
                "ва дар ҳамон сатҳи фосила истад.",
            )

        if self._check(TokenType.LET):
            return self._declaration()

        return self._expression_or_assignment()

    def _block(self, opener: Token) -> list[ast.Statement]:
        """NEWLINE INDENT statement+ DEDENT — the body of a block statement.

        `opener` is the keyword that opened the block. An empty block is
        reported at *that* keyword rather than at the blank line after it,
        which may not exist at all when the file simply ends.
        """
        self._expect(
            TokenType.NEWLINE,
            'Пас аз ":" бояд сатри нав сар шавад.',
            hint=f'Амалҳои "{opener.value}" -ро дар сатрҳои зерин нависед.',
        )

        # Blank and comment-only lines carry no indentation, so each one
        # arrives as a bare NEWLINE before the INDENT. Starting a block with
        # a comment explaining it is ordinary writing, not an error.
        while self._match(TokenType.NEWLINE):
            pass

        if not self._check(TokenType.INDENT):
            raise self._error(
                opener,
                f'Пас аз "{opener.value}" блоки холӣ мондааст.',
                hint="Сатрҳои дохили блок бояд 4 холигӣ фосила дошта бошанд.",
            )
        self._advance()

        statements: list[ast.Statement] = []
        while not self._check(TokenType.DEDENT) and not self._check(TokenType.EOF):
            if self._match(TokenType.NEWLINE):
                continue
            statements.append(self._statement())

        self._expect(TokenType.DEDENT, "Блок ба анҷом нарасид.")
        return statements

    def _if_statement(self) -> ast.IfStatement:
        keyword = self._advance()  # consume "агар"

        condition = self._expression()
        self._expect(
            TokenType.COLON,
            'Пас аз шарти "агар" аломати ":" лозим аст.',
            hint="Масалан: агар синну_сол >= 16:",
        )
        then_branch = self._block(keyword)

        else_branch: list[ast.Statement] | None = None
        if self._check(TokenType.ELSE):
            else_keyword = self._advance()  # consume "вагарна"

            if self._check(TokenType.IF):
                # `вагарна агар` — the whole chain is one nested IfStatement.
                else_branch = [self._if_statement()]
            else:
                self._expect(
                    TokenType.COLON,
                    'Пас аз "вагарна" аломати ":" лозим аст.',
                    hint="Барои шарти дигар нависед: вагарна агар ... :",
                )
                else_branch = self._block(else_keyword)

        return ast.IfStatement(
            line=keyword.line,
            column=keyword.column,
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
        )

    def _for_statement(self) -> ast.Statement:
        """барои i аз 1 то 10:   (a count)
        барои x аз рӯйхат:      (a walk)

        Both start `барои НОМ аз ...`; the presence of `то` decides which. That
        is why walking a collection does not need a keyword of its own — `дар`
        stays available as an ordinary variable name.
        """
        keyword = self._advance()  # consume "барои"

        variable = self._expect(
            TokenType.IDENT,
            f'Пас аз "барои" номи тағйирёбанда лозим аст, вале '
            f'"{self._current().value}" ёфт шуд.',
            hint="Масалан: барои i аз 1 то 10:",
        )

        self._expect(
            TokenType.FROM,
            'Пас аз номи тағйирёбанда калимаи "аз" лозим аст.',
            hint=f"Масалан: барои {variable.value} аз 1 то 10:",
        )

        start = self._expression()

        if self._match(TokenType.TO):
            end = self._expression()
            self._expect(
                TokenType.COLON,
                'Пас аз "то <қимат>" аломати ":" лозим аст.',
                hint=f"Масалан: барои {variable.value} аз 1 то 10:",
            )
            return ast.ForRange(
                line=keyword.line,
                column=keyword.column,
                variable=variable.value,
                start=start,
                end=end,
                body=self._loop_block(keyword),
            )

        self._expect(
            TokenType.COLON,
            'Пас аз "барои ... аз ..." аломати ":" лозим аст.',
            hint=f"Барои шумурдан: барои {variable.value} аз 1 то 10:",
        )
        return ast.ForEach(
            line=keyword.line,
            column=keyword.column,
            variable=variable.value,
            iterable=start,
            body=self._loop_block(keyword),
        )

    def _while_statement(self) -> ast.WhileStatement:
        keyword = self._advance()  # consume "то_вақте"

        condition = self._expression()
        self._expect(
            TokenType.COLON,
            'Пас аз шарти "то_вақте" аломати ":" лозим аст.',
            hint="Масалан: то_вақте ҳисоб < 10:",
        )

        return ast.WhileStatement(
            line=keyword.line,
            column=keyword.column,
            condition=condition,
            body=self._loop_block(keyword),
        )

    def _loop_block(self, opener: Token) -> list[ast.Statement]:
        """A block that `шикан` and `давом` are allowed inside."""
        self.loop_depth += 1
        try:
            return self._block(opener)
        finally:
            self.loop_depth -= 1

    def _loop_jump(self, type_: TokenType, word: str, node_type):
        keyword = self._advance()

        # A function boundary stops the search: `шикан` inside a function
        # declared inside a loop does not belong to that loop.
        if self.loop_depth == 0:
            raise self._error(
                keyword,
                f'"{word}" танҳо дар дохили давр истифода мешавад.',
                hint='Онро дар дохили "барои" ё "то_вақте" нависед.',
            )

        self._end_statement()
        return node_type(line=keyword.line, column=keyword.column)

    def _try_statement(self) -> ast.TryStatement:
        keyword = self._advance()  # consume "кӯшиш"
        self._expect(
            TokenType.COLON,
            'Пас аз "кӯшиш" аломати ":" лозим аст.',
            hint="Масалан: кӯшиш:",
        )
        body = self._block(keyword)

        if not self._check(TokenType.CATCH):
            raise self._error(
                self._current(),
                'Пас аз блоки "кӯшиш" блоки "хато" лозим аст.',
                hint="Масалан: кӯшиш: ... хато: ...",
            )

        handlers: list[ast.CatchClause] = []
        seen_catch_all = False

        while self._check(TokenType.CATCH):
            catch = self._advance()

            # `хато "тақсим_ба_сифр" паём:` — the text names the kind of
            # failure, the name binds its message. Both are optional.
            kind: str | None = None
            if self._check(TokenType.STRING):
                kind = self._advance().value

            name: str | None = None
            if self._check(TokenType.IDENT):
                name = self._advance().value

            if seen_catch_all:
                raise self._error(
                    catch,
                    'Пас аз "хато" -и умумӣ блоки дигар ҳеҷ гоҳ иҷро намешавад.',
                    hint='Блоки бе навъро охирин гузоред.',
                )
            if kind is None:
                seen_catch_all = True

            self._expect(
                TokenType.COLON,
                'Пас аз "хато" аломати ":" лозим аст.',
                hint="Барои гирифтани матни хато: хато паём:",
            )
            handlers.append(
                ast.CatchClause(
                    line=catch.line,
                    column=catch.column,
                    kind=kind,
                    name=name,
                    body=self._block(catch),
                )
            )

        return ast.TryStatement(
            line=keyword.line,
            column=keyword.column,
            body=body,
            handlers=handlers,
        )

    def _class_declaration(self) -> ast.ClassDeclaration:
        keyword = self._advance()  # consume "синф"

        name = self._expect(
            TokenType.IDENT,
            f'Пас аз "қолиб" ном лозим аст, вале "{self._current().value}" ёфт шуд.',
            hint="Масалан: қолиб Донишҷӯ:",
        )

        parent: str | None = None
        if self._match(TokenType.INHERITS):
            parent = self._expect(
                TokenType.IDENT,
                'Пас аз "мерос" номи синфи волид лозим аст.',
                hint="Масалан: қолиб Аълочӣ мерос Донишҷӯ:",
            ).value

        self._expect(
            TokenType.COLON,
            'Пас аз номи синф аломати ":" лозим аст.',
            hint=f"Масалан: қолиб {name.value}:",
        )

        # A class body holds only functions, so say that plainly rather than
        # letting a stray statement fail somewhere stranger.
        self._expect(
            TokenType.NEWLINE, 'Пас аз ":" бояд сатри нав сар шавад.'
        )
        while self._match(TokenType.NEWLINE):
            pass
        if not self._check(TokenType.INDENT):
            raise self._error(
                keyword,
                f'Синфи "{name.value}" холӣ мондааст.',
                hint="Синф бояд ҳадди аққал як функсия дошта бошад.",
            )
        self._advance()

        methods: list[ast.FunctionDeclaration] = []
        while not self._check(TokenType.DEDENT) and not self._check(TokenType.EOF):
            if self._match(TokenType.NEWLINE):
                continue
            if not self._check(TokenType.FUNC):
                raise self._error(
                    self._current(),
                    "Дар дохили синф танҳо функсияҳо навишта мешаванд.",
                    hint="Қиматҳоро дар функсияи «оғоз» муайян кунед.",
                )
            methods.append(self._function_declaration())

        self._expect(TokenType.DEDENT, "Блоки синф ба анҷом нарасид.")
        return ast.ClassDeclaration(
            line=keyword.line,
            column=keyword.column,
            name=name.value,
            parent=parent,
            methods=methods,
        )

    def _function_declaration(self) -> ast.FunctionDeclaration:
        keyword = self._advance()  # consume "функсия"

        name = self._expect(
            TokenType.IDENT,
            f'Пас аз "функсия" ном лозим аст, вале "{self._current().value}" ёфт шуд.',
            hint="Масалан: функсия ҷамъ(a, b):",
        )

        self._expect(
            TokenType.LPAREN,
            f'Пас аз номи функсия қавси "(" лозим аст.',
            hint=f"Масалан: функсия {name.value}(a, b):",
        )

        parameters: list[str] = []
        if not self._check(TokenType.RPAREN):
            while True:
                parameter = self._expect(
                    TokenType.IDENT,
                    "Номи параметр интизор мешуд, вале "
                    f'"{self._current().value}" ёфт шуд.',
                )
                if parameter.value in parameters:
                    raise self._error(
                        parameter,
                        f'Параметри "{parameter.value}" ду бор навишта шудааст.',
                        hint="Ҳар параметр бояд номи ягона дошта бошад.",
                    )
                parameters.append(parameter.value)
                if not self._match(TokenType.COMMA):
                    break

        self._expect(TokenType.RPAREN, 'Қавси пӯшида ")" ёфт нашуд.')
        self._expect(
            TokenType.COLON,
            'Пас аз рӯйхати параметрҳо аломати ":" лозим аст.',
            hint=f"Масалан: функсия {name.value}(...):",
        )

        self.function_depth += 1
        enclosing_loops, self.loop_depth = self.loop_depth, 0
        try:
            body = self._block(keyword)
        finally:
            self.function_depth -= 1
            self.loop_depth = enclosing_loops

        return ast.FunctionDeclaration(
            line=keyword.line,
            column=keyword.column,
            name=name.value,
            parameters=parameters,
            body=body,
        )

    def _return_statement(self) -> ast.ReturnStatement:
        keyword = self._advance()  # consume "баргардон"

        if self.function_depth == 0:
            raise self._error(
                keyword,
                '"баргардон" танҳо дар дохили функсия истифода мешавад.',
                hint="Берун аз функсия чизе барои баргардонидан нест.",
            )

        value: ast.Expression | None = None
        if not self._check(TokenType.NEWLINE) and not self._check(TokenType.EOF):
            value = self._expression()

        self._end_statement()
        return ast.ReturnStatement(
            line=keyword.line, column=keyword.column, value=value
        )

    def _import_statement(self) -> ast.ImportStatement:
        keyword = self._advance()  # consume "ворид"

        name = self._expect(
            TokenType.IDENT,
            f'Пас аз "ворид" номи модул лозим аст, вале '
            f'"{self._current().value}" ёфт шуд.',
            hint="Масалан: ворид риёзӣ",
        )
        self._end_statement()

        return ast.ImportStatement(
            line=keyword.line, column=keyword.column, name=name.value
        )

    def _declaration(self) -> ast.VarDeclaration:
        keyword = self._advance()  # consume "бигзор"

        name = self._expect(
            TokenType.IDENT,
            f'Пас аз "бигзор" номи тағйирёбанда лозим аст, вале '
            f'"{self._current().value}" ёфт шуд.',
            hint="Масалан: бигзор синну_сол = 16",
        )

        self._expect(
            TokenType.ASSIGN,
            'Пас аз номи тағйирёбанда аломати "=" лозим аст.',
            hint=f"Масалан: бигзор {name.value} = 0",
        )

        value = self._expression()
        self._end_statement()

        return ast.VarDeclaration(
            line=keyword.line, column=keyword.column, name=name.value, value=value
        )

    def _expression_or_assignment(self) -> ast.Statement:
        """One rule for `навис(x)`, `x = 1` and `рӯйхат[0] = 1`.

        Parse an expression first, then look for `=`. Deciding afterwards is
        simpler than looking ahead, and it extends to any assignable form
        without touching the statement dispatcher.
        """
        token = self._current()
        expression = self._expression()

        compound = COMPOUND_OPERATORS.get(self._current().type)

        if self._check(TokenType.ASSIGN) or compound:
            operator = self._advance()
            value = self._expression()
            self._end_statement()

            # `x += 1` becomes `x = x + 1` right here, so nothing downstream
            # ever learns that compound assignment exists.
            if compound:
                value = ast.BinaryOp(
                    line=operator.line,
                    column=operator.column,
                    operator=compound,
                    left=expression,
                    right=value,
                )

            if isinstance(expression, ast.Identifier):
                return ast.Assignment(
                    line=token.line,
                    column=token.column,
                    name=expression.name,
                    value=value,
                )

            if isinstance(expression, ast.IndexExpression):
                return ast.IndexAssignment(
                    line=token.line,
                    column=token.column,
                    target=expression.target,
                    index=expression.index,
                    value=value,
                )

            if isinstance(expression, ast.MemberExpression):
                return ast.MemberAssignment(
                    line=token.line,
                    column=token.column,
                    target=expression.target,
                    name=expression.name,
                    value=value,
                )

            raise self._error(
                token,
                "Ба ин ифода қимат додан мумкин нест.",
                hint="Дар тарафи чапи «=» бояд ном ё унсури рӯйхат бошад.",
            )

        self._end_statement()
        return ast.ExpressionStatement(
            line=token.line, column=token.column, expression=expression
        )

    # ------------------------------------------------------------------
    # grammar rules — expressions
    # ------------------------------------------------------------------
    def _expression(self) -> ast.Expression:
        return self._pipeline()

    def _pipeline(self) -> ast.Expression:
        """`номҳо |> тартиб |> навис` — left to right, in Tajik word order.

        Tajik puts the verb last: object, then what is done to it. Every
        programming language puts the verb first. This rule lets a student
        write either, and it is pure rewriting — `а |> f` becomes `f(а)`, and
        `а |> f(б)` becomes `f(а, б)`, so nothing downstream learns about it.
        """
        node = self._or()

        while self._check(TokenType.PIPE):
            pipe = self._advance()
            right = self._or()

            if isinstance(right, ast.CallExpression):
                right.arguments.insert(0, node)
                node = right
            else:
                node = ast.CallExpression(
                    line=pipe.line,
                    column=pipe.column,
                    callee=right,
                    arguments=[node],
                )

        return node

    def _or(self) -> ast.Expression:
        node = self._and()

        while self._check(TokenType.OR):
            operator = self._advance()
            right = self._and()
            node = ast.LogicalOp(
                line=operator.line,
                column=operator.column,
                operator="ё",
                left=node,
                right=right,
            )

        return node

    def _and(self) -> ast.Expression:
        node = self._not()

        while self._check(TokenType.AND):
            operator = self._advance()
            right = self._not()
            node = ast.LogicalOp(
                line=operator.line,
                column=operator.column,
                operator="ва",
                left=node,
                right=right,
            )

        return node

    def _not(self) -> ast.Expression:
        if self._check(TokenType.NOT):
            operator = self._advance()
            return ast.UnaryOp(
                line=operator.line,
                column=operator.column,
                operator="не",
                operand=self._not(),  # so that `не не x` parses
            )

        return self._comparison()

    def _comparison(self) -> ast.Expression:
        node = self._term()

        if self._current().type in COMPARISON_OPERATORS:
            operator = self._advance()
            right = self._term()
            node = ast.BinaryOp(
                line=operator.line,
                column=operator.column,
                operator=COMPARISON_OPERATORS[operator.type],
                left=node,
                right=right,
            )

            # Deliberately not a loop: `1 < 2 < 3` reads like mathematics but
            # would mean `(1 < 2) < 3` — comparing a boolean with a number.
            # Rejecting it here is clearer than letting it fail at runtime.
            if self._current().type in COMPARISON_OPERATORS:
                second = self._current()
                raise self._error(
                    second,
                    "Ду муқоиса паси ҳам навишта намешаванд.",
                    hint='Онҳоро бо "ва" ҷудо кунед: 1 < 2 ва 2 < 3',
                )

        return node

    def _term(self) -> ast.Expression:
        node = self._factor()

        while self._current().type in TERM_OPERATORS:
            operator = self._advance()
            right = self._factor()
            node = ast.BinaryOp(
                line=operator.line,
                column=operator.column,
                operator=TERM_OPERATORS[operator.type],
                left=node,
                right=right,
            )

        return node

    def _factor(self) -> ast.Expression:
        node = self._unary()

        while self._current().type in FACTOR_OPERATORS:
            operator = self._advance()
            right = self._unary()
            node = ast.BinaryOp(
                line=operator.line,
                column=operator.column,
                operator=FACTOR_OPERATORS[operator.type],
                left=node,
                right=right,
            )

        return node

    def _unary(self) -> ast.Expression:
        if self._check(TokenType.MINUS):
            operator = self._advance()
            operand = self._unary()  # so that --x parses
            return ast.UnaryOp(
                line=operator.line,
                column=operator.column,
                operator="-",
                operand=operand,
            )

        return self._postfix()

    def _postfix(self) -> ast.Expression:
        """Calls, indexing and member access, in any order and any number.

        `модул.функсия(рӯйхат[0])` is one loop, not three special cases.
        """
        expression = self._primary()

        while True:
            if self._check(TokenType.LPAREN):
                expression = self._finish_call(expression)
            elif self._check(TokenType.LBRACKET):
                bracket = self._advance()
                index = self._expression()
                self._expect(
                    TokenType.RBRACKET,
                    'Қавси пӯшида "]" ёфт нашуд.',
                    hint='Ҳар қавси "[" бояд бо "]" пӯшида шавад.',
                )
                expression = ast.IndexExpression(
                    line=bracket.line,
                    column=bracket.column,
                    target=expression,
                    index=index,
                )
            elif self._check(TokenType.DOT):
                dot = self._advance()

                # After a dot, a keyword is just a name. `питон.ворид(...)`
                # must work even though `ворид` opens an import statement —
                # a member name is never ambiguous with a statement here.
                current = self._current()
                if current.type is TokenType.IDENT or (
                    isinstance(current.value, str)
                    and current.value in KEYWORD_TOKENS
                ):
                    name = self._advance()
                else:
                    raise self._error(
                        current,
                        'Пас аз "." ном лозим аст.',
                        hint="Масалан: риёзӣ.реша(9)",
                    )

                expression = ast.MemberExpression(
                    line=dot.line,
                    column=dot.column,
                    target=expression,
                    name=name.value,
                )
            else:
                return expression

    def _finish_call(self, callee: ast.Expression) -> ast.CallExpression:
        paren = self._advance()  # consume "("
        arguments: list[ast.Expression] = []

        if not self._check(TokenType.RPAREN):
            arguments.append(self._expression())
            while self._match(TokenType.COMMA):
                # A trailing comma is allowed, as in list and dictionary
                # literals. Multi-line calls are where it earns its keep:
                # adding an argument stays a one-line change.
                if self._check(TokenType.RPAREN):
                    break
                arguments.append(self._expression())

        self._expect(
            TokenType.RPAREN,
            'Қавси пӯшида ")" ёфт нашуд.',
            hint='Ҳар қавси "(" бояд бо ")" пӯшида шавад.',
        )

        return ast.CallExpression(
            line=paren.line, column=paren.column, callee=callee, arguments=arguments
        )

    def _list_literal(self) -> ast.ListLiteral:
        bracket = self._advance()  # consume "["
        elements: list[ast.Expression] = []

        while not self._check(TokenType.RBRACKET):
            elements.append(self._expression())
            if not self._match(TokenType.COMMA):
                break

        self._expect(
            TokenType.RBRACKET,
            'Қавси пӯшида "]" ёфт нашуд.',
            hint="Масалан: [1, 2, 3]",
        )
        return ast.ListLiteral(
            line=bracket.line, column=bracket.column, elements=elements
        )

    def _dict_literal(self) -> ast.DictLiteral:
        brace = self._advance()  # consume "{"
        pairs: list[tuple[ast.Expression, ast.Expression]] = []

        while not self._check(TokenType.RBRACE):
            key = self._expression()
            self._expect(
                TokenType.COLON,
                'Дар луғат пас аз калид аломати ":" лозим аст.',
                hint='Масалан: {"ном": "Баҳром"}',
            )
            pairs.append((key, self._expression()))
            if not self._match(TokenType.COMMA):
                break

        self._expect(
            TokenType.RBRACE,
            'Қавси пӯшида "}" ёфт нашуд.',
            hint='Масалан: {"ном": "Баҳром"}',
        )
        return ast.DictLiteral(line=brace.line, column=brace.column, pairs=pairs)

    def _primary(self) -> ast.Expression:
        token = self._current()

        if self._check(TokenType.NUMBER):
            self._advance()
            return ast.NumberLiteral(token.line, token.column, token.value)

        if self._check(TokenType.STRING):
            self._advance()
            return ast.StringLiteral(token.line, token.column, token.value)

        if self._check(TokenType.TRUE):
            self._advance()
            return ast.BooleanLiteral(token.line, token.column, True)

        if self._check(TokenType.FALSE):
            self._advance()
            return ast.BooleanLiteral(token.line, token.column, False)

        if self._check(TokenType.NULL):
            self._advance()
            return ast.NullLiteral(token.line, token.column)

        if self._check(TokenType.LBRACKET):
            return self._list_literal()

        if self._check(TokenType.LBRACE):
            return self._dict_literal()

        if self._check(TokenType.IDENT):
            self._advance()
            return ast.Identifier(token.line, token.column, token.value)

        if self._match(TokenType.LPAREN):
            inner = self._expression()
            self._expect(TokenType.RPAREN, 'Қавси пӯшида ")" ёфт нашуд.')
            return inner

        if self._check(TokenType.ASSIGN):
            raise self._error(
                token,
                'Аломати "=" дар ин ҷо истифода намешавад.',
                hint="Барои муайян кардани тағйирёбанда: бигзор ном = қимат",
            )

        if self._check(TokenType.NEWLINE) or self._check(TokenType.EOF):
            raise self._error(
                token,
                "Дар ин ҷо қимат интизор мешуд, вале сатр тамом шуд.",
                hint="Матн, рақам ё номи тағйирёбандаро илова кунед.",
            )

        raise self._error(
            token,
            f'Дар ин ҷо қимат интизор мешуд, вале "{token.value}" ёфт шуд.',
            hint="Қимат метавонад матн, рақам ё ном бошад.",
        )
