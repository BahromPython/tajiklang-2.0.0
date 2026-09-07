import unittest

from tajiklang import ast_nodes as ast
from tajiklang.errors import ParseError
from tajiklang.lexer import Lexer
from tajiklang.parser import Parser


def parse(source):
    lexer = Lexer(source)
    return Parser(lexer.tokenize(), lexer.lines).parse()


def first(source):
    return parse(source).statements[0]


class TestCalls(unittest.TestCase):
    def test_call_with_one_argument(self):
        program = parse('навис("Салом")')
        self.assertEqual(len(program.statements), 1)

        call = program.statements[0].expression
        self.assertIsInstance(call, ast.CallExpression)
        self.assertEqual(call.callee.name, "навис")
        self.assertEqual(len(call.arguments), 1)
        self.assertEqual(call.arguments[0].value, "Салом")

    def test_call_with_several_arguments(self):
        call = first('навис("Салом", 2026)').expression
        self.assertEqual([a.value for a in call.arguments], ["Салом", 2026])

    def test_call_with_no_arguments(self):
        self.assertEqual(first("навис()").expression.arguments, [])

    def test_blank_lines_and_comments_are_not_statements(self):
        self.assertEqual(len(parse('\n# шарҳ\n\nнавис("а")\n').statements), 1)

    def test_two_statements(self):
        self.assertEqual(len(parse('навис("а")\nнавис("б")').statements), 2)


class TestDeclarationAndAssignment(unittest.TestCase):
    def test_declaration(self):
        node = first("бигзор x = 10")
        self.assertIsInstance(node, ast.VarDeclaration)
        self.assertEqual(node.name, "x")
        self.assertEqual(node.value.value, 10)

    def test_assignment(self):
        node = first("x = 10")
        self.assertIsInstance(node, ast.Assignment)
        self.assertEqual(node.name, "x")

    def test_a_bare_name_is_still_an_expression(self):
        self.assertIsInstance(first("x"), ast.ExpressionStatement)

    def test_a_name_in_arithmetic_is_not_an_assignment(self):
        node = first("x + 1")
        self.assertIsInstance(node, ast.ExpressionStatement)
        self.assertIsInstance(node.expression, ast.BinaryOp)

    def test_declaration_without_a_name(self):
        with self.assertRaises(ParseError) as ctx:
            parse("бигзор = 10")
        self.assertIn("номи тағйирёбанда лозим аст", ctx.exception.message)

    def test_declaration_without_a_value(self):
        with self.assertRaises(ParseError) as ctx:
            parse("бигзор x")
        self.assertIn('аломати "=" лозим аст', ctx.exception.message)


class TestPrecedence(unittest.TestCase):
    def test_multiplication_binds_tighter_than_addition(self):
        """2 + 3 * 4 must parse as 2 + (3 * 4), i.e. * sits deeper."""
        top = first("2 + 3 * 4").expression
        self.assertEqual(top.operator, "+")
        self.assertEqual(top.left.value, 2)
        self.assertEqual(top.right.operator, "*")

    def test_parentheses_override_precedence(self):
        top = first("(2 + 3) * 4").expression
        self.assertEqual(top.operator, "*")
        self.assertEqual(top.left.operator, "+")

    def test_subtraction_is_left_associative(self):
        """10 - 3 - 2 must be (10 - 3) - 2, not 10 - (3 - 2)."""
        top = first("10 - 3 - 2").expression
        self.assertEqual(top.operator, "-")
        self.assertEqual(top.left.operator, "-")
        self.assertEqual(top.right.value, 2)

    def test_unary_minus(self):
        node = first("-5").expression
        self.assertIsInstance(node, ast.UnaryOp)
        self.assertEqual(node.operand.value, 5)

    def test_unary_minus_binds_tighter_than_multiplication(self):
        top = first("-2 * 3").expression
        self.assertEqual(top.operator, "*")
        self.assertIsInstance(top.left, ast.UnaryOp)


class TestLogicAndComparison(unittest.TestCase):
    def test_boolean_and_null_literals(self):
        self.assertIs(first("рост").expression.value, True)
        self.assertIs(first("дурӯғ").expression.value, False)
        self.assertIsInstance(first("холӣ").expression, ast.NullLiteral)

    def test_logical_operators_get_their_own_node(self):
        """`ва` is a LogicalOp, not a BinaryOp — it may skip its right side."""
        node = first("рост ва дурӯғ").expression
        self.assertIsInstance(node, ast.LogicalOp)
        self.assertNotIsInstance(node, ast.BinaryOp)

    def test_comparison_binds_tighter_than_and(self):
        """x > 1 ва x < 5 must be (x > 1) ва (x < 5)."""
        top = first("x > 1 ва x < 5").expression
        self.assertIsInstance(top, ast.LogicalOp)
        self.assertEqual(top.left.operator, ">")
        self.assertEqual(top.right.operator, "<")

    def test_and_binds_tighter_than_or(self):
        """а ё б ва в must be а ё (б ва в)."""
        top = first("а ё б ва в").expression
        self.assertEqual(top.operator, "ё")
        self.assertEqual(top.right.operator, "ва")

    def test_not_binds_tighter_than_and(self):
        top = first("не а ва б").expression
        self.assertEqual(top.operator, "ва")
        self.assertEqual(top.left.operator, "не")

    def test_arithmetic_binds_tighter_than_comparison(self):
        """2 + 3 > 4 must be (2 + 3) > 4."""
        top = first("2 + 3 > 4").expression
        self.assertEqual(top.operator, ">")
        self.assertEqual(top.left.operator, "+")

    def test_chained_comparison_is_rejected(self):
        with self.assertRaises(ParseError) as ctx:
            parse("навис(1 < 2 < 3)")
        self.assertIn("Ду муқоиса", ctx.exception.message)
        self.assertIn("ва", ctx.exception.hint)


