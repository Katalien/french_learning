"""Перевод выделенного и добавление из текста (006, contracts/translate-api.md).

Внешний сервис подменяется — настоящих запросов нет.
"""

import re

import pytest

from french_learning.translate.providers import TranslationUnavailable


class FakeTranslator:
    name = "mymemory"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[str] = []

    def translate(self, text: str) -> str:
        self.calls.append(text)
        if self.fail:
            raise TranslationUnavailable("нет сети")
        return {"achètent": "покупают", "acheter": "покупать"}.get(text, f"«{text}»")


@pytest.fixture
def fake(client):
    translator = FakeTranslator()
    client.app.state.translation.translator = lambda: translator
    return translator


def get(client, q):
    return client.get("/translate", params={"q": q})


def test_from_dictionary_without_service(client, fake):
    data = get(client, "maisons").json()
    assert data["source"] == "dictionary" and data["translation"]
    assert data["entry"]["id"] == "voc-maisonaa"
    assert data["can_add"] is False
    assert fake.calls == []


def test_from_service_then_from_cache(client, fake):
    first = get(client, "achètent")
    assert first.status_code == 200
    data = first.json()
    assert (data["translation"], data["source"]) == ("покупают", "service")
    assert (data["lemma"], data["lemma_translation"]) == ("acheter", "покупать")
    assert data["can_add"] is True
    assert data["add_as"] == {"text": "acheter", "entry_type": "verb"}
    # внешний сервис получает только выделенное и его начальную форму (FR-008)
    assert fake.calls == ["achètent", "acheter"]
    again = get(client, "achètent").json()
    assert again["source"] == "cache"
    assert fake.calls == ["achètent", "acheter"]


def test_unavailable(client):
    client.app.state.translation.translator = lambda: FakeTranslator(fail=True)
    data = get(client, "pomme").json()
    assert data["translation"] is None and data["error"] == "Перевод сейчас недоступен"


def test_rejected_input(client, fake):
    assert get(client, "").status_code == 422
    assert get(client, "   ").status_code == 422
    response = get(client, "pomme — яблоко")
    assert response.status_code == 422 and "error" in response.json()
    assert fake.calls == []


def test_too_long(client, fake):
    data = get(client, "a " * 260).json()
    assert data["error"].startswith("Выделите меньше") and data["translation"] is None
    assert fake.calls == []


def test_paragraph_cannot_be_added(client, fake):
    data = get(client, "Il y a du monde. Claire mange une crêpe.").json()
    assert data["translation"] and data["can_add"] is False


# --- разметка: где работает перевод (T015, research R1) --------------------------------------


def test_translate_zones_on_pages(client):
    for path in (
        "/elements/th-articles",  # теория
        "/elements/tx-aucafeaa",  # текст
        "/elements/ex-gapchoic",  # упражнение
        "/elements/th-extrarul",  # доп. материал
        "/elements/th-articles?fragment=1",  # теория рядом
        "/lessons/1/theory",
        "/lessons/1/texts",
    ):
        assert re.search(r"<(article|div)[^>]*\sdata-translate[\s>]", client.get(path).text), path
    for path in ("/vocab", "/vocab/voc-maisonaa", "/topics/top-nourritu", "/lessons/1/vocab"):
        assert 'lang="fr"' in client.get(path).text, path


def test_html_flag_and_script(client):
    html = client.get("/lessons").text
    assert re.search(r'<html[^>]*data-translate="1"', html)
    assert "/static/js/translate.js" in html
    client.cookies.set("translate", "0")
    assert re.search(r'<html[^>]*data-translate="0"', client.get("/lessons").text)


# --- «+ В словарь» из текста (US2, T022) -----------------------------------------------------


@pytest.fixture
def git_repo(content_root):
    import subprocess

    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
    ):
        subprocess.run(["git", "-C", str(content_root), *args], check=True, capture_output=True)
    return content_root


def add(client, **payload):
    return client.post("/vocab/from-text", json=payload)


def vocab_file(root, entry_id):
    import yaml

    return yaml.safe_load((root / "vocabulary" / f"{entry_id}.yaml").read_text(encoding="utf-8"))


def test_add_verb_from_text(client, fake, git_repo):
    sentence = "Elles achètent des pommes, du fromage et une baguette."
    response = add(client, text="achètent", sentence=sentence, lesson=1)
    assert response.status_code == 201
    data = response.json()
    assert (data["text"], data["translation"], data["merged"]) == ("acheter", "покупают", False)
    saved = vocab_file(git_repo, data["id"])
    assert saved["entry_type"] == "verb" and saved["text"] == "acheter"
    assert saved["translations"] == [{"text": "покупают", "lesson": 1, "origin": "service"}]
    assert saved["examples"] == [{"text": sentence, "lesson": 1}]
    assert saved["topics"] == [] and "lessons" not in saved
    # после добавления подсказка показывает «✓ в словаре»
    again = get(client, "achètent").json()
    assert again["entry"]["id"] == data["id"] and again["can_add"] is False


def test_add_noun_gets_gender_from_article_before(client, fake, git_repo):
    data = add(
        client, text="crêpe", sentence="Claire mange une crêpe au chocolat.", lesson=1
    ).json()
    saved = vocab_file(git_repo, data["id"])
    assert (saved["text"], saved["article"], saved["gender"]) == ("crêpe", "la", "f")


