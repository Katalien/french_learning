"""База прогресса: SQLite в `CONTENT_DIR/.progress/progress.sqlite` (data-model 003).

Папка `.progress/` исключена из git хранилища; резервная копия — `backups/progress.sql`
(см. `practice/backup.py`).
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from french_learning.agent.storage import ensure_progress_ignored

SCHEMA_VERSION = 1

DEFAULT_SETTINGS = {"portion_size": "20", "directions": "staged"}

_SCHEMA = """
create table if not exists meta (key text primary key, value text);
create table if not exists settings (key text primary key, value text);
create table if not exists cards (
    entry_id text not null,
    direction text not null,
    fsrs text not null,
    due text not null,
    suspended integer not null default 0,
    created_at text not null,
    primary key (entry_id, direction)
);
create table if not exists reviews (
    id integer primary key autoincrement,
    entry_id text not null,
    direction text not null,
    rating text not null,
    method text not null,
    mode text not null,
    answer text,
    reviewed_at text not null,
    session_id text,
    prev_fsrs text not null
);
create index if not exists reviews_entry on reviews (entry_id, reviewed_at);
create table if not exists sessions (
    id text primary key,
    params text not null,
    queue text not null,
    position integer not null default 0,
    created_at text not null,
    last_review_id integer
);
"""


class ProgressDB:
    def __init__(self, content_dir: Path) -> None:
        folder = content_dir / ".progress"
        folder.mkdir(parents=True, exist_ok=True)
        ensure_progress_ignored(content_dir)
        self.path = folder / "progress.sqlite"
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        with self.lock, self.conn:
            self.conn.executescript(_SCHEMA)
            if self.get_meta("schema_version") is None:
                self.set_meta("schema_version", str(SCHEMA_VERSION))
            for key, value in DEFAULT_SETTINGS.items():
                self.conn.execute(
                    "insert or ignore into settings (key, value) values (?, ?)", (key, value)
                )

    def _get(self, table: str, key: str) -> str | None:
        with self.lock:
            row = self.conn.execute(f"select value from {table} where key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def _set(self, table: str, key: str, value: str) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                f"insert into {table} (key, value) values (?, ?) "
                "on conflict(key) do update set value = excluded.value",
                (key, value),
            )

    def get_meta(self, key: str) -> str | None:
        return self._get("meta", key)

    def set_meta(self, key: str, value: str) -> None:
        self._set("meta", key, value)

    def get_setting(self, key: str) -> str | None:
        return self._get("settings", key) or DEFAULT_SETTINGS.get(key)

    def set_setting(self, key: str, value: str) -> None:
        self._set("settings", key, value)

    def close(self) -> None:
        with self.lock:
            self.conn.close()
