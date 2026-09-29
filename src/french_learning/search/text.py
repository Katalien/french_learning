"""Нормализация, слова с позициями и совпадение (007, research R2, R3; FR-003–FR-005).

Одно правило для документа и запроса: регистр, диакритика, `œ`/`oe`, `æ`/`ae`, «ё»/«е»
не различаются; апострофы, дефисы и знаки — разделители слов. Та же нормализация повторена
в `static/js/search.js` для подсветки на странице.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

_WORD = re.compile(r"[^\W_]+")
_LIGATURES = str.maketrans({"œ": "oe", "æ": "ae", "ё": "е"})
MIN_QUERY = 2  # символов (FR-002)


@dataclass(frozen=True)
class Token:
    norm: str
    start: int
    end: int


def normalize(text: str) -> str:
    folded = text.casefold().translate(_LIGATURES)
    decomposed = unicodedata.normalize("NFKD", folded)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def tokens(text: str) -> list[Token]:
    """Слова текста: нормализованные, с местом в исходном тексте (для фрагмента)."""
    # «ʼ» Unicode считает буквой; замена одного знака одним — позиции не сдвигаются
    plain = text.replace("ʼ", "'")
    return [Token(normalize(m.group()), m.start(), m.end()) for m in _WORD.finditer(plain)]


def query_tokens(query: str) -> list[str]:
    """Слова запроса; короче 2 символов (или одни знаки) — пустой запрос."""
    words = [t.norm for t in tokens(query)]
    return words if len("".join(words)) >= MIN_QUERY else []


def _norm(token: Token | str) -> str:
    return token.norm if isinstance(token, Token) else token


def find(doc: Sequence[Token | str], query: Sequence[str]) -> list[int]:
    """Позиции, где слова запроса идут подряд; последнее — по началу слова."""
    if not query:
        return []
    words = [_norm(t) for t in doc]
    *head, last = query
    size = len(query)
    found = []
    for i in range(len(words) - size + 1):
        if words[i + size - 1].startswith(last) and all(
            words[i + k] == word for k, word in enumerate(head)
        ):
            found.append(i)
    return found


SNIPPET_BEFORE = 8  # слов до совпадения
SNIPPET_AFTER = 12  # слов после — вместе около 20 (FR-012)


def snippet(text: str, toks: Sequence[Token], at: int, size: int) -> list[tuple[str, bool]]:
    """Фрагмент исходного текста вокруг совпадения: кусочки (текст, найдено), «…» по краям."""
    first = max(0, at - SNIPPET_BEFORE)
    last = min(len(toks), at + size + SNIPPET_AFTER)
    # у края текста — до самого края (точка после последнего слова не теряется)
    start = toks[first].start if first > 0 else 0
    end = toks[last - 1].end if last < len(toks) else len(text)
    hit_start, hit_end = toks[at].start, toks[at + size - 1].end
    head = ("…" if first > 0 else "") + _flat(text[start:hit_start])
    tail = _flat(text[hit_end:end]) + ("…" if last < len(toks) else "")
    return [(head, False), (_flat(text[hit_start:hit_end]), True), (tail, False)]


def _flat(part: str) -> str:
    return part.replace("\n", " ")
