"""US1: повторение в интерфейсе (FR-032, FR-033, FR-037; contracts/ui-routes.md 003)."""

import re


def start(client, **form) -> str:
    data = {"mode": "today", "kind": "all", "direction": "fr_ru", "method": "self", **form}
    response = client.post("/practice/start", data=data)
    assert response.status_code == 200
    return response.url.path


def test_setup_page_shows_count(client):
    html = client.get("/practice").text
    assert "Пора повторить сегодня" in html
    assert "Карточек к повторению: 4" in html


def test_card_show_rate_flow(client):
    path = start(client)
    html = client.get(path).text
    assert "Показать" in html
    assert "Не помню" not in html  # оценки до показа недоступны
    session = path.rsplit("/", 1)[-1]
    shown = client.post(f"/practice/{session}/show").text
    for label in ("Не помню", "С трудом", "Помню"):
        assert label in shown
    after = client.post(f"/practice/{session}/rate", data={"rating": "good"})
    assert after.status_code == 200
    assert "1 из 4" in after.text or "2 из 4" in after.text


def test_undo_returns_previous_card(client):
    session = start(client).rsplit("/", 1)[-1]
    first = re.search(r'class="question"[^>]*>([^<]+)<', client.get(f"/practice/{session}").text)[1]
    client.post(f"/practice/{session}/show")
    client.post(f"/practice/{session}/rate", data={"rating": "good"})
    html = client.post(f"/practice/{session}/undo").text
    assert first in html


def test_lesson_practice_starts_whole_lesson(client):
    response = client.get("/lessons/2/practice")
    assert response.status_code == 200
    assert "из 2" in response.text


def test_theory_page_has_practice_button(client):
    assert 'href="/lessons/1/practice"' in client.get("/lessons/1/theory").text


def test_summary_after_last_card(client):
    session = start(client, mode="topic", topic="top-maisonxx").rsplit("/", 1)[-1]
    for _ in range(2):
        client.post(f"/practice/{session}/show")
        html = client.post(f"/practice/{session}/rate", data={"rating": "good"}).text
    assert "Готово" in html
