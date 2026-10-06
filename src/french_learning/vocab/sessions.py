"""Сеансы повторения: очередь, порции, отмена последней оценки (research R9).

Размер подхода задаётся при запуске (010: пусто — все одним подходом). Очередь
перемешивается при запуске (010, пункт 5) и дальше не меняется. Каждая оценка сохраняется
сразу (FR-035c); отменить можно только последнюю оценку текущего сеанса (FR-033).
"""

from __future__ import annotations

import datetime as dt
import json
import random
import secrets
from dataclasses import asdict, dataclass
from typing import Any

from french_learning.practice.db import ProgressDB
from french_learning.vocab import entries as vocab_entries
from french_learning.vocab.cards import CardStore


@dataclass
class SessionParams:
    source: str = "dictionary"  # dictionary | lesson
    mode: str = "today"  # today | lesson | topic | all | hard
    kind: str = "all"  # all | word | verb | phrase
    direction: str = "fr_ru"  # fr_ru | ru_fr
    method: str = "self"  # self | input
    lesson: int | None = None
    topic: str | None = None
    portion: int | None = None  # слов за подход; None — все (010)


@dataclass
class Progress:
    position: int
    total: int
    portion_size: int
    portion_end: int

    @property
    def finished(self) -> bool:
        return self.position >= self.total

    @property
    def portion_finished(self) -> bool:
        return self.position >= self.portion_end

    @property
    def number(self) -> int:
        return min(self.position + 1, self.total)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class SessionStore:
    def __init__(self, db: ProgressDB, cards: CardStore, rng: random.Random | None = None) -> None:
        self.db = db
        self.cards = cards
        self.rng = rng or random.Random()

    # --- очередь -----------------------------------------------------------------------------

    def _entry_ids(self, index: Any, params: SessionParams) -> set[str] | None:
        """Какие записи входят в сеанс; None — любые (режимы «сегодня», «все»)."""
        known = self.cards.known_ids()
        kind = None if params.kind == "all" else params.kind
        if params.mode == "lesson":
            pool = vocab_entries.filter_entries(index, lesson=params.lesson, kind=kind)
        elif params.mode == "topic":
            pool = vocab_entries.filter_entries(index, topic=params.topic, kind=kind)
        else:
            pool = vocab_entries.filter_entries(index, kind=kind)
        ids = {e.id for e in pool} - known
        if params.mode == "hard":
            ids &= self.cards.hard_ids()
        return ids

    def queue(self, index: Any, params: SessionParams, now: dt.datetime | None = None) -> list:
        """Очередь сеанса в случайном порядке (010 R3).

        «Сегодня»: сначала уже повторявшиеся карточки с подошедшим сроком, затем новые —
        каждая группа перемешана, чтобы забываемые слова не уходили в конец.
        """
        ids = self._entry_ids(index, params)
        if params.mode == "today":
            pool = self.cards.due(direction=params.direction, now=now or _now())
        else:
            pool = [
                c for c in self.cards.all() if c.direction == params.direction and not c.suspended
            ]
        pool = [c for c in pool if c.entry_id in ids]
        if params.mode == "today":
            groups = [[c for c in pool if c.reviewed], [c for c in pool if not c.reviewed]]
        else:
            groups = [pool]
        ordered = []
        for group in groups:
            self.rng.shuffle(group)
            ordered.extend(group)
        return [[c.entry_id, c.direction] for c in ordered]

    def count(self, index: Any, params: SessionParams, now: dt.datetime | None = None) -> int:
        return len(self.queue(index, params, now))

    # --- сеанс -------------------------------------------------------------------------------

    def start(self, index: Any, params: SessionParams, now: dt.datetime | None = None) -> str:
        queue = self.queue(index, params, now)
        portion = params.portion or len(queue)
        state = {"params": asdict(params), "portion_size": portion, "portion_end": portion}
        session_id = secrets.token_hex(6)
        with self.db.lock, self.db.conn:
            self.db.conn.execute(
                "insert into sessions (id, params, queue, position, created_at) "
                "values (?, ?, ?, 0, ?)",
                (session_id, json.dumps(state), json.dumps(queue), (now or _now()).isoformat()),
            )
        return session_id

    def _load(self, session_id: str) -> tuple[dict, list, int, int | None]:
        with self.db.lock:
            row = self.db.conn.execute(
                "select * from sessions where id = ?", (session_id,)
            ).fetchone()
        if row is None:
            raise KeyError(session_id)
        return (
            json.loads(row["params"]),
            json.loads(row["queue"]),
            row["position"],
            row["last_review_id"],
        )

    def _save(
        self, session_id: str, state: dict, position: int, last_review_id: int | None
    ) -> None:
        with self.db.lock, self.db.conn:
            self.db.conn.execute(
                "update sessions set params = ?, position = ?, last_review_id = ? where id = ?",
                (json.dumps(state), position, last_review_id, session_id),
            )

    def params(self, session_id: str) -> SessionParams:
        return SessionParams(**self._load(session_id)[0]["params"])

    def progress(self, session_id: str) -> Progress:
        state, queue, position, _ = self._load(session_id)
        return Progress(
            position, len(queue), state["portion_size"], min(state["portion_end"], len(queue))
        )

    def current(self, session_id: str) -> tuple[str, str] | None:
        _state, queue, position, _ = self._load(session_id)
        progress = self.progress(session_id)
        if progress.finished or progress.portion_finished:
            return None
        return tuple(queue[position])

    def rate(
        self,
        session_id: str,
        rating: str,
        *,
        answer: str | None = None,
        now: dt.datetime | None = None,
    ) -> int:
        state, _queue, position, _ = self._load(session_id)
        card = self.current(session_id)
        if card is None:
            raise ValueError("в сеансе нет текущей карточки")
        params = state["params"]
        review_id = self.cards.rate(
            card[0],
            card[1],
            rating,
            mode=params["mode"],
            method=params["method"],
            answer=answer,
            session_id=session_id,
            now=now,
        )
        self._save(session_id, state, position + 1, review_id)
        return review_id

    def undo(self, session_id: str) -> tuple[str, str] | None:
        state, _queue, position, last_review_id = self._load(session_id)
        if last_review_id is None:
            return None
        card = self.cards.undo(last_review_id)
        self._save(session_id, state, max(position - 1, 0), None)
        return card

    def continue_portion(self, session_id: str) -> None:
        state, _queue, position, last_review_id = self._load(session_id)
        state["portion_end"] = position + state["portion_size"]
        self._save(session_id, state, position, last_review_id)

    def summary(self, session_id: str) -> dict[str, int]:
        with self.db.lock:
            rows = self.db.conn.execute(
                "select rating, count(*) as n from reviews where session_id = ? group by rating",
                (session_id,),
            ).fetchall()
        return {row["rating"]: row["n"] for row in rows}
