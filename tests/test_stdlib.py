import unittest

from tajiklang import run_source
from tajiklang.errors import RuntimeErrorTJ


def run(source, answers=None):
    lines = []
    supply = iter(answers or [])
    run_source(
        source,
        output=lines.append,
        read_line=lambda prompt: next(supply, None),
    )
    return lines


def one(expression):
    return run("навис(" + expression + ")")[0]


class TestInput(unittest.TestCase):
    def test_reading_a_line(self):
        source = 'бигзор ном = хонед()\nнавис("Салом,", ном)'
        self.assertEqual(run(source, ["Баҳром"]), ["Салом, Баҳром"])

    def test_a_prompt_is_optional(self):
        source = 'бигзор ном = хонед("Номи шумо: ")\nнавис(ном)'
        self.assertEqual(run(source, ["Далер"]), ["Далер"])

    def test_input_is_always_text(self):
        self.assertEqual(run("навис(навъ(хонед()))", ["16"]), ["матн"])

    def test_converting_input_to_a_number(self):
        source = "бигзор сол = ба_рақам(хонед())\nнавис(сол + 1)"
        self.assertEqual(run(source, ["16"]), ["17"])

    def test_running_out_of_input_says_so(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("бигзор a = хонед()\nбигзор b = хонед()", ["якум"])
        self.assertIn("тамом шуд", ctx.exception.message)

    def test_input_is_unavailable_when_nothing_supplies_it(self):
        lines = []
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run_source("навис(хонед())", output=lines.append)
        self.assertIn("имконнопазир", ctx.exception.message)


class TestListBuiltins(unittest.TestCase):
    def test_ҷамъи(self):
        self.assertEqual(one("ҷамъи([1, 2, 3.5])"), "6.5")

    def test_ҷамъи_of_an_empty_list(self):
        self.assertEqual(one("ҷамъи([])"), "0")

    def test_ҷамъи_rejects_text(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('навис(ҷамъи([1, "а"]))')
        self.assertIn("рӯйхати рақамҳо", ctx.exception.message)

    def test_калонтарин_and_хурдтарин(self):
        self.assertEqual(one("калонтарин([3, 9, 2])"), "9")
        self.assertEqual(one("хурдтарин([3, 9, 2])"), "2")

    def test_extremes_of_text_use_the_tajik_alphabet(self):
        self.assertEqual(one('хурдтарин(["Яқубов", "Ғафуров"])'), "Ғафуров")

    def test_extremes_reject_an_empty_list(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("навис(калонтарин([]))")
        self.assertIn("холиро қабул намекунад", ctx.exception.message)

    def test_баръакс(self):
        self.assertEqual(one("баръакс([1, 2, 3])"), "[3, 2, 1]")
        self.assertEqual(one('баръакс("Салом")'), "молаС")

    def test_баръакс_does_not_change_the_original(self):
        source = "бигзор х = [1, 2]\nнавис(баръакс(х))\nнавис(х)"
        self.assertEqual(run(source), ["[2, 1]", "[1, 2]"])

    def test_хориҷ(self):
        source = "бигзор х = [1, 2, 3]\nнавис(хориҷ(х, 1))\nнавис(х)"
        self.assertEqual(run(source), ["2", "[1, 3]"])

    def test_хориҷ_out_of_range(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("бигзор х = [1]\nнавис(хориҷ(х, 5))")
        self.assertIn("берун аз ҳудуд", ctx.exception.message)

    def test_қиматҳо(self):
        self.assertEqual(one('қиматҳо({"а": 1, "б": 2})'), "[1, 2]")


class TestMathModule(unittest.TestCase):
    def test_rounding_family(self):
        source = (
            "ворид риёзӣ\n"
            "навис(риёзӣ.фарш(3.7))\n"
            "навис(риёзӣ.сақф(3.2))\n"
            "навис(риёзӣ.бутун(3.9))\n"
            "навис(риёзӣ.бутун(-3.9))\n"
        )
        self.assertEqual(run(source), ["3", "4", "3", "-3"])

    def test_гирд_takes_a_number_of_places(self):
        source = "ворид риёзӣ\nнавис(риёзӣ.гирд(3.14159, 2))"
        self.assertEqual(run(source), ["3.14"])

    def test_е_constant(self):
        source = "ворид риёзӣ\nнавис(риёзӣ.гирд(риёзӣ.Е, 2))"
        self.assertEqual(run(source), ["2.72"])

    def test_тасодуфӣ_stays_inside_its_range(self):
        source = (
            "ворид риёзӣ\n"
            "барои i аз 1 то 20:\n"
            "    бигзор n = риёзӣ.тасодуфӣ(1, 6)\n"
            "    агар n < 1 ё n > 6:\n"
            '        навис("берун")\n'
        )
        self.assertEqual(run(source), [])


class TestTextModule(unittest.TestCase):
    def test_case(self):
        source = 'ворид матн\nнавис(матн.калон("салом"))\nнавис(матн.хурд("САЛОМ"))'
        self.assertEqual(run(source), ["САЛОМ", "салом"])

    def test_case_works_on_tajik_letters(self):
        self.assertEqual(run('ворид матн\nнавис(матн.калон("ғоз"))'), ["ҒОЗ"])

    def test_тоза(self):
        self.assertEqual(run('ворид матн\nнавис(матн.тоза("  ҳа  "))'), ["ҳа"])

    def test_ҷудо_with_a_separator(self):
        source = 'ворид матн\nнавис(матн.ҷудо("а,б,в", ","))'
        self.assertEqual(run(source), ['["а", "б", "в"]'])

    def test_ҷудо_on_spaces_by_default(self):
        source = 'ворид матн\nнавис(матн.ҷудо("Салом Тоҷикистон"))'
        self.assertEqual(run(source), ['["Салом", "Тоҷикистон"]'])

    def test_пайваст(self):
        source = 'ворид матн\nнавис(матн.пайваст(["а", "б"], "-"))'
        self.assertEqual(run(source), ["а-б"])

    def test_пайваст_rejects_non_text(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('ворид матн\nнавис(матн.пайваст([1, 2], "-"))')
        self.assertIn("ба_матн", ctx.exception.hint)

    def test_иваз(self):
        source = 'ворид матн\nнавис(матн.иваз("салом-салом", "салом", "ҳа"))'
        self.assertEqual(run(source), ["ҳа-ҳа"])

    def test_буриш_is_inclusive_like_барои(self):
        """буриш(матн, 0, 2) gives three letters, matching `аз 0 то 2`."""
        source = 'ворид матн\nнавис(матн.буриш("Тоҷикистон", 0, 3))'
        self.assertEqual(run(source), ["Тоҷи"])

    def test_буриш_out_of_range(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('ворид матн\nнавис(матн.буриш("аб", 0, 9))')
        self.assertIn("берун аз ҳудуд", ctx.exception.message)

    def test_ёфтан(self):
        source = 'ворид матн\nнавис(матн.ёфтан("Душанбе", "шан"))'
        self.assertEqual(run(source), ["2"])

    def test_ёфтан_returns_холӣ_when_missing(self):
        """Not -1: a missing thing is nothing, and `!= холӣ` reads correctly."""
        source = 'ворид матн\nнавис(матн.ёфтан("Душанбе", "зз"))'
        self.assertEqual(run(source), ["холӣ"])

    def test_prefix_and_suffix(self):
        source = (
            "ворид матн\n"
            'навис(матн.сар_мешавад("Душанбе", "Ду"))\n'
            'навис(матн.тамом_мешавад("Душанбе", "бе"))\n'
        )
        self.assertEqual(run(source), ["рост", "рост"])

    def test_такрор(self):
        self.assertEqual(run('ворид матн\nнавис(матн.такрор("=", 5))'), ["====="])

    def test_ҳарфҳо(self):
        source = 'ворид матн\nнавис(матн.ҳарфҳо("ғоз"))'
        self.assertEqual(run(source), ['["ғ", "о", "з"]'])

    def test_рақам_аст(self):
        source = (
            "ворид матн\n"
            'навис(матн.рақам_аст("16"))\n'
            'навис(матн.рақам_аст("3.5"))\n'
            'навис(матн.рақам_аст("салом"))\n'
        )
        self.assertEqual(run(source), ["рост", "рост", "дурӯғ"])

    def test_a_text_function_rejects_a_number(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("ворид матн\nнавис(матн.калон(5))")
        self.assertIn("матн мехоҳад", ctx.exception.message)


if __name__ == "__main__":
    unittest.main()
