"""Сервисы перевода MyMemory и DeepL (006, research R2).

Сеть подменяется — настоящих запросов нет.
"""

import io
import json
import urllib.error
import urllib.parse
import urllib.request

import pytest

from french_learning.translate.providers import (
    DeepL,
    MyMemory,
    TranslationUnavailable,
    TranslatorNotConfigured,
    make_translator,
)


class FakeNet:
    """Подмена `urllib.request.urlopen`: запоминает запросы, отдаёт заданный ответ."""

    def __init__(self, monkeypatch, body=None, error=None):
        self.requests: list[urllib.request.Request] = []
        self.body = body
        self.error = error
        monkeypatch.setattr(urllib.request, "urlopen", self)

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        self.timeout = timeout
        if self.error is not None:
            raise self.error
        data = self.body if isinstance(self.body, bytes) else json.dumps(self.body).encode()
        return io.BytesIO(data)

    @property
    def query(self) -> dict[str, list[str]]:
        return urllib.parse.parse_qs(urllib.parse.urlsplit(self.requests[-1].full_url).query)


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(b"{}"))


def mymemory_body(text: str, status=200) -> dict:
    return {"responseData": {"translatedText": text}, "responseStatus": status}


# --- MyMemory ---------------------------------------------------------------------------------


def test_mymemory_success_sends_only_text_and_langpair(monkeypatch):
    net = FakeNet(monkeypatch, mymemory_body("покупают"))
    assert MyMemory().translate("achètent") == "покупают"
    assert net.query == {"q": ["achètent"], "langpair": ["fr|ru"]}
    assert net.requests[-1].full_url.startswith("https://api.mymemory.translated.net/get?")
    assert net.timeout == 5


def test_mymemory_sends_email_only_when_set(monkeypatch):
    net = FakeNet(monkeypatch, mymemory_body("яблоко"))
    MyMemory(email="me@example.org").translate("pomme")
    assert net.query["de"] == ["me@example.org"]


def test_mymemory_unescapes_html_entities(monkeypatch):
    FakeNet(monkeypatch, mymemory_body("это &#39;дом&#39;"))
    assert MyMemory().translate("maison") == "это 'дом'"


@pytest.mark.parametrize(
    "body",
    [
        mymemory_body("MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY."),
        mymemory_body("", 200),
        mymemory_body("что-то", 403),
        mymemory_body("что-то", "429"),
        {"responseData": None, "responseStatus": 500},
        b"not json",
    ],
)
def test_mymemory_bad_answers_are_unavailable(monkeypatch, body):
    FakeNet(monkeypatch, body)
    with pytest.raises(TranslationUnavailable):
        MyMemory().translate("pomme")


@pytest.mark.parametrize(
    "error",
    [http_error(429), urllib.error.URLError("no network"), TimeoutError("slow"), OSError("x")],
)
def test_network_problems_are_unavailable(monkeypatch, error):
    FakeNet(monkeypatch, error=error)
    with pytest.raises(TranslationUnavailable):
        MyMemory().translate("pomme")


# --- DeepL ------------------------------------------------------------------------------------


def test_deepl_success_sends_text_with_key_in_header(monkeypatch):
    net = FakeNet(
        monkeypatch, {"translations": [{"detected_source_language": "FR", "text": "яблоко"}]}
    )
    assert DeepL("secret:fx").translate("pomme") == "яблоко"
    request = net.requests[-1]
    assert request.full_url == "https://api-free.deepl.com/v2/translate"
    assert request.get_header("Authorization") == "DeepL-Auth-Key secret:fx"
    sent = urllib.parse.parse_qs(request.data.decode())
    assert sent == {"text": ["pomme"], "source_lang": ["FR"], "target_lang": ["RU"]}
    assert "secret" not in request.data.decode()


def test_deepl_pro_key_uses_pro_address(monkeypatch):
    net = FakeNet(monkeypatch, {"translations": [{"text": "яблоко"}]})
    DeepL("secret").translate("pomme")
    assert net.requests[-1].full_url == "https://api.deepl.com/v2/translate"


@pytest.mark.parametrize("code", [403, 456, 500])
def test_deepl_http_errors_are_unavailable(monkeypatch, code):
    FakeNet(monkeypatch, error=http_error(code))
    with pytest.raises(TranslationUnavailable):
        DeepL("secret:fx").translate("pomme")


def test_deepl_empty_answer_is_unavailable(monkeypatch):
    FakeNet(monkeypatch, {"translations": []})
    with pytest.raises(TranslationUnavailable):
        DeepL("secret:fx").translate("pomme")


def test_deepl_without_key_is_a_settings_error():
    with pytest.raises(TranslatorNotConfigured):
        DeepL(None)
    with pytest.raises(TranslatorNotConfigured):
        DeepL("  ")


# --- выбор сервиса ----------------------------------------------------------------------------


def test_make_translator_by_name():
    assert isinstance(make_translator("mymemory"), MyMemory)
    assert make_translator("mymemory", email="me@example.org").email == "me@example.org"
    assert make_translator("mymemory", email="").email is None
    assert isinstance(make_translator("deepl", deepl_key="k:fx"), DeepL)
    with pytest.raises(TranslatorNotConfigured):
        make_translator("deepl", deepl_key=None)
    with pytest.raises(ValueError):
        make_translator("google")
