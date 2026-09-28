"""US4: встроенные тренажёры в интерфейсе (FR-040–FR-046, FR-045a)."""

import re
from html import unescape

HX = {"HX-Request": "true"}


def start(client, trainer_id, **form):
    response = client.post(f"/trainers/{trainer_id}/start", data={"scope": "all", **form})
    return response.url.path.rsplit("/", 1)[-1], response.text


def prompt(html):
    return unescape(re.search(r'class="trainer-prompt"[^>]*>\s*([^<]+?)\s*<', html)[1])


def test_catalog_lists_builtin_and_own(client):
    html = client.get("/trainers").text
    for name in ("Артикли", "Спряжение", "Числа", "Собери предложение", "Отрицание"):
        assert name in html
    assert 'href="/practice"' in client.get("/lessons").text  # тренажёры — в «Практике»


def test_setup_page_and_missing_data(client):
    html = client.get("/trainers/articles").text
    assert 'name="scope"' in html and "Урок 1" in html
    missing = client.get("/trainers/conjugation").text
    assert "/complete-words" in missing and "Начать" not in missing


def test_articles_buttons_answer_right_and_wrong(client):
    session, html = start(client, "articles")
    assert ('value="le"' in html and 'value="un"' not in html) or 'value="un"' in html
    word = prompt(html)
    assert word.startswith("___ ")
    buttons = re.findall(r'name="answer" value="([^"]+)"', unescape(html))
    assert len(buttons) in (3, 4)
    result = client.post(f"/trainers/s/{session}/answer", data={"answer": "les"}).text
    assert "Неверно" in result or "Верно" in result
    assert "Дальше" in result


def test_numbers_input_and_spelling_choice(client):
    session, html = start(client, "numbers")
    number = int(prompt(html))
    from french_learning.trainers.french_numbers import spellings

    right = spellings(number)[0]
    result = client.post(f"/trainers/s/{session}/answer", data={"answer": right}).text
    assert "Верно" in result
    client.get(f"/trainers/s/{session}")
    nxt = int(prompt(client.get(f"/trainers/s/{session}").text))
    written = spellings(nxt)[0]
    plain = written.replace("é", "e")
    if plain != written:  # есть акцент — предлагается выбор написания
        choose = client.post(f"/trainers/s/{session}/answer", data={"answer": plain}).text
        assert "Выберите правильное написание" in choose


def test_reveal_counts_as_error(client):
    session, _html = start(client, "numbers")
    html = client.post(f"/trainers/s/{session}/reveal").text
    assert "Ответ" in html
    [row] = client.app.state.trainer_schedule.history("numbers")
    assert row["revealed"] == 1 and row["correct"] == 0


def test_portion_summary_and_continue(client):
    client.post(
        "/settings",
        data={
            "portion_size": "20",
            "directions": "staged",
            "voice": "siwis",
            "trainer_portion_size": "2",
        },
    )
    session, _ = start(client, "numbers")
    for _ in range(2):
        client.post(f"/trainers/s/{session}/answer", data={"answer": "faux"})
    summary = client.get(f"/trainers/s/{session}").text
    assert "0 из 2" in summary and "Продолжить" in summary and "Закончить" in summary
    client.post(f"/trainers/s/{session}/continue")
    assert "trainer-prompt" in client.get(f"/trainers/s/{session}").text


def test_scope_lesson_filters(client):
    _session, html = start(client, "articles", scope="lesson", lesson="2")
    # в уроке 2 — pain и eau: вопросы только по ним
    word = prompt(html)
    assert word in ("___ pain", "___ eau")


def test_sentence_builder_order(client):
    session, html = start(client, "sentence-builder")
    assert "x-data" in html and "trainer-token" in html
    result = client.post(f"/trainers/s/{session}/answer", data={"answer": "mauvais ordre"}).text
    assert "Неверно" in result


def test_settings_trainer_portion(client):
    assert 'name="trainer_portion_size"' in client.get("/settings").text


def test_resubmitted_answer_is_ignored(client):
    session, html = start(client, "numbers")
    key = re.search(r'name="key" value="([^"]+)"', html)[1]
    client.post(f"/trainers/s/{session}/answer", data={"answer": "x", "key": key})
    again = client.post(f"/trainers/s/{session}/answer", data={"answer": "x", "key": key})
    assert again.url.path == f"/trainers/s/{session}"  # обновление страницы — без записи
    assert len(client.app.state.trainer_schedule.history("numbers")) == 1
