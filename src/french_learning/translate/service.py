"""Перевод выделенного: словарь пользователя → запас → внешний сервис (006, FR-006, data-model).

Результат — то, что показывает подсказка: перевод, начальная форма, есть ли слово в словаре
и что добавит «+ В словарь».
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from typing import Any

from french_learning.translate.cache import TranslationCache
from french_learning.translate.lemma import add_as, lemma_of
from french_learning.translate.normalize import (
    MAX_LENGTH,
    has_cyrillic,
    is_multi_sentence,
    normalize_key,
    too_long,
)
from french_learning.translate.providers import (
    TranslationUnavailable,
    Translator,
    TranslatorNotConfigured,
)
from french_learning.vocab.entries import display_fr

UNAVAILABLE = "Перевод сейчас недоступен"
TOO_LONG = f"Выделите меньше (до {MAX_LENGTH} символов)"


@dataclass
class TranslationResult:
    text: str
    translation: str | None = None
    source: str = "none"  # dictionary | cache | service | none
    error: str | None = None
    lemma: str | None = None
    lemma_translation: str | None = None
    entry: dict | None = None
    can_add: bool = False
    add_as: dict | None = None
    head: str | None = None  # существительное с определённым артиклем: «les pommes»
    gender: str | None = None  # m | f — род в скобках рядом (макет 2026-09-30, А2)

    def to_dict(self) -> dict:
        return asdict(self)


def _entry_translation(entry: Any) -> str:
    return ", ".join(t.text for t in entry.translations)


def find_entry(entries: Iterable[Any], *texts: str | None) -> Any | None:
    """Запись словаря (в том числе скрытая) по тексту — с артиклем или без."""
    wanted = [normalize_key(t) for t in texts if t]
    by_key: dict[str, Any] = {}
    for entry in entries:
        for key in (normalize_key(entry.text), normalize_key(display_fr(entry))):
            by_key.setdefault(key, entry)
    return next((by_key[k] for k in wanted if k in by_key), None)


_DEFINITE = {"un": "le", "une": "la", "des": "les", "le": "le", "la": "la", "les": "les", "l": "l'"}


def _joined(article: str, word: str) -> str:
    return f"{article}{word}" if article == "l'" else f"{article} {word}"


def noun_head(
    text: str, before: str | None, entry: Any | None, gender: str | None
) -> tuple[str | None, str | None]:
    """Существительное с определённым артиклем и род (m / f) — для заголовка подсказки.

    Род — из записи словаря, иначе по артиклю (как при добавлении, `add_as`). Артикль —
    из текста (неопределённый → определённый), иначе из словаря; у другой формы — «les».
    """
    gender = getattr(entry, "gender", None) or gender
    if gender not in ("m", "f"):
        return None, None
    words = " ".join(text.split()).strip(" ,;:.!?")
    key = normalize_key(words)
    tokens = key.split()
    if len(tokens) == 2 and tokens[0] in _DEFINITE:  # «une crêpe» — артикль в выделении
        return _joined(_DEFINITE[tokens[0]], words.split(" ", 1)[1]), gender
    if len(tokens) != 1:
        return None, None
    if "'" in key:  # «l'eau» — артикль уже в слове
        return words, gender
    previous = normalize_key(before or "").rstrip("'")
    if previous in _DEFINITE:
        return _joined(_DEFINITE[previous], words), gender
    if entry is not None and entry.article:
        if normalize_key(entry.text) == key:
            return _joined(entry.article, words), gender
        return _joined("les", words), gender  # другая форма (pommes) — множественное число
    return None, gender


class TranslationService:
    def __init__(self, cache: TranslationCache, translator: Callable[[], Translator]) -> None:
        self.cache = cache
        self.translator = translator  # создаётся при запросе — настройки могли измениться

    def _external(self, text: str) -> tuple[str | None, str]:
        """(перевод, источник) из запаса или сервиса; ответ сервиса — в запас."""
        cached = self.cache.get(text)
        if cached:
            return cached[0], "cache"
        try:
            translator = self.translator()
            translation = translator.translate(text)
        except (TranslationUnavailable, TranslatorNotConfigured):
            return None, "none"
        if translation.isupper() and len(translation) > 1 and not text.isupper():
            translation = translation.lower()  # MyMemory: «ЗАКАЗ»
        if text[:1].islower() and translation[:1].isupper():
            translation = translation[:1].lower() + translation[1:]  # MyMemory: «Официант»
        self.cache.put(text, translation, translator.name)
        return translation, "service"

    def translate(
        self, text: str, entries: Iterable[Any], before: str | None = None
    ) -> TranslationResult:
        """`before` — слово перед выделенным (только для начальной формы, наружу не уходит)."""
        text = " ".join(text.split())
        if not text or has_cyrillic(text):
            raise ValueError("переводится только французский текст")
        result = TranslationResult(text=text)
        if too_long(text):
            result.error = TOO_LONG
            return result
        entries = list(entries)
        result.lemma = lemma_of(text, before)
        target = add_as(text, before)
        result.add_as = {"text": target.text, "entry_type": target.entry_type}

        entry = find_entry(entries, text, target.text, result.lemma)
        if entry is not None:
            result.entry = {"id": entry.id, "translation": _entry_translation(entry)}
            result.translation, result.source = result.entry["translation"], "dictionary"
        else:
            result.translation, result.source = self._external(text)
        if result.translation is None:
            result.error = UNAVAILABLE

        noun = entry or find_entry(entries, result.lemma)
        result.head, result.gender = noun_head(text, before, noun, add_as(text, before).gender)

        if result.lemma:
            lemma_entry = find_entry(entries, result.lemma)
            if lemma_entry is not None:
                result.lemma_translation = _entry_translation(lemma_entry)
            elif result.translation is not None:  # сервис недоступен — за формой не ходим
                result.lemma_translation, _source = self._external(result.lemma)

        result.can_add = (
            result.entry is None and result.translation is not None and not is_multi_sentence(text)
        )
        return result
