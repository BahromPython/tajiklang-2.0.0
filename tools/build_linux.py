"""Build a portable TajikLang Studio package for 64-bit Linux.

Run this only on Linux.  It creates a ``.tar.gz`` containing both the
windowed TajikLang Studio app and the command-line runtime; no Python is
needed on the student's computer after extraction.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build-linux"


def build(name: str, entry: Path, *, windowed: bool, dist: Path) -> int:
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
        "--name", name, "--distpath", str(dist), "--workpath", str(BUILD / name),
        "--specpath", str(BUILD / name), "--windowed" if windowed else "--console",
        "--add-data", f"{ROOT / 'бастаҳо' / 'феҳрист.json'}:бастаҳо",
        "--hidden-import", "tkinter", "--hidden-import", "tajiklang.web",
        "--hidden-import", "tajiklang.blocks", "--hidden-import", "tajiklang.environment",
        "--hidden-import", "tajiklang.webapp", str(entry),
    ]
    return subprocess.run(command, cwd=ROOT).returncode


def main() -> int:
    if sys.platform != "linux":
        print("Ин сохтмон танҳо дар Linux иҷро мешавад.", file=sys.stderr)
        return 2
    if platform.machine() not in {"x86_64", "amd64"}:
        print("Ҳоло танҳо Linux x86_64 дастгирӣ мешавад.", file=sys.stderr)
        return 2

    for path in (BUILD, DIST / "TajikLang-linux-x86_64"):
        if path.exists():
            shutil.rmtree(path)
    BUILD.mkdir(parents=True, exist_ok=True)
    DIST.mkdir(exist_ok=True)
    staging = DIST / "TajikLang-linux-x86_64"

    if build("tajik", ROOT / "main.py", windowed=False, dist=BUILD / "cli"):
        return 1
    if build("TajikLang Studio", ROOT / "tajiklang" / "desktop.py", windowed=True, dist=BUILD / "studio"):
        return 1

    shutil.copytree(BUILD / "cli" / "tajik", staging / "tajik")
    shutil.copytree(BUILD / "studio" / "TajikLang Studio", staging / "Studio")
    shutil.copytree(ROOT / "examples", staging / "мисолҳо")
    shutil.copy(ROOT / "LICENSE", staging / "LICENSE")
    (staging / "README.txt").write_text(
        "TajikLang Studio барои Linux\n\n"
        "Барои кушодан:\n    ./Studio/TajikLang\\ Studio\n\n"
        "Агар барнома кушода нашавад, tkinter-ро насб кунед:\n"
        "    sudo apt install python3-tk\n",
        encoding="utf-8",
    )
    archive = shutil.make_archive(str(DIST / "TajikLang-linux-x86_64"), "gztar", DIST, staging.name)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
