"""Карточки и расписание FSRS (FR-031, FR-034, FR-035a, FR-036, FR-051, FR-052; SC-002)."""

import datetime as dt
from pathlib import Path

import pytest

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content
from french_learning.practice.db import ProgressDB
from french_learning.vocab.cards import CardStore

NOW = dt.datetime(2026, 9, 27, 10, 0, tzinfo=dt.UTC)


@pytest.fixture
def db(clean_content_root: Path):
    database = ProgressDB(clean_content_root)
    yield database
    database.close()


@pytest.fixture
def index(clean_content_root: Path) -> ContentIndex:
    return ContentIndex(load_content(clean_content_root))


@pytest.fixture
def cards(db, index) -> CardStore:
    store = CardStore(db, fuzzing=False)
    store.sync(index, now=NOW)
    return store


def test_sync_creates_both_directions(cards: CardStore):
    """010: поэтапного режима нет — у каждого слова сразу обе карточки."""
    ids = {(c.entry_id, c.direction) for c in cards.all()}
    assert ("voc-maisonaa", "fr_ru") in ids
    assert ("voc-maisonaa", "ru_fr") in ids
    assert len(ids) == 8  # 4 записи в образце × 2 направления


def test_sync_ignores_old_staged_setting(db, index):
    db.set_setting("directions", "staged")
    store = CardStore(db, fuzzing=False)
    store.sync(index, now=NOW)
    assert store.get("voc-maisonaa", "ru_fr") is not None


def test_sync_creates_only_missing_cards(db, index, monkeypatch):
    """010 пункт 8: повторный sync не создаёт объектов FSRS (они медленные)."""
    import french_learning.vocab.cards as cards_module

    store = CardStore(db, fuzzing=False)
    store.sync(index, now=NOW)
    store.rate("voc-maisonaa", "fr_ru", "good", mode="today", method="self", now=NOW)
    before = store.get("voc-maisonaa", "fr_ru").due

    created = []
    real_card = cards_module.fsrs.Card

    class CountingCard(real_card):
        def __init__(self, *args, **kwargs):
            created.append(1)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(cards_module.fsrs, "Card", CountingCard)
    store.sync(index, now=NOW)
    assert created == []
    assert store.get("voc-maisonaa", "fr_ru").due == before


def test_sync_adds_ru_fr_to_existing_fr_ru_cards(db, index):
    """Слова, заведённые при поэтапном режиме, получают вторую карточку; первая не меняется."""
    store = CardStore(db, fuzzing=False)
    store.sync(index, now=NOW)
    store.rate("voc-maisonaa", "fr_ru", "good", mode="today", method="self", now=NOW)
    with db.lock, db.conn:
        db.conn.execute("delete from cards where direction = 'ru_fr'")
    before = store.get("voc-maisonaa", "fr_ru").due
    store.sync(index, now=NOW)
    assert store.get("voc-maisonaa", "ru_fr") is not None
    assert store.get("voc-maisonaa", "fr_ru").due == before


def test_sync_skips_hidden_entries(db, clean_content_root: Path):
    path = clean_content_root / "vocabulary/voc-chataaaa.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "hidden: true\n", encoding="utf-8")
    store = CardStore(db, fuzzing=False)
    store.sync(ContentIndex(load_content(clean_content_root)), now=NOW)
    assert "voc-chataaaa" not in {c.entry_id for c in store.all()}


def test_ratings_change_due(cards: CardStore):
    cards.rate("voc-maisonaa", "fr_ru", "good", mode="today", method="self", now=NOW)
    cards.rate("voc-painaaaa", "fr_ru", "again", mode="today", method="self", now=NOW)
    good = cards.get("voc-maisonaa", "fr_ru").due
    again = cards.get("voc-painaaaa", "fr_ru").due
    assert good > again > NOW


def test_directions_are_independent(cards: CardStore):
    cards.rate("voc-maisonaa", "fr_ru", "good", mode="today", method="self", now=NOW)
    before = cards.get("voc-maisonaa", "ru_fr").due
    cards.rate("voc-maisonaa", "fr_ru", "good", mode="all", method="self", now=NOW)
    assert cards.get("voc-maisonaa", "ru_fr").due == before


def test_good_via_lesson_not_due_tomorrow(cards: CardStore):
    cards.rate("voc-maisonaa", "fr_ru", "good", mode="lesson", method="self", now=NOW)
    tomorrow = NOW + dt.timedelta(days=1)
    due = {(c.entry_id, c.direction) for c in cards.due(direction="fr_ru", now=tomorrow)}
    assert ("voc-maisonaa", "fr_ru") not in due


def test_due_today_includes_new_cards(cards: CardStore):
    due = {c.entry_id for c in cards.due(direction="fr_ru", now=NOW)}
    assert due == {"voc-maisonaa", "voc-painaaaa", "voc-eauaaaaa", "voc-chataaaa"}


def test_known_suspends_and_restores_with_history(cards: CardStore):
    cards.rate("voc-maisonaa", "fr_ru", "good", mode="today", method="self", now=NOW)
    cards.set_known("voc-maisonaa", True)
    assert "voc-maisonaa" not in {
        c.entry_id for c in cards.due(direction="fr_ru", now=NOW + dt.timedelta(days=30))
    }
    assert cards.known_ids() == {"voc-maisonaa"}
    cards.set_known("voc-maisonaa", False)
    assert cards.known_ids() == set()
    assert len(cards.history("voc-maisonaa")) == 1


def test_hard_entries(cards: CardStore):
    for _ in range(3):
        cards.rate("voc-painaaaa", "fr_ru", "again", mode="all", method="self", now=NOW)
    cards.rate("voc-painaaaa", "fr_ru", "good", mode="all", method="self", now=NOW)
    cards.rate("voc-maisonaa", "fr_ru", "good", mode="all", method="self", now=NOW)
    assert cards.hard_ids() == {"voc-painaaaa"}


def test_review_logged_with_snapshot_and_undo(cards: CardStore):
    before = cards.get("voc-maisonaa", "fr_ru").due
    review_id = cards.rate(
        "voc-maisonaa", "fr_ru", "good", mode="today", method="input", answer="дом", now=NOW
    )
    [entry] = cards.history("voc-maisonaa")
    assert entry["rating"] == "good" and entry["method"] == "input" and entry["answer"] == "дом"
    cards.undo(review_id)
    assert cards.get("voc-maisonaa", "fr_ru").due == before
    assert cards.history("voc-maisonaa") == []
