"""Индекс контента в памяти (data-model: «Индекс», FR-011, FR-035, FR-039)."""

import os
import time
from pathlib import Path

from french_learning.content.index import ContentIndex, ContentStore
from french_learning.content.loader import load_content


def build(root: Path) -> ContentIndex:
    return ContentIndex(load_content(root))


def ids(elements):
    return [e.id for e in elements]


def test_lessons_newest_first(clean_content_root: Path):
    assert [lesson.number for lesson in build(clean_content_root).lessons()] == [4, 2, 1]


def test_elements_by_lesson_part_and_kind(clean_content_root: Path):
    index = build(clean_content_root)
    homework = index.elements(1, part="homework", kind="exercise")
    assert ids(homework) == [
        "ex-multigap",
        "ex-transfor",
        "ex-twoforms",
        "ex-grouping",
        "ex-picturea",
        "ex-openansw",
    ]
    assert ids(index.elements(1, kind="theory")) == ["th-articles"]
    assert ids(index.elements(1, kind="text")) == ["tx-aucafeaa"]


def test_lesson_topics_include_revision(clean_content_root: Path):
    names = [t.name for t in build(clean_content_root).lesson_topics(2)]
    assert names == ["Артикли", "Глагол être"]


def test_topic_elements_across_lessons_and_extras(clean_content_root: Path):
    elements = build(clean_content_root).topic_elements("top-articles")
    assert set(ids(elements)) == {
        "th-articles",
        "ex-gapchoic",
        "ex-multigap",
        "ex-twoforms",
        "ex-grouping",
        "ex-revision",
        "th-extrarul",
    }


def test_backlinks(clean_content_root: Path):
    index = build(clean_content_root)
    assert ids(index.linked_exercises("tx-aucafeaa")) == ["ex-truefals", "ex-choicecf"]
    assert ids(index.linked_exercises("th-articles")) == ["ex-gapchoic"]


def test_needs_review_list(clean_content_root: Path):
    reviews = build(clean_content_root).needs_review()
    assert [(r.element.id, r.item_id) for r in reviews] == [("ex-gapchoic", 2)]
    assert "eaux" in reviews[0].note


def test_new_and_repeat_words(clean_content_root: Path):
    index = build(clean_content_root)
    new1, repeat1 = index.lesson_vocabulary(1)
    assert (ids(new1), ids(repeat1)) == (["voc-maisonaa", "voc-painaaaa"], [])
    new2, repeat2 = index.lesson_vocabulary(2)
    assert (ids(new2), ids(repeat2)) == (["voc-eauaaaaa"], ["voc-painaaaa"])


def test_extras(clean_content_root: Path):
    assert set(ids(build(clean_content_root).extras())) == {"th-extrarul", "voc-chataaaa"}


def test_topics_by_section_with_counts(clean_content_root: Path):
    sections = build(clean_content_root).topics_by_section()
    grammar = sections[0]
    assert grammar.section.name == "Грамматика"
    counts = {t.topic.name: t.count for t in grammar.topics}
    assert counts["Артикли"] == 7


def test_store_rebuilds_when_files_change(clean_content_root: Path):
    store = ContentStore(clean_content_root)
    first = store.get()
    assert store.get() is first

    path = clean_content_root / "lessons/001/exercises/ex-gapinput.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("Поставить être", "Спрягать être"),
        encoding="utf-8",
    )
    later = time.time() + 5
    os.utime(path, (later, later))

    second = store.get()
    assert second is not first
    assert second.element("ex-gapinput").description_ru.startswith("Спрягать")


# --- 009: соседние упражнения и дерево урока -------------------------------------------------


def ids_or_none(elements):
    return [e.id if e else None for e in elements]


def test_neighbours_within_lesson_tab(clean_content_root: Path):
    index = ContentIndex(load_content(clean_content_root))
    el = index.element
    assert ids_or_none(index.neighbours(el("ex-gapchoic"))) == [None, "ex-gapinput"]
    assert ids_or_none(index.neighbours(el("ex-gapinput"))) == ["ex-gapchoic", "ex-truefals"]
    assert ids_or_none(index.neighbours(el("ex-choicecf"))) == ["ex-truefals", None]
    # домашка: резерв (ex-openansw) пропускается, необязательное — нет
    assert ids_or_none(index.neighbours(el("ex-picturea"))) == ["ex-grouping", None]
    assert ids_or_none(index.neighbours(el("ex-transfor"))) == ["ex-multigap", "ex-twoforms"]
    # резервное открывается среди резервных
    assert ids_or_none(index.neighbours(el("ex-openansw"))) == [None, None]


def test_lesson_tree(clean_content_root: Path):
    index = ContentIndex(load_content(clean_content_root))

    class Done:
        def is_done(self, exercise_id):
            return exercise_id == "ex-multigap"

    tree = index.lesson_tree(1, Done())
    assert [t.id for t in tree["theory"]] == ["th-articles"]
    assert [t.id for t in tree["texts"]] == ["tx-aucafeaa"]
    assert tree["vocab"] == 2  # maison, pain
    assert [(e.id, done) for e, done in tree["homework"]][:2] == [
        ("ex-multigap", True),
        ("ex-transfor", False),
    ]
    assert [e.id for e, _d in tree["class"]] == [
        "ex-gapchoic",
        "ex-gapinput",
        "ex-truefals",
        "ex-choicecf",
    ]
    assert [e.id for e in tree["reserve"]] == ["ex-openansw"]


def _hide(root: Path, entry_id: str) -> None:
    path = root / "vocabulary" / f"{entry_id}.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "hidden: true\n", encoding="utf-8")


def test_hidden_words_not_in_lesson_vocabulary(clean_content_root: Path):
    """012 (US1): скрытое слово не попадает в лексику урока."""
    _hide(clean_content_root, "voc-painaaaa")
    index = build(clean_content_root)
    assert ids(index.lesson_vocabulary(1)[0]) == ["voc-maisonaa"]
    assert ids(index.lesson_vocabulary(2)[1]) == []


def test_hidden_words_not_in_topic_elements(clean_content_root: Path):
    """012 (US1): на странице темы скрытых слов нет."""
    _hide(clean_content_root, "voc-painaaaa")
    elements = build(clean_content_root).topic_elements("top-nourritu")
    assert "voc-painaaaa" not in ids(elements)
    assert "voc-eauaaaaa" in ids(elements)


def test_vocabulary_section_only_topics_with_words(clean_content_root: Path):
    """012 (US6): в разделе «Лексика» — только темы с нескрытыми словами."""
    _hide(clean_content_root, "voc-painaaaa")
    _hide(clean_content_root, "voc-eauaaaaa")
    index = build(clean_content_root)
    names = lambda sections: {  # noqa: E731
        t.topic.name for s in sections if s.section.id == "vocabulary" for t in s.topics
    }
    assert names(index.topics_by_section(only_vocab_with_words=True)) == {"Дом"}
    assert names(index.topics_by_section()) == {"Дом", "Еда"}
