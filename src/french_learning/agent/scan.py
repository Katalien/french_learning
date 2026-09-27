"""Опись папки урока: файлы, части, типы, хеши, даты, дубли, состояние по журналу.

US1: FR-002, FR-005; US4: FR-040, FR-040a; research R7, R8.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from french_learning.content.loader import load_content

HOMEWORK_DIR = "Devoirs"
IGNORED_NAMES = {"thumbs.db", "desktop.ini", ".ds_store"}
KINDS = {
    "image": {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"},
    "pdf": {".pdf"},
    "docx": {".docx"},
    "audio": {".mp3", ".m4a", ".wav", ".ogg", ".aac"},
    "video": {".mov", ".mp4", ".avi", ".mkv", ".webm"},
}
_NUMBER = re.compile(r"(\d+)\s*$")


class ScanError(Exception):
    """Папку нельзя описать; сообщение показывается пользователю."""


@dataclass
class FileInfo:
    path: str
    part: str
    kind: str
    size: int
    sha256: str
    date: str
    duplicate_of: str | None = None
    state: str = "new"


@dataclass
class ScanResult:
    lesson: int
    folder: str
    suggested_date: str | None
    files: list[FileInfo] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    existing: bool = False
    conflict: dict | None = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _kind(path: Path) -> str:
    suffix = path.suffix.lower()
    return next((kind for kind, suffixes in KINDS.items() if suffix in suffixes), "other")


def _date(path: Path, kind: str) -> str:
    if kind == "image":
        try:
            with Image.open(path) as img:
                exif = img.getexif()
                raw = exif.get_ifd(0x8769).get(0x9003) or exif.get(0x0132)
            if raw:
                return (
                    dt.datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S").date().isoformat()
                )
        except (OSError, ValueError):
            pass
    return dt.date.fromtimestamp(path.stat().st_mtime).isoformat()


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def scan_lesson(folder: Path, materials_root: Path, content_root: Path | None) -> ScanResult:
    if not folder.is_dir():
        raise ScanError(f"папка не найдена: {folder}")
    match = _NUMBER.search(folder.name)
    if not match:
        raise ScanError(f"не удалось определить номер урока по имени папки «{folder.name}»")
    number = int(match.group(1))
    paths = sorted(
        p for p in folder.rglob("*") if p.is_file() and p.name.lower() not in IGNORED_NAMES
    )
    if not paths:
        raise ScanError(f"папка урока пуста: {folder}")

    files = []
    for path in paths:
        inside = path.relative_to(folder).parts
        part = (
            "homework" if inside[0].lower() == HOMEWORK_DIR.lower() and len(inside) > 1 else "class"
        )
        kind = _kind(path)
        files.append(
            FileInfo(
                path=_relative(path, materials_root),
                part=part,
                kind=kind,
                size=path.stat().st_size,
                sha256=sha256_file(path),
                date=_date(path, kind),
            )
        )

    # Дубли: основным считается файл домашки (research R8)
    groups: dict[str, list[FileInfo]] = {}
    for info in files:
        groups.setdefault(info.sha256, []).append(info)
    for group in groups.values():
        group.sort(key=lambda f: (f.part != "homework", f.path))
        for duplicate in group[1:]:
            duplicate.duplicate_of = group[0].path

    class_dates = [f.date for f in files if f.part == "class"] or [f.date for f in files]
    result = ScanResult(
        lesson=number,
        folder=_relative(folder, materials_root),
        suggested_date=min(class_dates) if class_dates else None,
        files=files,
    )
    if content_root is not None:
        _compare_with_journal(result, folder.name, content_root)
    return result


def _compare_with_journal(result: ScanResult, folder_name: str, content_root: Path) -> None:
    lesson = load_content(content_root).lessons.get(result.lesson)
    if lesson is None:
        return
    result.existing = True
    if lesson.source_folder != folder_name:
        result.conflict = {"existing_source_folder": lesson.source_folder}
    journal = {entry.path: entry.sha256 for entry in lesson.files}
    on_disk = {f.path for f in result.files}
    for info in result.files:
        if info.path in journal:
            info.state = "processed" if journal[info.path] == info.sha256 else "changed"
    result.missing = sorted(set(journal) - on_disk)
