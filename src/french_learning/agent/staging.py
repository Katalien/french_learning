"""Черновик и целостное сохранение урока (FR-032, FR-034, FR-035; research R3).

Агент складывает файлы в `CONTENT_DIR/.staging/<op>/` (структура как у хранилища), удаления —
в `_delete.txt`. `commit_staging` проверяет «хранилище + черновик» схемой 001, применяет всё
целиком (с откатом при сбое), пересобирает опись и указатель, делает коммит и отправку.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from french_learning.agent.archive import build_archive
from french_learning.content.loader import LoadError, load_content
from french_learning.content.writer import ContentWriter

TEXT_SUFFIXES = {".yaml", ".md"}
DELETE_LIST = "_delete.txt"


class StagingError(Exception):
    """Черновик нельзя применить; хранилище при этом не изменено."""


@dataclass
class CheckResult:
    ok: bool
    errors: list[LoadError] = field(default_factory=list)


@dataclass
class CommitResult:
    applied: bool
    committed: bool = False
    pushed: bool = False
    warning: str | None = None
    errors: list[LoadError] = field(default_factory=list)
    files: list[str] = field(default_factory=list)


def op_dir(root: Path, op: str) -> Path:
    return root / ".staging" / op


def _staged_files(root: Path, op: str) -> list[str]:
    base = op_dir(root, op)
    if not base.is_dir():
        return []
    return sorted(
        p.relative_to(base).as_posix()
        for p in base.rglob("*")
        if p.is_file() and p.name != DELETE_LIST
    )


def _deletions(root: Path, op: str) -> list[str]:
    path = op_dir(root, op) / DELETE_LIST
    if not path.exists():
        return []
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        relative = line.strip().replace("\\", "/")
        if not relative:
            continue
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or pure.parts[0] in {".git", ".staging"}:
            raise StagingError(f"недопустимый путь для удаления: {relative}")
        result.append(pure.as_posix())
    return result


def _overlay(root: Path, op: str, target: Path) -> None:
    """Копия хранилища для проверки: тексты целиком, остальные файлы — пустыми заглушками."""
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] in {".git", ".staging"}:
            continue
        destination = target / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif path.suffix in TEXT_SUFFIXES:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.touch()
    for relative in _deletions(root, op):
        (target / relative).unlink(missing_ok=True)
    base = op_dir(root, op)
    for relative in _staged_files(root, op):
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(base / relative, destination)


def _key(error: LoadError) -> tuple[str, str]:
    return error.path, error.message


def stage_check(root: Path, op: str) -> CheckResult:
    """Проверить черновик вместе с хранилищем; нарушения — только новые, не бывшие до него."""
    before = {_key(e) for e in load_content(root).errors}
    with tempfile.TemporaryDirectory(prefix="fl-check-") as tmp:
        _overlay(root, op, Path(tmp))
        after = load_content(Path(tmp)).errors
    new = [e for e in after if _key(e) not in before and not e.warning]
    return CheckResult(ok=not new, errors=new)


def _apply(root: Path, op: str) -> list[str]:
    """Перенести черновик в хранилище; при сбое вернуть всё как было."""
    base = op_dir(root, op)
    backup_dir = Path(tempfile.mkdtemp(prefix="fl-backup-"))
    backups: list[tuple[Path, Path]] = []  # (цель, резервная копия)
    created: list[Path] = []
    touched: list[str] = []
    try:
        for relative in _deletions(root, op):
            target = root / relative
            if target.exists():
                copy = backup_dir / f"del-{len(backups)}"
                shutil.copy2(target, copy)
                backups.append((target, copy))
                target.unlink()
            touched.append(relative)
        for relative in _staged_files(root, op):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                copy = backup_dir / f"rep-{len(backups)}"
                shutil.copy2(target, copy)
                backups.append((target, copy))
            else:
                created.append(target)
            temp = target.with_name(target.name + ".tmp")
            shutil.copyfile(base / relative, temp)
            try:
                os.replace(temp, target)
            finally:
                temp.unlink(missing_ok=True)
            touched.append(relative)
    except OSError as exc:
        for path in created:
            path.unlink(missing_ok=True)
        for target, copy in reversed(backups):
            shutil.copy2(copy, target)
        raise StagingError(f"не удалось применить черновик, изменения отменены: {exc}") from exc
    finally:
        shutil.rmtree(backup_dir, ignore_errors=True)
    return touched


def commit_staging(root: Path, op: str, message: str) -> CommitResult:
    check = stage_check(root, op)
    if not check.ok:
        return CommitResult(applied=False, errors=check.errors)
    touched = _apply(root, op)
    archive_files = build_archive(root)
    paths = sorted(set(touched) | set(archive_files))
    result = ContentWriter(root).commit_paths(paths, message)
    shutil.rmtree(op_dir(root, op), ignore_errors=True)
    return CommitResult(
        applied=True,
        committed=result.committed,
        pushed=result.pushed,
        warning=result.warning,
        files=paths,
    )
