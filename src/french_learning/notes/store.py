"""Заметки: пометки и вопросы к уроку, элементу урока или фрагменту (data-model 005).

Заметки — личные данные пользователя: хранятся в базе прогресса (таблица `notes`, схема v3)
и попадают в её резервную копию. Урок и название элемента берутся из индекса контента,
а не от клиента; название запоминается, чтобы заметка пропавшего элемента осталась понятной.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass
from typing import Any

from french_learning.practice.db import ProgressDB

KINDS = ("note", "question")
MAX_BODY = 2000
MAX_EXACT = 500
MAX_CONTEXT = 32
_UNSET: Any = object()


class NoteError(ValueError):
    """Нарушено правило заметки (API отвечает 422)."""


@dataclass(frozen=True)
class Anchor:
    """Привязка к фрагменту: цитата с контекстом и подсказка по позиции (research R2)."""

    exact: str
    prefix: str = ""
    suffix: str = ""
    start: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Anchor:
        try:
            anchor = cls(
                exact=str(data["exact"]),
                prefix=str(data.get("prefix", "")),
                suffix=str(data.get("suffix", "")),
                start=int(data.get("start", 0)),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise NoteError("неверная привязка к фрагменту") from error
        anchor.check()
        return anchor

    def check(self) -> None:
        if not self.exact.strip() or len(self.exact) > MAX_EXACT:
            raise NoteError("фрагмент пустой или слишком длинный")
        if len(self.prefix) > MAX_CONTEXT or len(self.suffix) > MAX_CONTEXT or self.start < 0:
            raise NoteError("неверная привязка к фрагменту")


@dataclass(frozen=True)
class Note:
    id: int
    kind: str
    body: str
    important: bool
    answered: bool
    answer: str | None
    lesson: int
    element_id: str | None
    element_title: str | None
    anchor: Anchor | None
    created_at: str
    updated_at: str

    @property
    def origin(self) -> str:
        return "user"  # принцип I: заметки всегда пишет пользователь

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["origin"] = self.origin
        return data


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _body(text: Any) -> str:
    body = str(text or "").strip()
    if not body:
        raise NoteError("текст заметки пустой")
    if len(body) > MAX_BODY:
        raise NoteError(f"заметка длиннее {MAX_BODY} символов")
    return body


def _kind(kind: Any) -> str:
    if kind not in KINDS:
        raise NoteError("вид заметки — пометка или вопрос")
    return kind


def _element_title(element: Any) -> str:
    return element.description_ru if element.kind == "exercise" else element.title


class NoteStore:
    def __init__(self, db: ProgressDB) -> None:
        self.db = db

    # --- чтение ------------------------------------------------------------------------------

    def _note(self, row: Any) -> Note:
        anchor = Anchor(**json.loads(row["anchor"])) if row["anchor"] else None
        return Note(
            id=row["id"],
            kind=row["kind"],
            body=row["body"],
            important=bool(row["important"]),
            answered=bool(row["answered"]),
            answer=row["answer"],
            lesson=row["lesson"],
            element_id=row["element_id"],
            element_title=row["element_title"],
            anchor=anchor,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _select(self, where: str = "1", params: tuple = (), order: str = "id") -> list[Note]:
        with self.db.lock:
            rows = self.db.conn.execute(
                f"select * from notes where {where} order by {order}", params
            ).fetchall()
        return [self._note(row) for row in rows]

    def get(self, note_id: int) -> Note | None:
        found = self._select("id = ?", (note_id,))
        return found[0] if found else None

    def for_elements(self, element_ids: list[str]) -> list[Note]:
        if not element_ids:
            return []
        marks = ", ".join("?" * len(element_ids))
        return self._select(f"element_id in ({marks})", tuple(element_ids))

    def for_lesson(self, lesson: int) -> list[Note]:
        return self._select("lesson = ?", (lesson,))

    def open_questions(self) -> list[Note]:
        """Открытые вопросы всех уроков: сначала новые уроки, внутри — по времени создания."""
        return self._select("kind = 'question' and answered = 0", order="lesson desc, id")

    def open_questions_count(self) -> int:
        with self.db.lock:
            row = self.db.conn.execute(
                "select count(*) from notes where kind = 'question' and answered = 0"
            ).fetchone()
        return row[0]

    def lesson_counts(self) -> dict[int, int]:
        with self.db.lock:
            rows = self.db.conn.execute(
                "select lesson, count(*) from notes group by lesson"
            ).fetchall()
        return {row[0]: row[1] for row in rows}

    # --- изменения ---------------------------------------------------------------------------

    def _target(
        self, index: Any, lesson: int | None, element_id: str | None
    ) -> tuple[int, str | None]:
        """Урок и название элемента; заметки есть только у элементов уроков и у уроков."""
        if element_id is not None:
            element = index.element(element_id)
            if element is None or element.kind not in ("theory", "text", "exercise"):
                raise NoteError("элемент не найден")
            if element.lesson is None:
                raise NoteError("заметки есть только у элементов уроков")
            return element.lesson, _element_title(element)
        if lesson is None:
            raise NoteError("укажите урок или элемент")
        if index.lesson(lesson) is None:
            raise NoteError(f"урок {lesson} не найден")
        return lesson, None

    def create(
        self,
        index: Any,
        *,
        kind: str,
        body: str,
        important: bool = False,
        lesson: int | None = None,
        element_id: str | None = None,
        anchor: Anchor | None = None,
    ) -> Note:
        kind, body = _kind(kind), _body(body)
        if anchor is not None:
            if element_id is None:
                raise NoteError("фрагмент можно отметить только в элементе урока")
            anchor.check()
        lesson, title = self._target(index, lesson, element_id)
        now = _now()
        with self.db.lock, self.db.conn:
            cursor = self.db.conn.execute(
                "insert into notes (kind, body, important, lesson, element_id, element_title, "
                "anchor, created_at, updated_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    kind,
                    body,
                    int(bool(important)),
                    lesson,
                    element_id,
                    title,
                    json.dumps(asdict(anchor), ensure_ascii=False) if anchor else None,
                    now,
                    now,
                ),
            )
        return self.get(cursor.lastrowid)  # type: ignore[return-value]

    def update(
        self,
        index: Any,
        note_id: int,
        *,
        body: Any = _UNSET,
        kind: Any = _UNSET,
        important: Any = _UNSET,
        answered: Any = _UNSET,
        answer: Any = _UNSET,
        anchor: Any = _UNSET,
    ) -> Note:
        note = self.get(note_id)
        if note is None:
            raise LookupError(f"заметка {note_id} не найдена")
        values = {
            "kind": note.kind,
            "body": note.body,
            "important": note.important,
            "answered": note.answered,
            "answer": note.answer,
            "anchor": note.anchor,
        }
        if kind is not _UNSET and kind != note.kind:
            values["kind"] = _kind(kind)
            values["answered"] = False  # смена вида: вопрос снова открыт, пометка не «отвечена»
        if body is not _UNSET:
            values["body"] = _body(body)
        if important is not _UNSET:
            values["important"] = bool(important)
        if answered is not _UNSET or answer is not _UNSET:
            if values["kind"] != "question":
                raise NoteError("ответ бывает только у вопроса")
            if answer is not _UNSET:
                text = str(answer or "").strip()
                values["answer"] = text or None
                if text:
                    values["answered"] = True  # записан ответ — вопрос закрыт (FR-006)
            if answered is not _UNSET:
                values["answered"] = bool(answered)
        if anchor is not _UNSET:
            if anchor is not None:
                if note.element_id is None:
                    raise NoteError("фрагмент можно отметить только в элементе урока")
                anchor.check()
            values["anchor"] = anchor
        with self.db.lock, self.db.conn:
            self.db.conn.execute(
                "update notes set kind = ?, body = ?, important = ?, answered = ?, answer = ?, "
                "anchor = ?, updated_at = ? where id = ?",
                (
                    values["kind"],
                    values["body"],
                    int(values["important"]),
                    int(values["answered"]),
                    values["answer"],
                    json.dumps(asdict(values["anchor"]), ensure_ascii=False)
                    if values["anchor"]
                    else None,
                    _now(),
                    note_id,
                ),
            )
        return self.get(note_id)  # type: ignore[return-value]

    def delete(self, note_id: int) -> bool:
        with self.db.lock, self.db.conn:
            cursor = self.db.conn.execute("delete from notes where id = ?", (note_id,))
        return cursor.rowcount > 0
