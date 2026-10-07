"""Данные экрана «Сегодня» (009, FR-003; research R4).

Показываются только три вещи: слова последнего урока (012: число слов и «Повторить» — все
слова урока), невыполненная основная домашка двух последних уроков, где она есть,
и встроенные тренажёры с вопросами «пора».
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from french_learning.trainers.catalog import catalog
from french_learning.trainers.questions import TrainerData
from french_learning.vocab.sessions import SessionParams

HOMEWORK_LESSONS = 2


@dataclass
class TodayTrainer:
    id: str
    name: str
    due: int


@dataclass
class TodayLesson:
    number: int
    exercises: list[Any]


@dataclass
class Today:
    due_fr_ru: int = 0
    due_ru_fr: int = 0
    new: int = 0
    last_lesson: int | None = None  # 012: последний урок со словами
    last_lesson_words: int = 0
    homework: list[TodayLesson] = field(default_factory=list)
    trainers: list[TodayTrainer] = field(default_factory=list)

    @property
    def due(self) -> int:
        return self.due_fr_ru + self.due_ru_fr

    @property
    def empty(self) -> bool:
        return not (self.last_lesson_words or self.homework or self.trainers)


@lru_cache(maxsize=4)
def _trainer_keys(index: Any) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """Ключи вопросов встроенных тренажёров; индекс контента неизменяем до перезагрузки."""
    data = TrainerData.from_index(index)
    return tuple(
        (t.id, t.name, tuple(q.key for q in t.questions(data)))
        for t in catalog(index)
        if t.source == "builtin"
    )


def build_today(index: Any, cards: Any, sessions: Any, progress: Any, schedule: Any) -> Today:
    today = Today()
    if cards is not None:
        cards.sync(index)
        queues = {
            direction: sessions.queue(index, SessionParams(mode="today", direction=direction))
            for direction in ("fr_ru", "ru_fr")
        }
        today.due_fr_ru, today.due_ru_fr = len(queues["fr_ru"]), len(queues["ru_fr"])
        fresh = {c.entry_id for c in cards.all() if not c.reviewed}
        today.new = sum(1 for entry_id, _d in queues["fr_ru"] if entry_id in fresh)

    for lesson in index.lessons():  # новые сверху; урок без слов — берётся предыдущий
        new_words, repeat_words = index.lesson_vocabulary(lesson.number)
        if new_words or repeat_words:
            today.last_lesson = lesson.number
            today.last_lesson_words = len(new_words) + len(repeat_words)
            break

    lessons_with_homework = [
        lesson
        for lesson in index.lessons()  # новые сверху
        if any(
            e.status == "main"
            for e in index.elements(lesson.number, part="homework", kind="exercise")
        )
    ][:HOMEWORK_LESSONS]
    for lesson in lessons_with_homework:
        undone = [
            e
            for e in index.elements(lesson.number, part="homework", kind="exercise")
            if e.status == "main" and not progress.is_done(e.id)
        ]
        if undone:
            today.homework.append(TodayLesson(lesson.number, undone))

    if schedule is not None:
        for trainer_id, name, keys in _trainer_keys(index):
            due = schedule.due_count(trainer_id, list(keys))
            if due:
                today.trainers.append(TodayTrainer(trainer_id, name, due))
    return today
