"""Порядок «словарь → запас → сервис», запас без дублей и без ошибок.

006, FR-006, FR-009, SC-003.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from french_learning.practice.db import ProgressDB
from french_learning.translate.cache import TranslationCache
from french_learning.translate.providers import TranslationUnavailable, TranslatorNotConfigured
from french_learning.translate.service import TranslationService


class FakeTranslator:
    name = "mymemory"

    def __init__(self, answers: dict[str, str] | None = None, fail: bool = False) -> None:
        self.answers = answers or {}
        self.fail = fail
        self.calls: list[str] = []

    def translate(self, text: str) -> str:
        self.calls.append(text)
        if self.fail:
            raise TranslationUnavailable("нет сети")
        return self.answers.get(text, f"<{text}>")


def entry(entry_id, text, translations, article=None, hidden=False):
    return SimpleNamespace(
        id=entry_id,
        text=text,
        article=article,
        hidden=hidden,
        translations=[SimpleNamespace(text=t) for t in translations],
    )


@pytest.fixture
def db(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    yield db
    db.close()


@pytest.fixture
def cache(db):
    return TranslationCache(db)


def service(cache, translator):
    return TranslationService(cache, lambda: translator)


# --- запас ------------------------------------------------------------------------------------


def test_cache_one_record_per_normalized_key(cache):
    cache.put("Pomme.", "яблоко", "mymemory")
    cache.put("pomme", "яблоко!", "mymemory")
    assert cache.get("  POMME ") == ("яблоко", "mymemory")
    assert cache.count() == 1
    assert cache.clear() == 1
    assert cache.count() == 0 and cache.get("pomme") is None


# --- порядок поиска ---------------------------------------------------------------------------


def test_dictionary_first_by_selected_text_without_service(cache):
    translator = FakeTranslator()
    words = [entry("voc-1", "pomme", ["яблоко"], article="la")]
    result = service(cache, translator).translate("la pomme", words)
    assert result.translation == "яблоко" and result.source == "dictionary"
    assert result.entry == {"id": "voc-1", "translation": "яблоко"}
    assert result.can_add is False
    assert translator.calls == []


def test_dictionary_by_lemma_and_hidden_entries_count(cache):
    translator = FakeTranslator()
    words = [entry("voc-2", "acheter", ["покупать", "купить"], hidden=True)]
    result = service(cache, translator).translate("achètent", words)
    assert result.source == "dictionary"
    assert result.translation == "покупать, купить"
    assert result.entry["id"] == "voc-2"
    assert result.lemma == "acheter" and result.lemma_translation == "покупать, купить"
    assert translator.calls == []


def test_service_answer_is_cached_once_and_reused(cache):
    translator = FakeTranslator({"achètent": "покупают", "acheter": "покупать"})
    first = service(cache, translator).translate("achètent", [])
    assert (first.translation, first.source) == ("покупают", "service")
    assert first.lemma == "acheter" and first.lemma_translation == "покупать"
    assert first.can_add is True
    assert first.add_as == {"text": "acheter", "entry_type": "verb"}
    assert translator.calls == ["achètent", "acheter"]

    again = service(cache, translator).translate("Achètent", [])
    assert (again.translation, again.source) == ("покупают", "cache")
    assert translator.calls == ["achètent", "acheter"]  # SC-003: сервис больше не вызывается
    assert cache.count() == 2


def test_unavailable_is_not_cached_and_lemma_still_shown(cache):
    translator = FakeTranslator(fail=True)
    result = service(cache, translator).translate("achètent", [])
    assert result.translation is None and result.source == "none"
    assert result.error == "Перевод сейчас недоступен"
    assert result.lemma == "acheter" and result.lemma_translation is None
    assert result.can_add is False
    assert cache.count() == 0
    assert translator.calls == ["achètent"]  # после отказа за формой не ходим


def test_translator_not_configured_is_unavailable(cache):
    def broken():
        raise TranslatorNotConfigured("ключ DeepL не задан")

    result = TranslationService(cache, broken).translate("pomme", [])
    assert result.translation is None and result.error == "Перевод сейчас недоступен"


def test_phrase_and_paragraph(cache):
    translator = FakeTranslator()
    phrase = service(cache, translator).translate("il y a", [])
    assert phrase.lemma is None
    assert phrase.add_as == {"text": "il y a", "entry_type": "phrase"}
    assert phrase.can_add is True
    paragraph = service(cache, translator).translate("Il y a du monde. Claire mange.", [])
    assert paragraph.translation and paragraph.can_add is False


def test_too_long_is_not_sent(cache):
    translator = FakeTranslator()
    result = service(cache, translator).translate("a" * 501, [])
    assert result.translation is None
    assert result.error == "Выделите меньше (до 500 символов)"
    assert translator.calls == []


def test_empty_or_cyrillic_is_rejected(cache):
    for text in ("  ", "яблоко"):
        with pytest.raises(ValueError):
            service(cache, FakeTranslator()).translate(text, [])


def test_to_dict_has_contract_fields(cache):
    data = service(cache, FakeTranslator()).translate("pomme", []).to_dict()
    assert set(data) == {
        "text",
        "translation",
        "source",
        "error",
        "lemma",
        "lemma_translation",
        "entry",
        "can_add",
        "add_as",
    }


def test_service_capital_letter_follows_selection(cache):
    # MyMemory часто пишет перевод с заглавной — для строчного слова это лишнее
    translator = FakeTranslator({"serveuse": "Официантка", "Bonjour": "Здравствуйте"})
    assert service(cache, translator).translate("serveuse", []).translation == "официантка"
    assert service(cache, translator).translate("Bonjour", []).translation == "Здравствуйте"
