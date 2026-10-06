"""US1: повторение в интерфейсе (FR-032, FR-033, FR-037; contracts/ui-routes.md 003)."""

import re


def start(client, **form) -> str:
    data = {"mode": "today", "kind": "all", "direction": "fr_ru", "method": "self", **form}
    response = client.post("/practice/start", data=data)
    assert response.status_code == 200
    return response.url.path


def test_setup_page_shows_count(client):
    html = client.get("/practice/setup").text  # 009: настройка переехала, /practice — хаб
    assert "Пора повторить сегодня" in html
    assert "Карточек к повторению: 4" in html


def test_card_show_rate_flow(client):
    path = start(client)
    html = client.get(path).text
    assert "Показать" in html
    # 2026-09-30 (макет Г1): оценки на обеих сторонах карточки — можно оценить, не переворачивая
    for label in ("Не помню", "С трудом", "Помню"):
        assert label in html
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


def test_lesson_practice_opens_setup_with_lesson(client):
    """010 пункт 3: из урока — страница настройки с выбранным уроком."""
    response = client.get("/lessons/2/practice", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/practice/setup?mode=lesson&lesson=2"
    assert client.get("/lessons/99/practice", follow_redirects=False).status_code == 404
    html = client.get("/practice/setup?mode=lesson&lesson=2").text
    assert "mode: 'lesson'" in html
    assert re.search(r'<option value="2"\s+selected>', html)
    assert re.search(r'name="portion"[^>]*value=""', html)


def test_start_portion_empty_means_all(client):
    path = start(client, mode="all", portion="", from_setup="1")
    assert "1/8" not in client.get(path).text  # одно направление: 4 слова
    session = path.rsplit("/", 1)[-1]
    progress = client.app.state.sessions.progress(session)
    assert progress.total == 4 and progress.portion_size == 4


def test_start_portion_number_is_used_and_remembered(client):
    path = start(client, mode="all", portion="3")
    progress = client.app.state.sessions.progress(path.rsplit("/", 1)[-1])
    assert progress.portion_size == 3
    assert client.app.state.progress_db.get_setting("portion_size") == "3"
    assert 'value="3"' in client.get("/practice/setup").text


def test_start_without_portion_field(client):
    """Кнопки «Повторить» без поля: прочие режимы — последнее число, урок / тема — все."""
    client.app.state.progress_db.set_setting("portion_size", "3")
    path = client.post("/practice/start", data={"mode": "today"}).url.path
    assert client.app.state.sessions.progress(path.rsplit("/", 1)[-1]).portion_size == 3
    path = client.post("/practice/start", data={"mode": "lesson", "lesson": "2"}).url.path
    assert client.app.state.sessions.progress(path.rsplit("/", 1)[-1]).portion_size == 2


def test_topic_page_links_to_setup(client):
    html = client.get("/topics/top-maisonxx").text
    assert 'href="/practice/setup?mode=topic&amp;topic=top-maisonxx"' in html


def test_start_portion_invalid(client):
    for bad in ("0", "abc", "501"):
        response = client.post(
            "/practice/start", data={"mode": "all", "portion": bad}, follow_redirects=False
        )
        assert response.status_code == 303
        assert "/practice/setup" in response.headers["location"]
        assert "error=" in response.headers["location"]


def test_start_with_empty_queue_returns_to_setup(client):
    response = client.post(
        "/practice/start", data={"mode": "all", "kind": "phrase"}, follow_redirects=False
    )
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/practice/setup") and "notice=" in location
    html = client.get(location).text
    assert "Нет слов для повторения" in html


def test_count_fragment(client):
    html = client.get(
        "/practice/count", params={"mode": "lesson", "lesson": "2", "direction": "ru_fr"}
    ).text
    assert "В сеансе: 2" in html
    empty = client.get("/practice/count", params={"mode": "all", "kind": "phrase"}).text
    assert "Нет слов для повторения" in empty


def test_setup_has_topic_combobox(client):
    html = client.get("/practice/setup").text
    assert "data-combobox" in html
    assert 'type="hidden" name="topic"' in html
    assert '<select name="topic"' not in html
    assert "top-maisonxx" in html  # список тем передаётся в поле


def test_vocab_section_has_practice_button(client):
    assert 'href="/lessons/1/practice"' in client.get("/lessons/1/vocab").text  # 009


def test_summary_after_last_card(client):
    session = start(client, mode="topic", topic="top-maisonxx").rsplit("/", 1)[-1]
    for _ in range(2):
        client.post(f"/practice/{session}/show")
        html = client.post(f"/practice/{session}/rate", data={"rating": "good"}).text
    assert "Готово" in html


def test_card_flips_on_click(client):
    """Карточка переворачивается нажатием (анимация в браузере, макет 2026-09-30 Г1):
    лицо и оборот уже на странице, отдельной кнопки «Показать» нет."""
    html = client.get(start(client)).text
    assert re.search(r'class="flashcard flip-card[^"]*"[^>]*data-flip', html)
    assert 'class="flip-face flip-back"' in html and 'class="answer"' in html
    assert ">Показать</button>" not in html
    assert "flipped" not in html.split('class="flashcard', 1)[1].split(">", 1)[0]


def test_show_route_renders_flipped_card(client):
    session = start(client).rsplit("/", 1)[-1]
    html = client.post(f"/practice/{session}/show").text
    assert re.search(r'class="flashcard flip-card[^"]* flipped"', html)


def only_eau_session(client, method="self") -> str:
    """Сеанс «русский → французский» только со словом l'eau (f); прочие — «Знаю»."""
    cards = client.app.state.cards
    cards.sync(client.app.state.store.get())
    for card in cards.all():
        if card.entry_id != "voc-eauaaaaa":
            cards.set_known(card.entry_id, True)
    return start(client, mode="all", direction="ru_fr", method=method).rsplit("/", 1)[-1]


def test_ru_fr_card_hides_gender_until_shown(client):
    """010 пункт 2: лицевая сторона ru_fr не выдаёт род ни цветом, ни меткой."""
    session = only_eau_session(client)
    html = client.get(f"/practice/{session}").text
    front, back = html.split('class="flip-face flip-back', 1)
    front = front.split('class="flashcard', 1)[1]
    assert 'class="flip-face neutral"' in front
    assert "gender-tag" not in front
    assert 'class="gender-tag">f<' in back.split("</article>", 1)[0]


def test_fr_ru_card_keeps_gender_on_front(client):
    html = client.get(start(client, mode="topic", topic="top-maisonxx")).text
    front = html.split('class="flip-face flip-back', 1)[0]
    assert "neutral" not in front and "gender-tag" in front


def test_ru_fr_input_card_neutral_before_answer(client):
    session = only_eau_session(client, method="input")
    html = client.get(f"/practice/{session}").text
    assert 'class="flashcard gender-none' in html and "gender-tag" not in html
    result = client.post(f"/practice/{session}/answer", data={"answer": "l'eau"}).text
    assert 'class="flashcard gender-f' in result


# --- 011: «Ошибка в артикле» ------------------------------------------------------------------


def test_article_button_only_for_ru_fr_nouns(client, content_root):
    session = only_eau_session(client)
    html = client.get(f"/practice/{session}").text
    assert 'value="article"' in html and "Ошибка в артикле" in html
    fr_ru = client.get(start(client, mode="all", direction="fr_ru")).text
    assert 'value="article"' not in fr_ru


def test_article_button_absent_without_gender(client, content_root):
    path = content_root / "vocabulary/voc-eauaaaaa.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("gender: f\n", ""), encoding="utf-8")
    session = only_eau_session(client)
    assert 'value="article"' not in client.get(f"/practice/{session}").text
    response = client.post(f"/practice/{session}/rate", data={"rating": "article"})
    assert response.status_code == 404


def test_article_rating_moves_word_to_front_of_articles_trainer(client):
    session = only_eau_session(client)
    html = client.post(f"/practice/{session}/rate", data={"rating": "article"}).text
    assert "Ошибка в артикле" in html  # строка итога
    assert re.search(r"Ошибка в артикле</span><strong>1</strong>", html)
    started = client.post("/trainers/articles/start", data={"scope": "all"})
    prompt = re.search(r'class="trainer-prompt"[^>]*>\s*([^<]+?)\s*<', started.text)[1]
    assert "eau" in prompt  # первым — слово с «Ошибкой в артикле»


# --- 011: переводы помещаются на карточке --------------------------------------------------


LONG = [
    "вода питьевая из-под крана",
    "жидкость прозрачная без цвета",
    "водоём, море или река в целом",
]


def long_translations(content_root):
    path = content_root / "vocabulary/voc-eauaaaaa.yaml"
    lines = "".join(f"  - {{text: '{t}', lesson: 2, origin: ai}}\n" for t in LONG)
    text = path.read_text(encoding="utf-8").replace(
        "  - {text: вода, lesson: 2, origin: ai}\n", lines
    )
    path.write_text(text, encoding="utf-8")


def test_ru_fr_question_each_translation_on_own_line(client, content_root):
    long_translations(content_root)
    html = client.get(f"/practice/{only_eau_session(client)}").text
    front = html.split('class="flip-face flip-back', 1)[0]
    assert re.search(r'class="question tr-lines tr-s"', front)
    assert [t for t in LONG if f'<span class="tr-line">{t}</span>' in front] == LONG


def test_fr_ru_answer_each_translation_on_own_line(client, content_root):
    long_translations(content_root)
    cards = client.app.state.cards
    cards.sync(client.app.state.store.get())
    for card in cards.all():
        if card.entry_id != "voc-eauaaaaa":
            cards.set_known(card.entry_id, True)
    html = client.get(start(client, mode="all", direction="fr_ru")).text
    back = html.split('class="flip-face flip-back', 1)[1]
    assert 'class="answer tr-lines tr-s"' in back
    assert all(f'<span class="tr-line">{t}</span>' in back for t in LONG)


def test_short_translation_unchanged(client):
    html = client.get(f"/practice/{only_eau_session(client)}").text
    assert '<p class="question" lang="ru">вода</p>' in html


# --- 011: повтор-тренировка на итоге --------------------------------------------------------


def finish(client, session, ratings):
    html = ""
    for rating in ratings:
        html = client.post(f"/practice/{session}/rate", data={"rating": rating}).text
    return html


def test_summary_offers_drill_buttons_with_counts(client):
    session = start(client, mode="all").rsplit("/", 1)[-1]
    html = finish(client, session, ["again", "again", "hard", "good"])
    assert "Повторить «Не помню» (2)" in html
    assert "Повторить «Не помню» и «С трудом» (3)" in html


def test_summary_without_mistakes_has_no_drill(client):
    session = start(client, mode="all").rsplit("/", 1)[-1]
    html = finish(client, session, ["good"] * 4)
    assert "Повторить «Не помню»" not in html


def test_drill_session_without_recording(client):
    session = start(client, mode="all").rsplit("/", 1)[-1]
    finish(client, session, ["again", "good", "good", "good"])
    cards = client.app.state.cards
    history = {c.entry_id: len(cards.history(c.entry_id)) for c in cards.all()}
    response = client.post(f"/practice/{session}/drill", data={"which": "again"})
    assert response.status_code == 200
    drill = response.url.path.rsplit("/", 1)[-1]
    assert drill != session
    assert "Тренировка — без записи" in response.text and "1/1" in response.text
    summary = client.post(f"/practice/{drill}/rate", data={"rating": "again"}).text
    assert "Тренировка — без записи" in summary
    assert "Повторить «Не помню» (1)" in summary  # повтор по ответам тренировки
    assert {c.entry_id: len(cards.history(c.entry_id)) for c in cards.all()} == history


def test_drill_with_no_words_returns_to_summary(client):
    session = start(client, mode="all").rsplit("/", 1)[-1]
    finish(client, session, ["good"] * 4)
    response = client.post(
        f"/practice/{session}/drill", data={"which": "again"}, follow_redirects=False
    )
    assert response.status_code == 303 and response.headers["location"] == f"/practice/{session}"
