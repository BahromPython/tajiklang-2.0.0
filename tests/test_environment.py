"""Project environments and TajikBlocks never need Python tooling from users."""

import json
import io
import os
import tempfile
import unittest
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from tajiklang import environment, packages, run_source
from tajiklang.blocks import BLOCKS_HTML, run_blocks_source, start_in_thread
from tajiklang.cli import main


class TestProjectEnvironment(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)

    def tearDown(self):
        self._temporary.cleanup()

    def test_new_project_has_a_local_library(self):
        project = environment.create_project("лоиҳаи_ман", self.root)
        self.assertTrue((project / "барнома.tj").is_file())
        self.assertTrue((project / ".tajiklang" / "китобхона").is_dir())
        config = json.loads((project / ".tajiklang" / "лоиҳа.json").read_text(encoding="utf-8"))
        self.assertEqual(config["навъ"], "муҳити TajikLang")

    def test_environment_is_found_from_a_child_folder(self):
        project = environment.create_project("лоиҳа", self.root)
        child = project / "рамз" / "дигар"
        child.mkdir(parents=True)
        self.assertEqual(environment.find(child), project)

    def test_cli_creates_a_project(self):
        old = Path.cwd()
        try:
            os.chdir(self.root)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["лоиҳа", "нав", "аз_cli"]), 0)
        finally:
            os.chdir(old)
        self.assertTrue((self.root / "аз_cli" / ".tajiklang" / "лоиҳа.json").is_file())

    def test_a_project_library_wins_over_the_global_library(self):
        project = environment.create_project("лоиҳа", self.root)
        local = project / ".tajiklang" / "китобхона" / "асбоб"
        local.mkdir()
        (local / "асбоб.tj").write_text(
            'функсия ном():\n    баргардон "лоиҳа"\n', encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as global_home:
            global_package = Path(global_home) / "китобхона" / "асбоб"
            global_package.mkdir(parents=True)
            (global_package / "асбоб.tj").write_text(
                'функсия ном():\n    баргардон "умумӣ"\n', encoding="utf-8"
            )
            with mock.patch.dict(os.environ, {"TAJIKLANG_HOME": global_home}):
                lines: list[str] = []
                run_source(
                    "ворид асбоб\nнавис(асбоб.ном())",
                    output=lines.append,
                    base_dir=project,
                )
        self.assertEqual(lines, ["лоиҳа"])


class TestTajikBlocks(unittest.TestCase):
    def test_blocks_run_the_same_language(self):
        result = run_blocks_source('бигзор ном = "Баҳром"\nнавис("Салом", ном)')
        self.assertEqual(result, {"output": "Салом Баҳром", "error": ""})

    def test_blocks_show_tajik_errors(self):
        result = run_blocks_source("навис(номаи_нест)")
        self.assertEqual(result["output"], "")
        self.assertIn("муайян нашудааст", result["error"])

    def test_editor_is_local_and_uses_tajik_controls(self):
        self.assertIn("/api/run", BLOCKS_HTML)
        self.assertIn("Тағйирёбанда", BLOCKS_HTML)
        self.assertIn("барномасозии визуалӣ", BLOCKS_HTML)

    def test_local_server_serves_editor_and_runs_program(self):
        server, thread = start_in_thread()
        try:
            host, port = server.server_address[:2]
            with urllib.request.urlopen(f"http://{host}:{port}/") as response:
                self.assertIn("TajikBlocks", response.read().decode("utf-8"))
            request = urllib.request.Request(
                f"http://{host}:{port}/api/run",
                data=json.dumps({"source": 'навис("Салом")'}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                result = json.loads(response.read().decode("utf-8"))
            self.assertEqual(result["output"], "Салом")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)


if __name__ == "__main__":
    unittest.main()