def test_add_phrase_and_sentence(client, fake, git_repo):
    phrase = add(client, text="il y a", sentence="Il y a beaucoup de monde.").json()
    assert vocab_file(git_repo, phrase["id"])["entry_type"] == "phrase"
    sentence = "Il y a beaucoup de monde."
    whole = add(client, text=sentence, sentence=sentence).json()
    saved = vocab_file(git_repo, whole["id"])
    assert saved["entry_type"] == "phrase" and "examples" not in saved  # пример не дублируется


def test_add_twice_is_merged(client, fake, git_repo):
    first = add(client, text="achètent", sentence="Elles achètent des pommes.").json()
    second = add(client, text="achète", sentence="Il achète du pain.")
    assert second.status_code == 201
    assert second.json()["merged"] is True and second.json()["id"] == first["id"]
    saved = vocab_file(git_repo, first["id"])
    assert [e["text"] for e in saved["examples"]] == [
        "Elles achètent des pommes.",
        "Il achète du pain.",
    ]


def test_add_rejected(client, fake, git_repo):
    assert add(client, text="Il y a du monde. Claire mange.", sentence="").status_code == 422
    assert add(client, text="", sentence="").status_code == 422
    assert add(client, text="кот", sentence="").status_code == 422
    client.app.state.translation.translator = lambda: FakeTranslator(fail=True)
    assert add(client, text="baguette", sentence="").status_code == 422


def test_entry_page_shows_example_lesson_and_service_origin(client, fake, git_repo):
    data = add(client, text="achètent", sentence="Elles achètent des pommes.", lesson=1).json()
    html = client.get(f"/vocab/{data['id']}").text
    assert "Elles achètent des pommes." in html and "урок 1" in html
    assert "внешний сервис" not in html
    client.cookies.set("show_origin", "1")
    assert "внешний сервис" in client.get(f"/vocab/{data['id']}").text


# --- переключатель «Перевод при выделении» (US4, T026) ---------------------------------------


def test_translate_toggle_sets_cookie_and_goes_back(client):
    html = client.get("/lessons").text
    assert 'action="/settings/translate"' in html and "Перевод при выделении" in html
    response = client.post(
        "/settings/translate",
        data={"show": "0"},
        headers={"referer": "http://testserver/lessons/1/texts"},
        follow_redirects=False,
    )
    assert response.status_code == 303 and response.headers["location"] == "/lessons/1/texts"
    assert "translate=0" in response.headers["set-cookie"]
    assert "Max-Age" in response.headers["set-cookie"]  # переживает перезапуск
    client.cookies.set("translate", "0")
    html = client.get("/lessons").text
    assert re.search(r'<html[^>]*data-translate="0"', html)
    menu = html[html.index('action="/settings/translate"') :][:800]
    assert re.search(r'class="on"[^>]*>выкл', menu)
    client.cookies.set("translate", "1")
    menu = client.get("/lessons").text
    menu = menu[menu.index('action="/settings/translate"') :][:800]
    assert re.search(r'class="on"[^>]*>вкл', menu)


# --- настройки перевода (T029) ---------------------------------------------------------------


def test_settings_show_translation_block(client, fake):
    get(client, "achètent")  # два перевода в запасе: форма и начальная форма
    html = client.get("/settings").text
    assert 'action="/settings/translator"' in html
    assert re.search(r'value="mymemory"[^>]*checked', html)
    assert "ключ не задан" in html and "DEEPL_API_KEY" in html
    assert 'name="mymemory_email"' in html and "уйдёт в сервис перевода" in html
    assert "Сохранённых переводов: 2" in html
    assert 'action="/settings/translations/clear"' in html


def test_choose_translator_and_email(client):
    response = client.post(
        "/settings/translator",
        data={"translator": "mymemory", "mymemory_email": " me@example.org "},
    )
    assert response.status_code == 200
    db = client.app.state.progress_db
    assert db.get_setting("mymemory_email") == "me@example.org"
    client.post("/settings/translator", data={"translator": "mymemory", "mymemory_email": ""})
    assert not db.get_setting("mymemory_email")


def test_deepl_needs_key(client):
    response = client.post("/settings/translator", data={"translator": "deepl"})
    assert "ключ DeepL не задан" in response.text
    assert client.app.state.progress_db.get_setting("translator") == "mymemory"
    client.app.state.settings.deepl_api_key = "k:fx"
    client.post("/settings/translator", data={"translator": "deepl"})
    assert client.app.state.progress_db.get_setting("translator") == "deepl"
    assert "ключ задан" in client.get("/settings").text


def test_clear_saved_translations(client, fake):
    get(client, "achètent")
    response = client.post("/settings/translations/clear")
    assert "Очищено: 2" in response.text
    assert "Сохранённых переводов: 0" in client.get("/settings").text


def test_translate_uses_word_before_locally(client, fake):
    data = client.get("/translate", params={"q": "entre", "before": "Paul"}).json()
    assert data["lemma"] == "entrer" and data["add_as"]["entry_type"] == "verb"
    assert fake.calls == ["entre", "entrer"]  # «Paul» во внешний сервис не уходит


def test_add_verb_homograph_from_text(client, fake, git_repo):
    data = add(client, text="commande", sentence="Il commande un café et un croissant.").json()
    assert data["text"] == "commander"
    assert vocab_file(git_repo, data["id"])["entry_type"] == "verb"
