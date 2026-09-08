"""Сохтани TajikLang барои macOS — only run this script on a Mac.

It produces both a portable ZIP and a conventional ``.pkg`` installer.  The
package is deliberately unsigned: signing and Apple notarization require the
project owner's Apple Developer credentials, which must never be kept in this
repository.  GitHub Actions runs this on real Intel and Apple-silicon macOS
machines for releases.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build-macos"


def main() -> int:
    if sys.platform != "darwin":
        print("Ин сохтмон танҳо дар macOS иҷро мешавад.", file=sys.stderr)
        return 2

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller лозим аст: python3 -m pip install pyinstaller", file=sys.stderr)
        return 1

    architecture = os.environ.get("TAJIKLANG_ARCH", platform.machine())
    package = DIST / "TajikLang"
    for folder in (BUILD, package):
        if folder.exists():
            shutil.rmtree(folder)
    DIST.mkdir(exist_ok=True)

    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--name", "tajik", "--onedir", "--console",
        "--distpath", str(DIST), "--workpath", str(BUILD), "--specpath", str(BUILD),
        "--add-data", f"{ROOT / 'бастаҳо' / 'феҳрист.json'}{os.pathsep}бастаҳо",
        "--hidden-import", "tkinter",
        "--hidden-import", "tajiklang.web",
        "--hidden-import", "tajiklang.blocks",
        "--hidden-import", "tajiklang.environment",
        "--hidden-import", "tajiklang.webapp",
        str(ROOT / "main.py"),
    ]
    if subprocess.run(command, cwd=ROOT).returncode:
        return 1

    (DIST / "tajik").rename(package)
    shutil.copytree(ROOT / "examples", package / "мисолҳо")
    shutil.copy(ROOT / "docs" / "дарсҳо.md", package / "дарсҳо.md")
    shutil.copy(ROOT / "LICENSE", package / "LICENSE")
    (package / "ХОНЕД.txt").write_text(
        "TajikLang барои macOS\n\n"
        "Барои иҷро аз Terminal:\n    ./tajik барнома.tj\n\n"
        "Ин нусха то имзои расмии Apple unsigned аст.\n",
        encoding="utf-8",
    )

    stem = f"TajikLang-macos-{architecture}"
    shutil.make_archive(str(DIST / stem), "zip", DIST, "TajikLang")
    result = subprocess.run([
        "pkgbuild", "--root", str(package),
        "--identifier", "org.tajiklang.desktop",
        "--version", os.environ.get("TAJIKLANG_VERSION", "2.1.0").lstrip("v"),
        "--install-location", "/Applications/TajikLang",
        str(DIST / f"{stem}.pkg"),
    ])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
