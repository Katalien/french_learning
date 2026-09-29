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
# после этих слов идёт глагол: подлежащее, отрицание, возвратное местоимение
_SUBJECTS = {"je", "j'", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles", "qui"}
_BEFORE_VERB = _SUBJECTS | {"ne", "n'", "se", "s'", "me", "m'", "te", "t'"}
_NOT_SUBJECT = {
    *_ARTICLES,
    "l'",
    "du",
    "au",
    "aux",
    "ce",
    "cet",
    "cette",
    "ces",
    "mon",
    "ma",
    "mes",
}


@dataclass
class AddAs:
    text: str
    entry_type: str  # word | verb | phrase
    article: str | None = None
    gender: str | None = None


def _is_subject(before: str | None) -> bool:
    """Перед словом подлежащее (il, elle, имя с заглавной) или отрицание — дальше глагол."""
    if not before:
        return False
    key = normalize_key(before)
    if key in _BEFORE_VERB:
        return True
    return before[:1].isupper() and key not in _NOT_SUBJECT


def _verb_reading(word: str) -> str | None:
    """Глагол на -er для омонима (entre → entrer, commande → commander), если он есть."""
    for ending in ("es", "e"):
        if word.endswith(ending):
            candidate = word[: -len(ending)] + "er"
            return candidate if simplemma.is_known(candidate, lang="fr") else None
    return None


def _lemma(word: str, before: str | None = None) -> str:
    lemma = simplemma.lemmatize(word, lang="fr")
    # «Paul entre», «il commande», «tu commandes» — глаголы, а не предлог и не существительное;
    # после имени с заглавной — только если словарная форма совпала (иначе «Deux pommes»)
    pronoun = normalize_key(before or "") in _BEFORE_VERB
    if (pronoun and not lemma.endswith(_VERB_ENDINGS)) or (lemma == word and _is_subject(before)):
        return _verb_reading(word) or lemma
    return lemma


def _split_elision(token: str) -> tuple[str | None, str]:
    match = _ELISION.match(token)
    return (match.group(1), match.group(2)) if match else (None, token)


def lemma_of(text: str, before: str | None = None) -> str | None:
    """Начальная форма одного слова, если она отличается от выделенного.

    `before` — слово перед выделенным (для омонимов вроде entre / entrer).
    """
    key = normalize_key(text)
    if not key or " " in key:
        return None
    prefix, word = _split_elision(key)
    lemma = _lemma(word, before if prefix is None else None)
    return lemma if lemma and lemma != key else None


def _is_verb(form: str, lemma: str) -> bool:
    if lemma == form or not lemma.endswith(_VERB_ENDINGS):
        return False
    return form not in (lemma + "s", lemma + "x")  # livres → livre — множественное, не глагол


def _word(word: str, article: str | None, before: str | None = None) -> AddAs:
    lemma = _lemma(word, None if article else before) or word
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
        if previous in _GENDERED:
            return _word(word, previous)
        return _word(word, None, before)
    return AddAs(" ".join(text.split()).strip(" ,;:"), "phrase")
