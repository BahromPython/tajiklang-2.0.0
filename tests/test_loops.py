import unittest

from tajiklang import run_source
from tajiklang.errors import ParseError, RuntimeErrorTJ
from tajiklang.interpreter import MAX_ITERATIONS


def run(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


class TestForRange(unittest.TestCase):
    def test_both_ends_are_inclusive(self):
        """аз 1 то 5 runs five times — "from 1 to 5" means what it says."""
        self.assertEqual(run("барои i аз 1 то 5:\n    навис(i)\n"),
                         ["1", "2", "3", "4", "5"])

    def test_a_single_step_range(self):
        self.assertEqual(run("барои i аз 3 то 3:\n    навис(i)\n"), ["3"])

    def test_a_backwards_range_counts_down(self):
        self.assertEqual(run("барои i аз 3 то 1:\n    навис(i)\n"), ["3", "2", "1"])

    def test_the_bounds_can_be_expressions(self):
        source = "бигзор n = 2\nбарои i аз n то n + 2:\n    навис(i)\n"
        self.assertEqual(run(source), ["2", "3", "4"])

    def test_the_loop_variable_does_not_escape(self):
        with self.assertRaises(RuntimeErrorTJ):
            run("барои i аз 1 то 2:\n    навис(i)\nнавис(i)\n")

    def test_declaring_inside_the_body_works_every_iteration(self):
        """One scope per iteration, not one per loop."""
        source = "барои i аз 1 то 3:\n    бигзор дучанд = i * 2\n    навис(дучанд)\n"
        self.assertEqual(run(source), ["2", "4", "6"])

    def test_the_body_can_change_an_outer_variable(self):
        source = "бигзор ҷамъ = 0\nбарои i аз 1 то 4:\n    ҷамъ = ҷамъ + i\nнавис(ҷамъ)"
        self.assertEqual(run(source), ["10"])

    def test_bounds_must_be_numbers(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('барои i аз 1 то "панҷ":\n    навис(i)\n')
        self.assertIn("бояд рақам бошад", ctx.exception.message)


class TestForEach(unittest.TestCase):
    def test_walking_a_list(self):
        source = 'бигзор ҳа = ["а", "б"]\nбарои x аз ҳа:\n    навис(x)\n'
        self.assertEqual(run(source), ["а", "б"])

    def test_walking_a_dictionary_walks_its_keys(self):
        source = 'бигзор л = {"а": 1, "б": 2}\nбарои к аз л:\n    навис(к)\n'
        self.assertEqual(run(source), ["а", "б"])

    def test_walking_a_string_walks_its_letters(self):
        self.assertEqual(run('барои ҳ аз "ғоз":\n    навис(ҳ)\n'), ["ғ", "о", "з"])

    def test_walking_a_number_is_an_error(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("барои x аз 5:\n    навис(x)\n")
        self.assertIn("гузаштан мумкин нест", ctx.exception.message)
        self.assertIn("аз 1 то 10", ctx.exception.hint)


class TestWhile(unittest.TestCase):
    def test_counting(self):
        source = "бигзор n = 0\nто_вақте n < 3:\n    n = n + 1\n    навис(n)\n"
        self.assertEqual(run(source), ["1", "2", "3"])

    def test_a_false_condition_never_runs(self):
        self.assertEqual(run('то_вақте дурӯғ:\n    навис("ҳеҷ гоҳ")\n'), [])

    def test_the_condition_must_be_a_boolean(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('то_вақте "матн":\n    навис(1)\n')
        self.assertIn('Шарти "то_вақте"', ctx.exception.message)

    def test_an_endless_loop_is_stopped_with_an_explanation(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("то_вақте рост:\n    бигзор x = 1\n")
        self.assertIn(str(MAX_ITERATIONS), ctx.exception.message)
        self.assertIn("шарти хотима", ctx.exception.hint)


class TestLoopSyntax(unittest.TestCase):
    def test_missing_from(self):
        with self.assertRaises(ParseError) as ctx:
            run("барои i 1 то 5:\n    навис(i)\n")
        self.assertIn('калимаи "аз" лозим аст', ctx.exception.message)

    def test_missing_colon(self):
        with self.assertRaises(ParseError) as ctx:
            run("барои i аз 1 то 5\n    навис(i)\n")
        self.assertIn('аломати ":" лозим аст', ctx.exception.message)

    def test_missing_variable_name(self):
        with self.assertRaises(ParseError) as ctx:
            run("барои аз 1 то 5:\n    навис(1)\n")
        self.assertIn("номи тағйирёбанда лозим аст", ctx.exception.message)


if __name__ == "__main__":
    unittest.main()
