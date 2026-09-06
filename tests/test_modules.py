import tempfile
import unittest
from pathlib import Path

from tajiklang import run_file, run_source
from tajiklang.errors import RuntimeErrorTJ


def run(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


class TestBuiltinModules(unittest.TestCase):
    def test_import_and_use(self):
        self.assertEqual(run("ворид риёзӣ\nнавис(риёзӣ.реша(16))"), ["4"])

    def test_several_functions(self):
        source = (
            "ворид риёзӣ\n"
            "навис(риёзӣ.дараҷа(2, 10))\n"
            "навис(риёзӣ.мутлақ(-5))\n"
            "навис(риёзӣ.мин(3, 7))\n"
            "навис(риёзӣ.макс(3, 7))\n"
            "навис(риёзӣ.гирд(3.7))\n"
        )
        self.assertEqual(run(source), ["1024", "5", "3", "7", "4"])

    def test_a_constant(self):
        self.assertEqual(run("ворид риёзӣ\nнавис(риёзӣ.гирд(риёзӣ.ПИ))"), ["3"])

    def test_a_module_function_reports_its_own_errors(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("ворид риёзӣ\nнавис(риёзӣ.реша(-1))")
        self.assertIn("рақами манфӣ", ctx.exception.message)

    def test_an_unknown_member_lists_what_exists(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("ворид риёзӣ\nнавис(риёзӣ.ҳеҷ)")
        self.assertIn("надорад", ctx.exception.message)
        self.assertIn("реша", ctx.exception.hint)

    def test_an_unknown_module(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("ворид ҳеҷ_чиз")
        self.assertIn("ёфт нашуд", ctx.exception.message)
        self.assertIn("риёзӣ", ctx.exception.hint)

    def test_a_module_cannot_take_a_taken_name(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("бигзор риёзӣ = 1\nворид риёзӣ")
        self.assertIn("аллакай муайян шудааст", ctx.exception.message)

    def test_dot_only_works_on_modules(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run("бигзор x = 1\nнавис(x.чиз)")
        self.assertIn("танҳо барои модулҳо", ctx.exception.hint)


class TestFileModules(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)

    def tearDown(self):
        self._dir.cleanup()

    def _write(self, name, text):
        path = self.folder / (name + ".tj")
        path.write_text(text, encoding="utf-8")
        return path

    def _run(self, path):
        lines = []
        run_file(path, output=lines.append)
        return lines

    def test_importing_a_neighbouring_file(self):
        self._write("асбоб", "функсия дучанд(x):\n    баргардон x * 2\n")
        main = self._write("асосӣ", "ворид асбоб\nнавис(асбоб.дучанд(21))\n")
        self.assertEqual(self._run(main), ["42"])

    def test_a_module_can_export_a_value(self):
        self._write("танзим", 'бигзор ном = "Душанбе"\n')
        main = self._write("асосӣ", "ворид танзим\nнавис(танзим.ном)\n")
        self.assertEqual(self._run(main), ["Душанбе"])

    def test_module_top_level_code_runs_once(self):
        self._write("салом", 'навис("бор карда шуд")\n')
        main = self._write("асосӣ", "ворид салом\nворид салом\n")
        with self.assertRaises(RuntimeErrorTJ):
            # the second import clashes on the name, but the file ran once
            self._run(main)

    def test_a_module_importing_itself_is_caught(self):
        main = self._write("худ", "ворид худ\n")
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            self._run(main)
        self.assertIn("худашро ворид мекунад", ctx.exception.message)

    def test_an_error_inside_a_module_names_the_module_line(self):
        self._write("бад", "навис(1 / 0)\n")
        main = self._write("асосӣ", "ворид бад\n")
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            self._run(main)
        self.assertIn("Тақсим ба сифр", ctx.exception.message)


if __name__ == "__main__":
    unittest.main()
