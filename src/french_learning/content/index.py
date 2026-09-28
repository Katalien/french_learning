"""Индекс контента в памяти и хранилище с автоматическим обновлением (research R7)."""

from __future__ import annotations

import hashlib
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from french_learning.content import schema
from french_learning.content.loader import Content, LoadError, load_content

_KIND_ORDER = {"theory": 0, "text": 1, "exercise": 2, "vocab": 3}


@dataclass
class ReviewItem:
    element: Any
    item_id: int | None
    note: str


@dataclass
class LessonSummary:
    lesson: schema.Lesson
    topics: list[schema.Topic]
    new_words: int
    homework_done: int
    homework_total: int
    homework_optional: int
    needs_review: int
    errors: int

    @property
    def number(self) -> int:
        return self.lesson.number

    @property
    def date(self):
        return self.lesson.date


@dataclass
class TopicCount:
    topic: schema.Topic
    count: int


@dataclass
class SectionTopics:
    section: schema.Section
    topics: list[TopicCount]


class ContentIndex:
    def __init__(self, content: Content) -> None:
        self.content = content
        self._topics = {t.id: t for t in content.topics.topics} if content.topics else {}
        self._by_topic: dict[str, list[Any]] = {}
        for element in content.elements.values():
            for topic_id in element.topics:
                self._by_topic.setdefault(topic_id, []).append(element)

    # --- базовый доступ ----------------------------------------------------------------------

    @property
    def errors(self) -> list[LoadError]:
        return self.content.errors

    def element(self, element_id: str) -> Any | None:
        return self.content.elements.get(element_id)

    def element_path(self, element_id: str) -> str | None:
        return self.content.element_paths.get(element_id)

    def topic(self, topic_id: str) -> schema.Topic | None:
        return self._topics.get(topic_id)

    # --- тренажёры (004) ---------------------------------------------------------------------

    @property
    def trainer_entries(self) -> list[schema.TrainerEntry]:
        return self.content.trainers

    def batches(self, trainer_id: str | None = None) -> list[schema.TaskBatch]:
        found = [b for b in self.content.batches.values() if trainer_id in (None, b.trainer)]
        return sorted(found, key=lambda b: (b.created, b.id))

    def batch(self, batch_id: str) -> schema.TaskBatch | None:
        return self.content.batches.get(batch_id)

    def all_topics(self) -> list[schema.Topic]:
        return sorted(self._topics.values(), key=lambda t: t.name.casefold())

    def lessons(self) -> list[schema.Lesson]:
        return [self.content.lessons[n] for n in sorted(self.content.lessons, reverse=True)]

    def lesson(self, number: int) -> schema.Lesson | None:
        return self.content.lessons.get(number)

    # --- элементы урока ----------------------------------------------------------------------

    def elements(
        self, lesson: int | None, part: str | None = None, kind: str | None = None
    ) -> list[Any]:
        found = [
            e
            for e in self.content.elements.values()
            if e.kind != "vocab"
            and e.lesson == lesson
            and (part is None or e.part == part)
            and (kind is None or e.kind == kind)
        ]
        return sorted(found, key=_sort_key)

    # --- переходы и дерево урока (009) -------------------------------------------------------

    def neighbours(self, exercise: Any) -> tuple[Any | None, Any | None]:
        """Предыдущее и следующее упражнение: та же вкладка урока (без резерва; резервное —
        среди резервных), для «Доп. материалов» — среди упражнений раздела."""
        if exercise.lesson is None:
            siblings = [e for e in self.extras() if e.kind == "exercise"]
        else:
            reserve = exercise.status == "reserve"
            siblings = [
                e
                for e in self.elements(exercise.lesson, part=exercise.part, kind="exercise")
                if (e.status == "reserve") == reserve
            ]
        ids = [e.id for e in siblings]
        if exercise.id not in ids:
            return None, None
        at = ids.index(exercise.id)
        before = siblings[at - 1] if at > 0 else None
        after = siblings[at + 1] if at + 1 < len(siblings) else None
        return before, after

    def lesson_tree(self, number: int, progress: Any) -> dict[str, Any]:
        """Содержание урока для меню «☰ Урок»: элементы разделов и выполненные задания."""
        new_words, repeat_words = self.lesson_vocabulary(number)
        exercises = self.elements(number, kind="exercise")

        def part(name: str) -> list[tuple[Any, bool]]:
            return [
                (e, progress.is_done(e.id))
                for e in exercises
                if e.part == name and e.status != "reserve"
            ]

        return {
            "theory": self.elements(number, kind="theory"),
            "texts": self.elements(number, kind="text"),
            "vocab": len(new_words) + len(repeat_words),
            "class": part("class"),
            "homework": part("homework"),
            "reserve": [e for e in exercises if e.status == "reserve"],
        }

    def lesson_errors(self, lesson: int) -> list[LoadError]:
        prefix = f"lessons/{lesson:03d}/"
        return [e for e in self.content.errors if e.path.startswith(prefix) and not e.warning]

    def lesson_topics(self, lesson: int) -> list[schema.Topic]:
        ids = {t for e in self.elements(lesson) for t in e.topics}
        topics = [self._topics[t] for t in ids if t in self._topics]
        return sorted(topics, key=lambda t: t.name.casefold())

    def lesson_vocabulary(self, lesson: int) -> tuple[list[Any], list[Any]]:
        """Лексика урока: (новые, на повторение) по правилу FR-039."""
        entries = sorted(
            (
                e
                for e in self.content.elements.values()
                if e.kind == "vocab" and lesson in e.lessons
            ),
            key=lambda e: e.text.casefold(),
        )
        new = [e for e in entries if min(e.lessons) == lesson]
        repeat = [e for e in entries if min(e.lessons) != lesson]
        return new, repeat

    def lesson_summary(self, number: int, progress: Any) -> LessonSummary:
        """Сводка урока (FR-031): домашка «X из Y» — только основные упражнения."""
        lesson = self.content.lessons[number]
        homework = self.elements(number, part="homework", kind="exercise")
        main = [e for e in homework if e.status == "main"]
        new_words, _repeat = self.lesson_vocabulary(number)
        return LessonSummary(
            lesson=lesson,
            topics=self.lesson_topics(number),
            new_words=len(new_words),
            homework_done=sum(1 for e in main if progress.is_done(e.id)),
            homework_total=len(main),
            homework_optional=sum(1 for e in homework if e.status == "optional"),
            needs_review=len(self.needs_review(lesson=number)),
            errors=len(self.lesson_errors(number)),
        )

    def linked_exercises(self, element_id: str) -> list[Any]:
        found = [
            e
            for e in self.content.elements.values()
            if e.kind == "exercise" and element_id in (e.links.text, e.links.theory)
        ]
        return sorted(found, key=_sort_key)

    # --- темы и дополнительные материалы -----------------------------------------------------

    def topic_elements(self, topic_id: str) -> list[Any]:
        return sorted(self._by_topic.get(topic_id, []), key=_topic_sort_key)

    def topic_tabs(self, elements: list[Any]) -> list[tuple[str, str, list[Any]]]:
        """Вкладки страницы темы (009, FR-040): (ключ, название, элементы), только непустые."""
        groups = [
            ("theory", "Теория", "theory"),
            ("texts", "Тексты", "text"),
            ("exercises", "Задания", "exercise"),
            ("words", "Слова", "vocab"),
        ]
        tabs = []
        for key, name, kind in groups:
            found = [e for e in elements if e.kind == kind]
            if found:
                tabs.append((key, name, found))
        return tabs

    def untopiced_elements(self) -> list[Any]:
        return sorted(
            (e for e in self.content.elements.values() if not e.topics), key=_topic_sort_key
        )

    def topics_by_section(self) -> list[SectionTopics]:
        sections = self.content.topics.sections if self.content.topics else []
        result = []
        for section in sections:
            topics = [
                TopicCount(t, len(self._by_topic.get(t.id, [])))
                for t in self.all_topics()
                if t.section == section.id
            ]
            result.append(SectionTopics(section, topics))
        return result

    def extras(self) -> list[Any]:
        found = [
            e
            for e in self.content.elements.values()
            if (e.kind == "vocab" and not e.lessons) or (e.kind != "vocab" and e.lesson is None)
        ]
        return sorted(found, key=_topic_sort_key)

    # --- проверка и сообщения ----------------------------------------------------------------

    def needs_review(self, lesson: int | None = None) -> list[ReviewItem]:
        result = []
        for element in sorted(self.content.elements.values(), key=_topic_sort_key):
            if lesson is not None and getattr(element, "lesson", None) != lesson:
                continue
            if element.needs_review.flag:
                result.append(ReviewItem(element, None, element.needs_review.note or ""))
            for item in getattr(element, "items", []):
                if item.needs_review.flag:
                    result.append(ReviewItem(element, item.id, item.needs_review.note or ""))
        return result

    def reports(self) -> list[schema.Report]:
        return sorted(
            self.content.reports.values(),
            key=lambda r: (r.status != "open", -r.created.timestamp()),
        )

    def open_reports_count(self) -> int:
        return sum(1 for r in self.content.reports.values() if r.status == "open")


