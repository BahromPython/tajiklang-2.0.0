"""The `саҳифа` module: building web pages from TajikLang.

The whole point of elements being plain data is that this is testable with no
browser anywhere in sight — the same tree that becomes DOM becomes HTML text.
"""

import tempfile
import unittest
from pathlib import Path

from tajiklang import run_file, run_source
from tajiklang.errors import RuntimeErrorTJ


def run(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def html(body):
    """Return the HTML for one `саҳифа.ҳамчун_матн(...)` expression."""
    return run("ворид саҳифа\nнавис(саҳифа.ҳамчун_матн(" + body + "))")[0]


class TestBuildingElements(unittest.TestCase):
    def test_a_heading(self):
        self.assertIn("<h1>Салом</h1>", html('саҳифа.сарлавҳа("Салом")'))

    def test_heading_levels(self):
        self.assertIn("<h2>Ду</h2>", html('саҳифа.сарлавҳа("Ду", 2)'))
        self.assertIn("<h3>Се</h3>", html('саҳифа.сарлавҳа("Се", 3)'))

    def test_text_joins_its_arguments(self):
        self.assertIn("<p>Ҳамагӣ 4 донишҷӯ</p>",
                      html('саҳифа.матн("Ҳамагӣ", 4, "донишҷӯ")'))

    def test_a_list(self):
        out = html('саҳифа.рӯйхат(["а", "б"])')
        self.assertIn("<li>а</li>", out)
        self.assertIn("<li>б</li>", out)

    def test_a_table_from_lists(self):
        out = html('саҳифа.ҷадвал([[1, 2], [3, 4]], ["як", "ду"])')
        self.assertIn("<th>як</th>", out)
        self.assertIn("<td>3</td>", out)

    def test_a_table_from_dictionaries_picks_columns(self):
        out = html(
            'саҳифа.ҷадвал([{"ном": "Аҳмадов", "баҳо": 5, "синф": 10}], '
            '["ном", "баҳо"])'
        )
        self.assertIn("<td>Аҳмадов</td>", out)
        self.assertIn("<td>5</td>", out)
        self.assertNotIn("<td>10</td>", out)   # синф was not asked for

    def test_a_table_of_dictionaries_defaults_to_every_key(self):
        out = html('саҳифа.ҷадвал([{"а": 1, "б": 2}])')
        self.assertIn("<th>а</th>", out)
        self.assertIn("<th>б</th>", out)

    def test_nesting(self):
        out = html('саҳифа.қуттӣ(саҳифа.сарлавҳа("А"), саҳифа.матн("Б"))')
        self.assertIn("<div>", out)
        self.assertIn("<h1>А</h1>", out)
        self.assertIn("<p>Б</p>", out)

    def test_a_row_lays_things_out_side_by_side(self):
        self.assertIn("display: flex", html('саҳифа.қатор(саҳифа.матн("а"))'))

    def test_plain_text_becomes_a_paragraph(self):
        self.assertIn("<p>танҳо матн</p>", html('саҳифа.қуттӣ("танҳо матн")'))

    def test_an_input_field(self):
        self.assertIn('data-ном="ном"', html('саҳифа.майдон("ном")'))

    def test_an_image(self):
        out = html('саҳифа.расм("расм.png", "тавсиф")')
        self.assertIn('src="расм.png"', out)
        self.assertIn('alt="тавсиф"', out)

    def test_the_title_comes_from_the_first_heading(self):
        self.assertIn("<title>Журнал</title>",
                      html('саҳифа.сарлавҳа("Журнал")'))


class TestStyling(unittest.TestCase):
    def test_tajik_property_names(self):
        out = html('саҳифа.услуб(саҳифа.матн("а"), {"ранг": "green"})')
        self.assertIn("color: green", out)

    def test_numbers_become_pixels_where_that_is_meant(self):
        out = html('саҳифа.услуб(саҳифа.матн("а"), {"андоза": 20})')
        self.assertIn("font-size: 20px", out)

    def test_unknown_names_pass_through_for_people_who_know_css(self):
        out = html('саҳифа.услуб(саҳифа.матн("а"), {"letter-spacing": "2px"})')
        self.assertIn("letter-spacing: 2px", out)

    def test_style_may_be_the_last_argument(self):
        out = html('саҳифа.матн("а", {"ранг": "red"})')
        self.assertIn("color: red", out)

    def test_a_style_must_be_a_dictionary(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('ворид саҳифа\nнавис(саҳифа.услуб(саҳифа.матн("а"), 5))')
        self.assertIn("услуб", ctx.exception.message)


class TestSafety(unittest.TestCase):
    def test_text_is_escaped(self):
        """A program must not be able to inject markup into its own page."""
        out = html('саҳифа.матн("<script>alert(1)</script>")')
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_attributes_are_escaped(self):
        out = html('саҳифа.расм("a\\" onerror=\\"x")')
        self.assertNotIn('onerror="x"', out)


class TestButtons(unittest.TestCase):
    def test_a_button_renders(self):
        source = (
            "ворид саҳифа\n"
            "функсия пахш():\n"
            '    навис("пахш шуд")\n'
            'навис(саҳифа.ҳамчун_матн(саҳифа.тугма("Пахш", пахш)))'
        )
        self.assertIn("<button>Пахш</button>", run(source)[0])

    def test_the_handler_must_be_a_function(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('ворид саҳифа\nнавис(саҳифа.тугма("Пахш", 5))')
        self.assertIn("функсия мехоҳад", ctx.exception.message)


class TestTerminalUse(unittest.TestCase):
    """In the terminal the page becomes a file — no browser required."""

    def test_writing_a_page_to_disk(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "созанда.tj"
            path.write_text(
                "ворид саҳифа\n"
                "ворид файл\n"
                "бигзор матни_саҳифа = саҳифа.ҳамчун_матн(\n"
                '    саҳифа.сарлавҳа("Салом"),\n'
                '    саҳифа.рӯйхат(["як", "ду"]),\n'
                ")\n"
                'файл.навиштан("саҳифа.html", матни_саҳифа)\n'
                'навис("сохта шуд")\n',
                encoding="utf-8",
            )
            lines = []
            run_file(path, output=lines.append)

            self.assertEqual(lines, ["сохта шуд"])
            written = (Path(folder) / "саҳифа.html").read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", written)
            self.assertIn("<h1>Салом</h1>", written)
            self.assertIn("<li>як</li>", written)

    def test_нависед_collects_for_ҳамчун_матн(self):
        source = (
            "ворид саҳифа\n"
            'саҳифа.нависед(саҳифа.сарлавҳа("Як"))\n'
            'саҳифа.нависед(саҳифа.матн("Ду"))\n'
            "навис(саҳифа.ҳамчун_матн())\n"
        )
        out = run(source)[0]
        self.assertIn("<h1>Як</h1>", out)
        self.assertIn("<p>Ду</p>", out)

    def test_reading_a_field_needs_a_browser(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run('ворид саҳифа\nнавис(саҳифа.қимат("ном"))')
        self.assertIn("браузер", ctx.exception.message)
        self.assertIn("ҳамчун_матн", ctx.exception.hint)


if __name__ == "__main__":
    unittest.main()
