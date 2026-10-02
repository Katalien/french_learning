"""Сеансы повторения (FR-030, FR-033, FR-035, FR-035b, FR-035c)."""

import datetime as dt
from pathlib import Path

import pytest

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content
from french_learning.practice.db import ProgressDB
from french_learning.vocab.cards import CardStore
from french_learning.vocab.sessions import SessionParams, SessionStore

NOW = dt.datetime(2026, 9, 27, 10, 0, tzinfo=dt.UTC)


@pytest.fixture
def setup(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    index = ContentIndex(load_content(clean_content_root))
    cards = CardStore(db, fuzzing=False)
    cards.sync(index, now=NOW)
    yield db, index, cards, SessionStore(db, cards)
    db.close()


def params(**overrides) -> SessionParams:
    base = {
        "source": "dictionary",
        "mode": "today",
        "kind": "all",
        "direction": "fr_ru",
        "method": "self",
    }
    base.update(overrides)
    return SessionParams(**base)


def test_today_includes_all_new_cards_and_count_is_known(setup):
    _db, index, _cards, sessions = setup
    assert sessions.count(index, params(), now=NOW) == 4
    session_id = sessions.start(index, params(), now=NOW)
    assert sessions.progress(session_id).total == 4


def test_portions_from_settings(setup):
    db, index, _cards, sessions = setup
    db.set_setting("portion_size", "3")
    session_id = sessions.start(index, params(), now=NOW)
    for _ in range(3):
        assert sessions.current(session_id) is not None
        sessions.rate(session_id, "good", now=NOW)
    assert sessions.current(session_id) is None
    state = sessions.progress(session_id)
    assert state.portion_finished and not state.finished
    sessions.continue_portion(session_id)
    assert sessions.current(session_id) is not None
    sessions.rate(session_id, "good", now=NOW)
    assert sessions.progress(session_id).finished


def test_lesson_session_is_whole_lesson_at_once(setup):
    db, index, _cards, sessions = setup
    db.set_setting("portion_size", "1")
    session_id = sessions.start(index, params(source="lesson", mode="lesson", lesson=2), now=NOW)
    state = sessions.progress(session_id)
    assert state.total == 2 and state.portion_size == 2


def test_modes_and_kinds(setup):
    _db, index, cards, sessions = setup
    assert sessions.count(index, params(mode="topic", topic="top-maisonxx"), now=NOW) == 2
    assert sessions.count(index, params(mode="all", kind="verb"), now=NOW) == 0
    for _ in range(2):
        cards.rate("voc-painaaaa", "fr_ru", "again", mode="all", method="self", now=NOW)
    assert sessions.count(index, params(mode="hard"), now=NOW) == 1


def test_ru_fr_includes_all_words(setup):
    """010: «русский → французский» — все слова сразу, без первого «Помню»."""
    _db, index, _cards, sessions = setup
    assert sessions.count(index, params(mode="all", direction="ru_fr"), now=NOW) == 4
    assert sessions.count(index, params(mode="lesson", lesson=2, direction="ru_fr"), now=NOW) == 2


def test_no_cards_message(setup):
    _db, index, _cards, sessions = setup
    assert sessions.count(index, params(mode="all", kind="phrase"), now=NOW) == 0


def test_ratings_saved_immediately_and_undo_last_only(setup):
    _db, index, cards, sessions = setup
    session_id = sessions.start(index, params(), now=NOW)
    first = sessions.current(session_id)
    sessions.rate(session_id, "good", now=NOW)
    second = sessions.current(session_id)
    sessions.rate(session_id, "again", now=NOW)
    assert len(cards.history(first[0])) == 1 and len(cards.history(second[0])) == 1

    assert sessions.undo(session_id) == second
    assert sessions.current(session_id) == second
    assert cards.history(second[0]) == []
    assert sessions.undo(session_id) is None  # только последняя оценка
    assert len(cards.history(first[0])) == 1


def test_summary_counts(setup):
    _db, index, _cards, sessions = setup
    session_id = sessions.start(index, params(), now=NOW)
    for rating in ("good", "again", "hard"):
        sessions.rate(session_id, rating, now=NOW)
    assert sessions.summary(session_id) == {"good": 1, "hard": 1, "again": 1}
