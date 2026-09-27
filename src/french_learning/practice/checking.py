"""Проверка введённого ответа (research R5 функции 003; конституция VIII).

Строго к буквам, диакритике и дефисам; «клавиатурные» различия не ошибка: вид апострофа,
регистр, лишние и неразрывные пробелы, пробел перед знаками препинания, конечная точка.
Если ответ отличается от правильного только диакритикой — пользователь выбирает написание.
Модуль общий для словаря (003) и упражнений (004).
"""

from __future__ import annotations

import random
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

# Панель символов для ввода без французской раскладки (003 FR-040, 004 FR-010)
FRENCH_SYMBOLS = "éèêëàâçœùûüîïô"

_APOSTROPHES = str.maketrans({"’": "'", "ʼ": "'", "‘": "'", "`": "'", "´": "'"})
_SPACES = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([?!;:])")
_LIGATURES = {"œ": "oe", "æ": "ae"}

# Группы букв, у которых во французском бывают акценты (для вариантов написания)
_ACCENT_GROUPS = [
    "eéèêë",
    "aàâ",
    "uùûü",
    "iîï",
    "oô",
    "cç",
    "yÿ",
]


@dataclass
class CheckResult:
    status: Literal["correct", "wrong", "choose_spelling"]
    matched: str | None = None
    variants: list[str] = field(default_factory=list)


def normalize_keyboard(text: str) -> str:
    text = text.translate(_APOSTROPHES).replace(" ", " ").replace(" ", " ")
    text = _SPACES.sub(" ", text).strip()
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = text.rstrip(".").strip()
    return text.casefold()


def strip_diacritics(text: str) -> str:
    text = "".join(_LIGATURES.get(ch, ch) for ch in text.casefold())
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def check_french(answer: str, accepted: list[str], rng: random.Random | None = None) -> CheckResult:
    given = normalize_keyboard(answer)
    for variant in accepted:
        if given == normalize_keyboard(variant):
            return CheckResult("correct", matched=variant)
    for variant in accepted:
        if strip_diacritics(given) == strip_diacritics(normalize_keyboard(variant)):
            return CheckResult(
                "choose_spelling", matched=variant, variants=spelling_variants(variant, rng=rng)
            )
    return CheckResult("wrong")


def check_russian(answer: str, accepted: list[str]) -> CheckResult:
    def norm(text: str) -> str:
        return normalize_keyboard(text).replace("ё", "е")

    given = norm(answer)
    for variant in accepted:
        if given == norm(variant):
            return CheckResult("correct", matched=variant)
    return CheckResult("wrong")


def spelling_variants(correct: str, count: int = 3, rng: random.Random | None = None) -> list[str]:
    """Правильное написание и до `count` правдоподобных подмен акцентов, перемешанные."""
    rng = rng or random.Random()
    positions = [
        (i, group)
        for i, ch in enumerate(correct)
        for group in _ACCENT_GROUPS
        if ch.lower() in group
    ]
    candidates: set[str] = set()
    for i, group in positions:
        for replacement in group:
            if replacement != correct[i].lower():
                candidates.add(correct[:i] + replacement + correct[i + 1 :])
    if "œ" in correct:
        candidates.add(correct.replace("œ", "oe"))
    candidates.discard(correct)
    chosen = rng.sample(sorted(candidates), min(count, len(candidates)))
    result = [correct, *chosen]
    rng.shuffle(result)
    return result
