"""Release-contract checks for the Electron Studio and its Windows integration."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tajiklang import __version__


ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "studio-electron"


class TestStudioDistribution(unittest.TestCase):
    def test_studio_has_the_required_menu_and_smoke_test(self):
        source = (STUDIO / "main.cjs").read_text(encoding="utf-8")
        for label in ("Файл", "Таҳрир", "Намоиш", "Иҷро", "Терминал", "Кумак"):
            self.assertIn(label, source)
        self.assertIn("TAJIKLANG_SMOKE", source)
        self.assertIn("Terminal runner failed", source)
        self.assertIn('ipcMain.handle("file:new"', source)

    def test_windows_installer_has_icon_and_terminal_context_action(self):
        source = (STUDIO / "installer.nsh").read_text(encoding="utf-8")
        self.assertIn("DefaultIcon", source)
        self.assertIn("TajikLang Studio.exe,0", source)
        self.assertIn("Иҷро дар терминали TajikLang", source)
        self.assertIn("tajik.cmd", source)
        self.assertIn("SHChangeNotify", source)

    def test_vscode_extension_is_complete_and_versioned(self):
        folder = ROOT / "editors" / "vscode"
        package = json.loads((folder / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["version"], __version__)
        self.assertTrue((folder / package["icon"]).is_file())
        readme = (folder / "README.md").read_text(encoding="utf-8")
        self.assertIn("TajikLang Next", readme)
        grammar = (folder / "syntaxes" / "tajiklang.tmLanguage.json").read_text(encoding="utf-8")
        for keyword in ("дода", "нишон", "дигар"):
            self.assertIn(keyword, grammar)


if __name__ == "__main__":
    unittest.main()
