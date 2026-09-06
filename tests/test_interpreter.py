import unittest

from tajiklang import run_source
from tajiklang.errors import RuntimeErrorTJ


def run(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def one(expression):
    """Evaluate a single expression by printing it."""
    return run("навис(" + expression + ")")[0]


class TestPrinting(unittest.TestCase):
    def test_hello_world(self):
        self.assertEqual(run('навис("Салом Тоҷикистон!")'), ["Салом Тоҷикистон!"])

    def test_several_arguments_are_space_separated(self):
        self.assertEqual(run('навис("Салом", "Баҳром")'), ["Салом Баҳром"])

    def test_numbers_print_without_trailing_zero(self):
        self.assertEqual(one("4.0"), "4")
        self.assertEqual(one("3.5"), "3.5")

    def test_no_arguments_prints_empty_line(self):
        self.assertEqual(run("навис()"), [""])

    def test_each_statement_prints_once(self):
        self.assertEqual(run('навис("а")\nнавис("б")'), ["а", "б"])


class TestVariables(unittest.TestCase):
    def test_declare_and_use(self):
        self.assertEqual(run('бигзор ном = "Баҳром"\nнавис(ном)'), ["Баҳром"])

    def test_tajik_variable_name(self):
        self.assertEqual(run("бигзор ҳарорат = 30\nнавис(ҳарорат)"), ["30"])

    def test_reassignment_without_the_keyword(self):
        self.assertEqual(run("бигзор x = 1\nx = 2\nнавис(x)"), ["2"])

    def test_a_variable_can_be_defined_from_another(self):
        self.assertEqual(run("бигзор a = 2\nбигзор b = a * 3\nнавис(b)"), ["6"])

    def test_redeclaring_is_an_error(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("бигзор x = 1\nбигзор x = 2")
        self.assertIn("аллакай муайян шудааст", ctx.exception.message)

    def test_assigning_to_an_undeclared_name_is_an_error(self):
        """The typo guard: `нмо = 5` must not silently create a new variable."""
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('бигзор ном = "Баҳром"\nнмо = "Далер"')
        self.assertIn("муайян нашудааст", ctx.exception.message)
        self.assertIn("бигзор", ctx.exception.hint)

    def test_unknown_name_suggests_the_closest_one(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('нависед("Салом")')
        self.assertIn("навис", ctx.exception.hint)


class TestArithmetic(unittest.TestCase):
    def test_four_operations(self):
        self.assertEqual(one("2 + 3"), "5")
        self.assertEqual(one("10 - 4"), "6")
        self.assertEqual(one("6 * 7"), "42")
        self.assertEqual(one("9 / 2"), "4.5")

    def test_modulo(self):
        self.assertEqual(one("10 % 3"), "1")

    def test_precedence(self):
        self.assertEqual(one("2 + 3 * 4"), "14")
        self.assertEqual(one("(2 + 3) * 4"), "20")

    def test_left_associativity(self):
        self.assertEqual(one("10 - 3 - 2"), "5")
        self.assertEqual(one("100 / 5 / 2"), "10")

    def test_unary_minus(self):
        self.assertEqual(one("-5 + 2"), "-3")
        self.assertEqual(one("-(2 + 3)"), "-5")

    def test_integers_stay_exact(self):
        self.assertEqual(one("2 + 2"), "4")

    def test_division_always_produces_a_number_not_a_fraction(self):
        self.assertEqual(one("10 / 5"), "2")

    def test_string_concatenation(self):
        self.assertEqual(one('"Салом " + "Баҳром"'), "Салом Баҳром")


class TestComparison(unittest.TestCase):
    def test_numeric_comparison(self):
        self.assertEqual(one("16 >= 16"), "рост")
        self.assertEqual(one("16 > 16"), "дурӯғ")
        self.assertEqual(one("2 != 3"), "рост")

    def test_integers_and_floats_compare_equal(self):
        self.assertEqual(one("2 == 2.0"), "рост")

    def test_booleans_are_not_numbers(self):
        """рост == 1 must be дурӯғ, even though Python says True == 1."""
        self.assertEqual(one("рост == 1"), "дурӯғ")

    def test_different_kinds_are_never_equal(self):
        self.assertEqual(one('1 == "1"'), "дурӯғ")
        self.assertEqual(one('холӣ == 0'), "дурӯғ")
        self.assertEqual(one("холӣ == холӣ"), "рост")

    def test_strings_compare_by_the_tajik_alphabet(self):
        """The whole point of collation.py, reachable from the language."""
        self.assertEqual(one('"Ғафуров" < "Яқубов"'), "рост")
        self.assertEqual(one('"г" < "ғ"'), "рост")

    def test_ordering_needs_matching_types(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('навис(1 < "а")')
        self.assertIn("рақам ва матн", ctx.exception.message)


class TestLogic(unittest.TestCase):
    def test_and_or_not(self):
        self.assertEqual(one("рост ва дурӯғ"), "дурӯғ")
        self.assertEqual(one("рост ё дурӯғ"), "рост")
        self.assertEqual(one("не дурӯғ"), "рост")

    def test_combined_with_comparison(self):
        self.assertEqual(run("бигзор x = 16\nнавис(x > 10 ва x < 20)"), ["рост"])

    def test_and_short_circuits(self):
        """The right side must not run when the left already decides it."""
        self.assertEqual(one("дурӯғ ва 1 / 0 == 1"), "дурӯғ")

    def test_or_short_circuits(self):
        self.assertEqual(one("рост ё 1 / 0 == 1"), "рост")

    def test_there_is_no_truthiness(self):
        for source in ("не 0", '"матн" ва рост', "1 ё дурӯғ", "холӣ ва рост"):
            with self.subTest(source=source):
                with self.assertRaises(RuntimeErrorTJ) as ctx:
                    run("навис(" + source + ")")
                self.assertIn("қимати мантиқӣ мехоҳад", ctx.exception.message)

    def test_booleans_print_in_tajik(self):
        self.assertEqual(run("навис(рост, дурӯғ, холӣ)"), ["рост дурӯғ холӣ"])


class TestIfStatement(unittest.TestCase):
    def test_true_branch_runs(self):
        self.assertEqual(run('агар рост:\n    навис("ҳа")\n'), ["ҳа"])

    def test_false_branch_is_skipped(self):
        self.assertEqual(run('агар дурӯғ:\n    навис("ҳа")\n'), [])

    def test_else_runs_when_the_condition_is_false(self):
        source = 'агар дурӯғ:\n    навис("ҳа")\nвагарна:\n    навис("не")\n'
        self.assertEqual(run(source), ["не"])

    def test_else_if_chain_picks_the_first_match(self):
        source = (
            "бигзор синну_сол = 16\n"
            'агар синну_сол >= 18:\n    навис("калонсол")\n'
            'вагарна агар синну_сол >= 16:\n    навис("наврас")\n'
            'вагарна:\n    навис("хурд")\n'
        )
        self.assertEqual(run(source), ["наврас"])

    def test_only_one_branch_runs(self):
        source = (
            "бигзор x = 5\n"
            'агар x > 0:\n    навис("мусбат")\n'
            'вагарна агар x > -10:\n    навис("хурд")\n'
        )
        self.assertEqual(run(source), ["мусбат"])

    def test_nested_if(self):
        source = (
            "бигзор x = 4\n"
            "агар x > 0:\n"
            '    навис("мусбат")\n'
            "    агар x % 2 == 0:\n"
            '        навис("ҷуфт")\n'
        )
        self.assertEqual(run(source), ["мусбат", "ҷуфт"])

    def test_statements_after_the_block_always_run(self):
        source = 'агар дурӯғ:\n    навис("ҳа")\nнавис("баъд")\n'
        self.assertEqual(run(source), ["баъд"])

    def test_the_condition_must_be_a_boolean(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('бигзор ном = "Баҳром"\nагар ном:\n    навис(1)\n')
        self.assertIn('Шарти "агар"', ctx.exception.message)
        self.assertIn("матн гирифт", ctx.exception.message)


class TestBlockScope(unittest.TestCase):
    def test_a_block_can_change_an_outer_variable(self):
        """The pattern we teach: declare outside, assign inside."""
        source = (
            'бигзор натиҷа = ""\n'
            'агар рост:\n    натиҷа = "калон"\n'
            "навис(натиҷа)\n"
        )
        self.assertEqual(run(source), ["калон"])

    def test_a_block_can_read_an_outer_variable(self):
        self.assertEqual(run("бигзор x = 7\nагар рост:\n    навис(x)\n"), ["7"])

    def test_a_name_declared_in_a_block_does_not_escape(self):
        source = 'агар рост:\n    бигзор ичозат = 1\nнавис(ичозат)\n'
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run(source)
        self.assertIn("дар дохили блок эълон шуда буд", ctx.exception.message)
        self.assertIn("пеш аз блок эълон кунед", ctx.exception.hint)

    def test_a_block_cannot_shadow_an_outer_name(self):
        source = "бигзор x = 1\nагар рост:\n    бигзор x = 2\n"
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run(source)
        self.assertIn("аллакай муайян шудааст", ctx.exception.message)


class TestRuntimeErrors(unittest.TestCase):
    def test_division_by_zero(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("навис(1 / 0)")
        self.assertIn("Тақсим ба сифр", ctx.exception.message)

    def test_modulo_by_zero(self):
        with self.assertRaises(RuntimeErrorTJ):
            run("навис(1 % 0)")

    def test_adding_a_string_to_a_number(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('навис("синну сол: " + 16)')
        self.assertIn("матн ва рақам", ctx.exception.message)

    def test_multiplying_strings(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('навис("а" * "б")')
        self.assertIn("танҳо барои рақамҳо", ctx.exception.hint)

    def test_negating_a_string(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('навис(-"а")')
        self.assertIn("барои матн", ctx.exception.message)

    def test_calling_a_non_function(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('"матн"()')
        self.assertIn("функсия даъват кардан мумкин нест", ctx.exception.message)

    def test_the_error_points_at_the_operator(self):
        try:
            run('навис("а" + 1)')
        except RuntimeErrorTJ as error:
            self.assertEqual(error.line, 1)
            # column of the "+" itself (11), not of the whole expression
            self.assertEqual(error.column, 11)


class TestErrorFormatting(unittest.TestCase):
    def test_caret_points_at_the_column(self):
        try:
            run('навис("Салом"')
        except Exception as error:
            text = error.format()
        self.assertIn("сатри 1", text)
        caret_line = [l for l in text.splitlines() if l.strip() == "^"][0]
        self.assertEqual(caret_line.index("^"), 4 + 13)  # 4-space indent + column-1


if __name__ == "__main__":
    unittest.main()
