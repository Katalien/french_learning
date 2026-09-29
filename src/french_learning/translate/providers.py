"""Сервисы перевода fr → ru (006, research R2): MyMemory без ключа и DeepL с ключом.

HTTP — стандартный `urllib`, тайм-аут 5 с. Во внешний сервис уходит только переводимый текст
(и почта для MyMemory, если пользователь её указал) — принцип IX конституции.
Новый сервис — новый класс с методом `translate`, остальной код не меняется.
"""

from __future__ import annotations

import html
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Protocol

TIMEOUT = 5  # секунд (spec, Edge Cases: сервис медленный — «недоступен»)

MYMEMORY_URL = "https://api.mymemory.translated.net/get"
DEEPL_FREE_URL = "https://api-free.deepl.com/v2/translate"
DEEPL_PRO_URL = "https://api.deepl.com/v2/translate"


class TranslationUnavailable(Exception):
    """Сервис не ответил, ответил ошибкой или исчерпан лимит — перевода сейчас нет."""


class TranslatorNotConfigured(Exception):
    """Сервис нельзя использовать без настройки (например, DeepL без ключа)."""


class Translator(Protocol):
    name: str

    def translate(self, text: str) -> str: ...


def _fetch(request: urllib.request.Request) -> bytes:
    try:
        # urllib.request.urlopen берётся при вызове — так его подменяют тесты
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read()
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise TranslationUnavailable(str(error)) from error


def _json(raw: bytes) -> dict:
    try:
        data = json.loads(raw)
    except ValueError as error:
        raise TranslationUnavailable("ответ сервиса не разобран") from error
    if not isinstance(data, dict):
        raise TranslationUnavailable("ответ сервиса не разобран")
    return data


class MyMemory:
    name = "mymemory"

    def __init__(self, email: str | None = None) -> None:
        self.email = email.strip() if email and email.strip() else None

    def translate(self, text: str) -> str:
        params = {"q": text, "langpair": "fr|ru"}
        if self.email:
            params["de"] = self.email
        url = f"{MYMEMORY_URL}?{urllib.parse.urlencode(params)}"
        data = _json(_fetch(urllib.request.Request(url)))
        status = str(data.get("responseStatus", ""))
        translated = (data.get("responseData") or {}).get("translatedText") or ""
        translated = html.unescape(str(translated)).strip()
        if status != "200" or not translated or translated.upper().startswith("MYMEMORY WARNING"):
            raise TranslationUnavailable(f"MyMemory: {status} {translated[:80]}")
        return translated


class DeepL:
    name = "deepl"

    def __init__(self, api_key: str | None) -> None:
        if not api_key or not api_key.strip():
            raise TranslatorNotConfigured("ключ DeepL не задан")
        self.api_key = api_key.strip()

    def translate(self, text: str) -> str:
        # ключи бесплатного тарифа оканчиваются на ":fx" и работают с отдельным адресом
        url = DEEPL_FREE_URL if self.api_key.endswith(":fx") else DEEPL_PRO_URL
        body = urllib.parse.urlencode({"text": text, "source_lang": "FR", "target_lang": "RU"})
        request = urllib.request.Request(
            url,
            data=body.encode(),
            headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
            method="POST",
        )
        data = _json(_fetch(request))
        items = data.get("translations") or []
        translated = str(items[0].get("text") or "").strip() if items else ""
        if not translated:
            raise TranslationUnavailable("DeepL: пустой ответ")
        return translated


def make_translator(
    name: str, *, email: str | None = None, deepl_key: str | None = None
) -> Translator:
    if name == "mymemory":
        return MyMemory(email)
    if name == "deepl":
        return DeepL(deepl_key)
    raise ValueError(f"неизвестный сервис перевода: {name}")
