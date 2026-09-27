"""Следующий номер упражнения во вкладке и справочник тем (FR-022, FR-040)."""

from pathlib import Path

from french_learning.agent.numbers import next_number, topics_list


def test_next_number_after_existing(store: Path):
    assert next_number(store, lesson=1, part="homework", op="op1") == 7
    assert next_number(store, lesson=1, part="class", op="op1") == 5


def test_next_number_counts_staging(store: Path):
    staged = store / ".staging/op1/lessons/001/exercises/ex-stagedaa.yaml"
    staged.parent.mkdir(parents=True)
    staged.write_text(
        "id: ex-stagedaa\nkind: exercise\nlesson: 1\npart: homework\nnumber: 7\n", encoding="utf-8"
    )
    assert next_number(store, lesson=1, part="homework", op="op1") == 8


def test_next_number_empty_tab(store: Path):
    assert next_number(store, lesson=4, part="class", op="op1") == 1
    assert next_number(store, lesson=99, part="class", op="op1") == 1


def test_topics_list(store: Path):
    topics = topics_list(store)
    articles = next(t for t in topics if t["id"] == "top-articles")
    assert articles == {
        "id": "top-articles",
        "name": "Артикли",
        "section": "grammar",
        "section_name": "Грамматика",
        "count": 7,
    }
