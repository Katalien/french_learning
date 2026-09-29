"""Нормализация выделенного текста (006, data-model «Нормализация ключа», research R9)."""

from french_learning.translate.normalize import (
    MAX_LENGTH,
    has_cyrillic,
    is_multi_sentence,
    is_single_word,
    normalize_key,
    too_long,
)


def test_key_ignores_case_spaces_apostrophes_and_final_punctuation():
    assert normalize_key("  Il  y a ") == "il y a"
    assert normalize_key("L’école") == normalize_key("l'école") == "l'école"
    assert normalize_key("lʼami") == "l'ami"
    assert normalize_key("Bonjour !") == "bonjour"
    assert normalize_key("«Merci…»") == "merci"
    assert normalize_key("Elles achètent des pommes.") == "elles achètent des pommes"


def test_key_keeps_letters_and_diacritics():
    assert normalize_key("Été") == "été"
    assert normalize_key("peut-être") == "peut-être"


def test_cyrillic_detected():
    assert has_cyrillic("pomme — яблоко")
    assert not has_cyrillic("pomme, fromage et crêpe")


def test_multi_sentence_only_when_sentence_end_inside():
    assert not is_multi_sentence("Elles achètent des pommes.")
    assert not is_multi_sentence("Elles achètent des pommes")
    assert not is_multi_sentence("Il y a beaucoup de monde !")
    assert is_multi_sentence("Il y a du monde. Claire mange une crêpe.")
    assert is_multi_sentence("Il y a du monde ! Claire mange")
    assert is_multi_sentence("Il y a du monde… Claire mange")


def test_single_word():
    assert is_single_word("achètent")
    assert is_single_word("peut-être")
    assert is_single_word("l'école") is False
    assert not is_single_word("il y a")


def test_length_limit():
    assert MAX_LENGTH == 500
    assert not too_long("a" * 500)
    assert too_long("a" * 501)
