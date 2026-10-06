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
    assert db.get_meta("schema_version") == str(SCHEMA_VERSION)
    assert db.get_setting("portion_size") == "35"
    assert db.get_setting("trainer_portion_size") == "20"
    db.close()


def test_backup_dump_includes_new_tables(clean_content_root: Path):
    from french_learning.practice.backup import dump

    db = ProgressDB(clean_content_root)
    assert "exercise_attempts" in dump(db)
    db.close()


def index_names(path: Path) -> set[str]:
    with sqlite3.connect(path) as conn:
        return {row[0] for row in conn.execute("select name from sqlite_master where type='index'")}


def test_schema_v3_has_notes(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    assert "notes" in tables(db.path)
    assert {"notes_lesson", "notes_open_questions"} <= index_names(db.path)
    db.close()


def test_migration_v2_to_v3_keeps_data(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    with db.lock, db.conn:
        db.conn.execute("drop table notes")
        db.conn.execute(
            "insert into cards values ('vc-maison', 'fr_ru', '{}', '2026-09-29', 0, '2026-09-01')"
        )
    db.set_meta("schema_version", "2")
    db.close()
    db = ProgressDB(clean_content_root)
    assert db.get_meta("schema_version") == str(SCHEMA_VERSION)
    assert "notes" in tables(db.path)
    assert db.conn.execute("select count(*) from cards").fetchone()[0] == 1
    db.close()


def test_notes_reject_empty_body_and_unknown_kind(clean_content_root: Path):
    import pytest

    db = ProgressDB(clean_content_root)
    insert = (
        "insert into notes (kind, body, lesson, created_at, updated_at) values (?, ?, 1, 'x', 'x')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute(insert, ("note", "   "))
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute(insert, ("todo", "текст"))
    db.close()


# --- 006: запас переводов, схема 4 -------------------------------------------------------------


def test_schema_v4_has_translations_and_translator_setting(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    assert SCHEMA_VERSION >= 4
    assert "translations" in tables(db.path)
    assert db.get_setting("translator") == "mymemory"
    assert not db.get_setting("mymemory_email")
    db.close()


def test_translations_one_row_per_key_and_direction(clean_content_root: Path):
    import pytest

    db = ProgressDB(clean_content_root)
    insert = "insert into translations values (?, 'fr-ru', ?, 'mymemory', '2026-09-30')"
    db.conn.execute(insert, ("pomme", "яблоко"))
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute(insert, ("pomme", "яблоко 2"))
    db.close()


def test_migration_v3_to_v4_keeps_notes_and_cards(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    with db.lock, db.conn:
        db.conn.execute("drop table translations")
        db.conn.execute(
            "insert into cards values ('vc-maison', 'fr_ru', '{}', '2026-09-29', 0, '2026-09-01')"
        )
        db.conn.execute(
            "insert into notes (kind, body, lesson, created_at, updated_at) "
            "values ('note', 'être', 1, 'x', 'x')"
        )
    db.set_meta("schema_version", "3")
    db.close()
    db = ProgressDB(clean_content_root)
    assert db.get_meta("schema_version") == str(SCHEMA_VERSION)
    assert "translations" in tables(db.path)
    assert db.conn.execute("select count(*) from cards").fetchone()[0] == 1
    assert db.conn.execute("select count(*) from notes").fetchone()[0] == 1
    db.close()


def test_schema_v5_trainer_priority(clean_content_root: Path):
    """011: приоритет вопросов тренажёра («Ошибка в артикле»); старая база получает таблицу."""
    db = ProgressDB(clean_content_root)
    db.set_setting("portion_size", "35")
    db.close()
    path = clean_content_root / ".progress" / "progress.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("drop table if exists trainer_priority")
    db = ProgressDB(clean_content_root)
    assert "trainer_priority" in tables(path)
    assert SCHEMA_VERSION == 5
    assert db.get_setting("portion_size") == "35"
    with db.lock, db.conn:
        db.conn.execute(
            "insert into trainer_priority (trainer_id, key, review_id, created_at) "
            "values (?, ?, ?, ?)",
            ("articles", "articles:x:def", 1, "2026-10-07"),
        )
        try:
            db.conn.execute(
                "insert into trainer_priority (trainer_id, key, review_id, created_at) "
                "values (?,?,?,?)",
                ("articles", "articles:x:def", 2, "2026-10-08"),
            )
            raise AssertionError("ключ должен быть уникальным")
        except sqlite3.IntegrityError:
            pass
    db.close()
