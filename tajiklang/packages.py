"""Бастаҳо — TajikLang's own package manager.

    tajik гирифтан омор      # install a package
    tajik бастаҳо            # list what is installed
    tajik нест омор          # remove one
    tajik ҷустуҷӯ            # see what exists

Deliberately **not** pip. A student installing a TajikLang library should not
have to learn Python's tooling first, and a school that runs the standalone
build has no pip at all. So packages are plain folders of `.tj` files, the
registry is one JSON file, and everything here uses the standard library.

Where things live:

    %LOCALAPPDATA%\\TajikLang\\        (Windows)
    ~/.tajiklang/                     (everywhere else)
        китобхона/                    installed packages
            омор/
                омор.tj               the file `ворид омор` finds
                баста.json            what was installed, and from where

Set `TAJIKLANG_HOME` to move the whole thing — a school can put it on a shared
drive, or a student on a USB stick.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

# The registry that ships with the language, so `tajik ҷустуҷӯ` works offline.
BUNDLED_REGISTRY = Path(__file__).resolve().parent.parent / "бастаҳо" / "феҳрист.json"

# The same file on GitHub, so a new package appears without a new release.
REMOTE_REGISTRY = (
    "https://raw.githubusercontent.com/BahromPython/tajiklang/main/"
    "%D0%B1%D0%B0%D1%81%D1%82%D0%B0%D2%B3%D0%BE/"
    "%D1%84%D0%B5%D2%B3%D1%80%D0%B8%D1%81%D1%82.json"
)

TIMEOUT = 20


class PackageError(Exception):
    """Something went wrong that the student should read, in Tajik."""

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


# ---------------------------------------------------------------------------
# where things live
# ---------------------------------------------------------------------------
def home() -> Path:
    """The folder holding installed packages."""
    override = os.environ.get("TAJIKLANG_HOME")
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / "TajikLang"
    return Path.home() / ".tajiklang"


def library(project_root: Path | None = None) -> Path:
    """The global library, or a project's own library when requested."""
    if project_root is not None:
        from . import environment

        return project_root / environment.ENV_DIR / environment.LIBRARY
    return home() / "китобхона"


def installed(project_root: Path | None = None) -> dict[str, dict[str, Any]]:
    """Every installed package, by name."""
    found: dict[str, dict[str, Any]] = {}
    folder = library(project_root)
    if not folder.is_dir():
        return found

    for entry in sorted(folder.iterdir()):
        metadata = entry / "баста.json"
        if entry.is_dir() and metadata.is_file():
            try:
                found[entry.name] = json.loads(metadata.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                found[entry.name] = {"ном": entry.name, "нусха": "?"}
    return found


def resolve(name: str, base_dir: Path | None = None) -> Path | None:
    """Find a package: project environment first, global library second."""
    if base_dir is not None:
        from . import environment

        project = environment.find(base_dir)
        if project is not None:
            candidate = library(project) / name / f"{name}.tj"
            if candidate.is_file():
                return candidate

    candidate = library() / name / f"{name}.tj"
    return candidate if candidate.is_file() else None


# ---------------------------------------------------------------------------
# the registry
# ---------------------------------------------------------------------------
def registry(offline: bool = False) -> dict[str, Any]:
    """The catalogue of packages — fetched if possible, bundled if not."""
    if not offline:
        try:
            with urllib.request.urlopen(REMOTE_REGISTRY, timeout=TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            pass          # no network is normal in a classroom; fall through

    if BUNDLED_REGISTRY.is_file():
        return json.loads(BUNDLED_REGISTRY.read_text(encoding="utf-8"))
    return {"бастаҳо": {}}


def catalogue(offline: bool = False) -> dict[str, dict[str, Any]]:
    return registry(offline).get("бастаҳо", {})


# ---------------------------------------------------------------------------
# installing
# ---------------------------------------------------------------------------
def install(
    name: str, offline: bool = False, project_root: Path | None = None
) -> dict[str, Any]:
    """Download a package and put its `.tj` files where `ворид` will find them."""
    entries = catalogue(offline)
    if name not in entries:
        near = ", ".join(sorted(entries)) or "ҳеҷ"
        raise PackageError(
            f'Бастаи "{name}" дар феҳрист нест.',
            hint=f"Бастаҳои мавҷуда: {near}. Барои дидан: tajik ҷустуҷӯ",
        )

    entry = entries[name]
    url = entry.get("манбаъ")
    if not url:
        raise PackageError(f'Бастаи "{name}" суроғаи боргирӣ надорад.')

    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            payload = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise PackageError(
            f'Бастаи "{name}" боргирӣ нашуд.',
            hint=f"Пайвасти интернетро санҷед. ({error})",
        ) from None

    target = library(project_root) / name
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    inside = entry.get("ҷузвдон", "")      # a package may live inside a monorepo
    count = _extract(payload, target, inside, name)

    if count == 0:
        shutil.rmtree(target)
        raise PackageError(
            f'Дар бастаи "{name}" ягон файли .tj нест.',
            hint="Шояд суроғаи баста нодуруст аст.",
        )
    if not (target / f"{name}.tj").is_file():
        shutil.rmtree(target)
        raise PackageError(
            f'Бастаи "{name}" файли асосии "{name}.tj" -ро надорад.',
            hint="Ҳар баста бояд файле бо номи худаш дошта бошад.",
        )

    metadata = {
        "ном": name,
        "нусха": entry.get("нусха", "?"),
        "тавсиф": entry.get("тавсиф", ""),
        "муаллиф": entry.get("муаллиф", ""),
        "манбаъ": url,
        "файлҳо": count,
    }
    (target / "баста.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metadata


def _extract(payload: bytes, target: Path, inside: str, name: str) -> int:
    """Pull the `.tj` files out of a downloaded zip, flat, and nothing else.

    Only `.tj` files are taken, and every path is checked before it is used:
    a zip that says `../../evil.tj` must not be able to write outside the
    package folder.
    """
    written = 0
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for item in archive.infolist():
            if item.is_dir() or not item.filename.endswith(".tj"):
                continue

            path = item.filename.replace("\\", "/")
            if inside and f"/{inside}/" not in f"/{path}":
                continue

            leaf = Path(path).name
            if not leaf or leaf.startswith(".") or "/" in leaf or ".." in leaf:
                continue

            destination = (target / leaf).resolve()
            if not str(destination).startswith(str(target.resolve())):
                continue          # a path trying to escape the folder

            destination.write_bytes(archive.read(item))
            written += 1
    return written


def remove(name: str, project_root: Path | None = None) -> None:
    target = library(project_root) / name
    if not target.is_dir():
        raise PackageError(
            f'Бастаи "{name}" насб нашудааст.',
            hint="Барои дидани бастаҳо: tajik бастаҳо",
        )
    shutil.rmtree(target)
