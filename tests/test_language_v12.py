"""Version 1.2: pre-run checking, decimal arithmetic, Python interop."""

import unittest
from decimal import Decimal

from tajiklang import CheckFailed, check_source, run_source
from tajiklang.errors import RuntimeErrorTJ


def run(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def one(expression):
    return run("навис(" + expression + ")")[0]


def problems(source):
    return [d.message for d in check_source(source) if not d.is_warning]


def warnings(source):
    return [d.message for d in check_source(source) if d.is_warning]


class TestCheckerFindsRealProblems(unittest.TestCase):
    def test_a_typo_in_a_branch_that_never_runs(self):
        """Python finds this only if that branch ever executes."""
        source = 'бигзор ном = "а"\nагар дурӯғ:\n    навис(нмо)\n'
        self.assertEqual(len(problems(source)), 1)
        self.assertIn("нмо", problems(source)[0])

    def test_every_problem_is_reported_at_once(self):
        source = "навис(аввал)\nдуюм = 5\nнавис(сеюм)\n"
        self.assertEqual(len(problems(source)), 3)

    def test_wrong_argument_count(self):
        source = "функсия ҷамъ(a, b):\n    баргардон a + b\nнавис(ҷамъ(1))\n"
        self.assertIn("2 аргумент мехоҳад", problems(source)[0])

    def test_unreachable_code(self):
        source = 'функсия f():\n    баргардон 1\n    навис("ҳеҷ гоҳ")\nнавис(f())\n'
        self.assertIn("ҳеҷ гоҳ иҷро намешавад", problems(source)[0])

    def test_unreachable_after_шикан(self):
        source = 'барои i аз 1 то 3:\n    шикан\n    навис(i)\n'
        self.assertIn("ҳеҷ гоҳ иҷро намешавад", problems(source)[0])

    def test_redeclaration(self):
        source = "бигзор x = 1\nбигзор x = 2\n"
        self.assertIn("аллакай муайян шудааст", problems(source)[0])

    def test_an_unused_variable_is_only_a_warning(self):
        source = (
            "функсия f():\n"
            "    бигзор истифоданашуда = 5\n"
            "    баргардон 1\n"
            "навис(f())\n"
        )
        self.assertEqual(problems(source), [])
        self.assertIn("истифода нашуд", warnings(source)[0])

    def test_the_suggestion_names_the_closest_name(self):
        source = 'бигзор ном = "а"\nнавис(нмо)\n'
        found = [d for d in check_source(source) if not d.is_warning]
        self.assertIn("ном", found[0].hint)


class TestCheckerHasNoFalseAlarms(unittest.TestCase):
    """A checker that cries wolf is worse than none — pin the quiet cases."""

    def test_mutual_recursion_declared_later(self):
        source = (
            "функсия ҷуфт(n):\n"
            "    агар n == 0:\n"
            "        баргардон рост\n"
            "    баргардон тоқ(n - 1)\n"
            "функсия тоқ(n):\n"
            "    агар n == 0:\n"
            "        баргардон дурӯғ\n"
            "    баргардон ҷуфт(n - 1)\n"
            "навис(ҷуфт(4))\n"
        )
        self.assertEqual(problems(source), [])
        self.assertEqual(run(source), ["рост"])

    def test_a_builtin_name_may_be_reused(self):
        """The checker must agree with the interpreter, which allows this."""
        self.assertEqual(problems("бигзор дарозӣ = 7.5\nнавис(дарозӣ)"), [])

    def test_loop_variables_parameters_imports_and_catch_bindings(self):
        source = (
            "ворид риёзӣ\n"
            "функсия f(x):\n"
            "    баргардон x * 2\n"
            "барои i аз 1 то 3:\n"
            "    навис(f(i), риёзӣ.реша(i))\n"
            'барои ном аз ["а"]:\n'
            "    навис(ном)\n"
            "кӯшиш:\n"
            "    навис(1 / 0)\n"
            "хато паём:\n"
            "    навис(паём)\n"
        )
        self.assertEqual(problems(source), [])

    def test_every_shipped_example_is_clean(self):
        from pathlib import Path

        folder = Path(__file__).resolve().parent.parent / "examples"
        for path in sorted(folder.glob("*.tj")):
            if "хато" in path.name:
                continue           # these fail on purpose
            with self.subTest(example=path.name):
                self.assertEqual(problems(path.read_text(encoding="utf-8")), [])


class TestCheckingBeforeRunning(unittest.TestCase):
    def test_nothing_runs_when_a_check_fails(self):
        source = 'навис("ин чоп намешавад")\nнавис(нест)\n'
        lines = []
        with self.assertRaises(CheckFailed):
            run_source(source, output=lines.append, check=True)
        self.assertEqual(lines, [])

    def test_the_report_counts_the_problems(self):
        source = "навис(аввал)\nнавис(дуюм)\n"
        try:
            run_source(source, output=lambda _: None, check=True)
        except CheckFailed as failure:
            text = failure.format()
        self.assertIn("Ҳамагӣ 2 хато", text)
        self.assertIn("Барнома иҷро нашуд", text)

    def test_a_clean_program_runs_normally(self):
        lines = []
        run_source('навис("хуб")', output=lines.append, check=True)
        self.assertEqual(lines, ["хуб"])


class TestDecimalArithmetic(unittest.TestCase):
    def test_the_famous_one(self):
        """Python, C, Java and JavaScript all say 0.30000000000000004."""
        self.assertEqual(one("0.1 + 0.2"), "0.3")
        self.assertEqual(one("0.1 + 0.2 == 0.3"), "рост")

    def test_money(self):
        self.assertEqual(one("19.99 * 3"), "59.97")
        self.assertEqual(one("0.1 * 3 == 0.3"), "рост")

    def test_integers_stay_integers(self):
        self.assertEqual(one("2 + 2"), "4")
        self.assertEqual(one("10 / 5"), "2")

    def test_division_produces_a_fraction(self):
        self.assertEqual(one("10 / 4"), "2.5")
        self.assertEqual(one("7 % 3"), "1")

    def test_a_repeating_fraction_is_finite_but_long(self):
        self.assertTrue(one("1 / 3").startswith("0.3333333333"))

    def test_comparison_across_int_and_decimal(self):
        self.assertEqual(one("2 == 2.0"), "рост")
        self.assertEqual(one("2.5 > 2"), "рост")

    def test_builtins_return_decimals_not_floats(self):
        """A stray float would fail far from its source, so nothing may make one."""
        self.assertEqual(one("реша(2) + 0.1 > 1.5"), "рост")
        self.assertEqual(one("миёна([1, 2]) + 0.5"), "2")

    def test_rounding(self):
        self.assertEqual(one("гирд(3.14159, 2)"), "3.14")
        self.assertEqual(one("гирд(2.5)"), "2")     # banker's rounding

    def test_ба_рақам_gives_a_decimal(self):
        self.assertEqual(one('ба_рақам("0.1") + ба_рақам("0.2") == 0.3'), "рост")

    def test_the_value_really_is_a_decimal(self):
        captured = []
        run_source("навис(0.1)", output=captured.append)
        self.assertEqual(captured, ["0.1"])
        self.assertEqual(Decimal("0.1") + Decimal("0.2"), Decimal("0.3"))


class TestPythonInterop(unittest.TestCase):
    def test_importing_and_calling(self):
        source = 'ворид питон\nбигзор m = питон.ворид("math")\nнавис(m.factorial(5))'
        self.assertEqual(run(source), ["120"])

    def test_a_module_with_a_list_argument(self):
        source = (
            "ворид питон\n"
            'бигзор омор = питон.ворид("statistics")\n'
            "навис(омор.median([3, 1, 4, 1, 5]))"
        )
        self.assertEqual(run(source), ["3"])

    def test_a_python_constant(self):
        source = 'ворид питон\nнавис(гирд(питон.ворид("math").pi, 4))'
        self.assertEqual(run(source), ["3.1416"])

    def test_a_python_float_arrives_as_a_decimal(self):
        """Otherwise Python's binary floats walk in through the back door."""
        source = (
            "ворид питон\n"
            'бигзор m = питон.ворид("math")\n'
            "навис(m.floor(3.7))\n"
            "навис(m.sqrt(2) + 0.1 > 1.5)\n"
        )
        self.assertEqual(run(source), ["3", "рост"])

    def test_a_python_error_becomes_a_tajik_error(self):
        source = 'ворид питон\nнавис(питон.ворид("math").sqrt(-1))'
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run(source)
        self.assertIn("хато дод", ctx.exception.message)
        self.assertIn("ValueError", ctx.exception.message)
        self.assertIn("китобхонаи Python", ctx.exception.hint)

    def test_a_python_error_can_be_caught(self):
        source = (
            "ворид питон\n"
            "кӯшиш:\n"
            '    навис(питон.ворид("math").sqrt(-1))\n'
            "хато паём:\n"
            '    навис("гирифтам")\n'
        )
        self.assertEqual(run(source), ["гирифтам"])

    def test_a_missing_module(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('ворид питон\nнавис(питон.ворид("ин_модул_нест").x)')
        self.assertIn("ёфт нашуд", ctx.exception.message)

    def test_a_missing_attribute(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('ворид питон\nнавис(питон.ворид("math").ҳеҷ_чиз)')
        self.assertIn("надорад", ctx.exception.message)

    def test_private_names_are_refused(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('ворид питон\nнавис(питон.ворид("math").__name__)')
        self.assertIn("хусусӣ", ctx.exception.message)

    def test_python_is_opt_in(self):
        """No program touches Python unless it says so."""
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('навис(питон.ворид("math"))')
        self.assertIn("муайян нашудааст", ctx.exception.message)

    def test_a_keyword_may_follow_a_dot(self):
        """`питон.ворид` must parse even though `ворид` starts a statement."""
        self.assertEqual(problems('ворид питон\nбигзор m = питон.ворид("math")'), [])


if __name__ == "__main__":
    unittest.main()
