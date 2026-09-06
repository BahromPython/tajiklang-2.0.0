"""Version 2.0: classes, typed errors, the pipeline, and `чаро`."""

import unittest

from tajiklang import check_source, run_source
from tajiklang.errors import ParseError, RuntimeErrorTJ


def run(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def one(expression):
    return run("навис(" + expression + ")")[0]


def problems(source):
    return [d.message for d in check_source(source) if not d.is_warning]


STUDENT = (
    "қолиб Донишҷӯ:\n"
    "    функсия оғоз(худ, ном, баҳо):\n"
    "        худ.ном = ном\n"
    "        худ.баҳо = баҳо\n"
    "\n"
    "    функсия хулоса(худ):\n"
    "        агар худ.баҳо >= 4.5:\n"
    '            баргардон "аъло"\n'
    '        баргардон "хуб"\n'
)


class TestClasses(unittest.TestCase):
    def test_fields_and_methods(self):
        source = STUDENT + 'бигзор д = Донишҷӯ("Аҳмадов", 4.75)\nнавис(д.ном, д.хулоса())'
        self.assertEqual(run(source), ["Аҳмадов аъло"])

    def test_худ_is_supplied_by_the_language(self):
        """`д.хулоса()` takes no arguments even though `худ` is a parameter."""
        source = STUDENT + 'навис(Донишҷӯ("Ғафуров", 3).хулоса())'
        self.assertEqual(run(source), ["хуб"])

    def test_an_object_prints_readably(self):
        source = STUDENT + 'навис(Донишҷӯ("Аҳмадов", 5))'
        self.assertEqual(run(source), ['Донишҷӯ(ном: "Аҳмадов", баҳо: 5)'])

    def test_навъ_names_the_class(self):
        source = STUDENT + 'навис(навъ(Донишҷӯ("а", 1)))'
        self.assertEqual(run(source), ["Донишҷӯ"])

    def test_two_objects_do_not_share_fields(self):
        source = STUDENT + (
            'бигзор а = Донишҷӯ("А", 5)\n'
            'бигзор б = Донишҷӯ("Б", 2)\n'
            "навис(а.ном, б.ном)"
        )
        self.assertEqual(run(source), ["А Б"])

    def test_fields_can_be_changed(self):
        source = STUDENT + 'бигзор д = Донишҷӯ("А", 2)\nд.баҳо = 5\nнавис(д.хулоса())'
        self.assertEqual(run(source), ["аъло"])

    def test_a_new_field_can_be_added(self):
        source = STUDENT + 'бигзор д = Донишҷӯ("А", 2)\nд.шаҳр = "Душанбе"\nнавис(д.шаҳр)'
        self.assertEqual(run(source), ["Душанбе"])

    def test_objects_in_a_list_sorted_by_a_field(self):
        source = STUDENT + (
            "функсия баҳои(д):\n"
            "    баргардон д.баҳо\n"
            'бигзор ҳама = [Донишҷӯ("Я", 3), Донишҷӯ("А", 5)]\n'
            "барои д аз тартиб_бо(ҳама, баҳои):\n"
            "    навис(д.ном)"
        )
        self.assertEqual(run(source), ["Я", "А"])

    def test_a_class_without_оғоз_takes_no_arguments(self):
        source = (
            "қолиб Ҳисоб:\n"
            "    функсия салом(худ):\n"
            '        баргардон "салом"\n'
            "навис(Ҳисоб().салом())"
        )
        self.assertEqual(run(source), ["салом"])

    def test_wrong_argument_count_does_not_count_худ(self):
        source = STUDENT + 'навис(Донишҷӯ("А"))'
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run(source)
        self.assertIn("2 аргумент мехоҳад", ctx.exception.message)
        self.assertIn("1 гирифт", ctx.exception.message)

    def test_an_unknown_member_lists_what_exists(self):
        source = STUDENT + 'навис(Донишҷӯ("А", 1).ҳеҷ)'
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run(source)
        self.assertIn("надорад", ctx.exception.message)
        self.assertIn("хулоса", ctx.exception.hint)

    def test_a_class_body_holds_only_functions(self):
        with self.assertRaises(ParseError) as ctx:
            run("қолиб А:\n    бигзор x = 1\n")
        self.assertIn("танҳо функсияҳо", ctx.exception.message)

    def test_an_empty_class(self):
        with self.assertRaises(ParseError) as ctx:
            run("қолиб А:\nнавис(1)\n")
        self.assertIn("холӣ мондааст", ctx.exception.message)

    def test_the_checker_knows_the_constructor_arity(self):
        self.assertIn("2 аргумент", problems(STUDENT + 'бигзор д = Донишҷӯ("А")')[0])

    def test_the_checker_is_quiet_about_correct_classes(self):
        self.assertEqual(problems(STUDENT + 'навис(Донишҷӯ("А", 1).хулоса())'), [])


class TestInheritance(unittest.TestCase):
    PARENT = (
        "қолиб Одам:\n"
        "    функсия оғоз(худ, ном):\n"
        "        худ.ном = ном\n"
        "    функсия салом(худ):\n"
        '        баргардон "Салом, " + худ.ном\n'
    )

    def test_a_child_inherits_methods(self):
        source = self.PARENT + (
            "қолиб Донишҷӯ мерос Одам:\n"
            "    функсия оғоз(худ, ном, синф):\n"
            "        худ.ном = ном\n"
            "        худ.синф = синф\n"
            'бигзор д = Донишҷӯ("Ғафуров", 10)\n'
            "навис(д.салом())"
        )
        self.assertEqual(run(source), ["Салом, Ғафуров"])

    def test_a_child_may_call_an_inherited_method(self):
        source = self.PARENT + (
            "қолиб Донишҷӯ мерос Одам:\n"
            "    функсия оғоз(худ, ном):\n"
            "        худ.ном = ном\n"
            "    функсия пурра(худ):\n"
            '        баргардон худ.салом() + "!"\n'
            'навис(Донишҷӯ("А").пурра())'
        )
        self.assertEqual(run(source), ["Салом, А!"])

    def test_a_child_may_replace_a_method(self):
        source = self.PARENT + (
            "қолиб Хомӯш мерос Одам:\n"
            "    функсия салом(худ):\n"
            '        баргардон "..."\n'
            'навис(Хомӯш("А").салом())'
        )
        self.assertEqual(run(source), ["..."])

    def test_an_unknown_parent(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("қолиб А мерос Нест:\n    функсия f(худ):\n        баргардон 1\n")
        self.assertIn("волид", ctx.exception.message)


class TestSchoolWordsAreFree(unittest.TestCase):
    """The class keyword is `қолиб` so that `синф` stays a usable name."""

    def test_синф_is_an_ordinary_variable(self):
        self.assertEqual(run("бигзор синф = 10\nнавис(синф)"), ["10"])

    def test_худ_outside_a_class_is_ordinary_too(self):
        self.assertEqual(run('бигзор худ = "ман"\nнавис(худ)'), ["ман"])


class TestTypedErrors(unittest.TestCase):
    def test_catching_one_kind(self):
        source = (
            "кӯшиш:\n"
            "    навис(1 / 0)\n"
            'хато "тақсим_ба_сифр":\n'
            '    навис("сифр")\n'
        )
        self.assertEqual(run(source), ["сифр"])

    def test_the_first_matching_clause_wins(self):
        source = (
            "кӯшиш:\n"
            "    навис(нест_чунин)\n"
            'хато "тақсим_ба_сифр":\n'
            '    навис("сифр")\n'
            'хато "номи_номаълум":\n'
            '    навис("ном")\n'
            "хато:\n"
            '    навис("дигар")\n'
        )
        self.assertEqual(run(source), ["ном"])

    def test_a_bare_clause_catches_the_rest(self):
        source = (
            "кӯшиш:\n"
            "    навис([1][9])\n"
            'хато "тақсим_ба_сифр":\n'
            '    навис("сифр")\n'
            "хато паём:\n"
            '    навис("дигар:", паём)\n'
        )
        self.assertEqual(len(run(source)), 1)
        self.assertTrue(run(source)[0].startswith("дигар:"))

    def test_an_unmatched_kind_travels_on(self):
        source = (
            "кӯшиш:\n"
            "    навис(1 / 0)\n"
            'хато "берун_аз_ҳудуд":\n'
            '    навис("ҳудуд")\n'
        )
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run(source)
        self.assertIn("Тақсим ба сифр", ctx.exception.message)

    def test_the_kinds_that_exist(self):
        cases = {
            "тақсим_ба_сифр": "навис(1 / 0)",
            "номи_номаълум": "навис(нест_чунин)",
            "берун_аз_ҳудуд": "навис([1][9])",
            "калиди_нест": 'навис({"а": 1}["б"])',
            "навъи_нодуруст": "навис(не 5)",
            "шумораи_аргумент": "функсия f(a):\n    баргардон a\nнавис(f())",
        }
        for kind, body in cases.items():
            with self.subTest(kind=kind):
                source = (
                    "кӯшиш:\n"
                    + "".join("    " + line + "\n" for line in body.split("\n"))
                    + f'хато "{kind}":\n'
                    + '    навис("гирифтам")\n'
                )
                self.assertEqual(run(source), ["гирифтам"])

    def test_a_bare_clause_must_come_last(self):
        source = (
            "кӯшиш:\n"
            "    навис(1)\n"
            "хато:\n"
            "    навис(2)\n"
            'хато "тақсим_ба_сифр":\n'
            "    навис(3)\n"
        )
        with self.assertRaises(ParseError) as ctx:
            run(source)
        self.assertIn("ҳеҷ гоҳ иҷро намешавад", ctx.exception.message)


class TestPipeline(unittest.TestCase):
    def test_a_single_step(self):
        self.assertEqual(one('"салом" |> калон'), "САЛОМ")

    def test_a_chain_reads_left_to_right(self):
        self.assertEqual(one("[3, 1, 2] |> тартиб |> баръакс"), "[3, 2, 1]")

    def test_it_ends_in_a_call(self):
        self.assertEqual(run('["б", "а"] |> тартиб |> навис'), ['["а", "б"]'])

    def test_extra_arguments_come_after(self):
        """`а |> f(б)` is `f(а, б)`, as in F# and Elixir."""
        self.assertEqual(one('"а,б" |> ҷудо(",")'), '["а", "б"]')

    def test_it_binds_looser_than_arithmetic(self):
        self.assertEqual(one("2 + 2 |> реша"), "2")

    def test_a_user_function_works_too(self):
        source = (
            "функсия дучанд(x):\n"
            "    баргардон x * 2\n"
            "навис(5 |> дучанд |> дучанд)"
        )
        self.assertEqual(run(source), ["20"])


class TestChar(unittest.TestCase):
    """`чаро` — the question every other language answers with silence."""

    def test_it_shows_every_change(self):
        source = "бигзор ҷамъ = 0\nбарои i аз 1 то 3:\n    ҷамъ += i\nчаро(ҷамъ)"
        out = run(source)
        self.assertEqual(out[0], 'Тағйирёбандаи "ҷамъ":')
        self.assertEqual(len(out), 5)              # declaration + three changes
        self.assertIn("сатри 1", out[1])
        self.assertIn("эълон", out[1])
        self.assertIn("6", out[-1])                # 0+1+2+3

    def test_an_untouched_name(self):
        self.assertIn("ҳеҷ гоҳ", run("чаро(нест)")[0])

    def test_a_program_may_define_its_own_чаро(self):
        """It is an ordinary shadowable name, not a keyword."""
        source = (
            "функсия чаро(x):\n"
            "    баргардон x * 2\n"
            "бигзор y = 5\n"
            "навис(чаро(y))"
        )
        self.assertEqual(run(source), ["10"])


class TestBilingualHeadings(unittest.TestCase):
    def test_the_english_term_is_carried_along(self):
        try:
            run("навис(1 / 0)")
        except RuntimeErrorTJ as error:
            self.assertIn("Хатои иҷро", error.format())
            self.assertIn("RuntimeError", error.format())

    def test_syntax_errors_too(self):
        try:
            run("навис(")
        except ParseError as error:
            self.assertIn("SyntaxError", error.format())


if __name__ == "__main__":
    unittest.main()
