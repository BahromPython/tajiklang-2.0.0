"""TajikWeb — turn a TajikLang page into a small static website.

This deliberately starts with static pages. A portfolio, school project,
class journal, documentation site, or landing page should be publishable
without teaching a beginner JavaScript, a web server, or deployment tools.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from . import CheckFailed, run_source
from .errors import TajikLangError


PROJECT_FILE = "tajikweb.json"
SOURCE_FILE = "index.tj"
OUTPUT_DIR = "нашр"
STATIC_DIR = "static"


class WebError(Exception):
    """An expected TajikWeb problem, ready for the command line to show."""


@dataclass(frozen=True)
class BuildResult:
    root: Path
    output: Path
    copied_assets: int


def _project_path(value: str | Path | None) -> Path:
    return Path.cwd() if value is None else Path(value)


def _valid_name(name: str) -> bool:
    """Folders may be Tajik, but not contain path separators or hidden paths."""
    return bool(re.fullmatch(r"[^\\/:*?\"<>|.][^\\/:*?\"<>|]*", name))


def create_project(name: str, parent: str | Path | None = None) -> Path:
    """Create one teachable TajikWeb project without overwriting anything."""
    if not _valid_name(name):
        raise WebError(
            "Номи сомона нодуруст аст. Номи кӯтоҳ бе /, \\ ё аломатҳои махсус диҳед."
        )

    root = _project_path(parent) / name
    if root.exists():
        raise WebError(f'Папкаи "{root}" аллакай вуҷуд дорад.')

    root.mkdir(parents=True)
    (root / STATIC_DIR).mkdir()
    (root / PROJECT_FILE).write_text(
        json.dumps({"ном": name, "навъ": "TajikWeb", "нусха": 1}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (root / SOURCE_FILE).write_text(_starter_source(name), encoding="utf-8")
    (root / "README.md").write_text(_starter_readme(name), encoding="utf-8")
    return root


def build_project(folder: str | Path | None = None) -> BuildResult:
    """Build ``index.tj`` in *folder* as a portable static website."""
    root = _project_path(folder).resolve()
    project = root / PROJECT_FILE
    source_path = root / SOURCE_FILE
    if not project.is_file():
        raise WebError(
            f'Дар "{root}" файли {PROJECT_FILE} нест. '
            "Аввал: tajik веб нав номи_сомона"
        )
    if not source_path.is_file():
        raise WebError(f'Файли {SOURCE_FILE} ёфт нашуд.')

    try:
        source = source_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise WebError(f'Файли {SOURCE_FILE} бояд UTF-8 бошад.') from error

    # ``нависед`` keeps page elements in the module. Asking for HTML after
    # the student's source ran is intentionally invisible to their program.
    output: list[str] = []
    rendered_source = source.rstrip() + "\n\nнавис(саҳифа.ҳамчун_матн())\n"
    try:
        run_source(
            rendered_source,
            filename=str(source_path),
            output=output.append,
            base_dir=root,
            check=True,
        )
    except CheckFailed as error:
        raise WebError(error.format()) from error
    except TajikLangError as error:
        raise WebError(error.format()) from error

    if not output or not output[-1].lstrip().lower().startswith("<!doctype html"):
        raise WebError(
            "Сомона сохта нашуд. Дар index.tj «ворид саҳифа» ва "
            "«саҳифа.нависед(...)» истифода баред."
        )

    destination = root / OUTPUT_DIR
    destination.mkdir(exist_ok=True)
    (destination / "index.html").write_text(output[-1], encoding="utf-8")

    copied = 0
    assets = root / STATIC_DIR
    if assets.is_dir():
        for item in assets.rglob("*"):
            if item.is_file():
                target = destination / STATIC_DIR / item.relative_to(assets)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
                copied += 1

    return BuildResult(root, destination, copied)


def prepare_github_pages(folder: str | Path | None = None) -> Path:
    """Add a GitHub Actions workflow that builds and publishes this website."""
    root = _project_path(folder).resolve()
    if not (root / PROJECT_FILE).is_file():
        raise WebError(f'Дар "{root}" файли {PROJECT_FILE} нест.')

    workflow = root / ".github" / "workflows" / "tajikweb-pages.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(GITHUB_PAGES_WORKFLOW, encoding="utf-8")
    return workflow


def _starter_source(name: str) -> str:
    return f'''# Сомонаи аввалини ман бо TajikWeb
ворид саҳифа

саҳифа.нависед(
    саҳифа.қуттӣ(
        саҳифа.сарлавҳа("{name}", {{"ранг": "#0b4f6c", "андоза": 34}}),
        саҳифа.матн("Салом! Ин сомона бо забони тоҷикӣ сохта шудааст."),
        саҳифа.сарлавҳа("Дар бораи ман", 2),
        саҳифа.матн("Матни худро дар index.tj иваз кунед."),
        саҳифа.рӯйхат(["Омӯхтан", "Сохтан", "Нашр кардан"]),
    ),
)
'''


def _starter_readme(name: str) -> str:
    return f'''# {name}

Ин сомона бо **TajikWeb** сохта мешавад.

1. Матнро дар `index.tj` тағйир диҳед.
2. Барои сохтани HTML: `tajik веб соз`
3. Файли тайёр дар `нашр/index.html` аст.
4. Барои GitHub Pages: `tajik веб омода-github`, баъд лоиҳаро ба GitHub push кунед.

Файлҳоеро монанди расм ба папкаи `static/` гузоред ва дар саҳифа ҳамчун
`static/номи-расм.png` истифода баред.
'''


GITHUB_PAGES_WORKFLOW = """# TajikWeb сомонаро баъд аз ҳар push ба GitHub Pages нашр мекунад.
name: Нашри TajikWeb

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Насби TajikLang
        run: pip install git+https://github.com/BahromPython/tajiklang.git
      - name: Сохтани сомона
        run: tajik веб соз .
      - uses: actions/upload-pages-artifact@v3
        with:
          path: нашр

  deploy:
    environment:
      name: github-pages
      url: ${{{{ steps.deployment.outputs.page_url }}}}
    needs: build
    runs-on: ubuntu-latest
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
"""
