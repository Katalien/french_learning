"""Проверка введённого ответа (research R5; конституция VIII). Общая для 003 и 004."""

import random

import pytest

from french_learning.practice.checking import (
    check_french,
    check_russian,
    spelling_variants,
    strip_diacritics,
)


@pytest.mark.parametrize(
    "answer",
    [
        "l'eau",
        "l’eau",
        "lʼeau",
        "L'eau",
        "  l'eau  ",
        "l'eau.",
        "l'eau ",
    ],
)
def test_keyboard_differences_are_not_errors(answer):
    assert check_french(answer, ["l'eau"]).status == "correct"


def test_space_before_punctuation_is_not_an_error():
    accepted = ["Est-ce qu'il y a un café ?"]
    for answer in (
        "Est-ce qu'il y a un café?",
        "Est-ce qu'il y a un café ?",
        "est-ce qu’il y a un café ?",
    ):
        assert check_french(answer, accepted).status == "correct"


def test_wrong_letter_is_an_error():
    assert check_french("le eau", ["l'eau"]).status == "wrong"
    assert check_french("maisons", ["maison"]).status == "wrong"


def test_missing_diacritics_ask_for_spelling_choice():
    result = check_french("ete", ["été"])
    assert result.status == "choose_spelling"
    assert "été" in result.variants
    assert 2 <= len(result.variants) <= 4
    assert len(set(result.variants)) == len(result.variants)


def test_wrong_diacritics_also_ask_for_choice():
    assert check_french("èté", ["été"]).status == "choose_spelling"


def test_ligature_typed_as_two_letters():
    assert check_french("coeur", ["cœur"]).status == "choose_spelling"


def test_hyphen_is_strict():
    assert check_french("est ce que", ["est-ce que"]).status == "wrong"


def test_any_accepted_answer():
    result = check_french("je suis allée", ["je suis allé", "je suis allée"])
    assert result.status == "correct" and result.matched == "je suis allée"


def test_russian_answers_ignore_case_and_yo():
    assert check_russian("Ёлка", ["елка"]).status == "correct"
    assert check_russian("кот", ["кот", "кошка"]).status == "correct"
    assert check_russian("собака", ["кот"]).status == "wrong"


def test_spelling_variants_are_plausible():
    variants = spelling_variants("été", rng=random.Random(1))
    assert "été" in variants
    assert all(strip_diacritics(v) == "ete" for v in variants)
    assert 2 <= len(variants) <= 4


def test_no_variants_without_accentable_letters():
    assert spelling_variants("pff", rng=random.Random(1)) == ["pff"]


def test_strip_diacritics():
    assert strip_diacritics("Ça, œuvre à l'hôtel") == "ca, oeuvre a l'hotel"
