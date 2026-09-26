"""Сводка урока (FR-031, FR-039)."""

import datetime as dt
from pathlib import Path

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content
from french_learning.content.progress import NoProgress


class DoneSet:
    def __init__(self, *ids: str) -> None:
        self.ids = set(ids)

    def is_done(self, exercise_id: str) -> bool:
        return exercise_id in self.ids


def summary(root: Path, number: int, progress=None):
    index = ContentIndex(load_content(root))
    return index.lesson_summary(number, progress or NoProgress())


def test_lesson_one(content_root: Path):
    s = summary(content_root, 1)
    assert s.number == 1
    assert s.date == dt.date(2026, 9, 1)
    assert [t.name for t in s.topics] == ["Артикли", "Глагол être", "Дом", "Еда"]
    assert s.new_words == 2
    # main-домашка: multigap, transfor, grouping, picturea; twoforms — optional; openansw — reserve
    assert (s.homework_done, s.homework_total, s.homework_optional) == (0, 4, 1)
    assert s.needs_review == 1


def test_lesson_two_without_date_and_broken_file(content_root: Path):
    s = summary(content_root, 2)
    assert s.date is None
    assert s.new_words == 1
    assert s.homework_total == 1
    assert s.errors == 1


def test_reserve_is_not_counted(content_root: Path):
    s = summary(content_root, 4)
    assert (s.homework_total, s.homework_optional) == (0, 0)


def test_done_counts_only_main_homework(content_root: Path):
    s = summary(content_root, 1, DoneSet("ex-multigap", "ex-twoforms", "ex-gapchoic"))
    assert s.homework_done == 1
