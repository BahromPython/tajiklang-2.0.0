"""Бастаи мустақил месозад — builds TajikLang into a folder with no Python.

    py tools/build_exe.py

Produces `dist/TajikLang/` containing `tajik.exe` and everything it needs.
A school can copy that folder onto a machine that has never seen Python and
run Tajik programs on it — which is the point. `pip install` assumes a Python
installation, a working network, and a student who already knows what pip is;
none of those are safe assumptions in a classroom.

Produces the runtime used by the graphical Windows installer. PyInstaller is
required only on the build machine — never on a student's computer.
"""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
NAME = "tajik"


def _utf8_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="replace")


def _make_icon(target: Path) -> Path:
    """Write a dependency-free 64px TajikLang Studio .ico for the EXE."""
    width = height = 64
    pixels = bytearray()
    for y in range(height - 1, -1, -1):  # ICO bitmap pixels are bottom-up
        for x in range(width):
            red, green, blue = (16, 33, 59)
            if 6 <= x < 58 and 6 <= y < 58:
                red, green, blue = (61, 214, 163)
            # A clear, high-contrast Tajik "Т" mark.
            if 16 <= x < 48 and 15 <= y < 23 or 28 <= x < 36 and 21 <= y < 51 or 18 <= x < 46 and 45 <= y < 53:
                red, green, blue = (223, 252, 242)
            pixels.extend((blue, green, red, 255))
    header = struct.pack("<HHH", 0, 1, 1)
    image_size = 40 + len(pixels) + (width * height // 8)
    directory = struct.pack("<BBBBHHII", width, height, 0, 0, 1, 32, image_size, 22)
    bitmap = struct.pack("<IIIHHIIIIII", 40, width, height * 2, 1, 32, 0, len(pixels), 0, 0, 0, 0)
    target.write_bytes(header + directory + bitmap + pixels + bytes(width * height // 8))
    return target


INSTALL_PS1 = r"""# TajikLang — насбкунанда
#
# Ин скрипт TajikLang-ро бе Python насб мекунад:
#   * файлҳоро ба %LOCALAPPDATA%\Programs\TajikLang мегузорад
#   * фармони `tajik`-ро ба PATH илова мекунад
#   * файлҳои .tj-ро бо TajikLang мепайвандад
#   * миёнбурҳоро дар менюи Start месозад
#
# Иҷро:  powershell -ExecutionPolicy Bypass -File насб.ps1

$ErrorActionPreference = "Stop"
$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = Join-Path $env:LOCALAPPDATA "Programs\TajikLang"

Write-Host "TajikLang — насб" -ForegroundColor Green
Write-Host ""

# --- 1. файлҳо ---------------------------------------------------------
if (Test-Path $target) {
    Write-Host "  Нусхаи кӯҳна нест карда мешавад..."
    Remove-Item -Recurse -Force $target
}
Write-Host "  Нусхабардорӣ ба $target"
New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -Path (Join-Path $source "*") -Destination $target -Recurse -Force

# --- 2. PATH -----------------------------------------------------------
$path = [Environment]::GetEnvironmentVariable("Path", "User")
if ($path -notlike "*$target*") {
    Write-Host "  Илова ба PATH"
    [Environment]::SetEnvironmentVariable("Path", "$path;$target", "User")
} else {
    Write-Host "  PATH аллакай дуруст аст"
}

# --- 3. файлҳои .tj ----------------------------------------------------
Write-Host "  Пайвасти файлҳои .tj"
$exe = Join-Path $target "tajik.exe"
New-Item -Path "HKCU:\Software\Classes\.tj" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\.tj" -Name "(Default)" -Value "TajikLang.Barnoma"
New-Item -Path "HKCU:\Software\Classes\TajikLang.Barnoma\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\TajikLang.Barnoma" -Name "(Default)" -Value "Барномаи TajikLang"
Set-ItemProperty -Path "HKCU:\Software\Classes\TajikLang.Barnoma\shell\open\command" -Name "(Default)" -Value "`"$exe`" `"%1`""

New-Item -Path "HKCU:\Software\Classes\TajikLang.Barnoma\shell\Муҳаррир\command" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\TajikLang.Barnoma\shell\Муҳаррир\command" -Name "(Default)" -Value "`"$exe`" муҳаррир `"%1`""

# --- 4. менюи Start ----------------------------------------------------
$menu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\TajikLang"
New-Item -ItemType Directory -Force -Path $menu | Out-Null
$shell = New-Object -ComObject WScript.Shell

$link = $shell.CreateShortcut((Join-Path $menu "TajikLang Муҳаррир.lnk"))
$link.TargetPath = $exe
$link.Arguments = "муҳаррир"
$link.WorkingDirectory = $target
$link.Description = "Муҳаррири TajikLang"
$link.Save()

$link = $shell.CreateShortcut((Join-Path $menu "TajikLang.lnk"))
$link.TargetPath = "cmd.exe"
$link.Arguments = "/k `"$exe`""
$link.WorkingDirectory = $env:USERPROFILE
$link.Description = "Реҷаи интерактивии TajikLang"
$link.Save()

Write-Host ""
Write-Host "Насб шуд." -ForegroundColor Green
Write-Host ""
Write-Host "  Терминали навро кушоед ва нависед:  tajik"
Write-Host "  Муҳаррир:                           tajik муҳаррир"
Write-Host "  Бастаҳо:                            tajik ҷустуҷӯ"
Write-Host ""
Write-Host "Файлҳои .tj акнун бо ду клик кор мекунанд."
"""

UNINSTALL_PS1 = r"""# TajikLang — несткунанда
#
# Иҷро:  powershell -ExecutionPolicy Bypass -File нест.ps1

$ErrorActionPreference = "Continue"
$target = Join-Path $env:LOCALAPPDATA "Programs\TajikLang"

Write-Host "TajikLang — нест кардан" -ForegroundColor Yellow

if (Test-Path $target) { Remove-Item -Recurse -Force $target }

$path = [Environment]::GetEnvironmentVariable("Path", "User")
$clean = ($path -split ";" | Where-Object { $_ -ne $target }) -join ";"
[Environment]::SetEnvironmentVariable("Path", $clean, "User")

Remove-Item -Recurse -Force "HKCU:\Software\Classes\.tj" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "HKCU:\Software\Classes\TajikLang.Barnoma" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\TajikLang") -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Нест шуд. Бастаҳои насбшуда дар $env:LOCALAPPDATA\TajikLang мондаанд."
Write-Host "Барои нест кардани онҳо низ он ҷузвдонро нест кунед."
"""

READ_ME = """TajikLang — забони барномасозӣ бо забони тоҷикӣ
================================================

Ин ҷузвдон нусхаи мустақили TajikLang аст. Python лозим НЕСТ.
Барои донишҷӯён: TajikLang Setup.exe-ро ду клик карда Install-ро пахш кунед.
Он нишонаи TajikLang Studio-ро дар мизи корӣ месозад.

ИСТИФОДА
--------
    Studio/TajikLang.exe    муҳаррири графикиро мекушояд

БАСТАҲО
-------
    tajik ҷустуҷӯ           бастаҳои мавҷуда
    tajik гирифтан омор     бастаро насб мекунад
    tajik бастаҳо           насбшударо нишон медиҳад

НЕСТ КАРДАН
-----------
Windows Settings → Apps → TajikLang → Uninstall

Дарсҳо ва ҳуҷҷатҳо:  https://github.com/BahromPython/tajiklang-2.0.0
"""


def main() -> int:
    _utf8_stdout()

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print(
            "PyInstaller лозим аст (танҳо барои сохтан):\n"
            "    pip install pyinstaller",
            file=sys.stderr,
        )
        return 1

    for folder in (BUILD, DIST / "TajikLang"):
        if folder.exists():
            shutil.rmtree(folder)
    BUILD.mkdir(parents=True, exist_ok=True)

    icon = _make_icon(BUILD / "tajiklang-studio.ico")
    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", NAME,
        "--distpath", str(DIST),
        "--workpath", str(BUILD),
        "--specpath", str(BUILD),
        # onedir, not onefile: a single .exe unpacks itself into a temp folder
        # on every run, which on a slow school machine is a visible pause
        # before "Салом" appears.
        "--onedir",
        "--console",
        "--icon", str(icon),
        # the bundled registry travels with the build, so `tajik ҷустуҷӯ`
        # works on a machine that has never had a network
        "--add-data", f"{ROOT / 'бастаҳо' / 'феҳрист.json'}{os.pathsep}бастаҳо",
        "--hidden-import", "tkinter",
        # CLI subcommands import these only when the student asks for them;
        # name them here so the no-Python Windows application has every
        # feature that the source version has.
        "--hidden-import", "tajiklang.web",
        "--hidden-import", "tajiklang.blocks",
        "--hidden-import", "tajiklang.environment",
        "--hidden-import", "tajiklang.webapp",
        # main.py, not tajiklang/__main__.py: PyInstaller runs the entry as a
        # top-level script, where `from .cli import main` has no parent
        # package to be relative to.
        str(ROOT / "main.py"),
    ]

    print("Сохтан… (як-ду дақиқа)")
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        return result.returncode

    package = DIST / "TajikLang"
    (DIST / NAME).rename(package)

    # The command-line tool remains available for advanced users, but the
    # installer launches this separate windowed build. It never creates a
    # PowerShell/cmd window behind the student-facing editor.
    studio_dist = BUILD / "studio-dist"
    studio_command = list(command)
    studio_command[studio_command.index("--name") + 1] = "TajikLang"
    studio_command[studio_command.index("--distpath") + 1] = str(studio_dist)
    studio_command[studio_command.index("--workpath") + 1] = str(BUILD / "studio-work")
    studio_command[studio_command.index("--specpath") + 1] = str(BUILD / "studio-spec")
    studio_command[studio_command.index("--console")] = "--windowed"
    studio_command[-1] = str(ROOT / "tajiklang" / "desktop.py")
    print("TajikLang Studio сохта мешавад…")
    result = subprocess.run(studio_command, cwd=ROOT)
    if result.returncode != 0:
        return result.returncode
    shutil.copytree(studio_dist / "TajikLang", package / "Studio")

    (package / "ХОНЕД.txt").write_text(READ_ME, encoding="utf-8-sig")

    shutil.copytree(ROOT / "examples", package / "мисолҳо", dirs_exist_ok=True)
    shutil.copy(ROOT / "docs" / "дарсҳо.md", package / "дарсҳо.md")
    shutil.copy(ROOT / "LICENSE", package / "LICENSE")

    archive = shutil.make_archive(
        str(DIST / "TajikLang-windows"), "zip", root_dir=DIST, base_dir="TajikLang"
    )

    size = sum(f.stat().st_size for f in package.rglob("*") if f.is_file())
    print()
    print(f"  {package.relative_to(ROOT)}  ({size / 1024 / 1024:.0f} MB)")
    print(f"  {Path(archive).relative_to(ROOT)}")
    print()
    print("Барои донишҷӯён: TajikLang Setup.exe-ро истифода баред.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