def _sort_key(element: Any) -> tuple:
    number = getattr(element, "number", 0)
    return (_KIND_ORDER[element.kind], number, getattr(element, "title", ""), element.id)


def _topic_sort_key(element: Any) -> tuple:
    lesson = getattr(element, "lesson", None)
    if element.kind == "vocab":
        lesson = min(element.lessons) if element.lessons else None
    return (lesson is None, lesson or 0, *_sort_key(element))


def tree_fingerprint(root: Path) -> str:
    """Отпечаток дерева файлов хранилища (имя, время изменения, размер).

    Пропускаются .git и база прогресса: оценки и попытки не должны перечитывать контент.
    """
    digest = hashlib.sha1()
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in (".git", ".progress"))
        for name in sorted(files):
            stat = os.stat(os.path.join(folder, name))
            digest.update(f"{folder}/{name}|{stat.st_mtime_ns}|{stat.st_size};".encode())
    return digest.hexdigest()


class ContentStore:
    """Хранит индекс и перестраивает его, если файлы хранилища изменились."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._lock = threading.Lock()
        self._fingerprint: str | None = None
        self._index: ContentIndex | None = None

    def get(self) -> ContentIndex:
        with self._lock:
            fingerprint = tree_fingerprint(self.root)
            if self._index is None or fingerprint != self._fingerprint:
                self._index = ContentIndex(load_content(self.root))
                self._fingerprint = fingerprint
            return self._index
