"""The editor: it must check, run and colour without a screen attached.

Skipped where tkinter is missing or no display exists — CI on Linux has no
X server, and an IDE test that fails there would be noise, not signal.
"""

import unittest
from pathlib import Path

try:
    import tkinter as tk

    _root = tk.Tk()
    _root.destroy()
    HAVE_TK = True
except Exception:                     # noqa: BLE001 - any failure means no GUI
    HAVE_TK = False

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@unittest.skipUnless(HAVE_TK, "tkinter or a display is unavailable")
class TestIDE(unittest.TestCase):
    def setUp(self):
        from tajiklang.ide import IDE

        self.root = tk.Tk()
        self.root.withdraw()
        self.ide = IDE(self.root, EXAMPLES)

    def tearDown(self):
        self.root.destroy()

    def _write(self, source):
        """Type into the editor — including the redraw a keystroke triggers."""
        self.ide.editor.delete("1.0", "end")
        self.ide.editor.insert("1.0", source)
        self.ide._after_edit()

    def test_it_lists_the_example_files(self):
        self.assertGreater(self.ide.file_list.size(), 5)

    def test_checking_finds_every_problem(self):
        self._write('агар дурӯғ:\n    навис(нмо)\nнавис(ҳеҷ_ном)\n')
        self.assertFalse(self.ide.check())
        self.assertEqual([line for line, _ in self.ide.problems], [2, 3])

    def test_a_clean_program_checks_clean(self):
        self._write('навис("Салом")\n')
        self.assertTrue(self.ide.check())

    def test_running_uses_the_input_pane(self):
        self._write('бигзор ном = хонед()\nнавис("Салом,", ном)\n')
        self.ide.stdin.insert("1.0", "Далер")
        self.ide.run()
        self.assertEqual(self.ide.output.get("1.0", "end-1c"), "Салом, Далер")

    def test_a_broken_program_never_runs(self):
        self._write('навис("ин чоп намешавад")\nнавис(нест)\n')
        self.ide.run()
        self.assertIn("иҷро нашуд", self.ide.output.get("1.0", "end-1c"))

    def test_a_runtime_error_is_shown_in_full(self):
        self._write("навис(1 / 0)\n")
        self.ide.run()
        shown = self.ide.output.get("1.0", "end-1c")
        self.assertIn("Тақсим ба сифр", shown)
        self.assertIn("^", shown)

    def test_syntax_errors_reach_the_problems_panel(self):
        self._write('навис("бе қавс"\n')
        self.assertFalse(self.ide.check())
        self.assertEqual(len(self.ide.problems), 1)

    def test_every_example_opens_and_checks_clean(self):
        for path in sorted(EXAMPLES.glob("*.tj")):
            if "хато" in path.name:
                continue
            with self.subTest(example=path.name):
                self.ide._open(path)
                self.assertTrue(self.ide.check(), path.name)

    def test_colouring_tags_are_applied(self):
        self._write('# шарҳ\nбигзор x = 5\nнавис("матн")\n')
        for tag in ("comment", "keyword", "number", "string", "builtin"):
            with self.subTest(tag=tag):
                self.assertTrue(self.ide.editor.tag_ranges(tag), tag)

    def test_a_keyword_inside_a_longer_name_is_not_coloured(self):
        """`тозагӣ` starts with `то`, `бароям` with `барои` — neither is one."""
        self._write("тозагӣ = 1\nбароям = 2\nагарчи = 3\n")
        self.assertFalse(self.ide.editor.tag_ranges("keyword"))

    def test_real_keywords_still_colour(self):
        self._write("бигзор x = 1\n")
        self.assertTrue(self.ide.editor.tag_ranges("keyword"))

    def test_enter_indents_after_a_colon(self):
        self._write("агар рост:")
        self.ide.editor.mark_set("insert", "end-1c")
        self.ide._auto_indent(None)
        self.assertTrue(self.ide.editor.get("2.0", "2.end").startswith("    "))


if __name__ == "__main__":
    unittest.main()
