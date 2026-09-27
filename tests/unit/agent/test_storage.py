"""Создание хранилища и защита публичного репозитория (research R12, R13)."""

from pathlib import Path

import pytest
import yaml

from french_learning.agent.storage import (
    CODE_ROOT,
    StorageError,
    ensure_writable_storage,
    init_content,
)
from french_learning.content.loader import load_content
from tests.unit.agent.conftest import commits


def test_init_content_creates_valid_empty_storage(tmp_path: Path):
    root = tmp_path / "materials"
    init_content(root)
    assert yaml.safe_load((root / "format.yaml").read_text(encoding="utf-8")) == {
        "format_version": 1
    }
    sections = yaml.safe_load((root / "topics.yaml").read_text(encoding="utf-8"))["sections"]
    assert [s["id"] for s in sections] == [
        "grammar",
        "vocabulary",
        "pronunciation",
        "reading",
        "communication",
    ]
    assert ".staging/" in (root / ".gitignore").read_text(encoding="utf-8")
    assert (root / ".git").is_dir()
    assert len(commits(root)) == 1
    assert load_content(root).errors == []


def test_init_content_keeps_existing_git_clone(tmp_path: Path):
    root = tmp_path / "clone"
    root.mkdir()
    init_content(root)  # пустой склонированный репозиторий: только .git — допустимо
    init_content_again = pytest.raises(StorageError, match="не пуст")
    with init_content_again:
        init_content(root)


def test_init_refuses_non_empty_folder(tmp_path: Path):
    (tmp_path / "x.txt").write_text("x", encoding="utf-8")
    with pytest.raises(StorageError):
        init_content(tmp_path)


def test_writable_storage_ok(store: Path):
    ensure_writable_storage(store)


def test_storage_inside_code_repository_is_refused():
    with pytest.raises(StorageError, match="репозитори"):
        ensure_writable_storage(CODE_ROOT / "tests" / "fixtures" / "content")


def test_storage_without_own_git_is_refused(clean_content_root: Path):
    with pytest.raises(StorageError, match="git"):
        ensure_writable_storage(clean_content_root)


def test_missing_storage_is_refused(tmp_path: Path):
    with pytest.raises(StorageError):
        ensure_writable_storage(tmp_path / "none")
