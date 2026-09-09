"""Лоиҳа ва муҳит — TajikLang's project-local programming environment.

Python needs a separate ``venv`` because a project shares Python's global
package world. TajikLang projects carry a deliberately visible `.tajiklang/`
folder instead: its configuration and its project-only libraries live beside
the student's program and work the same in the standalone application.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ENV_DIR = ".tajiklang"
CONFIG = "лоиҳа.json"
LIBRARY = "китобхона"
MAIN_FILE = "барнома.tj"

# A TajikLang project begins with a useful, runnable artefact.  Templates are
# deliberately files rather than hidden generator logic, so students can read
# every line the moment the project is created.
PROJECT_KINDS = {
    "console": "Консолӣ",
    "web": "Сомонаи интерактивӣ",
    "game": "Бозии хурд",
    "blocks": "TajikBlocks",
    "data": "Маълумот ва ҷадвалҳо",
}

TEMPLATES = {
    "console": (
        "# Барномаи аввалини ман\n"
        'дода ном <- "Баҳром"\n'
        'нишон "Салом", ном\n'
    ),
    "web": (
        "# Барои оғоз: tajik веб барнома барнома.tj\n"
        "ворид саҳифа\n\n"
        "саҳифа.нависед(\n"
        '    саҳифа.сарлавҳа("Салом аз TajikLang"),\n'
        '    саҳифа.матн("Ин сомона бо TajikLang сохта шуд."),\n'
        ")\n"
    ),
    "game": (
        "# Бозии аввалини ман\n"
        "дода хол <- 0\n"
        'нишон "Бозӣ оғоз шуд. Хол:", хол\n'
        "# Барои асбобҳои бозӣ: tajik гирифтан бозӣ\n"
    ),
    "blocks": (
        "# Ин файлро дар TajikBlocks ё Studio кушоед.\n"
        'дода қаҳрамон <- "Ситора"\n'
        'нишон "Салом аз", қаҳрамон\n'
    ),
    "data": (
        "# Кор бо маълумот\n"
        "дода холҳо <- [18, 20, 17]\n"
        'нишон "Шумора:", дарозӣ(холҳо)\n'
        "# Барои ҷадвалҳо: tajik гирифтан ҷадвал\n"
    ),
}


class EnvironmentError(Exception):
    """A problem the command line can explain in Tajik."""


def find(root: str | Path) -> Path | None:
    """Find the nearest TajikLang environment, walking towards the drive root."""
    current = Path(root).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ENV_DIR / CONFIG).is_file():
            return candidate
    return None


def library(root: str | Path) -> Path | None:
    project = find(root)
    return project / ENV_DIR / LIBRARY if project is not None else None


def create_environment(root: str | Path) -> Path:
    """Give an existing folder its own, visible package environment."""
    project = Path(root).resolve()
    if not project.is_dir():
        raise EnvironmentError(f'Папкаи "{project}" ёфт нашуд.')
    folder = project / ENV_DIR
    config = folder / CONFIG
    if config.exists():
        raise EnvironmentError("Ин папка аллакай муҳити TajikLang дорад.")

    (folder / LIBRARY).mkdir(parents=True)
    config.write_text(
        json.dumps(
            {"навъ": "муҳити TajikLang", "нусха": 1, "китобхона": LIBRARY},
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return folder


def create_project(
    name: str, parent: str | Path | None = None, kind: str = "console"
) -> Path:
    """Create a named project and its visible, project-local environment."""
    if not re.fullmatch(r"[^\\/:*?\"<>|.][^\\/:*?\"<>|]*", name):
        raise EnvironmentError("Номи лоиҳа нодуруст аст.")
    base = Path.cwd() if parent is None else Path(parent)
    project = base / name
    if project.exists():
        raise EnvironmentError(f'Папкаи "{project}" аллакай вуҷуд дорад.')
    if kind not in PROJECT_KINDS:
        choices = ", ".join(PROJECT_KINDS)
        raise EnvironmentError(f'Навъи лоиҳаи "{kind}" шинохта нашуд. Интихобҳо: {choices}.')

    project.mkdir(parents=True)
    create_environment(project)
    (project / MAIN_FILE).write_text(TEMPLATES[kind], encoding="utf-8")
    (project / "README.md").write_text(
        f"# {name}\n\n"
        f"Ин лоиҳаи TajikLang аст: **{PROJECT_KINDS[kind]}**.\n\n"
        "- Барномаи асосӣ: `барнома.tj`\n"
        "- Бастаҳои ҳамин лоиҳа: `.tajiklang/китобхона/`\n"
        "- Насби бастаи маҳаллӣ: `tajik гирифтан --лоиҳа омор`\n"
        "- Пешнамоиш дар Studio: тугмаи ▶ Иҷро\n",
        encoding="utf-8",
    )
    return project
