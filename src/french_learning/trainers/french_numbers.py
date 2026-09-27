"""Запись чисел 0–1000 по-французски (research R11 функции 004).

Первый вариант — традиционный (дефисы только между десятками и единицами меньше ста,
«et» без дефисов); второй — по реформе орфографии 1990 года (дефисы между всеми частями).
Оба написания правильные и засчитываются.
"""

from __future__ import annotations

_UNITS = [
    "zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf",
    "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize",
]  # fmt: skip
_TENS = {20: "vingt", 30: "trente", 40: "quarante", 50: "cinquante", 60: "soixante"}


def _below_100(n: int) -> list[str]:
    """Части числа < 100; «et» — отдельная часть."""
    if n <= 16:
        return [_UNITS[n]]
    if n < 20:
        return ["dix-" + _UNITS[n - 10]]
    if n < 70:
        tens, unit = divmod(n, 10)
        word = _TENS[tens * 10]
        if unit == 0:
            return [word]
        if unit == 1:
            return [word, "et", "un"]
        return [f"{word}-{_UNITS[unit]}"]
    if n < 80:
        rest = n - 60
        if rest == 11:
            return ["soixante", "et", "onze"]
        return ["soixante-" + _below_100(rest)[0]]
    rest = n - 80
    if rest == 0:
        return ["quatre-vingts"]
    return ["quatre-vingt-" + _below_100(rest)[0]]


def _parts(n: int) -> list[str]:
    if n < 100:
        return _below_100(n)
    if n == 1000:
        return ["mille"]
    hundreds, rest = divmod(n, 100)
    head = ["cent"] if hundreds == 1 else [_UNITS[hundreds], "cents" if rest == 0 else "cent"]
    if rest == 0:
        return head
    tail = _below_100(rest)
    # «quatre-vingts» теряет -s, если за ним что-то следует; здесь он последний — остаётся
    return head + tail


def spellings(n: int) -> list[str]:
    if not 0 <= n <= 1000:
        raise ValueError("поддерживаются числа от 0 до 1000")
    parts = _parts(n)
    traditional = " ".join(parts)
    reform = "-".join(parts)
    return [traditional] if reform == traditional else [traditional, reform]
