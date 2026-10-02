"""US4: ввод ответа с панелью символов и выбором написания (FR-040–FR-044)."""

import re
from html import unescape


def start_input(client, direction="fr_ru", **form) -> str:
    data = {"mode": "all", "kind": "all", "direction": direction, "method": "input", **form}
    return client.post("/practice/start", data=data).url.path.rsplit("/", 1)[-1]


def current_question(client, session) -> str:
    html = client.get(f"/practice/{session}").text
    return re.search(r'class="question"[^>]*>([^<]+)<', html)[1]


def cards_db(client):
    return client.app.state.cards


def test_input_field_and_symbol_panel(client):
    session = start_input(client)
    html = client.get(f"/practice/{session}").text
    assert 'name="answer"' in html
    for ch in "éèêëàâçœùûüîïô":
        assert f'data-char="{ch}"' in html


def test_correct_answer_recorded_as_good(client):
    session = start_input(client, mode="topic", topic="top-maisonxx")
    question = current_question(client, session)
    answer = "дом" if "maison" in question else "кот"
    html = client.post(f"/practice/{session}/answer", data={"answer": answer}).text
    assert "Верно" in html
    entry = "voc-maisonaa" if "maison" in question else "voc-chataaaa"
    [review] = cards_db(client).history(entry)
    assert review["rating"] == "good" and review["method"] == "input"


def test_wrong_answer_shows_correct_and_records_again(client):
    session = start_input(client, mode="topic", topic="top-maisonxx")
    question = current_question(client, session)
    html = client.post(f"/practice/{session}/answer", data={"answer": "собака"}).text
    assert "Неверно" in html
    assert ("дом" if "maison" in question else "кот") in html
    entry = "voc-maisonaa" if "maison" in question else "voc-chataaaa"
    assert cards_db(client).history(entry)[0]["rating"] == "again"


def ru_fr_session_for_eau(client) -> str:
    """Сеанс «русский → французский» только со словом eau (прочие — «Знаю»)."""
    cards = cards_db(client)
    cards.sync(client.app.state.store.get())
    for card in cards.all():
        if card.entry_id != "voc-eauaaaaa":
            cards.set_known(card.entry_id, True)
    return start_input(client, direction="ru_fr")


def test_spelling_choice_when_diacritics_missing(client):
    # «maison» без артикля — ошибка; «l'eau» без апострофа-артикля — тоже
    session = ru_fr_session_for_eau(client)
    html = client.post(f"/practice/{session}/answer", data={"answer": "l'eau"}).text
    assert "Верно" in html


def test_article_required_for_nouns_ru_fr(client):
    session = ru_fr_session_for_eau(client)
    html = client.post(f"/practice/{session}/answer", data={"answer": "eau"}).text
    assert "Неверно" in html


def test_choose_spelling_flow(client, content_root):
    path = content_root / "vocabulary/voc-eauaaaaa.yaml"
    path.write_text(
        path.read_text(encoding="utf-8")
        .replace("text: eau", "text: été")
        .replace('article: "l\'"', 'article: "l\'"'),
        encoding="utf-8",
    )
    session = ru_fr_session_for_eau(client)
    html = client.post(f"/practice/{session}/answer", data={"answer": "l'ete"}).text
    assert "Выберите правильное написание" in html
    variants = [unescape(v) for v in re.findall(r'name="choice" value="([^"]+)"', html)]
    assert "l'été" in variants
    wrong = next(v for v in variants if v != "l'été")
    result = client.post(
        f"/practice/{session}/spelling", data={"answer": "l'ete", "choice": wrong}
    ).text
    assert "Неверно" in result
    assert cards_db(client).history("voc-eauaaaaa")[-1]["rating"] == "again"
