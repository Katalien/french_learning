"""Расписание вопросов тренажёров и подходы порциями (FR-044, FR-045a; SC-006; research R10)."""

import datetime as dt
from pathlib import Path

import pytest

from french_learning.practice.db import ProgressDB
from french_learning.trainers.schedule import TrainerSchedule
from french_learning.trainers.sessions import TrainerSessions

NOW = dt.datetime(2026, 10, 1, 9, 0, tzinfo=dt.UTC)
KEYS = [f"numbers:{n}" for n in range(30)]


@pytest.fixture
def env(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    schedule = TrainerSchedule(db, fuzzing=False)
    yield db, schedule, TrainerSessions(db, schedule)
    db.close()


def test_answers_recorded_and_rated(env):
    _db, schedule, _ = env
    schedule.answer("numbers", "numbers:1", correct=True, answer="un", now=NOW)
    schedule.answer("numbers", "numbers:2", correct=False, answer="trois", now=NOW)
    schedule.answer("numbers", "numbers:3", correct=True, revealed=True, answer="", now=NOW)
    rows = schedule.history("numbers")
    assert [(r["key"], r["correct"], r["revealed"]) for r in rows] == [
        ("numbers:1", 1, 0),
        ("numbers:2", 0, 0),
        ("numbers:3", 0, 1),  # подсмотрено — ошибка
    ]
    assert schedule.due_at("numbers", "numbers:2") < schedule.due_at("numbers", "numbers:1")


def test_wrong_question_comes_back_earlier(env):
    _db, schedule, _ = env
    schedule.answer("numbers", "numbers:1", correct=True, now=NOW)
    schedule.answer("numbers", "numbers:2", correct=False, now=NOW)
    tomorrow = NOW + dt.timedelta(days=1)
    queue = schedule.select("numbers", ["numbers:1", "numbers:2", "numbers:3"], 3, now=tomorrow)
    assert queue.index("numbers:2") < queue.index("numbers:1")  # SC-006
    assert queue[0] == "numbers:2"  # «пора» — первыми, затем новые
    assert queue[1] == "numbers:3"


def test_stats_trainer_without_fsrs(env):
    _db, schedule, _ = env
    schedule.answer("negation", "tb-negaaaaa:1", correct=False, srs=False, now=NOW)
    assert schedule.due_at("negation", "tb-negaaaaa:1") is None
    assert len(schedule.history("negation")) == 1


def test_hard_keys(env):
    _db, schedule, _ = env
    schedule.answer("numbers", "numbers:5", correct=False, now=NOW)
    schedule.answer("numbers", "numbers:6", correct=True, now=NOW)
    assert schedule.hard_keys("numbers") == {"numbers:5"}


def test_portions_and_summary(env):
    db, schedule, sessions = env
    db.set_setting("trainer_portion_size", "5")
    sid = sessions.start("numbers", {"scope": "all"}, KEYS)
    assert sessions.progress(sid) == (0, 5, 0)
    for i in range(5):
        key = sessions.current(sid)
        sessions.record(sid, key, correct=i != 2, answer="x")
    assert sessions.current(sid) is None
    assert sessions.progress(sid) == (5, 5, 4)  # «4 из 5»
    first_portion = set(sessions.seen(sid))
    sessions.continue_with(sid, KEYS)
    assert sessions.progress(sid) == (0, 5, 0)
    assert not first_portion & set(sessions.queue(sid))  # новая порция без повторов
    assert len(schedule.history("numbers")) == 5  # ответы сохранены сразу
