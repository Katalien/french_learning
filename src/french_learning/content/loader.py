"""Загрузка контента из хранилища: чтение файлов, проверка по схеме, изоляция ошибок.

Правила — contracts/content-format.md, раздел «Правила проверки». Ошибка в одном файле
не мешает загрузке остальных (FR-005): файл попадает в `Content.errors`, а его элемент
не добавляется в `Content.elements`.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from pydantic import TypeAdapter, ValidationError

from french_learning.content import schema

_EXERCISE = TypeAdapter(schema.Exercise)


@dataclass
class LoadError:
    path: str
    message: str
    element_id: str | None = None
    # Предупреждение: элемент загружен и показывается, но файл надо поправить
    # (например, нет исходника для «открыть оригинал» — spec, Edge Cases).
    warning: bool = False


@dataclass
class Content:
    root: Path
    format_version: int | None = None
    topics: schema.TopicsFile | None = None
    lessons: dict[int, schema.Lesson] = field(default_factory=dict)
    lesson_paths: dict[int, str] = field(default_factory=dict)
    elements: dict[str, Any] = field(default_factory=dict)
    element_paths: dict[str, str] = field(default_factory=dict)
    reports: dict[str, schema.Report] = field(default_factory=dict)
    report_paths: dict[str, str] = field(default_factory=dict)
    errors: list[LoadError] = field(default_factory=list)

    def error_for(self, element_id: str) -> LoadError | None:
        return next((e for e in self.errors if e.element_id == element_id), None)


class _FileError(Exception):
    pass


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _read_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise _FileError(f"не удалось прочитать YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise _FileError("ожидался YAML-словарь")
    return data


def _read_markdown(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise _FileError(f"не удалось прочитать файл: {exc}") from exc
    text = text.lstrip("﻿")
    if not text.startswith("---"):
        raise _FileError("нет шапки YAML (файл должен начинаться с ---)")
    parts = text.split("\n---", 1)
    if len(parts) != 2:
        raise _FileError("шапка YAML не закрыта строкой ---")
    try:
        meta = yaml.safe_load(parts[0][3:])
    except yaml.YAMLError as exc:
        raise _FileError(f"ошибка в шапке YAML: {exc}") from exc
    if not isinstance(meta, dict):
        raise _FileError("шапка YAML должна быть словарём")
    meta["body"] = parts[1].lstrip("\r\n")
    return meta


def _describe(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        location = ".".join(str(p) for p in err["loc"] if not str(p).startswith("function-"))
        message = err["msg"].removeprefix("Value error, ")
        parts.append(f"{location}: {message}" if location else message)
    return "; ".join(parts)


def _validate(model: Any, data: dict) -> Any:
    try:
        if isinstance(model, TypeAdapter):
            return model.validate_python(data)
        return model.model_validate(data)
    except ValidationError as exc:
        raise _FileError(_describe(exc)) from exc


_ELEMENT_DIRS = {
    "theory": ("*.md", _read_markdown, schema.Theory),
    "texts": ("*.md", _read_markdown, schema.Text),
    "exercises": ("*.yaml", _read_yaml, _EXERCISE),
}


def _element_files(root: Path) -> list[tuple[Path, int | None]]:
    """Файлы элементов уроков и дополнительных материалов с ожидаемым номером урока."""
    found: list[tuple[Path, int | None]] = []
    lessons_dir = root / "lessons"
    if lessons_dir.is_dir():
        for folder in sorted(p for p in lessons_dir.iterdir() if p.is_dir()):
            number = int(folder.name) if folder.name.isdigit() else None
            for sub, (pattern, *_rest) in _ELEMENT_DIRS.items():
                found += [(p, number) for p in sorted((folder / sub).glob(pattern))]
    for sub, (pattern, *_rest) in _ELEMENT_DIRS.items():
        found += [(p, None) for p in sorted((root / "extra" / sub).glob(pattern))]
    return found


def load_content(root: Path) -> Content:
    content = Content(root=root)
    fmt_path = root / "format.yaml"
    try:
        fmt = _validate(schema.FormatFile, _read_yaml(fmt_path))
    except (_FileError, FileNotFoundError) as exc:
        content.errors.append(LoadError("format.yaml", f"format.yaml: {exc}"))
        return content
    if fmt.format_version != schema.FORMAT_VERSION:
        content.errors.append(
            LoadError(
                "format.yaml",
                f"версия формата {fmt.format_version} не поддерживается "
                f"(ожидается {schema.FORMAT_VERSION})",
            )
        )
        return content
    content.format_version = fmt.format_version

    _load_topics(content)
    _load_lessons(content)
    candidates = _load_elements(content)
    _check_elements(content, candidates)
    _check_journals(content)
    _load_reports(content)
    return content


def _check_journals(content: Content) -> None:
    """Журнал файлов урока ссылается только на существующие элементы (предупреждение)."""
    for number, lesson in content.lessons.items():
        missing = sorted(
            {i for entry in lesson.files for i in entry.elements} - set(content.elements)
        )
        if missing:
            content.errors.append(
                LoadError(
                    content.lesson_paths[number],
                    f"журнал файлов ссылается на несуществующие элементы: {', '.join(missing)}",
                    warning=True,
                )
            )


def _load_topics(content: Content) -> None:
    path = content.root / "topics.yaml"
    if not path.exists():
        content.topics = schema.TopicsFile(sections=[], topics=[])
        return
    try:
        content.topics = _validate(schema.TopicsFile, _read_yaml(path))
    except _FileError as exc:
        content.errors.append(LoadError("topics.yaml", str(exc)))
        content.topics = schema.TopicsFile(sections=[], topics=[])


def _load_lessons(content: Content) -> None:
    for path in sorted((content.root / "lessons").glob("*/lesson.yaml")):
        rel = _rel(content.root, path)
        try:
            lesson = _validate(schema.Lesson, _read_yaml(path))
            if path.parent.name != f"{lesson.number:03d}":
                raise _FileError(
                    f"папка урока {path.parent.name} не совпадает с номером {lesson.number}"
                )
            if lesson.number in content.lessons:
                raise _FileError(f"номер урока {lesson.number} повторяется")
        except _FileError as exc:
            content.errors.append(LoadError(rel, str(exc)))
            continue
        content.lessons[lesson.number] = lesson
        content.lesson_paths[lesson.number] = rel


def _load_elements(content: Content) -> dict[str, tuple[Any, str]]:
    candidates: dict[str, tuple[Any, str]] = {}
    duplicates: Counter[str] = Counter()
    parsed: list[tuple[Any, str]] = []

    for path, folder_number in _element_files(content.root):
        rel = _rel(content.root, path)
        _pattern, reader, model = _ELEMENT_DIRS[path.parent.name]
        raw_id = None
        try:
            data = reader(path)
            raw_id = data.get("id") if isinstance(data.get("id"), str) else None
            element = _validate(model, data)
            if element.lesson != folder_number:
                where = f"урока {folder_number}" if folder_number else "extra/"
                raise _FileError(f"lesson: {element.lesson}, а файл лежит в папке {where}")
        except _FileError as exc:
            content.errors.append(LoadError(rel, str(exc), raw_id))
            continue
        parsed.append((element, rel))
        duplicates[element.id] += 1

    for path in sorted((content.root / "vocabulary").glob("*.yaml")):
        rel = _rel(content.root, path)
        raw_id = None
        try:
            data = _read_yaml(path)
            raw_id = data.get("id") if isinstance(data.get("id"), str) else None
            element = _validate(schema.VocabEntry, data)
        except _FileError as exc:
            content.errors.append(LoadError(rel, str(exc), raw_id))
            continue
        parsed.append((element, rel))
        duplicates[element.id] += 1

    for element, rel in parsed:
        if duplicates[element.id] > 1:
            content.errors.append(
                LoadError(rel, f"идентификатор {element.id} повторяется в нескольких файлах")
            )
        else:
            candidates[element.id] = (element, rel)
    return candidates


def _check_elements(content: Content, candidates: dict[str, tuple[Any, str]]) -> None:
    topic_ids = {t.id for t in content.topics.topics} if content.topics else set()
    numbers: Counter[tuple[int | None, str | None, int]] = Counter(
        (el.lesson, el.part, el.number) for el, _ in candidates.values() if el.kind == "exercise"
    )

    for element_id, (element, rel) in candidates.items():
        problems: list[str] = []
        missing_topics = [t for t in element.topics if t not in topic_ids]
        if missing_topics:
            problems.append(f"неизвестные темы: {', '.join(missing_topics)}")
        if element.lesson is not None and element.lesson not in content.lessons:
            problems.append(f"урок {element.lesson} не найден")
        missing_sources = [
            s.file for s in element.sources if s.file and not _inside(content.root, s.file)
        ]
        if element.kind == "exercise":
            problems += _check_links(element, candidates)
            if numbers[(element.lesson, element.part, element.number)] > 1:
                problems.append(
                    f"номер упражнения {element.number} повторяется во вкладке {element.part}"
                )
        if problems:
            content.errors.append(LoadError(rel, "; ".join(problems), element_id))
            continue
        content.elements[element_id] = element
        content.element_paths[element_id] = rel
        if missing_sources:
            message = f"исходный файл не найден: {', '.join(missing_sources)}"
            content.errors.append(LoadError(rel, message, element_id, warning=True))


def _check_links(exercise: Any, candidates: dict[str, tuple[Any, str]]) -> list[str]:
    problems = []
    for kind, target in (("text", exercise.links.text), ("theory", exercise.links.theory)):
        if target and (target not in candidates or candidates[target][0].kind != kind):
            problems.append(f"ссылка links.{kind} на несуществующий элемент {target}")
    return problems


def _inside(root: Path, relative: str) -> bool:
    candidate = (root / PurePosixPath(relative)).resolve()
    return candidate.is_relative_to(root.resolve()) and candidate.is_file()


def _load_reports(content: Content) -> None:
    for path in sorted((content.root / "reports").glob("*.yaml")):
        rel = _rel(content.root, path)
        try:
            report = _validate(schema.Report, _read_yaml(path))
            if report.element not in content.elements:
                raise _FileError(f"сообщение ссылается на несуществующий элемент {report.element}")
        except _FileError as exc:
            content.errors.append(LoadError(rel, str(exc)))
            continue
        content.reports[report.id] = report
        content.report_paths[report.id] = rel
