"""Ҳеҷ чиз аз дарун берун намеояд — the implementation must not reach a student.

A learner writing their first program should never be shown a filename, a
traceback, or an English exception class. Not because the implementation is a
secret — the repository is public and the specification says plainly how the
language is built — but because none of it is *actionable* for someone whose
program has a typo on line 3. An error that cannot be acted on is noise, and
noise in a beginner's first hour is expensive.

These tests hold that line. They are the reason the property stays true after
the next refactor.
"""

import io
import re
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tajiklang import check_source, run_source
from tajiklang.errors import TajikLangError, internal_report

ROOT = Path(__file__).resolve().parent.parent

# Anything here appearing in text shown to a student is a bug.
FORBIDDEN = (
    "Traceback",
    'File "',
    ".py",
    "TypeError", "ValueError", "AttributeError", "KeyError",
    "IndexError", "NameError", "ZeroDivisionError", "RecursionError",
    "Exception", "self.", "def ", "lambda",
)


def student_sees(source: str) -> str:
    """Everything a student would see from running one program."""
    lines: list[str] = []
    try:
        run_source(source, output=lines.append)
    except TajikLangError as error:
        lines.append(error.format())
    return "\n".join(lines)


def assert_clean(case, text: str, label: str) -> None:
    # URLs carry the repository owner's name; they are not implementation
    # detail and must not be mistaken for it.
    stripped = re.sub(r"https?://\S+", "", text)
    for word in FORBIDDEN:
        case.assertNotIn(word, stripped, f"{label} leaked {word!r}: {text[:200]}")


class TestErrorsStayInTajik(unittest.TestCase):
    """Every way a student can break a program."""

    CASES = {
        "division by zero": "навис(1 / 0)",
        "undefined name": "навис(нест)",
        "type mismatch": 'навис("а" + 1)',
        "index out of range": "навис([1][9])",
        "missing dictionary key": 'навис({"а": 1}["б"])',
        "wrong argument count": "функсия f(a):\n    баргардон a\nнавис(f())",
        "unclosed bracket": 'навис("бе қавс"',
        "bad indent width": "агар рост:\n  навис(1)",
        "a tab in the indent": "агар рост:\n\tнавис(1)",
        "runaway recursion": "функсия f(n):\n    баргардон f(n + 1)\nf(1)",
        "endless loop": "то_вақте рост:\n    бигзор x = 1",
        "unknown module": "ворид ҳеҷ_чиз",
        "calling a non-function": '"матн"()',
        "truthiness attempt": "агар 5:\n    навис(1)",
        "an operator from another language": "навис(рост && дурӯғ)",
        "break outside a loop": "шикан",
        "return outside a function": "баргардон 1",
        "chained comparison": "навис(1 < 2 < 3)",
        "shadowing": "бигзор x = 1\nагар рост:\n    бигзор x = 2",
        "reading a block variable outside": "агар рост:\n    бигзор x = 1\nнавис(x)",
        "an error deep in a call chain": (
            "функсия дарунӣ():\n    баргардон 1 / 0\n"
            "функсия берунӣ():\n    баргардон дарунӣ()\n"
            "навис(берунӣ())"
        ),
        "a failure inside a class method": (
            "қолиб А:\n    функсия оғоз(худ):\n        худ.x = 1 / 0\nА()"
        ),
        "a bad package name": "ворид ин_баста_нест",
    }

    def test_no_error_shows_the_implementation(self):
        for label, source in self.CASES.items():
            with self.subTest(case=label):
                assert_clean(self, student_sees(source), label)

    def test_every_error_is_actually_in_tajik(self):
        """Cyrillic, not an empty string that would pass the check above."""
        for label, source in self.CASES.items():
            with self.subTest(case=label):
                text = student_sees(source)
                self.assertTrue(re.search(r"[А-Яа-яӯӣқғҳҷЁё]", text), label)


class TestCheckerOutput(unittest.TestCase):
    def test_the_report_stays_in_tajik(self):
        source = "навис(нест)\nагар дурӯғ:\n    навис(боз_нест)\nдуюм = 5"
        lines = source.split("\n")
        text = "\n".join(d.format(lines) for d in check_source(source))
        assert_clean(self, text, "checker")


class TestInternalFaults(unittest.TestCase):
    """Even our own bugs must be reported in the student's language."""

    def test_an_internal_fault_reports_in_tajik(self):
        try:
            {}["ҳеҷ"]
        except Exception as error:      # noqa: BLE001 - deliberately provoked
            text = internal_report(error, "санҷиш")

        assert_clean(self, text, "internal_report")
        self.assertIn("Хатои дохилии забон", text)
        self.assertIn("хатои барномаи шумо нест", text)

    def test_it_points_at_somewhere_to_report(self):
        try:
            raise RuntimeError("simulated")
        except RuntimeError as error:
            text = internal_report(error, "санҷиш")
        self.assertIn("github.com", text)


class TestShippedSurfaces(unittest.TestCase):
    """The playground is the first thing most students will ever open."""

    def test_the_playground_reports_faults_in_tajik(self):
        html = (ROOT / "playground" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Хатои дохилии забон", html)
        self.assertNotIn('"Хатои дохилӣ: " + err', html)

    def test_the_install_page_leads_with_routes_needing_nothing(self):
        """A student meets the browser and the standalone build, in that order.

        The source route exists for people changing the language, and says so.
        """
        install = ROOT / "site" / "install.html"
        if not install.exists():
            self.skipTest("site not built")
        text = install.read_text(encoding="utf-8")

        self.assertLess(text.index("Бе ҳеҷ насб"), text.index("Аз манбаъ"))
        self.assertIn("Ҳеҷ чизи дигар лозим", text)
        self.assertIn("худи забонро тағйир диҳанд", text)

    def test_the_installer_never_requires_a_command_prompt(self):
        """The ordinary student path is click-to-install, not a shell script."""
        install = ROOT / "site" / "install.html"
        if not install.exists():
            self.skipTest("site not built")
        text = install.read_text(encoding="utf-8").lower()
        self.assertNotIn("powershell -executionpolicy", text)
        self.assertNotIn("code --install-extension", text)
        self.assertIn("мизи корӣ", text)


if __name__ == "__main__":
    unittest.main()
