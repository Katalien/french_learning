"""Запись чисел по-французски 0–1000 (research R11): традиционная и по реформе 1990 года."""

import pytest

from french_learning.trainers.french_numbers import spellings


@pytest.mark.parametrize(
    ("n", "traditional"),
    [
        (0, "zéro"),
        (1, "un"),
        (16, "seize"),
        (17, "dix-sept"),
        (21, "vingt et un"),
        (22, "vingt-deux"),
        (70, "soixante-dix"),
        (71, "soixante et onze"),
        (72, "soixante-douze"),
        (80, "quatre-vingts"),
        (81, "quatre-vingt-un"),
        (90, "quatre-vingt-dix"),
        (91, "quatre-vingt-onze"),
        (97, "quatre-vingt-dix-sept"),
        (100, "cent"),
        (101, "cent un"),
        (180, "cent quatre-vingts"),
        (200, "deux cents"),
        (201, "deux cent un"),
        (999, "neuf cent quatre-vingt-dix-neuf"),
        (1000, "mille"),
    ],
)
def test_traditional_first(n, traditional):
    assert spellings(n)[0] == traditional


def test_reform_1990_also_accepted():
    assert spellings(21) == ["vingt et un", "vingt-et-un"]
    assert "deux-cent-un" in spellings(201)
    assert "cent-quatre-vingts" in spellings(180)
    assert spellings(16) == ["seize"]
