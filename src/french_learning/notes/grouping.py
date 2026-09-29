"""Страница «Заметки к уроку» (вариант В1, data-model 005): вопросы, «К уроку», блоки элементов."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from french_learning.notes.store import Note

KIND_NAMES = {"theory": "Теория", "text": "Текст", "exercise": "Упражнение"}


@dataclass
class ElementBlock:
    element: Any
    notes: list[Note]

    @property
    def kind_name(self) -> str:
        return KIND_NAMES[self.element.kind]


@dataclass
class LessonNotes:
    open_questions: list[Note] = field(default_factory=list)
    answered_questions: list[Note] = field(default_factory=list)
    lesson_notes: list[Note] = field(default_factory=list)
    orphan_titles: dict[int, str | None] = field(default_factory=dict)  # «было: …»
    blocks: list[ElementBlock] = field(default_factory=list)
    count: int = 0


def _lesson_elements(tree: dict[str, Any]) -> list[Any]:
    """Элементы урока в порядке урока: теория, тексты, классная, домашка, резерв."""
    return [
        *tree["theory"],
        *tree["texts"],
        *(e for e, _ in tree["class"]),
        *(e for e, _ in tree["homework"]),
        *tree["reserve"],
    ]


def lesson_page(notes: list[Note], tree: dict[str, Any]) -> LessonNotes:
    page = LessonNotes(count=len(notes))
    elements = _lesson_elements(tree)
    present = {e.id for e in elements}
    for note in sorted(notes, key=lambda n: n.id):
        if note.kind == "question":
            target = page.answered_questions if note.answered else page.open_questions
            target.append(note)
        elif note.element_id is None:
            page.lesson_notes.append(note)
        elif note.element_id not in present:
            page.lesson_notes.append(note)
            page.orphan_titles[note.id] = note.element_title
    for element in elements:
        own = [n for n in notes if n.kind == "note" and n.element_id == element.id]
        if own:
            own.sort(key=lambda n: (n.anchor is not None, n.id))  # ко всему элементу — сначала
            page.blocks.append(ElementBlock(element, own))
    return page
