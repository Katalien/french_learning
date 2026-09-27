"""Фикстуры команд агента: хранилище-образец под git и синтетические исходные материалы."""

import shutil
import subprocess
from pathlib import Path

import pytest

MATERIALS = Path(__file__).parents[2] / "fixtures" / "materials"


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout


@pytest.fixture
def store(clean_content_root: Path) -> Path:
    """Хранилище-образец (без повреждённого файла) под git, с .gitignore для черновика."""
    (clean_content_root / ".gitignore").write_text(".staging/\n", encoding="utf-8")
    git(clean_content_root, "init", "-q")
    git(clean_content_root, "add", "-A")
    git(clean_content_root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    return clean_content_root


@pytest.fixture
def materials(tmp_path: Path) -> Path:
    """Копия синтетических исходных материалов (папка с уроками)."""
    target = tmp_path / "materials"
    shutil.copytree(MATERIALS, target)
    return target


def commits(root: Path) -> list[str]:
    return git(root, "log", "--format=%s").splitlines()
