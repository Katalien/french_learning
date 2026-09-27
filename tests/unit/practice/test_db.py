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


def test_migration_v1_to_v2_keeps_data(clean_content_root: Path):
    folder = clean_content_root / ".progress"
    folder.mkdir()
    with sqlite3.connect(folder / "progress.sqlite") as conn:
        conn.executescript(
            "create table meta (key text primary key, value text);"
            "create table settings (key text primary key, value text);"
            "insert into meta values ('schema_version', '1');"
            "insert into settings values ('portion_size', '35');"
        )
    db = ProgressDB(clean_content_root)
    assert {"exercise_attempts", "trainer_cards", "trainer_answers", "trainer_sessions"} <= tables(
        db.path
    )
    assert db.get_meta("schema_version") == "2" == str(SCHEMA_VERSION)
    assert db.get_setting("portion_size") == "35"
    assert db.get_setting("trainer_portion_size") == "20"
    db.close()


def test_backup_dump_includes_new_tables(clean_content_root: Path):
    from french_learning.practice.backup import dump

    db = ProgressDB(clean_content_root)
    assert "exercise_attempts" in dump(db)
    db.close()
