"""Заметки на страницах (contracts/ui-routes.md, 005)."""

import json
import re
from html import unescape


def add(client, **fields):
    r = client.post("/notes", json=fields)
    assert r.status_code == 201, r.text
    return r.json()


def notes_data(html: str) -> dict:
    found = re.search(
        r'<script type="application/json" id="notes-data"[^>]*>(.*?)</script>', html, re.S
    )
    assert found, "нет данных заметок"
    return json.loads(unescape(found.group(1)))


# --- US1: данные и контейнеры -----------------------------------------------------------------


def test_element_pages_have_notes_data_and_container(client):
    note = add(client, kind="note", body="пометка к тексту", element_id="tx-aucafeaa")
    for element_id in ("tx-aucafeaa", "th-articles", "ex-gapchoic"):
        html = client.get(f"/elements/{element_id}").text
        assert f'data-note-container="{element_id}"' in html
        assert "/static/js/selection.js" in html and "/static/js/notes.js" in html
        data = notes_data(html)
        assert data["page"] == "element" and data["lesson"] == 1
    data = notes_data(client.get("/elements/tx-aucafeaa").text)
    assert [n["id"] for n in data["notes"]] == [note["id"]]


def test_extras_have_no_notes(client):
    html = client.get("/elements/th-extrarul").text
    assert "data-note-container" not in html and 'id="notes-data"' not in html


def test_reading_sections_have_containers(client):
    add(client, kind="note", body="x", element_id="tx-aucafeaa")
    html = client.get("/lessons/1/texts").text
    assert 'data-note-container="tx-aucafeaa"' in html
    data = notes_data(html)
    assert data["page"] == "reading" and len(data["notes"]) == 1
    assert 'data-note-container="th-articles"' in client.get("/lessons/1/theory").text


def test_side_fragment_has_container_and_notes(client):
    add(client, kind="note", body="x", element_id="th-articles")
    html = client.get("/elements/th-articles?fragment=1").text
    assert 'data-note-container="th-articles"' in html and "notes-data" in html


# --- US2: вопросы -----------------------------------------------------------------------------


def test_questions_badge_only_when_open(client):
    assert re.search(r'data-questions-count="0" hidden', client.get("/lessons").text)
    q = add(client, kind="question", body="почему un?", element_id="ex-gapchoic")
    add(client, kind="question", body="вопрос к уроку", lesson=1)
    assert re.search(r'data-questions-count="2"', client.get("/lessons").text)
    client.patch(f"/notes/{q['id']}", json={"answer": "ok"})
    assert re.search(r'data-questions-count="1"', client.get("/lessons").text)


def test_questions_panel(client):
    q = add(client, kind="question", body="почему un?", element_id="ex-gapchoic")
    add(client, kind="question", body="вопрос к уроку", lesson=1)
    html = unescape(client.get("/questions").text)
    assert "<html" not in html
    assert "почему un?" in html and "вопрос к уроку" in html
    assert f"/elements/ex-gapchoic#note-{q['id']}" in html and "/lessons/1/notes" in html
    assert "Урок 1" in html


# --- US3: кнопки у заголовка ------------------------------------------------------------------


def test_header_buttons_and_important(client):
    html = client.get("/elements/tx-aucafeaa").text
    assert "data-notes-add" in html and re.search(r'data-notes-toggle[^>]*data-count="0"', html)
    add(client, kind="note", body="ВАЖНО: être", element_id="tx-aucafeaa", important=True)
    add(client, kind="note", body="обычная", element_id="tx-aucafeaa")
    html = client.get("/elements/tx-aucafeaa").text
    assert re.search(r'data-notes-toggle[^>]*data-count="2"', html)
    strip = re.search(r"data-notes-important[^>]*>(.*?)</div>", html, re.S).group(1)
    assert "ВАЖНО: être" in strip and "обычная" not in strip


# --- US5: страница «Заметки к уроку» ----------------------------------------------------------


def test_lesson_notes_page(client):
    add(client, kind="question", body="открытый вопрос", lesson=1)
    add(client, kind="note", body="к уроку целиком", lesson=1)
    add(client, kind="note", body="к тексту", element_id="tx-aucafeaa")
    html = unescape(client.get("/lessons/1/notes").text)
    for text in ("Спросить на уроке", "открытый вопрос", "К уроку", "к уроку целиком"):
        assert text in html
    assert "Au café (démo)" in html and "к тексту" in html and "/elements/tx-aucafeaa" in html
    assert 'data-add-note="question"' in html and 'data-add-note="note"' in html
    fragment = client.get("/lessons/1/notes?fragment=1").text
    assert "<html" not in fragment and "открытый вопрос" in unescape(fragment)
    assert client.get("/lessons/77/notes").status_code == 404


def test_lesson_menus_link_notes(client):
    add(client, kind="note", body="a", lesson=1)
    add(client, kind="note", body="b", lesson=1)
    html = client.get("/lessons/1").text
    assert re.search(r'href="/lessons/1/notes"[^>]*>Заметки<span class="muted">2</span>', html)
    assert 'href="/lessons/1/notes"' in client.get("/elements/ex-gapchoic").text
