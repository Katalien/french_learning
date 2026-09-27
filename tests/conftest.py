"""Общие фикстуры: копии синтетического контент-образца во временной папке."""

import shutil
from pathlib import Path

import pytest

FIXTURE_CONTENT = Path(__file__).parent / "fixtures" / "content"
BROKEN_FILE = Path("lessons/002/exercises/ex-brokenaa.yaml")


@pytest.fixture
def content_root(tmp_path: Path) -> Path:
    """Полная копия образца, включая намеренно повреждённый файл."""
    target = tmp_path / "content"
    shutil.copytree(FIXTURE_CONTENT, target)
    return target


@pytest.fixture
def clean_content_root(content_root: Path) -> Path:
    """Копия образца без повреждённого файла."""
    (content_root / BROKEN_FILE).unlink()
    return content_root
