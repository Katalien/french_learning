"""Нормализация выделенного фрагмента (006, data-model «Нормализация ключа», research R9).

Одна функция ключа — для запаса переводов, поиска в словаре и проверки на дубль.
"""

import re

MAX_LENGTH = 500  # ориентир лимита сервиса на один запрос (spec, Edge Cases)

_APOSTROPHES = str.maketrans({"’": "'", "ʼ": "'", "`": "'"})
_EDGE = ' .,;:!?…»«"“”()'
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
# знак конца предложения, после которого идёт ещё текст
_SENTENCE_INSIDE = re.compile(r"[.!?…]+[\s»\"”)]*\s+\S")


def normalize_key(text: str) -> str:
    key = text.casefold().translate(_APOSTROPHES)
    key = " ".join(key.split())
    return key.strip(_EDGE)


def has_cyrillic(text: str) -> bool:
    return bool(_CYRILLIC.search(text))


def is_multi_sentence(text: str) -> bool:
    """Больше одного предложения (абзац) — у такого выделения нет «+ В словарь»."""
    return bool(_SENTENCE_INSIDE.search(" ".join(text.split())))


def is_single_word(text: str) -> bool:
    key = normalize_key(text)
    return bool(key) and " " not in key and "'" not in key


def too_long(text: str) -> bool:
    return len(text) > MAX_LENGTH
