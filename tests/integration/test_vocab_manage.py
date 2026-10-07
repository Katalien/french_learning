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


def test_hidden_word_only_in_hidden_filter(client):
    """012 (US1): скрытое слово видно только в фильтре «скрытые» и на своей странице."""
    client.post("/vocab/voc-maisonaa/hide")
    assert "скрыто" in client.get("/vocab/voc-maisonaa").text
    assert "voc-maisonaa" not in client.get("/vocab").text
    assert "voc-maisonaa" in client.get("/vocab?filter=hidden").text
    lesson = client.get("/lessons/1/vocab").text
    assert "voc-maisonaa" not in lesson and "скрыто" not in lesson
    topic = client.get("/topics/top-maisonxx").text
    assert "voc-maisonaa" not in topic and "скрыто" not in topic
    client.post("/vocab/voc-maisonaa/unhide")
    assert "voc-maisonaa" in client.get("/lessons/1/vocab").text


def test_delete_lesson_word_keeps_history(client):
    """012 (US1): удалить можно любое слово; история повторений остаётся в базе (VII)."""
    cards = client.app.state.cards
    cards.sync(client.app.state.store.get())
    cards.rate("voc-maisonaa", "fr_ru", "good", mode="all", method="self")
    response = client.post("/vocab/voc-maisonaa/delete", follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"].startswith("/vocab")
    assert "Слово удалено" in client.get(response.headers["location"]).text
    assert client.get("/vocab/voc-maisonaa").status_code == 404
    assert "voc-maisonaa" not in client.get("/lessons/1/vocab").text
    assert "voc-maisonaa" not in client.get("/search?q=maison").text
    assert len(cards.history("voc-maisonaa")) == 1


def test_delete_own_word(client):
    client.post("/vocab/voc-chataaaa/delete")
    assert client.get("/vocab/voc-chataaaa").status_code == 404


def test_entry_page_has_delete_confirmation(client):
    page = client.get("/vocab/voc-maisonaa").text
    assert "Удалить слово" in page
    assert "<dialog" in page and 'action="/vocab/voc-maisonaa/delete"' in page


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


def test_session_survives_deleted_and_hidden_words(client):
    """012 (US1): удалённое посреди сеанса слово пропускается, скрытое — доходит до конца."""
    data = {"mode": "all", "kind": "all", "direction": "fr_ru", "method": "self"}
    path = client.post("/practice/start", data=data).url.path
    session = path.rsplit("/", 1)[-1]
    sessions = client.app.state.sessions
    total = sessions.progress(session).total
    first = sessions.current(session)[0]
    client.post(f"/vocab/{first}/delete")
    page = client.get(path)
    assert page.status_code == 200
    second = sessions.current(session, exists=lambda i: i != first)[0]
    assert second != first
    client.post(f"/vocab/{second}/hide")
    assert sessions.current(session, exists=lambda i: i != first)[0] == second
    assert client.get(path).status_code == 200
    assert client.post(f"/practice/{session}/rate", data={"rating": "good"}).status_code == 200
    assert sessions.progress(session).total == total
    new = client.post("/practice/start", data=data).url.path.rsplit("/", 1)[-1]
    assert second not in {card[0] for card in sessions._load(new)[1]}


def test_delete_from_carousel_opens_next_word(client):
    """012 (приёмка): удаление из карусели слов урока — следующая карточка, а не весь словарь."""
    page = client.get("/vocab/voc-eauaaaaa?from=lesson&lesson=2").text
    assert 'name="next" value="/vocab/voc-painaaaa?from=lesson&amp;lesson=2"' in page
    response = client.post(
        "/vocab/voc-eauaaaaa/delete",
        data={"next": "/vocab/voc-painaaaa?from=lesson&lesson=2"},
        follow_redirects=False,
    )
    location = response.headers["location"]
    assert location.startswith("/vocab/voc-painaaaa?from=lesson&lesson=2&notice=")
    assert "Слово удалено" in client.get(location).text
    # последнее слово урока — к предыдущему; единственное — назад к лексике урока
    last = client.get("/vocab/voc-painaaaa?from=lesson&lesson=2").text
    assert 'name="next" value="/lessons/2/vocab"' in last
    # чужой адрес не принимается
    evil = client.post(
        "/vocab/voc-painaaaa/delete", data={"next": "//evil.example"}, follow_redirects=False
    )
    assert evil.headers["location"].startswith("/vocab?notice=")
