"""Вопрос встроенного тренажёра и данные для генераторов (data-model 004).

Ключ вопроса стабилен (например, `articles:voc-abc:def`): по нему ведётся расписание FSRS
и история ответов, поэтому ключ не должен меняться при перезапуске приложения.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Mode = Literal["buttons", "input", "order", "gaps"]


@dataclass
class Question:
    key: str
    prompt: str
    answers: list[str]
    mode: Mode = "input"
    options: list[str] = field(default_factory=list)
    tokens: list[str] = field(default_factory=list)
    hint: str | None = None
    full: str | None = None  # полная правильная форма для показа после ответа
    source: str | None = None  # id элемента, из которого построен вопрос
    lessons: list[int] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    # задания от агента (пакеты): инструкция, пометка агента, ответы по пропускам (mode=gaps)
    instruction: str | None = None
    review_note: str | None = None
    gaps: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class TrainerData:
    vocab: list[Any] = field(default_factory=list)
    exercises: list[Any] = field(default_factory=list)
    texts: list[Any] = field(default_factory=list)

    @classmethod
    def from_index(cls, index: Any) -> TrainerData:
        elements = index.content.elements.values()
        return cls(
            vocab=sorted(
                (e for e in elements if e.kind == "vocab" and not e.hidden),
                key=lambda e: (e.text.casefold(), e.id),
            ),
            exercises=sorted(
                (e for e in elements if e.kind == "exercise"),
                key=lambda e: (e.lesson or 0, e.part or "", e.number),
            ),
            texts=sorted((e for e in elements if e.kind == "text"), key=lambda e: e.id),
        )


def translation(entry: Any) -> str:
    return ", ".join(t.text for t in entry.translations)


def from_entry(entry: Any) -> dict:
    """Поля вопроса, общие для всех вопросов по записи словаря."""
    return {"source": entry.id, "lessons": list(entry.lessons), "topics": list(entry.topics)}


VOWELS = "aeiouyàâäéèêëîïôöùûüœæ"


def elides(word: str, h_aspire: bool = False) -> bool:
    """Перед словом элизия (l', cet, mon для ж. р.): гласная или h немое."""
    first = word[:1].casefold()
    return first in VOWELS or (first == "h" and not h_aspire)
