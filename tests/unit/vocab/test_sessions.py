"""Сеансы повторения (FR-030, FR-033, FR-035, FR-035b, FR-035c)."""

import datetime as dt
import random
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
    yield db, index, cards, SessionStore(db, cards, rng=random.Random(1))
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


def test_portions_from_params(setup):
    """010: размер подхода задаётся при запуске (страница настройки повторения)."""
    db, index, _cards, sessions = setup
    db.set_setting("portion_size", "1")  # настройка больше не влияет на сеанс
    session_id = sessions.start(index, params(portion=3), now=NOW)
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


def test_no_portion_means_all_at_once(setup):
    db, index, _cards, sessions = setup
    db.set_setting("portion_size", "1")
    session_id = sessions.start(index, params(mode="lesson", lesson=2), now=NOW)
    state = sessions.progress(session_id)
    assert state.total == 2 and state.portion_size == 2


def test_old_session_without_portion_field_is_read(setup):
    _db, index, _cards, sessions = setup
    session_id = sessions.start(index, params(), now=NOW)
    state, _queue, _position, _last = sessions._load(session_id)
    del state["params"]["portion"]
    sessions._save(session_id, state, 0, None)
    assert sessions.params(session_id).portion is None
    assert sessions.current(session_id) is not None


def order(sessions, index, seed, **overrides):
    sessions.rng = random.Random(seed)
    return [entry for entry, _direction in sessions.queue(index, params(**overrides), now=NOW)]


def test_queue_is_shuffled(setup):
    """010 пункт 5: порядок слов разный от запуска к запуску, при одном seed — одинаковый."""
    _db, index, _cards, sessions = setup
    for mode in ({"mode": "all"}, {"mode": "topic", "topic": "top-maisonxx"}):
        assert order(sessions, index, 7, **mode) == order(sessions, index, 7, **mode)
    orders = {tuple(order(sessions, index, seed, mode="all")) for seed in range(20)}
    assert len(orders) > 1
    assert all(sorted(o) == sorted(next(iter(orders))) for o in orders)


def test_today_reviewed_due_first_then_new(setup):
    _db, index, cards, sessions = setup
    cards.rate("voc-painaaaa", "fr_ru", "again", mode="today", method="self", now=NOW)
    later = NOW + dt.timedelta(days=60)
    for seed in range(10):
        sessions.rng = random.Random(seed)
        queue = sessions.queue(index, params(), now=later)
        assert queue[0] == ["voc-painaaaa", "fr_ru"]
        assert len(queue) == 4
    firsts = set()
    for seed in range(20):
        sessions.rng = random.Random(seed)
        firsts.add(sessions.queue(index, params(), now=later)[1][0])
    assert len(firsts) > 1  # новые карточки тоже перемешаны


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


# --- 011: повтор-тренировка без записи ------------------------------------------------------


def rate_all(sessions, session_id, ratings):
    for rating in ratings:
        sessions.rate(session_id, rating, now=NOW)


def test_drill_candidates_by_last_rating(setup):
    _db, index, _cards, sessions = setup
    session_id = sessions.start(index, params(mode="all"), now=NOW)
    queue = [tuple(c) for c in sessions._load(session_id)[1]]
    rate_all(sessions, session_id, ["again", "hard", "good", "article"])
    assert sessions.drill_candidates(session_id, "again") == [queue[0]]
    assert sessions.drill_candidates(session_id, "again_hard") == [queue[0], queue[1]]


def test_drill_does_not_write_progress(setup):
    _db, index, cards, sessions = setup
    session_id = sessions.start(index, params(mode="all"), now=NOW)
    rate_all(sessions, session_id, ["again", "again", "good", "good"])
    before = {c.entry_id: c.due for c in cards.all()}
    reviews_before = sum(len(cards.history(e)) for e in before)
    drill = sessions.start_drill(session_id, "again", now=NOW)
    assert sessions.params(drill).drill is True
    assert sessions.progress(drill).total == 2
    rate_all(sessions, drill, ["good", "again"])
    assert {c.entry_id: c.due for c in cards.all()} == before
    assert sum(len(cards.history(e)) for e in before) == reviews_before
    assert sessions.summary(drill) == {"good": 1, "again": 1}
    assert len(sessions.drill_candidates(drill, "again")) == 1  # повтор по ответам тренировки


def test_drill_undo(setup):
    _db, index, _cards, sessions = setup
    session_id = sessions.start(index, params(mode="all"), now=NOW)
    rate_all(sessions, session_id, ["again", "again", "good", "good"])
    drill = sessions.start_drill(session_id, "again", now=NOW)
    first = sessions.current(drill)
    assert not sessions.can_undo(drill)
    sessions.rate(drill, "good", now=NOW)
    assert sessions.can_undo(drill)
    assert sessions.undo(drill) == first
    assert sessions.current(drill) == first and sessions.summary(drill) == {}
