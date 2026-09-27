"""Проверка упражнения по типам (FR-002–FR-005, FR-011; research R2, R3 функции 004).

Ответ пункта — словарь «поле → значение»: у пропусков поле — номер пропуска (`"1"`),
у остальных типов — `"a"`. У `choice` значение — список индексов, у `true_false` —
`"true"` / `"false"`. Если ответ отличается от правильного только диакритикой, пункт
получает статус `choose`: пользователь выбирает написание, выбор передаётся в поле
`"<поле>~choice"`, и неверный выбор — ошибка. Сравнение — общий `practice/checking.py`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Literal

from french_learning.practice.checking import check_french, normalize_keyboard

GAP_TYPES = {"gap_choice", "gap_input", "multi_gap", "two_forms"}
SELECT_TYPES = {"gap_choice", "two_forms"}
TEXT_TYPES = {"transform", "picture"}
FIELD = "a"
CHOICE_SUFFIX = "~choice"

Status = Literal["correct", "wrong", "choose"]


@dataclass
class GapResult:
    status: Status
    variants: list[str] = field(default_factory=list)


@dataclass
class ItemResult:
    item_id: int
    gaps: dict[str, GapResult]

    @property
    def status(self) -> Status:
        statuses = {g.status for g in self.gaps.values()}
        if "wrong" in statuses:
            return "wrong"
        if "choose" in statuses:
            return "choose"
        return "correct"


def checkable(exercise: Any) -> bool:
    """Открытый ответ и «по картинке» без ответов сохраняются без проверки (FR-005)."""
    if exercise.type == "open":
        return False
    if exercise.type == "picture":
        return all(item.answers for item in exercise.items)
    return True


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _accepted(exercise: Any, item: Any) -> dict[str, list[str]]:
    """Допустимые ответы по полям пункта (для текстовых сравнений)."""
    if exercise.type in GAP_TYPES:
        return {str(gap): list(variants) for gap, variants in item.answers.items()}
    if exercise.type in TEXT_TYPES:
        return {FIELD: list(item.answers)}
    if exercise.type == "grouping":
        return {FIELD: [item.answer]}
    return {}


def _grade_text(
    key: str, answer: dict[str, Any], accepted: list[str], seed: str, spelling: bool
) -> GapResult:
    chosen = answer.get(key + CHOICE_SUFFIX)
    if chosen:
        ok = any(chosen == variant for variant in accepted)
        return GapResult("correct" if ok else "wrong")
    given = _text(answer.get(key))
    if not given.strip():
        return GapResult("wrong")
    if not spelling:
        ok = any(normalize_keyboard(given) == normalize_keyboard(v) for v in accepted)
        return GapResult("correct" if ok else "wrong")
    result = check_french(given, accepted, rng=random.Random(seed))
    if result.status == "choose_spelling":
        return GapResult("choose", result.variants)
    return GapResult("correct" if result.status == "correct" else "wrong")


def grade_item(exercise: Any, item: Any, answer: dict[str, Any]) -> ItemResult:
    seed = f"{exercise.id}:{item.id}"
    kind = exercise.type
    if kind == "true_false":
        expected = "true" if item.answer else "false"
        ok = answer.get(FIELD) == expected
        return ItemResult(item.id, {FIELD: GapResult("correct" if ok else "wrong")})
    if kind == "choice":
        given = answer.get(FIELD) or []
        given = [given] if isinstance(given, str) else given
        try:
            ok = sorted(int(i) for i in given) == sorted(item.answer)
        except ValueError:
            ok = False
        return ItemResult(item.id, {FIELD: GapResult("correct" if ok else "wrong")})
    # выбор из списка и группы — без выбора написания; ввод — с выбором
    spelling = kind not in SELECT_TYPES and kind != "grouping"
    gaps = {
        key: _grade_text(key, answer, accepted, f"{seed}:{key}", spelling)
        for key, accepted in _accepted(exercise, item).items()
    }
    return ItemResult(item.id, gaps)


def correct_answers(exercise: Any, item: Any) -> dict[str, list[str]]:
    """Правильные ответы пункта для «Показать ответ» — в виде, понятном человеку."""
    if exercise.type == "true_false":
        return {FIELD: ["верно" if item.answer else "неверно"]}
    if exercise.type == "choice":
        return {FIELD: [item.options[i] for i in item.answer]}
    return _accepted(exercise, item)
