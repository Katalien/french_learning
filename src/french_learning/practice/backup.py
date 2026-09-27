"""Резервная копия прогресса (FR-053, FR-053a; research R1 функции 003).

Текстовый SQL-дамп `backups/progress.sql` в приватном хранилище: коммит и отправка на GitHub
раз в день (в фоне, при первом запросе дня) и по кнопке. Версии копии — история git файла.
Нет сети — копия сохраняется локальным коммитом, дата последней успешной отправки
не меняется, работа приложения не блокируется.
"""

from __future__ import annotations

import datetime as dt
import threading
from pathlib import Path

from french_learning.content.writer import ContentWriter, WriteResult
from french_learning.practice.db import ProgressDB

BACKUP_PATH = "backups/progress.sql"
_started: set[tuple[str, str]] = set()
_started_lock = threading.Lock()


def dump(db: ProgressDB) -> str:
    """SQL-дамп без служебных дат копии (иначе копия менялась бы при каждом запуске)."""
    with db.lock:
        lines = [
            line
            for line in db.conn.iterdump()
            if not (line.startswith('INSERT INTO "meta"') and "'last_backup_" in line)
        ]
    return "\n".join(lines) + "\n"


def backup_due(db: ProgressDB, today: dt.date) -> bool:
    return db.get_meta("last_backup_date") != today.isoformat()


def run_backup(db: ProgressDB, content_dir: Path, today: dt.date | None = None) -> WriteResult:
    today = today or dt.date.today()
    target = content_dir / BACKUP_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    text = dump(db)
    changed = not target.exists() or target.read_text(encoding="utf-8") != text
    if changed:
        target.write_text(text, encoding="utf-8", newline="\n")
        result = ContentWriter(content_dir).commit_paths(
            [BACKUP_PATH, ".gitignore"], f"Резервная копия прогресса {today.isoformat()}"
        )
    else:
        result = WriteResult(committed=False, pushed=False, warning=None)
    db.set_meta("last_backup_date", today.isoformat())
    if result.pushed:
        db.set_meta("last_backup_pushed", today.isoformat())
    return result


def start_daily_backup(
    db: ProgressDB, content_dir: Path, today: dt.date | None = None
) -> threading.Thread | None:
    """Запустить ежедневную копию в фоне, если сегодня её ещё не было."""
    today = today or dt.date.today()
    key = (str(content_dir), today.isoformat())
    with _started_lock:
        if key in _started or not backup_due(db, today):
            return None
        _started.add(key)
    thread = threading.Thread(target=run_backup, args=(db, content_dir, today), daemon=True)
    thread.start()
    return thread


def restore(content_dir: Path, source: Path | None = None) -> Path:
    """Восстановить базу прогресса из дампа; прежний файл сохраняется рядом с суффиксом .bak."""
    import sqlite3

    source = source or content_dir / BACKUP_PATH
    database = content_dir / ".progress" / "progress.sqlite"
    database.parent.mkdir(parents=True, exist_ok=True)
    if database.exists():
        database.replace(database.with_suffix(".sqlite.bak"))
    conn = sqlite3.connect(database)
    try:
        conn.executescript(source.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
    return database
