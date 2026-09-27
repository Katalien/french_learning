"""База прогресса (data-model 003)."""

import sqlite3
from pathlib import Path

from french_learning.practice.db import SCHEMA_VERSION, ProgressDB


def tables(path: Path) -> set[str]:
    with sqlite3.connect(path) as conn:
        return {row[0] for row in conn.execute("select name from sqlite_master where type='table'")}


def test_created_in_progress_folder_with_schema(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    path = clean_content_root / ".progress" / "progress.sqlite"
    assert path.exists()
    assert {"meta", "settings", "cards", "reviews", "sessions"} <= tables(path)
    assert db.get_meta("schema_version") == str(SCHEMA_VERSION)
    db.close()


def test_default_settings(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    assert db.get_setting("portion_size") == "20"
    assert db.get_setting("directions") == "staged"
    db.close()


def test_reopen_keeps_data(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    db.set_setting("portion_size", "35")
    db.close()
    db = ProgressDB(clean_content_root)
    assert db.get_setting("portion_size") == "35"
    db.close()


def test_progress_folder_ignored_by_storage_git(clean_content_root: Path):
    ProgressDB(clean_content_root).close()
    assert ".progress/" in (clean_content_root / ".gitignore").read_text(encoding="utf-8")
