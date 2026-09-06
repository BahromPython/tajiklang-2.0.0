import unittest

from tajiklang import run_source
from tajiklang.errors import RuntimeErrorTJ


def run(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def one(expression):
    return run("навис(" + expression + ")")[0]


class TestLists(unittest.TestCase):
    def test_literal_and_printing(self):
        self.assertEqual(one("[1, 2, 3]"), "[1, 2, 3]")

    def test_strings_inside_a_list_keep_their_quotes(self):
        """Otherwise a list of names and a list of strings look identical."""
        self.assertEqual(one('["а", "б"]'), '["а", "б"]')

    def test_empty_list(self):
        self.assertEqual(one("[]"), "[]")

    def test_trailing_comma_is_allowed(self):
        self.assertEqual(one("[1, 2,]"), "[1, 2]")

    def test_indexing(self):
        self.assertEqual(run("бигзор х = [10, 20, 30]\nнавис(х[1])"), ["20"])

    def test_index_assignment(self):
        self.assertEqual(run("бигзор х = [1, 2]\nх[0] = 9\nнавис(х)"), ["[9, 2]"])

    def test_nested_lists(self):
        self.assertEqual(run("бигзор х = [[1, 2], [3]]\nнавис(х[0][1])"), ["2"])

    def test_joining_lists(self):
        self.assertEqual(one("[1] + [2, 3]"), "[1, 2, 3]")

    def test_equality_is_element_by_element(self):
        self.assertEqual(one("[1, 2] == [1, 2]"), "рост")
        self.assertEqual(one("[1, 2] == [2, 1]"), "дурӯғ")
        self.assertEqual(one("[1] == [рост]"), "дурӯғ")

    def test_index_out_of_range(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("бигзор х = [1, 2]\nнавис(х[5])")
        self.assertIn("берун аз ҳудуд", ctx.exception.message)
        self.assertIn("0 то 1", ctx.exception.hint)

    def test_index_must_be_a_whole_number(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('бигзор х = [1, 2]\nнавис(х["а"])')
        self.assertIn("бояд бутун бошад", ctx.exception.message)


class TestDictionaries(unittest.TestCase):
    def test_literal_and_lookup(self):
        source = 'бигзор одам = {"ном": "Баҳром"}\nнавис(одам["ном"])'
        self.assertEqual(run(source), ["Баҳром"])

    def test_adding_a_key(self):
        source = 'бигзор л = {}\nл["а"] = 1\nнавис(л)'
        self.assertEqual(run(source), ['{"а": 1}'])

    def test_number_keys(self):
        self.assertEqual(run("бигзор л = {1: 10}\nнавис(л[1])"), ["10"])

    def test_a_missing_key_says_how_to_check(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('бигзор л = {"а": 1}\nнавис(л["б"])')
        self.assertIn("дар луғат нест", ctx.exception.message)
        self.assertIn("дорад", ctx.exception.hint)

    def test_a_list_cannot_be_a_key(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("навис({[1]: 2})")
        self.assertIn("матн ё рақам", ctx.exception.message)


class TestBuiltins(unittest.TestCase):
    def test_дарозӣ(self):
        self.assertEqual(one("дарозӣ([1, 2, 3])"), "3")
        self.assertEqual(one('дарозӣ("салом")'), "5")
        self.assertEqual(one('дарозӣ({"а": 1})'), "1")

    def test_илова(self):
        self.assertEqual(run("бигзор х = [1]\nилова(х, 2)\nнавис(х)"), ["[1, 2]"])

    def test_тартиб_uses_the_tajik_alphabet(self):
        """The collation from 0.3, now reachable as a function."""
        self.assertEqual(
            one('тартиб(["Яқубов", "Ғафуров", "Аҳмадов"])'),
            '["Аҳмадов", "Ғафуров", "Яқубов"]',
        )

    def test_тартиб_of_numbers(self):
        self.assertEqual(one("тартиб([3, 1, 2])"), "[1, 2, 3]")

    def test_тартиб_refuses_a_mixed_list(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('навис(тартиб([1, "а"]))')
        self.assertIn("ҳамаи матнҳо ё ҳамаи рақамҳо", ctx.exception.message)

    def test_калидҳо_and_дорад(self):
        source = 'бигзор л = {"а": 1, "б": 2}\nнавис(калидҳо(л))\nнавис(дорад(л, "б"))'
        self.assertEqual(run(source), ['["а", "б"]', "рост"])

    def test_conversions(self):
        self.assertEqual(one('ба_рақам("16") + 1'), "17")
        self.assertEqual(one('ба_матн(16) + " сол"'), "16 сол")

    def test_ба_рақам_rejects_nonsense(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('навис(ба_рақам("салом"))')
        self.assertIn("ба рақам табдил намеёбад", ctx.exception.message)

    def test_навъ(self):
        self.assertEqual(one("навъ(1)"), "рақам")
        self.assertEqual(one('навъ("а")'), "матн")
        self.assertEqual(one("навъ(рост)"), "мантиқӣ")
        self.assertEqual(one("навъ([1])"), "рӯйхат")
        self.assertEqual(one("навъ({})"), "луғат")
        self.assertEqual(one("навъ(холӣ)"), "холӣ")
        self.assertEqual(one("навъ(навис)"), "функсия")

    def test_a_builtin_reports_its_own_arity(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("навис(дарозӣ([1], [2]))")
        self.assertIn("1 аргумент мехоҳад", ctx.exception.message)

    def test_a_builtin_error_points_at_the_call(self):
        try:
            run("навис(1)\nнавис(дарозӣ(5))")
        except RuntimeErrorTJ as error:
            self.assertEqual(error.line, 2)


if __name__ == "__main__":
    unittest.main()
