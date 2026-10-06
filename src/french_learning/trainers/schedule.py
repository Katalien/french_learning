"""Расписание вопросов тренажёров и история ответов (FR-044, FR-053; research R10 функции 004).

Каждый ответ пишется в `trainer_answers`. Для встроенных тренажёров (`srs=True`) вопрос
ведётся FSRS, как карточка словаря: верно → good, неверно или подсмотрено → again.
Самооценки нет. Для заданий от агента FSRS не ведётся — только статистика.
"""

from __future__ import annotations

import datetime as dt
import json
import random

import fsrs

from french_learning.practice.db import ProgressDB
from french_learning.vocab.cards import HARD_WINDOW, end_of_local_day


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class TrainerSchedule:
    def __init__(self, db: ProgressDB, fuzzing: bool = True) -> None:
        self.db = db
        self.scheduler = fsrs.Scheduler(
            learning_steps=(), relearning_steps=(), enable_fuzzing=fuzzing
        )

    # --- ответы ------------------------------------------------------------------------------

    def answer(
        self,
        trainer_id: str,
        key: str,
        *,
        correct: bool,
        answer: str | None = None,
        revealed: bool = False,
        session_id: str | None = None,
        srs: bool = True,
        now: dt.datetime | None = None,
    ) -> None:
        now = now or _now()
        ok = correct and not revealed
        with self.db.lock, self.db.conn:
            self.db.conn.execute(
                "insert into trainer_answers (trainer_id, key, answer, correct, revealed, "
                "answered_at, session_id) values (?, ?, ?, ?, ?, ?, ?)",
                (trainer_id, key, answer, int(ok), int(revealed), now.isoformat(), session_id),
            )
            # ответ снимает приоритет «в начало очереди» (011, «Ошибка в артикле»)
            self.db.conn.execute(
                "delete from trainer_priority where trainer_id = ? and key = ?", (trainer_id, key)
            )
            if not srs:
                return
            row = self.db.conn.execute(
                "select fsrs from trainer_cards where trainer_id = ? and key = ?",
                (trainer_id, key),
            ).fetchone()
            card = fsrs.Card.from_dict(json.loads(row["fsrs"])) if row else fsrs.Card(due=now)
            rating = fsrs.Rating.Good if ok else fsrs.Rating.Again
            updated, _log = self.scheduler.review_card(card, rating, now)
            self.db.conn.execute(
                "insert into trainer_cards (trainer_id, key, fsrs, due, created_at) "
                "values (?, ?, ?, ?, ?) on conflict(trainer_id, key) do update set "
                "fsrs = excluded.fsrs, due = excluded.due",
                (
                    trainer_id,
                    key,
                    json.dumps(updated.to_dict()),
                    updated.due.isoformat(),
                    now.isoformat(),
                ),
            )

    def history(self, trainer_id: str) -> list[dict]:
        with self.db.lock:
            rows = self.db.conn.execute(
                "select * from trainer_answers where trainer_id = ? order by id", (trainer_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    # --- расписание --------------------------------------------------------------------------

    def _dues(self, trainer_id: str) -> dict[str, dt.datetime]:
        with self.db.lock:
            rows = self.db.conn.execute(
                "select key, due from trainer_cards where trainer_id = ?", (trainer_id,)
            ).fetchall()
        return {r["key"]: dt.datetime.fromisoformat(r["due"]) for r in rows}

    def due_at(self, trainer_id: str, key: str) -> dt.datetime | None:
        return self._dues(trainer_id).get(key)

    def due_count(self, trainer_id: str, keys: list[str], now: dt.datetime | None = None) -> int:
        limit = end_of_local_day(now or _now())
        dues = self._dues(trainer_id)
        return sum(1 for k in keys if k in dues and dues[k] <= limit)

    def hard_keys(self, trainer_id: str) -> set[str]:
        """Вопросы, где среди последних ответов ошибок больше, чем верных (как в 003)."""
        recent: dict[str, list[int]] = {}
        for row in self.history(trainer_id):
            recent.setdefault(row["key"], []).append(row["correct"])
        return {
            key
            for key, marks in recent.items()
            if marks[-HARD_WINDOW:].count(0) > marks[-HARD_WINDOW:].count(1)
        }

    def select(
        self,
        trainer_id: str,
        keys: list[str],
        size: int,
        *,
        exclude: set[str] | frozenset = frozenset(),
        now: dt.datetime | None = None,
    ) -> list[str]:
        """Порция: сначала приоритетные (011), затем «пора» (раньше срок — раньше), новые,
        досрочно."""
        limit = end_of_local_day(now or _now())
        dues = self._dues(trainer_id)
        allowed = {k for k in keys if k not in exclude}
        with self.db.lock:
            rows = self.db.conn.execute(
                "select key from trainer_priority where trainer_id = ? order by created_at, key",
                (trainer_id,),
            ).fetchall()
        first = [r["key"] for r in rows if r["key"] in allowed]
        candidates = [k for k in keys if k in allowed and k not in first]
        due = sorted((k for k in candidates if k in dues and dues[k] <= limit), key=dues.get)
        new = [k for k in candidates if k not in dues]
        random.Random(trainer_id).shuffle(new)  # разнообразие, но стабильный порядок
        ahead = sorted((k for k in candidates if k in dues and dues[k] > limit), key=dues.get)
        return (first + due + new + ahead)[:size]
