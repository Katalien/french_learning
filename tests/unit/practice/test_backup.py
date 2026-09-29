"""Резервная копия прогресса (FR-053, FR-053a; SC-006; research R1)."""

import datetime as dt
import subprocess
from pathlib import Path

import pytest

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content
from french_learning.practice import backup
from french_learning.practice.db import ProgressDB
from french_learning.vocab.cards import CardStore

NOW = dt.datetime(2026, 9, 27, 10, tzinfo=dt.UTC)


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout


@pytest.fixture
def repo(clean_content_root: Path) -> Path:
    git(clean_content_root, "init", "-q")
    git(clean_content_root, "add", "-A")
    git(clean_content_root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    return clean_content_root


@pytest.fixture
def db_with_reviews(repo: Path):
    db = ProgressDB(repo)
    cards = CardStore(db, fuzzing=False)
    cards.sync(ContentIndex(load_content(repo)), now=NOW)
    cards.rate("voc-maisonaa", "fr_ru", "good", mode="today", method="self", now=NOW)
    cards.rate("voc-painaaaa", "fr_ru", "again", mode="today", method="input", answer="x", now=NOW)
    yield db
    db.close()


def test_backup_writes_dump_and_commits(repo: Path, db_with_reviews):
    result = backup.run_backup(db_with_reviews, repo, today=dt.date(2026, 9, 27))
    dump = (repo / "backups/progress.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE" in dump and "voc-maisonaa" in dump
    assert result.committed
    assert git(repo, "log", "-1", "--format=%s").strip() == "Резервная копия прогресса 2026-09-27"
    assert ".progress" not in git(repo, "ls-files")


def test_restore_without_loss(repo: Path, db_with_reviews):
    backup.run_backup(db_with_reviews, repo, today=dt.date(2026, 9, 27))
    before = [tuple(r) for r in db_with_reviews.conn.execute("select * from reviews order by id")]
    db_with_reviews.close()
    (repo / ".progress/progress.sqlite").unlink()

    backup.restore(repo)
    restored = ProgressDB(repo)
    after = [tuple(r) for r in restored.conn.execute("select * from reviews order by id")]
    assert after == before
    restored.close()


def test_daily_backup_once_per_day(repo: Path, db_with_reviews):
    day = dt.date(2026, 9, 27)
    assert backup.backup_due(db_with_reviews, day)
    backup.run_backup(db_with_reviews, repo, today=day)
    assert not backup.backup_due(db_with_reviews, day)
    assert backup.backup_due(db_with_reviews, day + dt.timedelta(days=1))


def test_failed_push_keeps_last_pushed_date(repo: Path, db_with_reviews):
    result = backup.run_backup(db_with_reviews, repo, today=dt.date(2026, 9, 27))
    assert not result.pushed  # у тестового репозитория нет удалённого
    assert db_with_reviews.get_meta("last_backup_pushed") is None
    assert db_with_reviews.get_meta("last_backup_date") == "2026-09-27"


def test_no_changes_no_empty_commit(repo: Path, db_with_reviews):
    backup.run_backup(db_with_reviews, repo, today=dt.date(2026, 9, 27))
    count = len(git(repo, "log", "--format=%s").splitlines())
    backup.run_backup(db_with_reviews, repo, today=dt.date(2026, 9, 28))
    assert len(git(repo, "log", "--format=%s").splitlines()) == count


def test_start_daily_backup_runs_in_background(repo: Path, db_with_reviews, monkeypatch):
    calls = []
    monkeypatch.setattr(backup, "run_backup", lambda db, root, today: calls.append(today))
    thread = backup.start_daily_backup(db_with_reviews, repo, today=dt.date(2026, 9, 27))
    thread.join(timeout=5)
    assert calls == [dt.date(2026, 9, 27)]
    assert backup.start_daily_backup(db_with_reviews, repo, today=dt.date(2026, 9, 27)) is None


def test_notes_survive_dump_and_restore(clean_content_root: Path, tmp_path: Path):
    """Заметки с привязкой к фрагменту попадают в копию и восстанавливаются (005, SC-004)."""
    from french_learning.notes.store import Anchor, NoteStore

    db = ProgressDB(clean_content_root)
    index = ContentIndex(load_content(clean_content_root))
    anchor = Anchor(exact="un café", prefix="commande ", suffix=" et", start=40)
    note = NoteStore(db).create(
        index, kind="question", body="почему «un café»?", element_id="tx-aucafeaa", anchor=anchor
    )
    text = backup.dump(db)
    db.close()
    assert "CREATE TABLE notes" in text or 'CREATE TABLE "notes"' in text
    source = tmp_path / "progress.sql"
    source.write_text(text, encoding="utf-8")
    backup.restore(clean_content_root, source)
    db = ProgressDB(clean_content_root)
    restored = NoteStore(db).get(note.id)
    assert restored == note and restored.anchor == anchor
    db.close()
