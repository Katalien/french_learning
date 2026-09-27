"""«Мои ошибки» по упражнениям уроков (FR-021a; research R5 функции 004).

Для каждого пункта решает самая свежая проверенная попытка, в которую он входит (полная
или по одному пункту). Пункт в списке, если итог его первой проверки в этой попытке —
ошибка (с учётом пересчёта после исправлений агента). Верное решение убирает пункт
из списка, история попыток остаётся.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from french_learning.content.index import ContentIndex
from french_learning.exercises.attempts import Attempt, AttemptStore


@dataclass
class Mistake:
    exercise: Any
    item: Any
    attempt: Attempt

    @property
    def answer(self) -> dict[str, Any]:
        first = self.attempt.first_results.get(str(self.item.id), {})
        return first.get("answer", {})


def find_mistakes(
    index: ContentIndex,
    store: AttemptStore,
    lesson: int | None = None,
    topic: str | None = None,
) -> list[Mistake]:
    decided: set[tuple[str, int]] = set()
    found: list[Mistake] = []
    recalculated: set[int] = set()
    for attempt in store.all_checked():  # новые сверху
        exercise = index.element(attempt.exercise_id)
        if exercise is None or exercise.kind != "exercise":
            continue
        if attempt.id not in recalculated:
            store.recalculate(exercise, attempt)
            recalculated.add(attempt.id)
        items = {i.id: i for i in exercise.items}
        for item_id in attempt.item_ids:
            key = (exercise.id, item_id)
            if key in decided or item_id not in items:
                continue
            status = attempt.first_status(item_id)
            if status is None:
                continue
            decided.add(key)
            if status == "wrong":
                found.append(Mistake(exercise, items[item_id], attempt))
    found = [
        m
        for m in found
        if (lesson is None or m.exercise.lesson == lesson)
        and (topic is None or topic in m.exercise.topics)
    ]
    return sorted(found, key=lambda m: (m.exercise.lesson or 0, m.exercise.number, m.item.id))
