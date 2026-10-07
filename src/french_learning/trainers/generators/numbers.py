"""Тренажёр «Числа»: 0–1000 цифрами → словами (оба написания верны; research R11) и, с 012,
словами → цифрами (на карточке основное написание, ответ — цифрами)."""

from __future__ import annotations

from french_learning.trainers.french_numbers import spellings
from french_learning.trainers.questions import Question, TrainerData

LIMIT = 1000

# Диапазоны по правилам записи (правка приёмки 009): ключ → (подпись, от, до)
RANGES = {
    "0-16": ("0–16", "основа: zéro … seize", 0, 16),
    "17-69": ("17–69", "десятки: dix-sept … soixante-neuf", 17, 69),
    "70-99": ("70–99", "soixante-dix, quatre-vingts, quatre-vingt-dix", 70, 99),
    "0-100": ("0–100", "всё до ста", 0, 100),
    "100-999": ("100–999", "сотни: cent, deux cents …", 100, 999),
    "0-1000": ("0–1000", "все числа", 0, 1000),
}
DEFAULT_RANGE = "0-100"

# 012, пункт 10: форматы вопросов (ключ → (подпись, префикс ключа вопроса))
FORMATS = {
    "digits_to_words": ("75 → soixante-quinze", "numbers:"),
    "words_to_digits": ("soixante-quinze → 75", "numbers-fr:"),
}
DEFAULT_FORMAT = "digits_to_words"


def parse_range(value: str, start: str = "", end: str = "") -> tuple[int, int]:
    """Диапазон из формы: готовый ключ или свой («custom» + от / до); границы 0–1000."""
    if value in RANGES:
        _label, _hint, low, high = RANGES[value]
        return low, high
    try:
        low, high = int(start), int(end)
    except ValueError:
        _label, _hint, low, high = RANGES[DEFAULT_RANGE]
        return low, high
    low, high = sorted((max(0, min(LIMIT, low)), max(0, min(LIMIT, high))))
    return low, high


def in_range(key: str, low: int, high: int) -> bool:
    prefix, _sep, number = key.partition(":")
    return prefix in ("numbers", "numbers-fr") and low <= int(number) <= high


def in_format(key: str, fmt: str) -> bool:
    return key.startswith(FORMATS.get(fmt, FORMATS[DEFAULT_FORMAT])[1])


def generate(data: TrainerData) -> list[Question]:
    questions = []
    for n in range(LIMIT + 1):
        written = spellings(n)
        questions.append(
            Question(
                key=f"numbers:{n}",
                prompt=str(n),
                answers=written,
                hint="напишите словами",
                full=written[0],
            )
        )
        questions.append(
            Question(
                key=f"numbers-fr:{n}",
                prompt=written[0],
                answers=[str(n)],
                hint="напишите цифрами",
                full=str(n),
            )
        )
    return questions
