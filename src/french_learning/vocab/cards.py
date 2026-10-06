"""Карточки повторения и расписание FSRS (research R2, R3, R10, R13; data-model 003).

Карточка = (запись словаря, направление `fr_ru` / `ru_fr`). Прогресс направлений независим.
Каждая оценка пишется в `reviews` со снимком прежнего состояния (для отмены).
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from typing import Any

import fsrs

from french_learning.practice.db import ProgressDB

RATINGS = {"again": fsrs.Rating.Again, "hard": fsrs.Rating.Hard, "good": fsrs.Rating.Good}
HARD_WINDOW = 5
DIRECTIONS = ("fr_ru", "ru_fr")


@dataclass
class CardRow:
    entry_id: str
    direction: str
    card: fsrs.Card
    due: dt.datetime
    suspended: bool
    reviewed: bool


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def end_of_local_day(moment: dt.datetime) -> dt.datetime:
    local = moment.astimezone()
    end = local.replace(hour=23, minute=59, second=59, microsecond=0)
    return end.astimezone(dt.UTC)


class CardStore:
    def __init__(self, db: ProgressDB, fuzzing: bool = True) -> None:
        self.db = db
        self.scheduler = fsrs.Scheduler(
            learning_steps=(), relearning_steps=(), enable_fuzzing=fuzzing
        )

    # --- чтение ------------------------------------------------------------------------------

    def _row(self, row) -> CardRow:
        card = fsrs.Card.from_dict(json.loads(row["fsrs"]))
        return CardRow(
            entry_id=row["entry_id"],
            direction=row["direction"],
            card=card,
            due=card.due,
            suspended=bool(row["suspended"]),
            reviewed=card.last_review is not None,
        )

    def get(self, entry_id: str, direction: str) -> CardRow | None:
        with self.db.lock:
            row = self.db.conn.execute(
                "select * from cards where entry_id = ? and direction = ?", (entry_id, direction)
            ).fetchone()
        return self._row(row) if row else None

    def all(self) -> list[CardRow]:
        with self.db.lock:
            rows = self.db.conn.execute(
                "select * from cards order by entry_id, direction"
            ).fetchall()
        return [self._row(r) for r in rows]

    def due(self, direction: str | None = None, now: dt.datetime | None = None) -> list[CardRow]:
        limit = end_of_local_day(now or _now())
        cards = [c for c in self.all() if not c.suspended and c.due <= limit]
        if direction:
            cards = [c for c in cards if c.direction == direction]
        return sorted(cards, key=lambda c: (c.reviewed, c.due))

    def known_ids(self) -> set[str]:
        with self.db.lock:
            rows = self.db.conn.execute("select distinct entry_id from cards where suspended = 1")
            return {r["entry_id"] for r in rows}

    def history(self, entry_id: str) -> list[dict]:
        with self.db.lock:
            rows = self.db.conn.execute(
                "select * from reviews where entry_id = ? order by id", (entry_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def hard_ids(self) -> set[str]:
        with self.db.lock:
            rows = self.db.conn.execute(
                "select entry_id, rating from reviews order by id"
            ).fetchall()
        recent: dict[str, list[str]] = {}
        for row in rows:
            recent.setdefault(row["entry_id"], []).append(row["rating"])
        return {
            entry_id
            for entry_id, ratings in recent.items()
            if ratings[-HARD_WINDOW:].count("again") > ratings[-HARD_WINDOW:].count("good")
        }

    # --- изменение ---------------------------------------------------------------------------

    def _insert(self, entry_id: str, direction: str, now: dt.datetime) -> None:
        card = fsrs.Card(due=now)
        self.db.conn.execute(
            "insert or ignore into cards (entry_id, direction, fsrs, due, created_at) "
            "values (?, ?, ?, ?, ?)",
            (
                entry_id,
                direction,
                json.dumps(card.to_dict()),
                card.due.isoformat(),
                now.isoformat(),
            ),
        )

    def sync(self, index: Any, now: dt.datetime | None = None) -> None:
        """Карточки обоих направлений для всех нескрытых записей словаря (research R3; 010 R2).

        Создаются только недостающие: `fsrs.Card()` медленный (ждёт ~1,5 мс ради уникального
        номера), а `sync` вызывается на каждом запросе повторения (010, пункт 8).
        """
        now = now or _now()
        entries = [e for e in index.content.elements.values() if e.kind == "vocab" and not e.hidden]
        with self.db.lock, self.db.conn:
            existing = {
                (row["entry_id"], row["direction"])
                for row in self.db.conn.execute("select entry_id, direction from cards")
            }
            for entry in entries:
                for direction in DIRECTIONS:
                    if (entry.id, direction) not in existing:
                        self._insert(entry.id, direction, now)

    def rate(
        self,
        entry_id: str,
        direction: str,
        rating: str,
        *,
        mode: str,
        method: str,
        answer: str | None = None,
        session_id: str | None = None,
        now: dt.datetime | None = None,
    ) -> int:
        now = now or _now()
        current = self.get(entry_id, direction)
        if current is None:
            raise KeyError(f"нет карточки {entry_id} / {direction}")
        updated, _log = self.scheduler.review_card(current.card, RATINGS[rating], now)
        with self.db.lock, self.db.conn:
            cursor = self.db.conn.execute(
                "insert into reviews (entry_id, direction, rating, method, mode, answer, "
                "reviewed_at, session_id, prev_fsrs) values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry_id,
                    direction,
                    rating,
                    method,
                    mode,
                    answer,
                    now.isoformat(),
                    session_id,
                    json.dumps(current.card.to_dict()),
                ),
            )
            self.db.conn.execute(
                "update cards set fsrs = ?, due = ? where entry_id = ? and direction = ?",
                (json.dumps(updated.to_dict()), updated.due.isoformat(), entry_id, direction),
            )
        return cursor.lastrowid

    def undo(self, review_id: int) -> tuple[str, str] | None:
        """Отменить оценку: вернуть прежнее состояние карточки и убрать запись оценки."""
        with self.db.lock, self.db.conn:
            row = self.db.conn.execute(
                "select * from reviews where id = ?", (review_id,)
            ).fetchone()
            if row is None:
                return None
            previous = fsrs.Card.from_dict(json.loads(row["prev_fsrs"]))
            self.db.conn.execute(
                "update cards set fsrs = ?, due = ? where entry_id = ? and direction = ?",
                (row["prev_fsrs"], previous.due.isoformat(), row["entry_id"], row["direction"]),
            )
            self.db.conn.execute("delete from reviews where id = ?", (review_id,))
        return row["entry_id"], row["direction"]

    def set_known(self, entry_id: str, known: bool) -> None:
        with self.db.lock, self.db.conn:
            self.db.conn.execute(
                "update cards set suspended = ? where entry_id = ?", (int(known), entry_id)
            )

    def remove_cards(self, entry_id: str) -> None:
        """Карточки удалённой записи убираются; история оценок остаётся (принцип VII)."""
        with self.db.lock, self.db.conn:
            self.db.conn.execute("delete from cards where entry_id = ?", (entry_id,))
