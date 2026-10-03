"""Правки контента из интерфейса: атомарная запись, git-коммит, отправка (research R2)."""

import datetime as dt
import subprocess
from pathlib import Path

import pytest
import yaml

from french_learning.content.loader import load_content
from french_learning.content.writer import ContentWriter, WriteError


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    ).stdout


@pytest.fixture
def repo(clean_content_root: Path) -> Path:
    git(clean_content_root, "init", "-q")
    git(clean_content_root, "add", "-A")
    git(clean_content_root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    return clean_content_root


def commits(root: Path) -> list[str]:
    return git(root, "log", "--format=%s").splitlines()


def writer(root: Path) -> ContentWriter:
    return ContentWriter(root, author=("test", "test@localhost"))


def test_set_lesson_date_commits(repo: Path):
    result = writer(repo).set_lesson_date(2, dt.date(2026, 9, 8))
    assert load_content(repo).lessons[2].date == dt.date(2026, 9, 8)
    assert result.committed
    assert commits(repo)[0] == "Урок 2: дата 2026-09-08"


def test_clear_lesson_date(repo: Path):
    writer(repo).set_lesson_date(1, None)
    assert load_content(repo).lessons[1].date is None


def test_set_element_topics_existing_and_new(repo: Path):
    w = writer(repo)
    w.set_element_topics("ex-gapinput", ["top-articles"], new_topic=("Спряжение", "grammar"))
    content = load_content(repo)
    topics = {t.name: t.id for t in content.topics.topics}
    assert set(content.elements["ex-gapinput"].topics) == {"top-articles", topics["Спряжение"]}
    assert content.errors == []


def test_markdown_topics_keep_body(repo: Path):
    writer(repo).set_element_topics("th-articles", ["top-etreverb"])
    theory = load_content(repo).elements["th-articles"]
    assert theory.topics == ["top-etreverb"]
    assert "| ед. ч. |" in theory.body


def test_new_topic_name_must_be_unique_case_insensitive(repo: Path):
    with pytest.raises(WriteError, match="уже есть"):
        writer(repo).create_topic("артикли", "grammar")


def test_rename_topic_changes_only_topics_file(repo: Path):
    writer(repo).rename_topic("top-articles", "Определённые артикли")
    changed = git(repo, "show", "--name-only", "--format=", "HEAD").split()
    assert changed == ["topics.yaml"]
    names = {t.id: t.name for t in load_content(repo).topics.topics}
    assert names["top-articles"] == "Определённые артикли"


def test_merge_topics_replaces_references_and_removes_source(repo: Path):
    writer(repo).merge_topics("top-nasalson", "top-articles")
    content = load_content(repo)
    assert "top-nasalson" not in {t.id for t in content.topics.topics}
    assert content.elements["ex-reservea"].topics == ["top-articles"]
    assert content.errors == []
    assert len(commits(repo)) == 2  # init + одно объединение одним коммитом


def test_merge_into_itself_is_refused(repo: Path):
    with pytest.raises(WriteError):
        writer(repo).merge_topics("top-articles", "top-articles")


def test_atomic_write_keeps_file_on_failure(repo: Path, monkeypatch):
    path = repo / "lessons/001/lesson.yaml"
    before = path.read_text(encoding="utf-8")

    def boom(*args, **kwargs):
        raise OSError("диск недоступен")

    monkeypatch.setattr("french_learning.content.writer.os.replace", boom)
    with pytest.raises(WriteError):
        writer(repo).set_lesson_date(1, dt.date(2020, 1, 1))
    assert path.read_text(encoding="utf-8") == before
    assert list(path.parent.glob("*.tmp")) == []


def test_push_failure_is_a_warning(repo: Path):
    result = writer(repo).set_lesson_date(1, dt.date(2026, 9, 2))
    assert result.committed
    assert not result.pushed
    assert "копия не отправлена" in result.warning


def test_without_git_writes_and_warns(clean_content_root: Path):
    result = writer(clean_content_root).set_lesson_date(1, dt.date(2026, 9, 3))
    assert load_content(clean_content_root).lessons[1].date == dt.date(2026, 9, 3)
    assert not result.committed
    assert "git" in result.warning


def test_yaml_stays_readable(repo: Path):
    writer(repo).set_element_topics("ex-gapinput", ["top-articles"])
    text = (repo / "lessons/001/exercises/ex-gapinput.yaml").read_text(encoding="utf-8")
    assert "Поставьте глагол" in text  # кириллица без \u-экранирования
    assert yaml.safe_load(text)["id"] == "ex-gapinput"


def test_set_exercise_status_commits(repo: Path):
    result = writer(repo).set_exercise_status("ex-gapchoic", "optional")
    assert load_content(repo).elements["ex-gapchoic"].status == "optional"
    assert result.committed and "ex-gapchoic" in commits(repo)[0]
    with pytest.raises(WriteError):
        writer(repo).set_exercise_status("ex-gapchoic", "wrong")
    with pytest.raises(WriteError):
        writer(repo).set_exercise_status("th-articles", "optional")


def test_create_report_for_known_element_skips_reading_content(repo: Path, monkeypatch):
    """010 пункт 7: маршрут уже проверил упражнение — полное чтение хранилища не нужно."""
    import french_learning.content.writer as writer_module

    def forbidden(_root):
        raise AssertionError("load_content не должен вызываться")

    monkeypatch.setattr(writer_module, "load_content", forbidden)
    report, _result = writer(repo).create_report("ex-gapchoic", 1, "опечатка", known_element=True)
    assert (repo / "reports" / f"{report.id}.yaml").exists()


def test_create_report_checks_element_by_default(repo: Path):
    with pytest.raises(WriteError):
        writer(repo).create_report("ex-nonexist", 1, "опечатка")
