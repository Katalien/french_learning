"""Запас полученных переводов — таблица `translations` базы прогресса (006, research R4, FR-009).

Одна запись на нормализованный фрагмент и направление; повторное выделение берёт перевод
отсюда, без обращения к сервису. Ошибки сервиса сюда не пишутся.
"""

from __future__ import annotations

from datetime import datetime

from french_learning.practice.db import ProgressDB
from french_learning.translate.normalize import normalize_key

DIRECTION = "fr-ru"


class TranslationCache:
    def __init__(self, db: ProgressDB) -> None:
        self.db = db

    def get(self, text: str) -> tuple[str, str] | None:
        """(перевод, сервис) или None."""
        with self.db.lock:
            row = self.db.conn.execute(
                "select text, service from translations where key = ? and direction = ?",
                (normalize_key(text), DIRECTION),
            ).fetchone()
        return (row["text"], row["service"]) if row else None

    def put(self, text: str, translation: str, service: str) -> None:
        with self.db.lock, self.db.conn:
            self.db.conn.execute(
                "insert or ignore into translations values (?, ?, ?, ?, ?)",
                (
                    normalize_key(text),
                    DIRECTION,
                    translation,
                    service,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )

    def count(self) -> int:
        with self.db.lock:
            return self.db.conn.execute("select count(*) from translations").fetchone()[0]

    def clear(self) -> int:
        with self.db.lock, self.db.conn:
            return self.db.conn.execute("delete from translations").rowcount
