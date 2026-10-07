"""База прогресса: SQLite в `CONTENT_DIR/.progress/progress.sqlite` (data-model 003 и 004).

Версия 2 (004) добавляет попытки упражнений и тренажёры, версия 3 (005) — заметки,
версия 4 (006) — запас переводов;
миграции — только новые таблицы.

Папка `.progress/` исключена из git хранилища; резервная копия — `backups/progress.sql`
(см. `practice/backup.py`).
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from french_learning.agent.storage import ensure_progress_ignored

SCHEMA_VERSION = 5

DEFAULT_SETTINGS = {
    "portion_size": "20",
    "directions": "staged",
    "voice": "siwis",
    "trainer_portion_size": "20",
    "exercise_list_view": "rows",
    "translator": "mymemory",
    "search_translations": "1",
}

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
create table if not exists exercise_attempts (
    id integer primary key autoincrement,
    exercise_id text not null,
    scope text not null,
    item_ids text not null,
    status text not null,
    answers text not null default '{}',
    first_results text not null default '{}',
    current_results text not null default '{}',
    marks text not null default '{}',
    created_at text not null,
    checked_at text,
    updated_at text not null
);
create index if not exists attempts_exercise on exercise_attempts (exercise_id, id);
create table if not exists trainer_cards (
    trainer_id text not null,
    key text not null,
    fsrs text not null,
    due text not null,
    created_at text not null,
    primary key (trainer_id, key)
);
create table if not exists trainer_answers (
    id integer primary key autoincrement,
    trainer_id text not null,
    key text not null,
    answer text,
    correct integer not null,
    revealed integer not null default 0,
    answered_at text not null,
    session_id text
);
create index if not exists trainer_answers_key on trainer_answers (trainer_id, key, id);
-- v5 (011): «Ошибка в роде» ставит вопросы слова в начало тренажёра «Артикли»
create table if not exists trainer_priority (
    trainer_id text not null,
    key text not null,
    review_id integer,
    created_at text not null,
    primary key (trainer_id, key)
);
create table if not exists notes (
    id integer primary key autoincrement,
    kind text not null check (kind in ('note', 'question')),
    body text not null check (length(trim(body)) > 0),
    important integer not null default 0,
    answered integer not null default 0,
    answer text,
    lesson integer not null,
    element_id text,
    element_title text,
    anchor text,
    created_at text not null,
    updated_at text not null
);
create index if not exists notes_lesson on notes (lesson, element_id);
create index if not exists notes_open_questions on notes (kind, answered);
create table if not exists trainer_sessions (
    id text primary key,
    trainer_id text not null,
    params text not null,
    queue text not null,
    position integer not null default 0,
    correct integer not null default 0,
    created_at text not null
);
create table if not exists translations (
    key text not null,
    direction text not null,
    text text not null,
    service text not null,
    created_at text not null,
    primary key (key, direction)
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
            # таблицы всех версий создаются выше; версия — для будущих миграций с изменениями
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
