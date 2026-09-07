"""TajikWeb: a plain .tj page becomes a portable static website."""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tajiklang.cli import EX_DATAERR, main
from tajiklang.web import WebError, build_project, create_project, prepare_github_pages


class TestTajikWeb(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)

    def tearDown(self):
        self._temporary.cleanup()

    def test_a_project_has_an_editable_tajik_source(self):
        site = create_project("сомонаи_ман", self.root)
        source = (site / "index.tj").read_text(encoding="utf-8")
        self.assertIn("ворид саҳифа", source)
        self.assertTrue((site / "tajikweb.json").is_file())
        self.assertTrue((site / "static").is_dir())

    def test_build_writes_normal_html_and_assets(self):
        site = create_project("сайт", self.root)
        (site / "static" / "нишон.txt").write_text("салом", encoding="utf-8")
        result = build_project(site)
        page = (result.output / "index.html").read_text(encoding="utf-8")
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertIn("сайт", page)
        self.assertEqual((result.output / "static" / "нишон.txt").read_text(encoding="utf-8"), "салом")

    def test_build_reports_language_errors_without_a_python_traceback(self):
        site = create_project("сайт", self.root)
        (site / "index.tj").write_text("ворид саҳифа\nнавис(номи_нест)\n", encoding="utf-8")
        with self.assertRaisesRegex(WebError, "муайян нашудааст"):
            build_project(site)

    def test_github_pages_workflow_builds_the_static_output(self):
        site = create_project("сайт", self.root)
        workflow = prepare_github_pages(site)
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("tajik веб соз .", text)
        self.assertIn("actions/deploy-pages@v4", text)

    def test_cli_creates_a_site_in_the_current_folder(self):
        out, err = io.StringIO(), io.StringIO()
        old = Path.cwd()
        try:
            os.chdir(self.root)
            with redirect_stdout(out), redirect_stderr(err):
                code = main(["веб", "нав", "сайти_ман"])
        finally:
            os.chdir(old)
        self.assertEqual(code, 0)
        self.assertEqual(err.getvalue(), "")
        self.assertTrue((self.root / "сайти_ман" / "index.tj").is_file())

    def test_cli_builds_a_site(self):
        site = create_project("сайт", self.root)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["веб", "соз", str(site)])
        self.assertEqual(code, 0)
        self.assertEqual(err.getvalue(), "")
        self.assertIn("index.html", out.getvalue())

    def test_cli_returns_a_normal_error_for_a_bad_web_project(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["веб", "соз", str(self.root)])
        self.assertEqual(code, EX_DATAERR)
        self.assertIn("tajikweb.json", err.getvalue())


if __name__ == "__main__":
    unittest.main()
