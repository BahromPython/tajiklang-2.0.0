import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tajiklang import __version__
from tajiklang.cli import EX_DATAERR, EX_NOINPUT, EX_USAGE, main, opens_block


def call(*args):
    """Run the CLI and capture (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


class TestCommandLine(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)

    def tearDown(self):
        self._dir.cleanup()

    def _write(self, text, name="барнома.tj"):
        path = self.folder / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_running_a_file(self):
        code, out, _ = call(self._write('навис("Салом")\n'))
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "Салом")

    def test_a_failing_program_exits_65(self):
        code, _, err = call(self._write("навис(1 / 0)\n"))
        self.assertEqual(code, EX_DATAERR)
        self.assertIn("Тақсим ба сифр", err)

    def test_a_missing_file_exits_66(self):
        code, _, err = call(str(self.folder / "нест.tj"))
        self.assertEqual(code, EX_NOINPUT)
        self.assertIn("ёфт нашуд", err)

    def test_too_many_arguments_exits_64(self):
        code, out, _ = call("a.tj", "b.tj")
        self.assertEqual(code, EX_USAGE)
        self.assertIn("Истифода", out)

    def test_version(self):
        code, out, _ = call("--version")
        self.assertEqual(code, 0)
        self.assertIn(__version__, out)

    def test_help(self):
        code, out, _ = call("--help")
        self.assertEqual(code, 0)
        self.assertIn("реҷаи интерактивӣ", out)

    def test_tokens_mode(self):
        code, out, _ = call("--tokens", self._write('навис("а")\n'))
        self.assertEqual(code, 0)
        self.assertIn("IDENT", out)
        self.assertIn("EOF", out)

    def test_ast_mode(self):
        code, out, _ = call("--ast", self._write('навис("а")\n'))
        self.assertEqual(code, 0)
        self.assertIn("CallExpression", out)

    def test_imports_resolve_next_to_the_file_not_the_shell(self):
        """`tajik пойгоҳ/барнома.tj` must find пойгоҳ/асбоб.tj."""
        (self.folder / "асбоб.tj").write_text(
            "функсия дучанд(x):\n    баргардон x * 2\n", encoding="utf-8"
        )
        path = self._write("ворид асбоб\nнавис(асбоб.дучанд(21))\n")
        code, out, _ = call(path)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "42")


class TestReplBuffering(unittest.TestCase):
    def test_a_block_opener_keeps_reading(self):
        self.assertTrue(opens_block("агар x > 1:"))
        self.assertTrue(opens_block("функсия ҷамъ(a, b):"))
        self.assertTrue(opens_block("    барои i аз 1 то 5:"))

    def test_a_complete_line_does_not(self):
        self.assertFalse(opens_block('навис("а")'))
        self.assertFalse(opens_block(""))

    def test_a_comment_ending_in_a_colon_does_not(self):
        self.assertFalse(opens_block("# ба ин монанд:"))


if __name__ == "__main__":
    unittest.main()
