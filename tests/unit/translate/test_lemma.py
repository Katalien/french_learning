"""Начальная форма и вид записи для «+ В словарь» (006, research R5, FR-010, FR-012)."""

import pytest

from french_learning.translate.lemma import add_as, lemma_of


def test_lemma_of_verb_and_noun_forms():
    assert lemma_of("achètent") == "acheter"
    assert lemma_of("pommes") == "pomme"
    assert lemma_of("Achètent") == "acheter"


def test_no_lemma_when_same_or_several_words():
    assert lemma_of("maison") is None
    assert lemma_of("il y a") is None
    assert lemma_of("sont rentrées") is None


def test_lemma_after_elision():
    assert lemma_of("l'école") == "école"
    assert lemma_of("l’école") == "école"


@pytest.mark.parametrize(
    ("selected", "text", "entry_type"),
    [
        ("achètent", "acheter", "verb"),
        ("ont", "avoir", "verb"),
        ("prend", "prendre", "verb"),
        ("pommes", "pomme", "word"),
        ("livres", "livre", "word"),  # множественное число, а не глагол на -re
        ("grandes", "grand", "word"),
        ("maison", "maison", "word"),
        ("Maison,", "maison", "word"),
    ],
)
def test_add_as_single_word(selected, text, entry_type):
    result = add_as(selected)
    assert (result.text, result.entry_type) == (text, entry_type)
    assert result.article is None and result.gender is None


def test_add_as_phrase_keeps_text_as_selected():
    assert (add_as("il y a").text, add_as("il y a").entry_type) == ("il y a", "phrase")
    sentence = add_as("  Elles achètent des pommes. ")
    assert (sentence.text, sentence.entry_type) == ("Elles achètent des pommes.", "phrase")


def test_gender_from_article_in_selection():
    # как при быстром вводе (003): артикль даёт род; неопределённый → определённый
    result = add_as("une crêpe")
    assert (result.text, result.entry_type, result.article, result.gender) == (
        "crêpe",
        "word",
        "la",
        "f",
    )
    result = add_as("le fromage")
    assert (result.text, result.article, result.gender) == ("fromage", "le", "m")
    result = add_as("les pommes")
    assert (result.text, result.entry_type, result.gender) == ("pomme", "word", None)


def test_gender_from_word_before_selection():
    result = add_as("crêpe", before="une")
    assert (result.text, result.article, result.gender) == ("crêpe", "la", "f")
    assert add_as("pommes", before="des").gender is None
    # перед глаголом артикля нет — род не ставится
    assert add_as("achètent", before="Elles").gender is None


def test_elided_article_gives_article_without_gender():
    result = add_as("l'école")
    assert (result.text, result.entry_type, result.article, result.gender) == (
        "école",
        "word",
        "l'",
        None,
    )


# --- омонимы: глагол после подлежащего (SC-005) ----------------------------------------------


@pytest.mark.parametrize(
    ("form", "before", "lemma"),
    [
        ("entre", "Paul", "entrer"),  # Paul entre dans un café
        ("commande", "Il", "commander"),
        ("commande", "ne", "commander"),  # il ne commande pas
        ("commandes", "tu", "commander"),
        ("entre", None, None),  # без контекста — как в словаре (предлог entre)
        ("entre", "la", None),  # после артикля — не глагол
        ("pommes", "des", "pomme"),
        ("pommes", "Deux", "pomme"),  # слово с заглавной в начале предложения — не подлежащее
    ],
)
def test_verb_reading_after_subject(form, before, lemma):
    assert lemma_of(form, before=before) == lemma


def test_add_as_uses_verb_reading_after_subject():
    result = add_as("commande", before="Il")
    assert (result.text, result.entry_type) == ("commander", "verb")
    assert add_as("commande", before="une").entry_type == "word"
