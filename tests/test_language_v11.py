"""Version 1.1: loop control, error handling, call stacks, global builtins."""

import tempfile
import unittest
from pathlib import Path

from tajiklang import run_file, run_source
from tajiklang.errors import ParseError, RuntimeErrorTJ


def run(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def one(expression):
    return run("навис(" + expression + ")")[0]


class TestLoopControl(unittest.TestCase):
    def test_шикан_leaves_a_counted_loop(self):
        source = "барои i аз 1 то 10:\n    агар i > 3:\n        шикан\n    навис(i)"
        self.assertEqual(run(source), ["1", "2", "3"])

    def test_шикан_leaves_a_while_loop(self):
        source = "бигзор n = 0\nто_вақте рост:\n    n += 1\n    агар n == 3:\n        шикан\nнавис(n)"
        self.assertEqual(run(source), ["3"])

    def test_шикан_leaves_a_walk(self):
        source = 'барои x аз [1, 2, 3]:\n    агар x == 2:\n        шикан\n    навис(x)'
        self.assertEqual(run(source), ["1"])

    def test_давом_skips_the_rest_of_the_turn(self):
        source = "барои i аз 1 то 5:\n    агар i % 2 == 0:\n        давом\n    навис(i)"
        self.assertEqual(run(source), ["1", "3", "5"])

    def test_шикан_only_leaves_the_inner_loop(self):
        source = (
            "барои a аз 1 то 2:\n"
            "    барои b аз 1 то 5:\n"
            "        агар b == 2:\n"
            "            шикан\n"
            "        навис(a, b)\n"
        )
        self.assertEqual(run(source), ["1 1", "2 1"])

    def test_шикан_outside_a_loop_is_a_syntax_error(self):
        with self.assertRaises(ParseError) as ctx:
            run("шикан")
        self.assertIn("танҳо дар дохили давр", ctx.exception.message)

    def test_a_function_does_not_inherit_the_enclosing_loop(self):
        """`шикан` inside a function declared in a loop belongs to no loop."""
        with self.assertRaises(ParseError):
            run("барои i аз 1 то 2:\n    функсия f():\n        шикан\n    f()")


class TestErrorHandling(unittest.TestCase):
    def test_catching_an_error(self):
        source = 'кӯшиш:\n    навис(1 / 0)\nхато:\n    навис("хато шуд")'
        self.assertEqual(run(source), ["хато шуд"])

    def test_binding_the_message(self):
        source = 'кӯшиш:\n    навис(1 / 0)\nхато паём:\n    навис(паём)'
        self.assertEqual(run(source), ["Тақсим ба сифр мумкин нест."])

    def test_the_handler_is_skipped_when_nothing_fails(self):
        source = 'кӯшиш:\n    навис("хуб")\nхато:\n    навис("бад")'
        self.assertEqual(run(source), ["хуб"])

    def test_output_before_the_failure_is_kept(self):
        source = 'кӯшиш:\n    навис("як")\n    навис(1 / 0)\nхато:\n    навис("ду")'
        self.assertEqual(run(source), ["як", "ду"])

    def test_баргардон_passes_straight_through(self):
        """A return inside кӯшиш must return from the function, not be caught."""
        source = (
            "функсия f():\n"
            "    кӯшиш:\n"
            '        баргардон "аз дохил"\n'
            "    хато:\n"
            '        баргардон "хато"\n'
            "навис(f())"
        )
        self.assertEqual(run(source), ["аз дохил"])

    def test_шикан_passes_straight_through(self):
        source = (
            "барои i аз 1 то 5:\n"
            "    кӯшиш:\n"
            "        агар i == 2:\n"
            "            шикан\n"
            "    хато:\n"
            '        навис("хато")\n'
            "    навис(i)"
        )
        self.assertEqual(run(source), ["1"])

    def test_validating_input_without_crashing(self):
        source = (
            'кӯшиш:\n'
            '    бигзор n = ба_рақам("салом")\n'
            '    навис(n)\n'
            'хато:\n'
            '    навис("Ин рақам нест")'
        )
        self.assertEqual(run(source), ["Ин рақам нест"])

    def test_хато_without_кӯшиш(self):
        with self.assertRaises(ParseError) as ctx:
            run('навис(1)\nхато:\n    навис(2)')
        self.assertIn('бе "кӯшиш"', ctx.exception.message)

    def test_кӯшиш_without_хато(self):
        with self.assertRaises(ParseError) as ctx:
            run("кӯшиш:\n    навис(1)")
        self.assertIn('блоки "хато" лозим аст', ctx.exception.message)


class TestCallStack(unittest.TestCase):
    def test_an_error_names_the_calls_that_led_to_it(self):
        source = (
            "функсия дарунӣ(x):\n"
            "    баргардон x / 0\n"
            "функсия берунӣ():\n"
            "    баргардон дарунӣ(5)\n"
            "навис(берунӣ())\n"
        )
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run(source)

        error = ctx.exception
        self.assertEqual(error.line, 2)              # where it broke
        self.assertEqual(error.call_stack, [("берунӣ", 5), ("дарунӣ", 4)])

        text = error.format()
        self.assertIn("Роҳи даъват:", text)
        self.assertIn('дар функсияи "дарунӣ", даъват дар сатри 4', text)
        self.assertIn('дар функсияи "берунӣ", даъват дар сатри 5', text)

    def test_top_level_errors_have_no_stack(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("навис(1 / 0)")
        self.assertEqual(ctx.exception.call_stack, [])
        self.assertNotIn("Роҳи даъват", ctx.exception.format())

    def test_the_stack_unwinds_after_a_caught_error(self):
        source = (
            "функсия f():\n"
            "    баргардон 1 / 0\n"
            "кӯшиш:\n"
            "    навис(f())\n"
            "хато:\n"
            "    навис(1 / 0)\n"
        )
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run(source)
        self.assertEqual(ctx.exception.call_stack, [])


class TestCompoundAssignment(unittest.TestCase):
    def test_all_five(self):
        source = "бигзор x = 10\nx += 5\nx -= 3\nx *= 2\nx /= 4\nx %= 4\nнавис(x)"
        self.assertEqual(run(source), ["2"])

    def test_on_a_list_element(self):
        self.assertEqual(run("бигзор р = [1, 2]\nр[0] += 10\nнавис(р)"), ["[11, 2]"])

    def test_on_a_dictionary_value(self):
        source = 'бигзор л = {"a": 1}\nл["a"] += 4\nнавис(л)'
        self.assertEqual(run(source), ['{"a": 5}'])

    def test_it_joins_text_too(self):
        source = 'бигзор s = "Салом"\ns += " Баҳром"\nнавис(s)'
        self.assertEqual(run(source), ["Салом Баҳром"])

    def test_an_undeclared_name_still_fails(self):
        with self.assertRaises(RuntimeErrorTJ):
            run("нест += 1")


class TestNegativeIndexing(unittest.TestCase):
    def test_reading_from_the_end(self):
        self.assertEqual(run("бигзор р = [1, 2, 3]\nнавис(р[-1], р[-3])"), ["3 1"])

    def test_on_text(self):
        self.assertEqual(one('"Салом"[-1]'), "м")

    def test_assigning_from_the_end(self):
        self.assertEqual(run("бигзор р = [1, 2, 3]\nр[-1] = 9\nнавис(р)"), ["[1, 2, 9]"])

    def test_too_far_back_is_still_an_error(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("навис([1, 2][-5])")
        self.assertIn("берун аз ҳудуд", ctx.exception.message)
        self.assertIn("аз охир", ctx.exception.hint)


class TestGlobalsWithoutImport(unittest.TestCase):
    """Everything a beginner needs must work with no `ворид` at all."""

    def test_text_functions_are_global(self):
        self.assertEqual(one('калон("салом")'), "САЛОМ")
        self.assertEqual(one('тоза("  а  ")'), "а")
        self.assertEqual(one('ҷудо("а,б", ",")'), '["а", "б"]')

    def test_math_functions_are_global(self):
        self.assertEqual(one("реша(16)"), "4")
        self.assertEqual(one("гирд(3.14159, 2)"), "3.14")
        self.assertEqual(one("мутлақ(-5)"), "5")

    def test_the_module_is_the_same_function(self):
        source = "ворид риёзӣ\nнавис(реша(9) == риёзӣ.реша(9))"
        self.assertEqual(run(source), ["рост"])

    def test_мин_макс_take_two_values_or_a_list(self):
        self.assertEqual(one("мин(3, 7)"), "3")
        self.assertEqual(one("макс([5, 2, 9])"), "9")

    def test_рақамҳо(self):
        self.assertEqual(one("рақамҳо(1, 5)"), "[1, 2, 3, 4, 5]")
        self.assertEqual(one("рақамҳо(3)"), "[1, 2, 3]")
        self.assertEqual(one("рақамҳо(3, 1)"), "[3, 2, 1]")

    def test_буриш_on_both_kinds(self):
        self.assertEqual(one("буриш([1,2,3,4,5], 1, 3)"), "[2, 3, 4]")
        self.assertEqual(one('буриш("Тоҷикистон", 0, 3)'), "Тоҷи")

    def test_нусха_breaks_the_link(self):
        source = "бигзор а = [1]\nбигзор б = нусха(а)\nилова(б, 2)\nнавис(а, б)"
        self.assertEqual(run(source), ["[1] [1, 2]"])

    def test_aliasing_without_нусха(self):
        """The trap нусха exists for — worth pinning down."""
        source = "бигзор а = [1]\nбигзор б = а\nилова(б, 2)\nнавис(а)"
        self.assertEqual(run(source), ["[1, 2]"])

    def test_list_editing(self):
        source = "бигзор р = [2]\nдарҷ(р, 0, 1)\nвасеъ(р, [3])\nнавис(р)\nхолӣ_кун(р)\nнавис(р)"
        self.assertEqual(run(source), ["[1, 2, 3]", "[]"])

    def test_ҷои_and_шумор(self):
        self.assertEqual(one('ҷои(["а", "б"], "б")'), "1")
        self.assertEqual(one('ҷои(["а"], "я")'), "холӣ")
        self.assertEqual(one("шумор([1, 1, 2], 1)"), "2")

    def test_миёна(self):
        self.assertEqual(one("миёна([2, 4, 6])"), "4")

    def test_ҳама_and_ягон(self):
        self.assertEqual(one("ҳама([рост, рост])"), "рост")
        self.assertEqual(one("ягон([дурӯғ, рост])"), "рост")
        self.assertEqual(one("ҳама([])"), "рост")

    def test_ҳама_requires_booleans(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("навис(ҳама([1, 2]))")
        self.assertIn("мантиқ", ctx.exception.message)

    def test_dictionary_helpers(self):
        source = (
            'бигзор л = {"а": 1, "б": 2}\n'
            "навис(ҷуфтҳо(л))\n"
            'навис(гирифтан(л, "я", 0))\n'
            'навис(нест_кун(л, "а"), л)\n'
        )
        self.assertEqual(run(source), ['[["а", 1], ["б", 2]]', "0", '1 {"б": 2}'])

    def test_холӣ_аст(self):
        self.assertEqual(one("холӣ_аст([])"), "рост")
        self.assertEqual(one('холӣ_аст("а")'), "дурӯғ")


class TestSortByKey(unittest.TestCase):
    """The gap that forced an O(n²) loop in журнал.tj."""

    PEOPLE = (
        "бигзор донишҷӯён = [\n"
        '    {"ном": "Яқубов", "балл": 3},\n'
        '    {"ном": "Ғафуров", "балл": 5},\n'
        '    {"ном": "Аҳмадов", "балл": 4},\n'
        "]\n"
        "функсия ном_и(д):\n"
        '    баргардон д["ном"]\n'
        "функсия балл_и(д):\n"
        '    баргардон д["балл"]\n'
    )

    def test_sorting_records_by_a_text_field(self):
        source = self.PEOPLE + (
            "барои д аз тартиб_бо(донишҷӯён, ном_и):\n    навис(д[\"ном\"])"
        )
        self.assertEqual(run(source), ["Аҳмадов", "Ғафуров", "Яқубов"])

    def test_sorting_records_by_a_number_field(self):
        source = self.PEOPLE + (
            "барои д аз тартиб_бо(донишҷӯён, балл_и):\n    навис(д[\"балл\"])"
        )
        self.assertEqual(run(source), ["3", "4", "5"])

    def test_the_original_list_is_untouched(self):
        source = self.PEOPLE + (
            "тартиб_бо(донишҷӯён, ном_и)\nнавис(донишҷӯён[0][\"ном\"])"
        )
        self.assertEqual(run(source), ["Яқубов"])

    def test_the_key_must_be_a_function(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("навис(тартиб_бо([1, 2], 5))")
        self.assertIn("функсия мехоҳад", ctx.exception.message)

    def test_a_builtin_may_be_the_key(self):
        self.assertEqual(one('тартиб_бо(["ббб", "а", "вв"], дарозӣ)'),
                         '["а", "вв", "ббб"]')

    def test_тартиб_suggests_тартиб_бо_for_mixed_lists(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('навис(тартиб([{"а": 1}]))')
        self.assertIn("тартиб_бо", ctx.exception.hint)


class TestFileModule(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)

    def tearDown(self):
        self._dir.cleanup()

    def _run(self, program):
        path = self.folder / "барнома.tj"
        path.write_text(program, encoding="utf-8")
        lines = []
        run_file(path, output=lines.append)
        return lines

    def test_write_then_read(self):
        out = self._run(
            "ворид файл\n"
            'файл.навиштан("маълумот.txt", "Салом")\n'
            'навис(файл.хондан("маълумот.txt"))\n'
        )
        self.assertEqual(out, ["Салом"])

    def test_appending(self):
        out = self._run(
            "ворид файл\n"
            'файл.навиштан("а.txt", "як")\n'
            'файл.илова_кардан("а.txt", " ду")\n'
            'навис(файл.хондан("а.txt"))\n'
        )
        self.assertEqual(out, ["як ду"])

    def test_reading_lines(self):
        (self.folder / "номҳо.txt").write_text(
            "Яқубов\nҒафуров\n", encoding="utf-8"
        )
        out = self._run(
            "ворид файл\n"
            'барои ном аз тартиб(файл.сатрҳо("номҳо.txt")):\n    навис(ном)\n'
        )
        self.assertEqual(out, ["Ғафуров", "Яқубов"])

    def test_мавҷуд(self):
        out = self._run(
            "ворид файл\n"
            'навис(файл.мавҷуд("нест.txt"))\n'
            'файл.навиштан("ҳаст.txt", "x")\n'
            'навис(файл.мавҷуд("ҳаст.txt"))\n'
        )
        self.assertEqual(out, ["дурӯғ", "рост"])

    def test_a_missing_file_points_at_мавҷуд(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            self._run('ворид файл\nнавис(файл.хондан("нест.txt"))')
        self.assertIn("ёфт нашуд", ctx.exception.message)
        self.assertIn("мавҷуд", ctx.exception.hint)

    def test_paths_are_relative_to_the_program_not_the_shell(self):
        (self.folder / "маълумот.txt").write_text("дуруст", encoding="utf-8")
        out = self._run('ворид файл\nнавис(файл.хондан("маълумот.txt"))')
        self.assertEqual(out, ["дуруст"])


if __name__ == "__main__":
    unittest.main()
