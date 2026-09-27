"""Вопрос и ответ карточки, артикли, фильтры словаря (FR-010, FR-032a; research R4)."""

from pathlib import Path

import pytest

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content
from french_learning.vocab import entries


@pytest.fixture
def index(clean_content_root: Path) -> ContentIndex:
    return ContentIndex(load_content(clean_content_root))


def entry(index, entry_id):
    return index.element(entry_id)


def test_display_with_article(index):
    assert entries.display_fr(entry(index, "voc-maisonaa")) == "la maison"
    assert entries.display_fr(entry(index, "voc-eauaaaaa")) == "l'eau"


def test_indefinite_article_from_gender():
    class E:
        def __init__(self, gender, plural_only=False):
            self.gender = gender
            self.flags = type("F", (), {"plural_only": plural_only})()

    assert entries.indefinite(E("m")) == "un"
    assert entries.indefinite(E("f")) == "une"
    assert entries.indefinite(E("both")) == "un / une"
    assert entries.indefinite(E("m", plural_only=True)) == "des"
    assert entries.indefinite(E(None)) is None


def test_question_and_answers_fr_ru(index):
    e = entry(index, "voc-maisonaa")
    q = entries.question(index, e, "fr_ru")
    assert q.text == "la maison"
    assert entries.accepted_answers(index, e, "fr_ru") == ["дом"]


def test_question_and_answers_ru_fr(index):
    e = entry(index, "voc-maisonaa")
    q = entries.question(index, e, "ru_fr")
    assert q.text == "дом"
    assert "сущ" in q.hint or "nom" in q.hint
    assert entries.accepted_answers(index, e, "ru_fr") == ["la maison"]


def test_ru_fr_accepts_all_entries_with_same_translation(index, clean_content_root: Path):
    extra = clean_content_root / "vocabulary/voc-demeureq.yaml"
    extra.write_text(
        "id: voc-demeureq\nkind: vocab\nentry_type: word\ntext: demeure\narticle: la\n"
        "gender: f\ntranslations: [{text: дом, origin: user}]\ntopics: [top-maisonxx]\n"
        "origin: user\n",
        encoding="utf-8",
    )
    fresh = ContentIndex(load_content(clean_content_root))
    answers = entries.accepted_answers(fresh, fresh.element("voc-maisonaa"), "ru_fr")
    assert sorted(answers) == ["la demeure", "la maison"]


def test_filters(index):
    by_lesson = {e.id for e in entries.filter_entries(index, lesson=2)}
    assert by_lesson == {"voc-painaaaa", "voc-eauaaaaa"}
    by_topic = {e.id for e in entries.filter_entries(index, topic="top-maisonxx")}
    assert by_topic == {"voc-maisonaa", "voc-chataaaa"}
    assert entries.filter_entries(index, kind="verb") == []
    known = {e.id for e in entries.filter_entries(index, flag="known", known_ids={"voc-painaaaa"})}
    assert known == {"voc-painaaaa"}
    assert entries.filter_entries(index, flag="hidden") == []
    assert len(entries.filter_entries(index)) == 4
