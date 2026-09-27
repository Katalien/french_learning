"""Тренажёр «Числа»: 0–1000 цифрами → словами (оба написания верны; research R11)."""

from __future__ import annotations

from french_learning.trainers.french_numbers import spellings
from french_learning.trainers.questions import Question, TrainerData

LIMIT = 1000


def generate(data: TrainerData) -> list[Question]:
    return [
        Question(
            key=f"numbers:{n}",
            prompt=str(n),
            answers=(written := spellings(n)),
            hint="напишите словами",
            full=written[0],
        )
        for n in range(LIMIT + 1)
    ]
