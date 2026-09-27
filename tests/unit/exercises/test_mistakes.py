"""«Мои ошибки» (FR-021a; research R5)."""

from pathlib import Path

import pytest

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content
from french_learning.exercises.attempts import AttemptStore
from french_learning.exercises.mistakes import find_mistakes
from french_learning.practice.db import ProgressDB


@pytest.fixture
def env(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    index = ContentIndex(load_content(clean_content_root))
    yield AttemptStore(db), index
    db.close()


REST = {"2": {"1": "l'"}, "3": {"1": "les"}}  # остальные пункты ex-gapchoic — верно


def keys(found):
    return [(m.exercise.id, m.item.id) for m in found]


def test_wrong_items_listed_and_filtered(env):
    store, index = env
    store.check(index.element("ex-gapchoic"), {"1": {"1": "la"}, **REST})
    store.check(index.element("ex-gapinput"), {"1": {"1": "x"}, "2": {"1": "sommes"}})
    assert keys(find_mistakes(index, store)) == [("ex-gapchoic", 1), ("ex-gapinput", 1)]
    assert keys(find_mistakes(index, store, topic="top-etreverb")) == [("ex-gapinput", 1)]
    assert find_mistakes(index, store, lesson=2) == []
    assert len(find_mistakes(index, store, lesson=1)) == 2


def test_fixed_self_and_revealed_stay_in_list(env):
    store, index = env
    e = index.element("ex-gapchoic")
    store.check(e, {"1": {"1": "la"}, **REST})
    store.check(e, {"1": {"1": "le"}, **REST})  # исправлено само — но итог первой проверки «ошибка»
    assert keys(find_mistakes(index, store)) == [("ex-gapchoic", 1)]


def test_item_leaves_list_when_solved_correctly(env):
    store, index = env
    e = index.element("ex-gapchoic")
    store.check(e, {"1": {"1": "la"}, **REST})
    single = store.start_item(e, 1)
    store.check(e, {"1": {"1": "le"}}, single)
    assert find_mistakes(index, store) == []
    # но история сохранена: две попытки
    assert len(store.history("ex-gapchoic")) == 2


def test_new_full_attempt_decides(env):
    store, index = env
    e = index.element("ex-gapchoic")
    store.check(e, {"1": {"1": "la"}, **REST})
    store.restart(e)
    store.check(e, {"1": {"1": "le"}, **REST})
    assert find_mistakes(index, store) == []
