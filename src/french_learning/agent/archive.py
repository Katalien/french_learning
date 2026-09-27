"""Опись урока (`lessons/NNN/inventory.md`) и общий указатель (`index.md`) — FR-038, FR-039.

Генерируются из журнала файлов и элементов; руками не правятся. Вывод детерминирован:
повторная сборка без изменений данных даёт те же файлы.
"""

from __future__ import annotations

from pathlib import Path

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content

PART_TITLES = {"class": "В классе", "homework": "Домашка"}
CLASSIFICATION_NAMES = {
    "theory": "теория",
    "vocabulary": "лексика",
    "text": "текст",
    "exercises": "лист упражнений",
    "exercises_with_reference": "лист упражнений со справкой",
    "media": "медиафайл",
    "duplicate": "дубль",
    "unrecognized": "не распознан",
    "skipped": "пропущен",
}
MONTHS = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]  # fmt: skip


def _date(value) -> str:
    return f"{value.day} {MONTHS[value.month - 1]} {value.year}" if value else "дата не указана"


def _describe(index: ContentIndex, element_id: str) -> str:
    element = index.element(element_id)
    if element is None:
        return f"`{element_id}` (не найден)"
    if element.kind == "exercise":
        topic = index.topic(element.topics[0]) if element.topics else None
        name = topic.name if topic else "Без темы"
        return f"{element.number} — {name} — {element.description_ru} (`{element.id}`)"
    if element.kind == "vocab":
        return f"{element.text} (`{element.id}`)"
    return f"{element.title} (`{element.id}`)"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _inventory(index: ContentIndex, number: int) -> str:
    lesson = index.lesson(number)
    topics = ", ".join(t.name for t in index.lesson_topics(number)) or "—"
    lines = [
        f"# Урок {number}",
        "",
        f"Дата: {_date(lesson.date)} · Папка: {lesson.source_folder} · Темы: {topics}",
        "",
        "_Файл создан автоматически командой `build-archive` — не правьте его вручную._",
        "",
    ]
    processed = [
        f
        for f in lesson.files
        if f.classification not in {"media", "duplicate", "unrecognized", "skipped"}
    ]
    for part in ("class", "homework"):
        entries = [f for f in processed if f.part == part]
        lines += [f"## {PART_TITLES[part]}", ""]
        if not entries:
            lines += ["Нет файлов.", ""]
            continue
        lines += ["| Файл | Классификация | Элементы | Копия |", "|---|---|---|---|"]
        for entry in entries:
            elements = "<br>".join(_cell(_describe(index, i)) for i in entry.elements) or "—"
            lines.append(
                f"| {_cell(entry.path)} | {CLASSIFICATION_NAMES[entry.classification]} "
                f"| {elements} | {_cell(entry.stored_as or '—')} |"
            )
        lines.append("")
    if lesson.media or any(f.classification == "media" for f in lesson.files):
        lines += ["## Аудио и видео", ""]
        media_paths = {m.path for m in lesson.media}
        media_paths |= {f.path for f in lesson.files if f.classification == "media"}
        lines += [f"- {path}" for path in sorted(media_paths)]
        lines.append("")
    skipped = [
        f for f in lesson.files if f.classification in {"duplicate", "unrecognized", "skipped"}
    ]
    if skipped:
        lines += ["## Пропущено", ""]
        for entry in skipped:
            label = CLASSIFICATION_NAMES[entry.classification]
            lines.append(f"- {entry.path} — {label}: {entry.note}")
        lines.append("")
    return "\n".join(lines)


def _index(index: ContentIndex) -> str:
    lines = [
        "# Указатель уроков и тем",
        "",
        "_Файл создан автоматически командой `build-archive` — не правьте его вручную._",
        "",
        "## Уроки",
        "",
    ]
    for lesson in sorted(index.lessons(), key=lambda item: item.number):
        exercises = len(index.elements(lesson.number, kind="exercise"))
        new_words, repeat = index.lesson_vocabulary(lesson.number)
        topics = ", ".join(t.name for t in index.lesson_topics(lesson.number)) or "—"
        lines.append(
            f"- Урок {lesson.number} ({_date(lesson.date)}): {topics}. "
            f"Упражнений: {exercises}, слов: {len(new_words) + len(repeat)}"
        )
    lines += ["", "## Темы", ""]
    for group in index.topics_by_section():
        if not group.topics:
            continue
        lines += [f"### {group.section.name}", ""]
        for item in group.topics:
            lessons = sorted(
                {
                    e.lesson
                    for e in index.topic_elements(item.topic.id)
                    if getattr(e, "lesson", None) is not None
                }
                | {
                    n
                    for e in index.topic_elements(item.topic.id)
                    if e.kind == "vocab"
                    for n in e.lessons
                }
            )
            where = f"уроки {', '.join(map(str, lessons))}" if lessons else "только доп. материалы"
            lines.append(f"- {item.topic.name}: {where}")
        lines.append("")
    return "\n".join(lines)


def _write_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def build_archive(root: Path) -> list[str]:
    """Перестроить опись всех уроков и указатель; вернуть изменённые пути."""
    index = ContentIndex(load_content(root))
    changed: list[str] = []
    for lesson in index.lessons():
        relative = f"lessons/{lesson.number:03d}/inventory.md"
        if _write_if_changed(root / relative, _inventory(index, lesson.number)):
            changed.append(relative)
    if _write_if_changed(root / "index.md", _index(index)):
        changed.append("index.md")
    return changed
