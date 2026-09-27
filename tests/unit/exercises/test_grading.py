"""Проверка упражнений по типам (FR-002–FR-005, FR-011; SC-002; research R2, R3)."""

from pathlib import Path

import pytest

from french_learning.content.loader import load_content
from french_learning.exercises.grading import checkable, correct_answers, grade_item


@pytest.fixture
def ex(clean_content_root: Path):
    elements = load_content(clean_content_root).elements
    return lambda exercise_id: elements[exercise_id]


def grade(exercise, item_id, answer):
    item = next(i for i in exercise.items if i.id == item_id)
    return grade_item(exercise, item, answer)


def test_gap_choice(ex):
    e = ex("ex-gapchoic")
    assert grade(e, 1, {"1": "le"}).status == "correct"  # регистр не важен
    assert grade(e, 1, {"1": "la"}).status == "wrong"
    assert grade(e, 2, {"1": "l’"}).status == "correct"  # вид апострофа не важен
    assert grade(e, 2, {}).status == "wrong"  # пусто — ошибка


def test_gap_input_and_multi_gap(ex):
    assert grade(ex("ex-gapinput"), 1, {"1": " Suis "}).status == "correct"
    assert grade(ex("ex-gapinput"), 1, {"1": "sui"}).status == "wrong"
    multi = ex("ex-multigap")
    result = grade(multi, 1, {"1": "le", "2": "le"})
    assert result.status == "wrong"
    assert result.gaps["1"].status == "correct" and result.gaps["2"].status == "wrong"
    assert grade(multi, 1, {"1": "Le", "2": "la"}).status == "correct"


def test_transform_keyboard_differences(ex):
    e = ex("ex-transfor")
    assert grade(e, 1, {"a": "je ne suis pas fatiguée"}).status == "correct"  # без точки
    assert grade(e, 1, {"a": "Je ne suis pas fatiguee."}).status == "choose"
    assert grade(e, 1, {"a": "Je suis pas fatiguée."}).status == "wrong"


def test_spelling_choice_resolution(ex):
    e = ex("ex-transfor")
    pending = grade(e, 1, {"a": "je ne suis pas fatiguee"})
    assert pending.status == "choose"
    variants = pending.gaps["a"].variants
    assert "Je ne suis pas fatiguée." in variants and len(variants) >= 2
    # варианты стабильны между показами
    assert grade(e, 1, {"a": "je ne suis pas fatiguee"}).gaps["a"].variants == variants
    right = {"a": "je ne suis pas fatiguee", "a~choice": "Je ne suis pas fatiguée."}
    assert grade(e, 1, right).status == "correct"
    wrong_variant = next(v for v in variants if v != "Je ne suis pas fatiguée.")
    assert grade(e, 1, {"a": "x", "a~choice": wrong_variant}).status == "wrong"


def test_true_false_choice_grouping_two_forms(ex):
    tf = ex("ex-truefals")
    assert grade(tf, 1, {"a": "false"}).status == "correct"
    assert grade(tf, 2, {"a": "false"}).status == "wrong"
    ch = ex("ex-choicecf")
    assert grade(ch, 1, {"a": ["0"]}).status == "correct"
    assert grade(ch, 1, {"a": ["0", "1"]}).status == "wrong"
    gr = ex("ex-grouping")
    assert grade(gr, 2, {"a": "féminin"}).status == "correct"
    assert grade(gr, 2, {"a": "masculin"}).status == "wrong"
    assert grade(ex("ex-twoforms"), 1, {"1": "les"}).status == "correct"


def test_picture_and_open(ex):
    assert grade(ex("ex-picturea"), 1, {"a": "Dans mon sac, il n’y a pas de stylo"}).status == (
        "correct"
    )
    assert checkable(ex("ex-picturea")) and not checkable(ex("ex-openansw"))


def test_several_accepted_answers(ex):
    e = ex("ex-gapinput")
    item = e.items[0].model_copy(update={"answers": {1: ["suis", "reste"]}})
    assert grade_item(e, item, {"1": "reste"}).status == "correct"


def test_correct_answers_for_reveal(ex):
    assert correct_answers(ex("ex-multigap"), ex("ex-multigap").items[0]) == {
        "1": ["le"],
        "2": ["la"],
    }
    assert correct_answers(ex("ex-truefals"), ex("ex-truefals").items[0]) == {"a": ["неверно"]}
    choice = ex("ex-choicecf")
    assert correct_answers(choice, choice.items[0]) == {"a": ["dans un café"]}
