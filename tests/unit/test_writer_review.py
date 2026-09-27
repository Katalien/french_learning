"""US4: снятие «требует проверки» и сообщения об ошибках (FR-041, FR-042)."""

import subprocess
from pathlib import Path

import pytest
import yaml

from french_learning.content.loader import load_content
from french_learning.content.writer import ContentWriter, WriteError


@pytest.fixture
def repo(clean_content_root: Path) -> Path:
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
    ):
        subprocess.run(["git", "-C", str(clean_content_root), *args], check=True)
    return clean_content_root


def last_commit(root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "log", "-1", "--format=%s"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()


def writer(root: Path) -> ContentWriter:
    return ContentWriter(root, author=("test", "test@localhost"))


def test_mark_item_verified(repo: Path):
    writer(repo).mark_verified("ex-gapchoic", item_id=2)
    item = load_content(repo).elements["ex-gapchoic"].items[1]
    assert item.needs_review.flag is False
    assert "проверен" in last_commit(repo)


def test_mark_element_verified(repo: Path):
    path = repo / "lessons/001/texts/tx-aucafeaa.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "needs_review: {flag: false}", "needs_review: {flag: true, note: плохо видно}"
        ),
        encoding="utf-8",
    )
    writer(repo).mark_verified("tx-aucafeaa")
    assert load_content(repo).elements["tx-aucafeaa"].needs_review.flag is False


def test_unknown_item_is_refused(repo: Path):
    with pytest.raises(WriteError):
        writer(repo).mark_verified("ex-gapchoic", item_id=99)


def test_create_report(repo: Path):
    report, result = writer(repo).create_report("ex-gapinput", 1, "Неверный ответ")
    data = yaml.safe_load((repo / f"reports/{report.id}.yaml").read_text(encoding="utf-8"))
    assert data["element"] == "ex-gapinput"
    assert data["item"] == 1
    assert data["comment"] == "Неверный ответ"
    assert data["status"] == "open"
    assert data["resolution"] is None
    assert result.committed
    assert report.id in load_content(repo).reports


def test_report_needs_comment(repo: Path):
    with pytest.raises(WriteError):
        writer(repo).create_report("ex-gapinput", None, "   ")
