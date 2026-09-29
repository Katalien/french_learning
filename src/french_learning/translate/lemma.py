"""Начальная форма и вид записи словаря для выделенного (006, research R5, FR-010, FR-012).

Начальная форма — локально, библиотекой simplemma (без сети и без ИИ). Род — как при быстром
вводе (003): только по артиклю, в самом выделении («une crêpe») или прямо перед ним
в предложении. Остальное (часть речи, спряжение) дополнит `/complete-words`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import simplemma

from french_learning.translate.normalize import normalize_key
from french_learning.vocab.parsing import _GENDER, _definite

_ELISION = re.compile(r"^(l|d|j|m|t|s|n|c|qu)'(.+)$")
_GENDERED = ("le", "la", "un", "une")
_ARTICLES = (*_GENDERED, "les", "des")
_VERB_ENDINGS = ("er", "ir", "re", "oir")


@dataclass
class AddAs:
    text: str
    entry_type: str  # word | verb | phrase
    article: str | None = None
    gender: str | None = None


def _lemma(word: str) -> str:
    return simplemma.lemmatize(word, lang="fr")


def _split_elision(token: str) -> tuple[str | None, str]:
    match = _ELISION.match(token)
    return (match.group(1), match.group(2)) if match else (None, token)


def lemma_of(text: str) -> str | None:
    """Начальная форма одного слова, если она отличается от выделенного."""
    key = normalize_key(text)
    if not key or " " in key:
        return None
    _prefix, word = _split_elision(key)
    lemma = _lemma(word)
    return lemma if lemma and lemma != key else None


def _is_verb(form: str, lemma: str) -> bool:
    if lemma == form or not lemma.endswith(_VERB_ENDINGS):
        return False
    return form not in (lemma + "s", lemma + "x")  # livres → livre — множественное, не глагол


def _word(word: str, article: str | None) -> AddAs:
    lemma = _lemma(word) or word
    gender = _GENDER.get(article or "")
    if article in _GENDERED:
        return AddAs(lemma, "word", _definite(article, lemma), gender)
    if article == "l":
        return AddAs(lemma, "word", "l'", None)
    if article in ("les", "des"):
        return AddAs(lemma, "word")
    return AddAs(lemma, "verb" if _is_verb(word, lemma) else "word")


def add_as(text: str, before: str | None = None) -> AddAs:
    """Что добавит «+ В словарь»: одно слово — начальная форма, несколько — фраза как есть.

    `before` — слово перед выделением в предложении (для рода по артиклю).
    """
    tokens = normalize_key(text).split()
    if len(tokens) == 2 and tokens[0] in _ARTICLES and "'" not in tokens[1]:
        return _word(tokens[1], tokens[0])
    if len(tokens) == 1:
        prefix, word = _split_elision(tokens[0])
        if prefix == "l":
            return _word(word, "l")
        previous = normalize_key(before or "")
        return _word(word, previous if previous in _GENDERED else None)
    return AddAs(" ".join(text.split()).strip(" ,;:"), "phrase")
