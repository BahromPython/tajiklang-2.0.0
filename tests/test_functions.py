import unittest

from tajiklang import run_source
from tajiklang.errors import ParseError, RuntimeErrorTJ
from tajiklang.interpreter import MAX_CALL_DEPTH


def run(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


class TestFunctions(unittest.TestCase):
    def test_declare_and_call(self):
        source = "функсия ҷамъ(a, b):\n    баргардон a + b\nнавис(ҷамъ(5, 7))\n"
        self.assertEqual(run(source), ["12"])

    def test_no_parameters(self):
        source = 'функсия салом():\n    навис("Салом")\nсалом()\n'
        self.assertEqual(run(source), ["Салом"])

    def test_a_function_without_return_gives_холӣ(self):
        source = "функсия ҳеҷ():\n    бигзор x = 1\nнавис(ҳеҷ())\n"
        self.assertEqual(run(source), ["холӣ"])

    def test_bare_return_gives_холӣ(self):
        source = "функсия ҳеҷ():\n    баргардон\nнавис(ҳеҷ())\n"
        self.assertEqual(run(source), ["холӣ"])

    def test_return_stops_the_function(self):
        source = (
            "функсия санҷиш():\n"
            "    баргардон 1\n"
            '    навис("ҳеҷ гоҳ")\n'
            "навис(санҷиш())\n"
        )
        self.assertEqual(run(source), ["1"])

    def test_return_from_inside_a_block(self):
        source = (
            "функсия аломат(n):\n"
            "    агар n > 0:\n"
            '        баргардон "мусбат"\n'
            '    баргардон "манфӣ ё сифр"\n'
            "навис(аломат(5))\n"
            "навис(аломат(-5))\n"
        )
        self.assertEqual(run(source), ["мусбат", "манфӣ ё сифр"])

    def test_recursion(self):
        source = (
            "функсия факториал(n):\n"
            "    агар n <= 1:\n"
            "        баргардон 1\n"
            "    баргардон n * факториал(n - 1)\n"
            "навис(факториал(5))\n"
        )
        self.assertEqual(run(source), ["120"])

    def test_functions_are_values(self):
        source = (
            "функсия дучанд(x):\n"
            "    баргардон x * 2\n"
            "бигзор корбар = дучанд\n"
            "навис(корбар(4))\n"
        )
        self.assertEqual(run(source), ["8"])

    def test_a_function_can_call_another(self):
        source = (
            "функсия дучанд(x):\n    баргардон x * 2\n"
            "функсия чорчанд(x):\n    баргардон дучанд(дучанд(x))\n"
            "навис(чорчанд(3))\n"
        )
        self.assertEqual(run(source), ["12"])


class TestScoping(unittest.TestCase):
    def test_a_function_sees_globals(self):
        source = "бигзор андоза = 10\nфунксия калон():\n    баргардон андоза\nнавис(калон())"
        self.assertEqual(run(source), ["10"])

    def test_a_parameter_may_share_a_name_with_a_global(self):
        """Functions must not depend on what the caller named things."""
        source = (
            "бигзор x = 1\n"
            "функсия санҷиш(x):\n    баргардон x * 10\n"
            "навис(санҷиш(5))\n"
            "навис(x)\n"
        )
        self.assertEqual(run(source), ["50", "1"])

    def test_a_local_declaration_may_share_a_name_with_a_global(self):
        source = (
            "бигзор ҳисоб = 1\n"
            "функсия санҷиш():\n"
            "    бигзор ҳисоб = 99\n"
            "    баргардон ҳисоб\n"
            "навис(санҷиш())\n"
            "навис(ҳисоб)\n"
        )
        self.assertEqual(run(source), ["99", "1"])

    def test_a_block_inside_a_function_still_cannot_shadow(self):
        source = (
            "функсия санҷиш():\n"
            "    бигзор x = 1\n"
            "    агар рост:\n"
            "        бигзор x = 2\n"
            "санҷиш()\n"
        )
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run(source)
        self.assertIn("аллакай муайян шудааст", ctx.exception.message)

    def test_locals_do_not_escape(self):
        source = "функсия санҷиш():\n    бигзор пинҳон = 1\nсанҷиш()\nнавис(пинҳон)\n"
        with self.assertRaises(RuntimeErrorTJ):
            run(source)

    def test_closures_capture_the_defining_scope(self):
        """A function sees the names that surrounded its own text."""
        source = (
            "бигзор зарб = 3\n"
            "функсия сегона(x):\n    баргардон x * зарб\n"
            "функсия даъват(f):\n"
            "    бигзор зарб_дигар = 100\n"
            "    баргардон f(2)\n"
            "навис(даъват(сегона))\n"
        )
        self.assertEqual(run(source), ["6"])


class TestBuiltinNames(unittest.TestCase):
    def test_a_builtin_name_can_be_used_as_a_variable(self):
        """`дарозӣ` was a fine variable name in 0.2 and a builtin from 0.7.

        Refusing this would mean every builtin added later breaks programs
        that happened to use that word.
        """
        self.assertEqual(run("бигзор дарозӣ = 7.5\nнавис(дарозӣ)"), ["7.5"])

    def test_a_builtin_name_can_be_used_as_a_parameter(self):
        source = "функсия майдон(дарозӣ, паҳно):\n    баргардон дарозӣ * паҳно\nнавис(майдон(3, 4))"
        self.assertEqual(run(source), ["12"])

    def test_the_builtin_still_works_where_it_is_not_shadowed(self):
        source = "функсия f():\n    бигзор дарозӣ = 1\n    баргардон дарозӣ\nнавис(f())\nнавис(дарозӣ([1, 2]))"
        self.assertEqual(run(source), ["1", "2"])

    def test_a_builtin_cannot_be_assigned_over(self):
        """`навис = 5` must not silently replace printing."""
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("навис = 5")
        self.assertIn("муайян нашудааст", ctx.exception.message)
        self.assertIn("бигзор", ctx.exception.hint)


class TestFunctionErrors(unittest.TestCase):
    def test_too_few_arguments(self):
        source = "функсия ҷамъ(a, b):\n    баргардон a + b\nнавис(ҷамъ(1))\n"
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run(source)
        self.assertIn("2 аргумент мехоҳад", ctx.exception.message)
        self.assertIn("a, b", ctx.exception.hint)

    def test_too_many_arguments(self):
        source = "функсия як(a):\n    баргардон a\nнавис(як(1, 2))\n"
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run(source)
        self.assertIn("1 аргумент мехоҳад", ctx.exception.message)

    def test_runaway_recursion_is_stopped(self):
        source = "функсия беохир(n):\n    баргардон беохир(n + 1)\nбеохир(1)\n"
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run(source)
        self.assertIn(str(MAX_CALL_DEPTH), ctx.exception.message)
        self.assertIn("ҳолати хотима", ctx.exception.hint)

    def test_return_outside_a_function_is_a_syntax_error(self):
        with self.assertRaises(ParseError) as ctx:
            run("баргардон 1\n")
        self.assertIn("танҳо дар дохили функсия", ctx.exception.message)

    def test_duplicate_parameter_names(self):
        with self.assertRaises(ParseError) as ctx:
            run("функсия санҷиш(a, a):\n    баргардон a\n")
        self.assertIn("ду бор навишта шудааст", ctx.exception.message)

    def test_a_function_cannot_take_a_taken_name(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("бигзор ҷамъ = 1\nфунксия ҷамъ(a):\n    баргардон a\n")
        self.assertIn("аллакай муайян шудааст", ctx.exception.message)


if __name__ == "__main__":
    unittest.main()
