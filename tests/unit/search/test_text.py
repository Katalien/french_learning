"""Нормализация, слова с позициями и совпадение (007, research R2, R3; FR-003–FR-005)."""

import pytest

from french_learning.search.text import find, normalize, query_tokens, tokens


def norms(text):
    return [t.norm for t in tokens(text)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Été", "ete"),
        ("Français", "francais"),
        ("ŒUF", "oeuf"),
        ("ex æquo", "ex aequo"),
        ("Ёжик", "ежик"),
        ("naïf", "naif"),
    ],
)
def test_normalize(text, expected):
    assert normalize(text) == expected


def test_tokens_split_on_apostrophes_hyphens_and_punctuation():
    assert norms("l'eau") == norms("l’eau") == norms("lʼeau") == ["l", "eau"]
    assert norms("peut-être, oui !") == ["peut", "etre", "oui"]
    assert norms("  Il y a  ") == ["il", "y", "a"]


def test_tokens_keep_positions_in_original_text():
    text = "Le café, l'été."
    found = tokens(text)
    assert [text[t.start : t.end] for t in found] == ["Le", "café", "l", "été"]
    assert [t.norm for t in found] == ["le", "cafe", "l", "ete"]


def test_query_tokens_need_two_characters():
    assert query_tokens("m") == []
    assert query_tokens("  ?! ") == []
    assert query_tokens("ma") == ["ma"]
    assert query_tokens("Il y a") == ["il", "y", "a"]


def test_single_word_matches_by_start():
    doc = norms("je veux manger une mangue")
    assert find(doc, ["mang"]) == [2, 4]
    assert find(doc, ["ange"]) == []
    assert find(doc, ["manger"]) == [2]


def test_phrase_words_in_a_row_last_by_start():
    doc = norms("Il y avait un chat. Il a y pensé.")
    assert find(doc, ["il", "y", "a"]) == [0]
    assert find(doc, ["y", "avait"]) == [1]
    assert find(doc, ["il", "a"]) == [5]  # «Il a» — да, «il y a» с другим порядком — нет
    assert find(doc, ["i", "y"]) == []  # не последнее слово — целиком


def test_find_accepts_token_objects():
    assert find(tokens("peut-être"), ["peut", "etre"]) == [0]
