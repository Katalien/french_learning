"""Пул заданий от агента: пул, архив, «Ошибки», статистика (FR-050b–FR-053; research R9)."""

import datetime as dt
from pathlib import Path

import pytest

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content
from french_learning.practice.db import ProgressDB
from french_learning.trainers.pools import pool_mistakes, pool_questions, pool_stats, pool_summary
from french_learning.trainers.schedule import TrainerSchedule

DAY1 = dt.datetime(2026, 10, 1, 9, 0, tzinfo=dt.UTC)
DAY2 = DAY1 + dt.timedelta(days=1)


@pytest.fixture
def env(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    yield ContentIndex(load_content(clean_content_root)), TrainerSchedule(db, fuzzing=False)
    db.close()


def answer(schedule, n, correct, text="x", now=DAY1, revealed=False):
    schedule.answer(
        "negation",
        f"tb-negaaaaa:{n}",
        correct=correct,
        answer=text,
        revealed=revealed,
        srs=False,
        now=now,
    )


def test_questions_from_batch(env):
    index, schedule = env
    questions = {q.key: q for q in pool_questions(index, schedule, "negation")}
    assert len(questions) == 5
    q = questions["tb-negaaaaa:3"]
    assert q.prompt == "Nous aimons le beurre." and q.mode == "input"
    assert q.answers == ["Nous n'aimons pas le beurre."]
    assert "le beurre — масло" in q.hint
    assert q.instruction == "Сделайте предложение отрицательным."
    assert questions["tb-negaaaaa:5"].review_note


def test_pool_archive_mistakes(env):
    index, schedule = env
    answer(schedule, 1, True)
    answer(schedule, 2, True)
    answer(schedule, 3, True)
    answer(schedule, 4, True)
    answer(schedule, 5, False, "Elle ne boit pas de l'eau.")
    assert [q.key for q in pool_questions(index, schedule, "negation")] == ["tb-negaaaaa:5"]
    summary = pool_summary(index, schedule, "negation")
    assert summary == {"in_pool": 1, "archived": 4, "mistakes": 1, "total": 5}
    [mistake] = pool_mistakes(index, schedule, "negation")
    assert mistake["question"].key == "tb-negaaaaa:5"
    assert mistake["answers"] == ["Elle ne boit pas de l'eau."]
    answer(schedule, 5, True, now=DAY2)
    assert pool_questions(index, schedule, "negation") == []
    assert pool_mistakes(index, schedule, "negation") == []


def test_stats(env):
    index, schedule = env
    answer(schedule, 1, True)
    answer(schedule, 2, False, "Il mange pas de pain.")
    answer(schedule, 3, True, revealed=True)  # подсмотрено — ошибка
    answer(schedule, 2, False, "Il mange pas de pain.", now=DAY2)
    answer(schedule, 2, True, now=DAY2)
    stats = pool_stats(index, schedule, "negation")
    assert stats["answers"] == 5 and stats["correct"] == 2 and stats["percent"] == 40
    assert [(d["date"], d["answers"], d["correct"]) for d in stats["days"]] == [
        ("2026-10-01", 3, 1),
        ("2026-10-02", 2, 1),
    ]
    [typical] = stats["typical"]
    assert typical["answer"] == "Il mange pas de pain." and typical["count"] == 2
