"""US5: управление записями словаря в интерфейсе (FR-050–FR-052)."""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _git(content_root: Path):
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
    ):
        subprocess.run(["git", "-C", str(content_root), *args], check=True, capture_output=True)


def test_edit_notes(client):
    client.post("/vocab/voc-maisonaa/edit", data={"translations": "дом", "notes": "запомнить"})
    assert "запомнить" in client.get("/vocab/voc-maisonaa").text


def test_hide_lesson_word_shows_mark_in_lesson(client):
    client.post("/vocab/voc-maisonaa/hide")
    assert "скрыто" in client.get("/vocab/voc-maisonaa").text
    assert "voc-maisonaa" not in client.get("/vocab").text
    assert "voc-maisonaa" in client.get("/vocab?filter=hidden").text
    assert "скрыто" in client.get("/lessons/1/vocab").text  # отметка у слова в «Лексике» урока


def test_delete_own_and_refuse_lesson_word(client):
    response = client.post("/vocab/voc-maisonaa/delete")
    assert "только свои" in response.text
    client.post("/vocab/voc-chataaaa/delete")
    assert client.get("/vocab/voc-chataaaa").status_code == 404


def test_known_and_back_keeps_history(client):
    cards = client.app.state.cards
    cards.sync(client.app.state.store.get())
    cards.rate("voc-painaaaa", "fr_ru", "good", mode="all", method="self")
    client.post("/vocab/voc-painaaaa/known")
    assert "voc-painaaaa" in client.get("/vocab?filter=known").text
    assert "знаю" in client.get("/vocab/voc-painaaaa").text
    client.post("/vocab/voc-painaaaa/unknown")
    assert "voc-painaaaa" not in client.get("/vocab?filter=known").text
    assert len(cards.history("voc-painaaaa")) == 1
