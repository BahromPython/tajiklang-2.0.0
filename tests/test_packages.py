"""Бастаҳо — the package manager, and the import path it adds."""

import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from tajiklang import packages, run_source
from tajiklang.errors import RuntimeErrorTJ


def make_zip(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, body in files.items():
            archive.writestr(name, body)
    return buffer.getvalue()


REGISTRY = {
    "бастаҳо": {
        "санҷишӣ": {
            "тавсиф": "барои санҷиш",
            "нусха": "1.2.3",
            "манбаъ": "https://example.invalid/санҷишӣ.zip",
            "ҷузвдон": "санҷишӣ",
        }
    }
}


class PackageTestCase(unittest.TestCase):
    """Each test gets its own library folder, never the real one."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(
            os.environ, {"TAJIKLANG_HOME": self._dir.name}
        )
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self._dir.cleanup()

    def install(self, files, registry=REGISTRY, name="санҷишӣ"):
        payload = make_zip(files)
        with mock.patch.object(packages, "registry", return_value=registry):
            with mock.patch.object(packages.urllib.request, "urlopen") as opened:
                opened.return_value.__enter__.return_value.read.return_value = payload
                return packages.install(name)


class TestWhereThingsLive(PackageTestCase):
    def test_the_home_folder_is_configurable(self):
        """A school can put the library on a shared drive or a USB stick."""
        self.assertEqual(packages.home(), Path(self._dir.name))

    def test_nothing_is_installed_to_begin_with(self):
        self.assertEqual(packages.installed(), {})
        self.assertIsNone(packages.resolve("санҷишӣ"))


class TestInstalling(PackageTestCase):
    def test_a_package_installs_and_is_importable(self):
        meta = self.install(
            {"repo-main/санҷишӣ/санҷишӣ.tj": "функсия салом():\n    баргардон 1\n"}
        )
        self.assertEqual(meta["нусха"], "1.2.3")
        self.assertEqual(meta["файлҳо"], 1)
        self.assertIsNotNone(packages.resolve("санҷишӣ"))
        self.assertIn("санҷишӣ", packages.installed())

    def test_only_tj_files_are_taken(self):
        meta = self.install({
            "repo-main/санҷишӣ/санҷишӣ.tj": "функсия f():\n    баргардон 1\n",
            "repo-main/санҷишӣ/setup.py": "import os; os.system('rm -rf /')",
            "repo-main/санҷишӣ/README.md": "# hello",
        })
        self.assertEqual(meta["файлҳо"], 1)
        names = {p.name for p in (packages.library() / "санҷишӣ").iterdir()}
        self.assertEqual(names, {"санҷишӣ.tj", "баста.json"})

    def test_the_subfolder_filter_ignores_the_rest_of_a_monorepo(self):
        meta = self.install({
            "repo-main/санҷишӣ/санҷишӣ.tj": "функсия f():\n    баргардон 1\n",
            "repo-main/дигар/дигар.tj": "функсия g():\n    баргардон 2\n",
        })
        self.assertEqual(meta["файлҳо"], 1)

    def test_a_zip_cannot_write_outside_its_folder(self):
        """The classic zip-slip: a path claiming to climb out of the target."""
        with self.assertRaises(packages.PackageError):
            self.install({"repo-main/санҷишӣ/../../../evil.tj": "навис(1)"})
        self.assertFalse((Path(self._dir.name).parent / "evil.tj").exists())

    def test_a_package_must_contain_its_own_named_file(self):
        with self.assertRaises(packages.PackageError) as ctx:
            self.install({"repo-main/санҷишӣ/дигар.tj": "функсия f():\n    баргардон 1\n"})
        self.assertIn("файли асоси", ctx.exception.message)

    def test_an_empty_package_is_refused(self):
        with self.assertRaises(packages.PackageError) as ctx:
            self.install({"repo-main/санҷишӣ/README.md": "nothing"})
        self.assertIn("ягон файли .tj нест", ctx.exception.message)

    def test_an_unknown_package_lists_what_exists(self):
        with mock.patch.object(packages, "registry", return_value=REGISTRY):
            with self.assertRaises(packages.PackageError) as ctx:
                packages.install("ҳеҷ_чиз")
        self.assertIn("дар феҳрист нест", ctx.exception.message)
        self.assertIn("санҷишӣ", ctx.exception.hint)

    def test_installing_twice_replaces_rather_than_merges(self):
        self.install({"repo-main/санҷишӣ/санҷишӣ.tj": "функсия f():\n    баргардон 1\n",
                      "repo-main/санҷишӣ/кӯҳна.tj": "функсия g():\n    баргардон 2\n"})
        self.install({"repo-main/санҷишӣ/санҷишӣ.tj": "функсия f():\n    баргардон 9\n"})
        names = {p.name for p in (packages.library() / "санҷишӣ").iterdir()}
        self.assertNotIn("кӯҳна.tj", names)

    def test_removing(self):
        self.install({"repo-main/санҷишӣ/санҷишӣ.tj": "функсия f():\n    баргардон 1\n"})
        packages.remove("санҷишӣ")
        self.assertEqual(packages.installed(), {})

    def test_removing_something_absent(self):
        with self.assertRaises(packages.PackageError) as ctx:
            packages.remove("ҳеҷ_чиз")
        self.assertIn("насб нашудааст", ctx.exception.message)


class TestTheRegistry(PackageTestCase):
    def test_the_bundled_registry_works_with_no_network(self):
        """A classroom with no internet must still get `tajik ҷустуҷӯ`."""
        with mock.patch.object(
            packages.urllib.request, "urlopen", side_effect=OSError("no network")
        ):
            found = packages.catalogue()
        self.assertIn("омор", found)
        self.assertIn("шакл", found)

    def test_the_shipped_registry_is_valid(self):
        data = json.loads(packages.BUNDLED_REGISTRY.read_text(encoding="utf-8"))
        for name, entry in data["бастаҳо"].items():
            with self.subTest(package=name):
                self.assertIn("манбаъ", entry)
                self.assertIn("нусха", entry)
                self.assertIn("тавсиф", entry)


class TestImportResolution(PackageTestCase):
    def test_ворид_finds_an_installed_package(self):
        self.install({
            "repo-main/санҷишӣ/санҷишӣ.tj":
                "функсия дучанд(x):\n    баргардон x * 2\n"
        })
        lines = []
        run_source(
            "ворид санҷишӣ\nнавис(санҷишӣ.дучанд(21))",
            output=lines.append,
        )
        self.assertEqual(lines, ["42"])

    def test_a_local_file_wins_over_an_installed_package(self):
        """Easier to explain than any search-path rule."""
        self.install({
            "repo-main/санҷишӣ/санҷишӣ.tj":
                'функсия аз_куҷо():\n    баргардон "баста"\n'
        })
        with tempfile.TemporaryDirectory() as folder:
            here = Path(folder)
            (here / "санҷишӣ.tj").write_text(
                'функсия аз_куҷо():\n    баргардон "файли ҳамсоя"\n',
                encoding="utf-8",
            )
            lines = []
            run_source(
                "ворид санҷишӣ\nнавис(санҷишӣ.аз_куҷо())",
                output=lines.append,
                base_dir=here,
            )
        self.assertEqual(lines, ["файли ҳамсоя"])

    def test_a_missing_module_says_how_to_install_one(self):
        with self.assertRaises(RuntimeErrorTJ) as ctx:
            run_source("ворид ҳеҷ_чиз", output=lambda _: None)
        self.assertIn("tajik гирифтан", ctx.exception.hint)


class TestShippedPackages(unittest.TestCase):
    """The two starter packages must pass the checker like any other program."""

    def test_they_check_clean(self):
        from tajiklang import check_source

        folder = Path(__file__).resolve().parent.parent / "бастаҳо"
        for path in sorted(folder.rglob("*.tj")):
            with self.subTest(package=path.name):
                found = [
                    d for d in check_source(path.read_text(encoding="utf-8"))
                    if not d.is_warning
                ]
                self.assertEqual(found, [], path.name)


if __name__ == "__main__":
    unittest.main()
