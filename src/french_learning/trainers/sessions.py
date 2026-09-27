"""Подход к тренажёру порциями по N заданий (FR-045a; data-model `trainer_sessions`).

Сеанс хранит очередь ключей текущей порции, позицию и число верных. «Продолжить» строит
следующую порцию без уже заданных в этом подходе вопросов. Ответы пишутся сразу, поэтому
остановиться можно в любой момент.
"""

from __future__ import annotations

import datetime as dt
import json
import secrets
from typing import Any

from french_learning.practice.db import ProgressDB
from french_learning.trainers.schedule import TrainerSchedule


class TrainerSessions:
    def __init__(self, db: ProgressDB, schedule: TrainerSchedule) -> None:
        self.db = db
        self.schedule = schedule

    def portion_size(self) -> int:
        value = self.db.get_setting("trainer_portion_size") or "20"
        return int(value) if value.isdigit() and int(value) > 0 else 20

    def _load(self, session_id: str) -> dict[str, Any]:
        with self.db.lock:
            row = self.db.conn.execute(
                "select * from trainer_sessions where id = ?", (session_id,)
            ).fetchone()
        if row is None:
            raise KeyError(session_id)
        return {
            "trainer_id": row["trainer_id"],
            "params": json.loads(row["params"]),
            "queue": json.loads(row["queue"]),
            "position": row["position"],
            "correct": row["correct"],
        }

    def _save(self, session_id: str, state: dict[str, Any]) -> None:
        with self.db.lock, self.db.conn:
            self.db.conn.execute(
                "update trainer_sessions set params = ?, queue = ?, position = ?, correct = ? "
                "where id = ?",
                (
                    json.dumps(state["params"], ensure_ascii=False),
                    json.dumps(state["queue"]),
                    state["position"],
                    state["correct"],
                    session_id,
                ),
            )

    def _portion(self, trainer_id: str, params: dict, keys: list[str]) -> list[str]:
        exclude = set(params.get("seen", []))
        if params.get("pool"):  # задания от агента: по порядку пула, без расписания
            return [k for k in keys if k not in exclude][: self.portion_size()]
        return self.schedule.select(trainer_id, keys, self.portion_size(), exclude=exclude)

    def start(self, trainer_id: str, params: dict, keys: list[str]) -> str:
        session_id = secrets.token_urlsafe(8)
        params = {**params, "seen": []}
        queue = self._portion(trainer_id, params, keys)
        with self.db.lock, self.db.conn:
            self.db.conn.execute(
                "insert into trainer_sessions (id, trainer_id, params, queue, created_at) "
                "values (?, ?, ?, ?, ?)",
                (
                    session_id,
                    trainer_id,
                    json.dumps(params, ensure_ascii=False),
                    json.dumps(queue),
                    dt.datetime.now(dt.UTC).isoformat(),
                ),
            )
        return session_id

    def trainer_id(self, session_id: str) -> str:
        return self._load(session_id)["trainer_id"]

    def params(self, session_id: str) -> dict:
        return self._load(session_id)["params"]

    def queue(self, session_id: str) -> list[str]:
        return self._load(session_id)["queue"]

    def seen(self, session_id: str) -> list[str]:
        state = self._load(session_id)
        return state["params"]["seen"] + state["queue"][: state["position"]]

    def current(self, session_id: str) -> str | None:
        state = self._load(session_id)
        queue, position = state["queue"], state["position"]
        return queue[position] if position < len(queue) else None

    def progress(self, session_id: str) -> tuple[int, int, int]:
        """(отвечено, в порции, верных)."""
        state = self._load(session_id)
        return state["position"], len(state["queue"]), state["correct"]

    def record(
        self,
        session_id: str,
        key: str,
        *,
        correct: bool,
        answer: str | None = None,
        revealed: bool = False,
        srs: bool = True,
    ) -> None:
        state = self._load(session_id)
        if self.current(session_id) != key:
            return  # повторная отправка той же формы
        self.schedule.answer(
            state["trainer_id"],
            key,
            correct=correct,
            answer=answer,
            revealed=revealed,
            session_id=session_id,
            srs=srs,
        )
        state["position"] += 1
        state["correct"] += int(correct and not revealed)
        self._save(session_id, state)

    def continue_with(self, session_id: str, keys: list[str]) -> None:
        state = self._load(session_id)
        state["params"]["seen"] = self.seen(session_id)
        state["queue"] = self._portion(state["trainer_id"], state["params"], keys)
        state["position"] = state["correct"] = 0
        self._save(session_id, state)
