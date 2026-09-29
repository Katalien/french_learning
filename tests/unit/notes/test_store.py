"""Хранилище заметок: правила, привязки, выборки (data-model 005)."""

from pathlib import Path

import pytest

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content
from french_learning.notes.store import Anchor, NoteError, NoteStore
from french_learning.practice.db import ProgressDB

ANCHOR = Anchor(exact="un café", prefix="Il commande ", suffix=" et un", start=45)


@pytest.fixture
def env(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    yield NoteStore(db), ContentIndex(load_content(clean_content_root))
    db.close()


def test_note_to_lesson(env):
    store, index = env
    note = store.create(index, kind="note", body="  passé simple не нужен  ", lesson=1)
    assert note.id > 0 and note.body == "passé simple не нужен"
    assert note.lesson == 1 and note.element_id is None and note.anchor is None
    assert not note.important and not note.answered and note.origin == "user"
    assert store.get(note.id) == note


def test_note_to_element_takes_lesson_and_title_from_index(env):
    store, index = env
    note = store.create(index, kind="note", body="текст", element_id="tx-aucafeaa", lesson=99)
    assert note.lesson == 1 and note.element_title == "Au café (démo)"


def test_exercise_title_is_description(env):
    store, index = env
    note = store.create(index, kind="note", body="x", element_id="ex-gapchoic")
    assert note.element_title == index.element("ex-gapchoic").description_ru


def test_note_to_fragment_keeps_anchor(env):
    store, index = env
    note = store.create(
        index, kind="question", body="почему un?", element_id="tx-aucafeaa", anchor=ANCHOR
    )
    assert store.get(note.id).anchor == ANCHOR


@pytest.mark.parametrize(
    "fields",
    [
        {"kind": "note", "body": "   ", "lesson": 1},
        {"kind": "todo", "body": "x", "lesson": 1},
        {"kind": "note", "body": "x" * 2001, "lesson": 1},
        {"kind": "note", "body": "x", "lesson": 1, "anchor": ANCHOR},
        {"kind": "note", "body": "x"},
        {"kind": "note", "body": "x", "element_id": "th-extrarul"},
        {"kind": "note", "body": "x", "element_id": "voc-maisonaa"},
        {"kind": "note", "body": "x", "element_id": "нет-такого"},
        {"kind": "note", "body": "x", "lesson": 77},
    ],
)
def test_invalid_notes_rejected(env, fields):
    store, index = env
    with pytest.raises(NoteError):
        store.create(index, **fields)


def test_extras_message(env):
    store, index = env
    with pytest.raises(NoteError, match="только у элементов уроков"):
        store.create(index, kind="note", body="x", element_id="th-extrarul")


def test_answer_closes_question_and_unmark_keeps_answer(env):
    store, index = env
    q = store.create(index, kind="question", body="вопрос", lesson=1)
    q = store.update(index, q.id, answer="ответ")
    assert q.answered and q.answer == "ответ"
    q = store.update(index, q.id, answered=False)
    assert not q.answered and q.answer == "ответ"
    q = store.update(index, q.id, answered=True, answer="  ")
    assert q.answered and q.answer is None


def test_note_cannot_be_answered(env):
    store, index = env
    n = store.create(index, kind="note", body="пометка", lesson=1)
    with pytest.raises(NoteError):
        store.update(index, n.id, answer="ответ")


def test_kind_switch(env):
    store, index = env
    q = store.create(index, kind="question", body="вопрос", lesson=1)
    q = store.update(index, q.id, answer="ответ")
    n = store.update(index, q.id, kind="note")
    assert n.kind == "note" and not n.answered
    q = store.update(index, n.id, kind="question")
    assert q.kind == "question" and not q.answered


def test_update_body_important_anchor(env):
    store, index = env
    n = store.create(index, kind="note", body="a", element_id="tx-aucafeaa", anchor=ANCHOR)
    n2 = store.update(index, n.id, body="b", important=True, anchor=None)
    assert n2.body == "b" and n2.important and n2.anchor is None
    assert n2.updated_at >= n.updated_at
    with pytest.raises(NoteError):
        store.update(index, n.id, body=" ")


def test_anchor_requires_element_on_update(env):
    store, index = env
    n = store.create(index, kind="note", body="a", lesson=1)
    with pytest.raises(NoteError):
        store.update(index, n.id, anchor=ANCHOR)


def test_missing_note(env):
    store, index = env
    assert store.get(123) is None
    with pytest.raises(LookupError):
        store.update(index, 123, body="x")
    assert store.delete(123) is False


def test_delete(env):
    store, index = env
    n = store.create(index, kind="note", body="a", lesson=1)
    assert store.delete(n.id) is True and store.get(n.id) is None


def test_queries(env):
    store, index = env
    a = store.create(index, kind="note", body="a", element_id="tx-aucafeaa")
    b = store.create(index, kind="question", body="b", element_id="ex-gapchoic")
    c = store.create(index, kind="question", body="c", lesson=2)
    d = store.create(index, kind="question", body="d", lesson=1)
    store.update(index, d.id, answer="ok")
    store.create(index, kind="note", body="e", lesson=1)

    assert [n.id for n in store.for_elements(["tx-aucafeaa", "ex-gapchoic"])] == [a.id, b.id]
    assert {n.body for n in store.for_lesson(1)} == {"a", "b", "d", "e"}
    # сначала новые уроки, внутри урока — по времени создания
    assert [n.id for n in store.open_questions()] == [c.id, b.id]
    assert store.open_questions_count() == 2
    assert store.lesson_counts() == {1: 4, 2: 1}
