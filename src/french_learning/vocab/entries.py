"""Записи словаря: отображение, вопрос и ответ карточки, фильтры (FR-010, FR-032a; R4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from french_learning.content.index import ContentIndex

POS_NAMES = {
    "nom": "сущ.",
    "verbe": "глаг.",
    "adj": "прил.",
    "adv": "нареч.",
    "prep": "предл.",
    "pron": "мест.",
}
KIND_NAMES = {"word": "слово", "verb": "глагол", "phrase": "фраза"}


@dataclass
class Question:
    text: str
    hint: str = ""


def display_fr(entry: Any) -> str:
    """Французская форма для показа и проверки: у существительных — с артиклем."""
    if not entry.article:
        return entry.text
    joiner = "" if entry.article == "l'" else " "
    return f"{entry.article}{joiner}{entry.text}"


def indefinite(entry: Any) -> str | None:
    """Неопределённый артикль выводится из рода и признаков (решение 004, data-model 003)."""
    if getattr(entry.flags, "plural_only", False):
        return "des"
    return {"m": "un", "f": "une", "both": "un / une"}.get(entry.gender)


def translations(entry: Any) -> list[str]:
    return [t.text for t in entry.translations]


def vocab_entries(index: ContentIndex) -> list[Any]:
    return sorted(
        (e for e in index.content.elements.values() if e.kind == "vocab"),
        key=lambda e: e.text.casefold(),
    )


def question(index: ContentIndex, entry: Any, direction: str) -> Question:
    if direction == "fr_ru":
        return Question(display_fr(entry))
    hint_parts = [POS_NAMES.get(entry.pos or "", entry.pos or ""), KIND_NAMES[entry.entry_type]]
    if entry.examples:
        hint_parts.append(f"пример: {entry.examples[0].text}")
    hint = " · ".join(p for p in hint_parts if p)
    return Question(", ".join(translations(entry)), hint)


def accepted_answers(index: ContentIndex, entry: Any, direction: str) -> list[str]:
    if direction == "fr_ru":
        return translations(entry)
    wanted = {t.casefold() for t in translations(entry)}
    same = [
        display_fr(other)
        for other in vocab_entries(index)
        if not other.hidden and wanted & {t.casefold() for t in translations(other)}
    ]
    return sorted(set(same))


def filter_entries(
    index: ContentIndex,
    *,
    lesson: int | None = None,
    topic: str | None = None,
    kind: str | None = None,
    flag: str | None = None,
    known_ids: set[str] | frozenset = frozenset(),
) -> list[Any]:
    result = []
    for entry in vocab_entries(index):
        if flag == "hidden":
            if not entry.hidden:
                continue
        elif entry.hidden:
            continue
        if flag == "known" and entry.id not in known_ids:
            continue
        if flag == "incomplete" and not entry.needs_completion:
            continue
        if lesson is not None and lesson not in entry.lessons:
            continue
        if topic and topic not in entry.topics:
            continue
        if kind and entry.entry_type != kind:
            continue
        result.append(entry)
    return result
