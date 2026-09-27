"""US1: выполнение упражнения в интерфейсе (FR-001–FR-011, FR-020a, FR-022)."""

import re
from html import unescape

HX = {"HX-Request": "true"}


def page(client, exercise_id):
    return client.get(f"/elements/{exercise_id}").text


def check(client, exercise_id, data):
    return client.post(f"/exercises/{exercise_id}/check", data=data, headers=HX).text


def test_form_fields_by_type(client):
    html = page(client, "ex-gapchoic")
    assert re.search(r'<select name="i1\.1"', html)
    assert '<option value="l\'"' in unescape(html) or '<option value="l&#39;"' in html
    assert 'name="i1.1"' in page(client, "ex-gapinput")
    assert 'name="i1.2"' in page(client, "ex-multigap")
    assert 'name="i1.a"' in page(client, "ex-transfor")
    tf = page(client, "ex-truefals")
    assert 'type="radio" name="i1.a" value="true"' in tf
    assert 'type="radio" name="i1.a" value="0"' in page(client, "ex-choicecf")
    grouping = page(client, "ex-grouping")
    assert '<select name="i1.a"' in grouping and "féminin" in grouping
    assert '<textarea name="i1.a"' in page(client, "ex-openansw")
    assert 'data-char="é"' in page(client, "ex-gapinput")  # панель символов
    assert "Проверить" in page(client, "ex-gapinput")


def test_reference_hidden_behind_button(client):
    html = page(client, "ex-transfor")
    assert "Справка" in html and 'x-show="reference"' in html


def test_check_highlights_and_counts(client):
    html = check(client, "ex-gapchoic", {"i1.1": "le", "i2.1": "la", "i3.1": "les"})
    assert 'id="item-1" class="item item-correct"' in html
    assert 'id="item-2" class="item item-wrong"' in html
    assert "Показать ответ" in html
    assert "Верно сразу: 2 из 3" in html
    # правильный ответ неверного пункта не виден до «Показать ответ» (и в «Не согласна» тоже)
    wrong_item = html.split('id="item-2"', 1)[1].split('id="item-3"', 1)[0]
    assert "l&#39;" not in wrong_item.split("<select", 1)[1].split("</select>", 1)[1]
    assert "review-badge" in html and "<form method" not in html.split("solve-form", 1)[1]


def test_fix_then_reveal(client):
    check(client, "ex-gapchoic", {"i1.1": "la", "i2.1": "la"})
    html = check(client, "ex-gapchoic", {"i1.1": "le", "i2.1": "la"})
    assert "исправлено самостоятельно" in html
    revealed = client.post(
        "/exercises/ex-gapchoic/reveal/2", data={"i1.1": "le", "i2.1": "la"}, headers=HX
    ).text
    assert "Ответ:" in unescape(revealed) and "l'" in unescape(revealed)


def test_spelling_choice_in_exercise(client):
    html = check(client, "ex-transfor", {"i1.a": "je ne suis pas fatiguee"})
    assert "Выберите написание" in html
    assert 'name="i1.a~choice"' in html


def test_draft_saved_and_restored(client):
    client.post("/exercises/ex-gapinput/draft", data={"i1.1": "sui"}, headers=HX)
    assert 'value="sui"' in page(client, "ex-gapinput")


def test_open_answer_saved(client):
    html = client.post(
        "/exercises/ex-openansw/save", data={"i1.a": "Je mange du pain."}, headers=HX
    ).text
    assert "Сохранено" in html and "Je mange du pain." in html


def test_homework_counter_counts_checked(client):
    before = client.get("/lessons/1").text
    assert "0 из" in before
    check(client, "ex-multigap", {"i1.1": "x", "i1.2": "y"})  # с ошибками — всё равно выполнено
    after = client.get("/lessons/1").text
    assert "1 из" in after
    assert "✓ выполнено" in client.get("/lessons/1/tasks?part=homework").text


def test_without_htmx_redirects_to_page(client):
    response = client.post("/exercises/ex-gapinput/check", data={"i1.1": "suis"})
    assert response.url.path == "/elements/ex-gapinput"
    assert "item-correct" in response.text
