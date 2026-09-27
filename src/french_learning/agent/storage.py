"""Хранилище контента: создание и защита публичного репозитория (research R12, R13)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from french_learning.content.schema import FORMAT_VERSION

# Корень репозитория кода: src/french_learning/agent/storage.py → parents[3]
CODE_ROOT = Path(__file__).resolve().parents[3]

SECTIONS = [
    {"id": "grammar", "name": "Грамматика"},
    {"id": "vocabulary", "name": "Лексика"},
    {"id": "pronunciation", "name": "Произношение"},
    {"id": "reading", "name": "Фонетика и чтение"},
    {"id": "communication", "name": "Общение"},
]


class StorageError(Exception):
    """Хранилище нельзя использовать; сообщение показывается пользователю."""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def ensure_writable_storage(root: Path | None) -> Path:
    """Проверить, что в хранилище можно писать, не рискуя публичным репозиторием."""
    if root is None or not root.is_dir():
        raise StorageError(f"хранилище не найдено: {root} (задайте CONTENT_DIR в .env)")
    resolved = root.resolve()
    if resolved.is_relative_to(CODE_ROOT):
        raise StorageError(
            f"хранилище {resolved} находится внутри публичного репозитория кода — "
            "так контент может попасть в публичный доступ (конституция VI)"
        )
    top = _git(resolved, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != resolved:
        raise StorageError(f"хранилище {resolved} должно быть отдельным git-репозиторием")
    return resolved


def init_content(root: Path) -> None:
    """Создать пустое хранилище (допускается пустая папка или свежий клон с одним .git)."""
    if root.exists() and any(p.name != ".git" for p in root.iterdir()):
        raise StorageError(f"папка {root} не пуста")
    if root.resolve().is_relative_to(CODE_ROOT):
        raise StorageError("хранилище нельзя создавать внутри репозитория кода")
    root.mkdir(parents=True, exist_ok=True)
    dump = {"allow_unicode": True, "sort_keys": False}
    (root / "format.yaml").write_text(
        yaml.safe_dump({"format_version": FORMAT_VERSION}, **dump), encoding="utf-8"
    )
    (root / "topics.yaml").write_text(
        yaml.safe_dump({"sections": SECTIONS, "topics": []}, **dump), encoding="utf-8"
    )
    (root / ".gitignore").write_text(".staging/\n", encoding="utf-8")
    if not (root / ".git").exists():
        _git(root, "init", "-q")
    _git(root, "add", "-A")
    commit = _git(root, "commit", "-q", "-m", "Хранилище контента: начальная структура")
    if commit.returncode != 0:
        raise StorageError(f"не удалось создать первый коммит: {commit.stderr.strip()}")
