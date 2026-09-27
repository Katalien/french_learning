"""Тренажёры «Женский род» и «Множественное число»: форма слова из словаря (FR-040)."""

from __future__ import annotations

from french_learning.trainers.questions import Question, TrainerData, from_entry, translation

MISSING_FEMININE = (
    "В словаре нет слов с формой женского рода. Добавьте прилагательные или существительные "
    "и попросите агента дополнить их командой /complete-words."
)
MISSING_PLURAL = (
    "В словаре нет слов с формой множественного числа. Попросите агента дополнить слова "
    "командой /complete-words."
)


def _generate(data: TrainerData, trainer: str, field: str, label: str) -> list[Question]:
    questions = []
    for entry in data.vocab:
        value = getattr(entry.forms, field)
        if not value or value == entry.text:
            continue
        hint = f"{label} · {translation(entry)}"
        if entry.forms.note:
            hint += f" · {entry.forms.note}"
        questions.append(
            Question(
                key=f"{trainer}:{entry.id}",
                prompt=entry.text,
                answers=[value],
                hint=hint,
                full=f"{entry.text} → {value}",
                **from_entry(entry),
            )
        )
    return questions


def generate_feminine(data: TrainerData) -> list[Question]:
    return _generate(data, "feminine", "feminine", "женский род")


def generate_plural(data: TrainerData) -> list[Question]:
    return _generate(data, "plural", "plural", "множественное число")