class TestIfStatement(unittest.TestCase):
    def test_if_without_else(self):
        node = first('агар x:\n    навис(1)\n')
        self.assertIsInstance(node, ast.IfStatement)
        self.assertEqual(len(node.then_branch), 1)
        self.assertIsNone(node.else_branch)

    def test_if_else(self):
        node = first('агар x:\n    навис(1)\nвагарна:\n    навис(2)\n')
        self.assertEqual(len(node.else_branch), 1)

    def test_else_if_nests_a_second_if(self):
        """`вагарна агар` needs no node of its own."""
        node = first(
            "агар x:\n    навис(1)\n"
            "вагарна агар y:\n    навис(2)\n"
            "вагарна:\n    навис(3)\n"
        )
        inner = node.else_branch[0]
        self.assertIsInstance(inner, ast.IfStatement)
        self.assertEqual(len(inner.else_branch), 1)

    def test_a_block_holds_several_statements(self):
        node = first("агар x:\n    навис(1)\n    навис(2)\n    навис(3)\n")
        self.assertEqual(len(node.then_branch), 3)

    def test_nested_if(self):
        node = first("агар x:\n    агар y:\n        навис(1)\n")
        self.assertIsInstance(node.then_branch[0], ast.IfStatement)

    def test_statements_after_the_block_are_siblings_not_children(self):
        program = parse("агар x:\n    навис(1)\nнавис(2)\n")
        self.assertEqual(len(program.statements), 2)
        self.assertEqual(len(program.statements[0].then_branch), 1)

    def test_missing_colon(self):
        with self.assertRaises(ParseError) as ctx:
            parse("агар x\n    навис(1)\n")
        self.assertIn('аломати ":" лозим аст', ctx.exception.message)

    def test_a_block_may_start_with_a_comment(self):
        """Explaining a block on its first line is ordinary writing.

        Comment and blank lines carry no indentation, so each arrives as
        a bare NEWLINE before the INDENT — which the block rule used to
        read as an empty block.
        """
        source = chr(10).join(["агар x:", "    # чӣ мекунад", "    навис(1)"])
        self.assertEqual(len(first(source).then_branch), 1)

    def test_a_block_may_start_with_a_blank_line(self):
        source = chr(10).join(["агар x:", "", "    навис(1)"])
        self.assertEqual(len(first(source).then_branch), 1)

    def test_several_blank_and_comment_lines_before_the_body(self):
        source = chr(10).join(
            ["агар x:", "", "    # як", "", "    # ду", "    навис(1)"]
        )
        self.assertEqual(len(first(source).then_branch), 1)

    def test_a_class_body_may_start_with_a_comment(self):
        source = chr(10).join([
            "қолиб А:", "    # шарҳ", "    функсия f(худ):",
            "        баргардон 1",
        ])
        self.assertEqual(len(parse(source).statements[0].methods), 1)

    def test_empty_block(self):
        with self.assertRaises(ParseError) as ctx:
            parse("агар x:\nнавис(1)\n")
        self.assertIn("блоки холӣ", ctx.exception.message)

    def test_else_without_if(self):
        with self.assertRaises(ParseError) as ctx:
            parse("навис(1)\nвагарна:\n    навис(2)\n")
        self.assertIn('бе "агар"', ctx.exception.message)

    def test_indent_with_no_block_to_open(self):
        with self.assertRaises(ParseError) as ctx:
            parse("навис(1)\n    навис(2)\n")
        self.assertIn("бе сабаб фосила", ctx.exception.message)


class TestParseErrors(unittest.TestCase):
    def test_missing_closing_paren(self):
        with self.assertRaises(ParseError) as ctx:
            parse('навис("Салом"')
        self.assertIn("Қавси пӯшида", ctx.exception.message)

    def test_a_trailing_comma_is_allowed(self):
        """Consistent with list literals, and needed for multi-line calls."""
        self.assertEqual(len(first('навис("а",)').expression.arguments), 1)
        self.assertEqual(len(first('навис("а", "б",)').expression.arguments), 2)

    def test_two_statements_on_one_line_are_rejected(self):
        with self.assertRaises(ParseError) as ctx:
            parse('навис("а") навис("б")')
        self.assertIn("сатри алоҳида", ctx.exception.hint)

    def test_operator_without_a_right_hand_side(self):
        with self.assertRaises(ParseError) as ctx:
            parse("навис(2 +)")
        self.assertIn("қимат интизор мешуд", ctx.exception.message)

    def test_assignment_is_not_an_expression(self):
        """навис(x = 1) must be rejected, so `=` can never hide inside a test."""
        with self.assertRaises(ParseError) as ctx:
            parse("навис(x = 1)")
        self.assertIn("бигзор", ctx.exception.hint)


if __name__ == "__main__":
    unittest.main()
