"""Попытки упражнений уроков (FR-006, FR-020–FR-022, FR-031; data-model и research R2, R4 004).

Попытка — одно прохождение упражнения (`scope = full`) или одного пункта из «Моих ошибок»
(`scope = item`). Итог пункта фиксируется при первой проверке вместе с ответом, который
тогда был дан: так после исправления правильного ответа агентом итог можно честно
пересчитать, не меняя сохранённых данных (VII). Отметки: `fixed_self` — исправлено после
подсветки, `revealed` — подсмотрен ответ (считается ошибкой).
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from typing import Any

from french_learning.exercises.grading import grade_item
from french_learning.practice.db import ProgressDB

Answers = dict[str, dict[str, Any]]  # {id пункта: {поле: значение}}


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


@dataclass
class Attempt:
    id: int
    exercise_id: str
    scope: str
    item_ids: list[int]
    status: str
    answers: Answers
    first_results: dict[str, dict[str, Any]]  # {пункт: {"status", "answer"}}
    current_results: dict[str, dict[str, Any]]  # {пункт: {поле: {"status", "variants"}}}
    marks: dict[str, str]
    created_at: str
    checked_at: str | None
    updated_at: str
    recalculated: dict[str, str] = field(default_factory=dict)  # пункт → новый итог (R4)

    @property
    def checked(self) -> bool:
        return self.status == "checked"

    def first_status(self, item_id: int | str) -> str | None:
        key = str(item_id)
        if key in self.recalculated:
            return self.recalculated[key]
        found = self.first_results.get(key)
        return found["status"] if found else None

    def current_status(self, item_id: int | str) -> str | None:
        fields = self.current_results.get(str(item_id))
        if not fields:
            return None
        statuses = {f["status"] for f in fields.values()}
        for status in ("wrong", "choose"):
            if status in statuses:
                return status
        return "correct"

    def field_status(self, item_id: int | str, name: str) -> str | None:
        found = self.current_results.get(str(item_id), {}).get(name)
        return found["status"] if found else None

    def variants(self, item_id: int | str, name: str) -> list[str]:
        return self.current_results.get(str(item_id), {}).get(name, {}).get("variants", [])

    def outcome(self, item_id: int | str) -> str | None:
        """Итог пункта: correct / wrong / fixed_self / revealed; None — ещё не проверен."""
        first = self.first_status(item_id)
        if first is None or first == "correct":
            return first
        return self.marks.get(str(item_id), "wrong")

    def is_error(self, item_id: int | str) -> bool:
        return self.first_status(item_id) == "wrong"

    @property
    def score(self) -> tuple[int, int]:
        """(верно сразу, проверено пунктов)."""
        checked = [i for i in self.item_ids if self.first_status(i) is not None]
        return sum(1 for i in checked if self.first_status(i) == "correct"), len(checked)


class AttemptStore:
    def __init__(self, db: ProgressDB) -> None:
        self.db = db

    # --- чтение ------------------------------------------------------------------------------

    def _attempt(self, row: Any) -> Attempt:
        return Attempt(
            id=row["id"],
            exercise_id=row["exercise_id"],
            scope=row["scope"],
            item_ids=json.loads(row["item_ids"]),
            status=row["status"],
            answers=json.loads(row["answers"]),
            first_results=json.loads(row["first_results"]),
            current_results=json.loads(row["current_results"]),
            marks=json.loads(row["marks"]),
            created_at=row["created_at"],
            checked_at=row["checked_at"],
            updated_at=row["updated_at"],
        )

    def _query(self, sql: str, *args: Any) -> list[Attempt]:
        with self.db.lock:
            rows = self.db.conn.execute(sql, args).fetchall()
        return [self._attempt(r) for r in rows]

    def get(self, attempt_id: int) -> Attempt | None:
        found = self._query("select * from exercise_attempts where id = ?", attempt_id)
        return found[0] if found else None

    def current(self, exercise_id: str) -> Attempt | None:
        """Последняя попытка всего упражнения (черновик или проверенная)."""
        found = self._query(
            "select * from exercise_attempts where exercise_id = ? and scope = 'full' "
            "order by id desc limit 1",
            exercise_id,
        )
        return found[0] if found else None

    def history(self, exercise_id: str) -> list[Attempt]:
        """Все попытки упражнения, новые сверху (включая попытки по пункту)."""
        return self._query(
            "select * from exercise_attempts where exercise_id = ? order by id desc", exercise_id
        )

    def all_checked(self) -> list[Attempt]:
        return self._query(
            "select * from exercise_attempts where status = 'checked' order by id desc"
        )

    def done_ids(self) -> set[str]:
        with self.db.lock:
            rows = self.db.conn.execute(
                "select distinct exercise_id from exercise_attempts "
                "where scope = 'full' and status in ('checked', 'saved')"
            ).fetchall()
        return {r["exercise_id"] for r in rows}

    # --- запись ------------------------------------------------------------------------------

    def _create(self, exercise: Any, scope: str = "full", items: list[int] | None = None) -> int:
        now = _now()
        item_ids = items or [i.id for i in exercise.items]
        with self.db.lock, self.db.conn:
            cursor = self.db.conn.execute(
                "insert into exercise_attempts (exercise_id, scope, item_ids, status, "
                "created_at, updated_at) values (?, ?, ?, 'draft', ?, ?)",
                (exercise.id, scope, json.dumps(item_ids), now, now),
            )
        return cursor.lastrowid

    def _save(self, attempt: Attempt) -> Attempt:
        attempt.updated_at = _now()
        with self.db.lock, self.db.conn:
            self.db.conn.execute(
                "update exercise_attempts set status = ?, answers = ?, first_results = ?, "
                "current_results = ?, marks = ?, checked_at = ?, updated_at = ? where id = ?",
                (
                    attempt.status,
                    json.dumps(attempt.answers, ensure_ascii=False),
                    json.dumps(attempt.first_results, ensure_ascii=False),
                    json.dumps(attempt.current_results, ensure_ascii=False),
                    json.dumps(attempt.marks),
                    attempt.checked_at,
                    attempt.updated_at,
                    attempt.id,
                ),
            )
        return attempt

    def _working(self, exercise: Any) -> Attempt:
        attempt = self.current(exercise.id)
        if attempt is None:
            attempt = self.get(self._create(exercise))
        return attempt

    def save_draft(self, exercise: Any, answers: Answers) -> Attempt:
        attempt = self._working(exercise)
        attempt.answers = _clean(answers, attempt.item_ids)
        return self._save(attempt)

    def restart(self, exercise: Any) -> Attempt:
        return self.get(self._create(exercise))

    def start_item(self, exercise: Any, item_id: int) -> Attempt:
        """Попытка одного пункта из «Моих ошибок» (FR-021a)."""
        return self.get(self._create(exercise, scope="item", items=[item_id]))

    def check(self, exercise: Any, answers: Answers, attempt: Attempt | None = None) -> Attempt:
        attempt = attempt or self._working(exercise)
        attempt.answers = _clean(answers, attempt.item_ids)
        items = {i.id: i for i in exercise.items}
        for item_id in attempt.item_ids:
            if item_id not in items:
                continue
            key = str(item_id)
            given = attempt.answers.get(key, {})
            result = grade_item(exercise, items[item_id], given)
            attempt.current_results[key] = {
                name: {"status": g.status, "variants": g.variants}
                for name, g in result.gaps.items()
            }
            status = result.status
            first = attempt.first_results.get(key)
            if first is None and status != "choose":
                attempt.first_results[key] = {"status": status, "answer": given}
            elif (
                first
                and first["status"] == "wrong"
                and status == "correct"
                and key not in attempt.marks
            ):
                attempt.marks[key] = "fixed_self"
        if attempt.status != "checked":
            attempt.status = "checked"
            attempt.checked_at = _now()
        return self._save(attempt)

    def reveal(self, exercise: Any, item_id: int, attempt: Attempt | None = None) -> Attempt:
        attempt = attempt or self._working(exercise)
        key = str(item_id)
        first = attempt.first_results.get(key)
        if first is None:
            attempt.first_results[key] = {
                "status": "wrong",
                "answer": attempt.answers.get(key, {}),
            }
            attempt.marks[key] = "revealed"
        elif first["status"] == "wrong" and attempt.marks.get(key) != "fixed_self":
            attempt.marks[key] = "revealed"
        return self._save(attempt)

    def save_open(self, exercise: Any, answers: Answers) -> Attempt:
        attempt = self._working(exercise)
        attempt.answers = _clean(answers, attempt.item_ids)
        attempt.status = "saved"
        attempt.checked_at = attempt.checked_at or _now()
        return self._save(attempt)

    # --- пересчёт (R4) -----------------------------------------------------------------------

    def recalculate(self, exercise: Any, attempt: Attempt) -> Attempt:
        """Итоги первой проверки по текущим правильным ответам; данные в базе не меняются."""
        items = {i.id: i for i in exercise.items}
        attempt.recalculated = {}
        for key, first in attempt.first_results.items():
            item = items.get(int(key))
            if item is None or (attempt.marks.get(key) == "revealed" and not first["answer"]):
                continue
            status = grade_item(exercise, item, first["answer"]).status
            if status != "choose" and status != first["status"]:
                attempt.recalculated[key] = status
        return attempt


def _clean(answers: Answers, item_ids: list[int]) -> Answers:
    allowed = {str(i) for i in item_ids}
    return {k: v for k, v in answers.items() if k in allowed and isinstance(v, dict)}


class ExerciseProgress:
    """Выполнено = хотя бы одна полная проверка или сохранённый открытый ответ (FR-022)."""

    def __init__(self, store: AttemptStore) -> None:
        self.store = store

    def is_done(self, exercise_id: str) -> bool:
        return exercise_id in self.store.done_ids()
