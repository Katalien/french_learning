"""Добавление и правка слов в хранилище (FR-020–FR-022, FR-050, FR-052)."""

import subprocess
from pathlib import Path

import pytest

from french_learning.content.loader import load_content
from french_learning.vocab.edits import VocabEditor, VocabError


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


def editor(root: Path) -> VocabEditor:
    return VocabEditor(root, author=("test", "test@localhost"))


def vocab(root: Path):
    return {e.text: e for e in load_content(root).elements.values() if e.kind == "vocab"}


def test_add_single_word(repo: Path):
    entry_id, merged = editor(repo).add_word(
        text="fromage", translations=["сыр"], topics=["top-nourritu"], article="le"
    )
    assert not merged
    entry = vocab(repo)["fromage"]
    assert entry.id == entry_id
    assert entry.origin == "user" and entry.translations[0].origin == "user"
    assert entry.gender == "m" and entry.needs_completion
    assert load_content(repo).errors == []


def test_translation_required(repo: Path):
    with pytest.raises(VocabError):
        editor(repo).add_word(text="fromage", translations=[], topics=["top-nourritu"])


def test_import_list_adds_merges_and_reports(repo: Path):
    report = editor(repo).import_list(
        "le fromage — сыр\nla maison — жилище\nchat кот\n", topics=["top-maisonxx"], lesson=None
    )
    assert report.added == ["fromage"]
    assert report.merged == ["maison"]
    assert [u.line_no for u in report.unrecognized] == [3]
    maison = vocab(repo)["maison"]
    assert [t.text for t in maison.translations] == ["дом", "жилище"]
    assert git(repo, "log", "-1", "--format=%s").startswith("Словарь: добавлено 1, объединено 1")
    assert len(git(repo, "log", "--format=%s").splitlines()) == 2


def test_different_gender_is_a_new_entry(repo: Path):
    report = editor(repo).import_list("le maison — дом (м.)", topics=["top-maisonxx"], lesson=None)
    assert report.added == ["maison"]


def test_import_to_lesson(repo: Path):
    editor(repo).import_list("le fromage — сыр", topics=["top-nourritu"], lesson=2)
    assert vocab(repo)["fromage"].lessons == [2]


# --- US5: правка, скрытие, удаление -----------------------------------------------------------


def test_update_translations_and_notes(repo: Path):
    editor(repo).update(
        "voc-maisonaa", translations=["дом", "жилище"], notes="ж. р., как по-русски"
    )
    entry = vocab(repo)["maison"]
    assert [t.text for t in entry.translations] == ["дом", "жилище"]
    assert entry.translations[0].origin == "material"  # прежний перевод сохранил происхождение
    assert entry.translations[1].origin == "user"
    assert entry.notes == "ж. р., как по-русски"


def test_update_gender_removes_ai_mark(repo: Path):
    path = repo / "vocabulary/voc-chataaaa.yaml"
    path.write_text(
        path.read_text(encoding="utf-8") + "completed_by_ai: [gender, article]\n", encoding="utf-8"
    )
    editor(repo).update("voc-chataaaa", gender="f", article="la")
    entry = vocab(repo)["chat"]
    assert entry.gender == "f" and entry.completed_by_ai == []


def test_hide_lesson_entry_and_unhide(repo: Path):
    editor(repo).set_hidden("voc-maisonaa", True)
    assert vocab(repo)["maison"].hidden
    editor(repo).set_hidden("voc-maisonaa", False)
    assert not vocab(repo)["maison"].hidden


def test_delete_only_own_entries(repo: Path):
    with pytest.raises(VocabError, match="только свои"):
        editor(repo).delete("voc-maisonaa")
    editor(repo).delete("voc-chataaaa")
    assert "chat" not in vocab(repo)
    assert load_content(repo).errors == []
