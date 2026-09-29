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
