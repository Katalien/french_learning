"""Проверка, что в публичный репозиторий не попали учебные материалы и контент.

Конституция, принцип VI: материалы преподавателя, распознанный контент и личные данные
никогда не попадают в публичный репозиторий. Скрипт запускается git-хуком и в CI.

Выход: 0 — нарушений нет, 1 — найдены запрещённые файлы (список печатается).
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

FORBIDDEN_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".heic",
    ".pdf",
    ".doc",
    ".docx",
    ".mp3",
    ".m4a",
    ".wav",
    ".mov",
    ".mp4",
    ".sqlite",
    ".sqlite3",
}

# Корневые папки, характерные для хранилища контента (contracts/content-format.md).
CONTENT_ROOTS = {"lessons", "vocabulary", "extra", "reports"}

ALLOWED_PREFIXES = (
    PurePosixPath("tests/fixtures"),
    PurePosixPath("src/french_learning/web/static"),
)

SKIPPED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}


def _is_allowed(relative: PurePosixPath) -> bool:
    return any(relative.is_relative_to(prefix) for prefix in ALLOWED_PREFIXES)


def _is_forbidden(relative: PurePosixPath) -> bool:
    if relative.suffix.lower() in FORBIDDEN_SUFFIXES:
        return True
    return relative.parts[0] in CONTENT_ROOTS if relative.parts else False


def _walk(root: Path) -> Iterable[PurePosixPath]:
    for path in root.rglob("*"):
        if path.is_file() and not SKIPPED_DIRS.intersection(path.relative_to(root).parts):
            yield PurePosixPath(path.relative_to(root).as_posix())


def find_violations(root: Path, tracked: list[str] | None) -> list[PurePosixPath]:
    """Вернуть запрещённые файлы.

    tracked — список путей из git (проверяются только они); None — обойти всю папку.
    """
    candidates = (PurePosixPath(p) for p in tracked) if tracked is not None else _walk(root)
    return sorted(p for p in candidates if not _is_allowed(p) and _is_forbidden(p))


def _git_tracked(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parent.parent
    violations = find_violations(root, tracked=_git_tracked(root))
    if not violations:
        print("Материалов и контента в репозитории нет.")
        return 0
    print("В публичный репозиторий не должны попадать эти файлы (конституция, принцип VI):")
    for path in violations:
        print(f"  {path}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
