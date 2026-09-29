"""Группировка страницы «Заметки к уроку» (data-model 005, вариант В1)."""

from pathlib import Path

import pytest

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content
from french_learning.content.progress import NoProgress
from french_learning.notes.grouping import lesson_page
from french_learning.notes.store import Anchor, NoteStore
from french_learning.practice.db import ProgressDB

ANCHOR = Anchor(exact="un café", prefix="", suffix="", start=0)


@pytest.fixture
def env(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    yield NoteStore(db), ContentIndex(load_content(clean_content_root)), db
    db.close()


def build(store, index):
    return lesson_page(store.for_lesson(1), index.lesson_tree(1, NoProgress()))


def test_questions_open_then_answered(env):
    store, index, _ = env
    q1 = store.create(index, kind="question", body="q1", element_id="ex-gapchoic")
    q2 = store.create(index, kind="question", body="q2", lesson=1)
    q3 = store.create(index, kind="question", body="q3", lesson=1)
    store.update(index, q2.id, answer="ok")
    page = build(store, index)
    assert [n.id for n in page.open_questions] == [q1.id, q3.id]
    assert [n.id for n in page.answered_questions] == [q2.id]
    assert all(n.kind == "note" for b in page.blocks for n in b.notes)


def test_lesson_notes_and_orphans(env):
    store, index, db = env
    a = store.create(index, kind="note", body="к уроку", lesson=1)
    gone = store.create(index, kind="note", body="пропал", element_id="ex-gapinput")
    with db.lock, db.conn:  # элемент исчез из урока после переобработки
        db.conn.execute("update notes set element_id = 'ex-gone' where id = ?", (gone.id,))
    page = build(store, index)
    assert [n.id for n in page.lesson_notes] == [a.id, gone.id]
    assert page.orphan_titles == {gone.id: index.element("ex-gapinput").description_ru}
    assert page.blocks == []


def test_blocks_in_lesson_order_whole_then_fragments(env):
    store, index, _ = env
    frag = store.create(index, kind="note", body="frag", element_id="tx-aucafeaa", anchor=ANCHOR)
    whole = store.create(index, kind="note", body="whole", element_id="tx-aucafeaa")
    ex = store.create(index, kind="note", body="ex", element_id="ex-gapchoic")
    th = store.create(index, kind="note", body="th", element_id="th-articles")
    page = build(store, index)
    assert [b.element.id for b in page.blocks] == ["th-articles", "tx-aucafeaa", "ex-gapchoic"]
    assert [b.kind_name for b in page.blocks] == ["Теория", "Текст", "Упражнение"]
    assert [n.id for n in page.blocks[1].notes] == [whole.id, frag.id]
    assert page.blocks[0].notes[0].id == th.id and page.blocks[2].notes[0].id == ex.id
    assert page.count == 4
