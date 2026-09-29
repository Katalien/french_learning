"""Запрос: группы, ранжирование, область и фильтры (007, research R4–R6; FR-008, FR-009)."""

from pathlib import Path

import pytest

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content
from french_learning.search.index import build
from french_learning.search.query import Query, search


@pytest.fixture
def index(clean_content_root: Path):
    return build(ContentIndex(load_content(clean_content_root)))


def ids(results, group):
    return [r.id for r in results.groups[group]]


# --- US1: группы и порядок ---------------------------------------------------------------------


def test_groups_words_topics_theory(index):
    results = search(index, Query("дом"))
    assert list(results.groups) == ["words", "topics", "theory"]
    assert ids(results, "words") == ["voc-maisonaa"]
    assert ids(results, "topics") == ["top-maisonxx"]
    assert results.total == 2


def test_accents_case_and_apostrophes(index):
    assert ids(search(index, Query("MAISON")), "words") == ["voc-maisonaa"]
    assert ids(search(index, Query("l’eau")), "words") == ["voc-eauaaaaa"]
    assert ids(search(index, Query("etre")), "topics") == ["top-etreverb"]


def test_articles_alone_do_not_find_words(index):
    for article in ("la", "le", "les", "l'", "un", "une", "des"):
        assert search(index, Query(article)).groups["words"] == [], article
    assert ids(search(index, Query("le")), "theory")  # в теории — обычное слово
    assert ids(search(index, Query("le chat")), "words") == ["voc-chataaaa"]


def test_word_ranking_french_before_translation(clean_content_root: Path):
    (clean_content_root / "vocabulary" / "voc-domxxxxx.yaml").write_text(
        "id: voc-domxxxxx\nkind: vocab\nentry_type: word\ntext: domicile\n"
        "translations:\n  - {text: жильё, origin: user}\ntopics: []\norigin: user\n",
        encoding="utf-8",
    )
    (clean_content_root / "vocabulary" / "voc-aaaaxxxx.yaml").write_text(
        "id: voc-aaaaxxxx\nkind: vocab\nentry_type: word\ntext: abri\n"
        "translations:\n  - {text: домик, origin: user}\ntopics: []\norigin: user\n",
        encoding="utf-8",
    )
    index = build(ContentIndex(load_content(clean_content_root)))
    # «dom» — во французском у domicile, в переводе («домик») нет: русское «дом» ≠ «dom»
    assert ids(search(index, Query("dom")), "words") == ["voc-domxxxxx"]
    # «дом» — в переводах у abri («домик») и maison («дом»); по алфавиту
    assert ids(search(index, Query("дом")), "words") == ["voc-aaaaxxxx", "voc-maisonaa"]


def test_theory_title_match_above_text_match(index):
    results = search(index, Query("артикли"))
    assert ids(results, "theory")[:2] == ["th-articles", "th-extrarul"]
    only_text = search(index, Query("элизия"))
    assert set(ids(only_text, "theory")) == {"th-articles", "th-extrarul"}


def test_theory_counts_matches(index):
    result = search(index, Query("les")).groups["theory"][0]
    assert result.id == "th-articles" and result.count == 2


def test_empty_reasons(index):
    assert search(index, Query("m")).empty_reason == "short"
    assert search(index, Query(" ?! ")).empty_reason == "short"
    assert search(index, Query("zzzz")).empty_reason == "none"
    assert search(index, Query("maison")).empty_reason is None


def test_translation_shown_only_when_enabled(index):
    assert search(index, Query("maison")).groups["words"][0].translation == "дом"
    hidden = search(index, Query("maison"), show_translation=False)
    assert hidden.groups["words"][0].translation is None


# --- US2: область и фильтры (T012) ------------------------------------------------------------


def test_scope(index):
    words = search(index, Query("дом", scope="words"))
    assert ids(words, "words") and not words.groups["topics"] and not words.groups["theory"]
    topics = search(index, Query("дом", scope="topics"))
    assert not topics.groups["words"] and ids(topics, "topics")
    assert search(index, Query("дом", scope="nonsense")).query.scope == "all"


def test_lesson_filter(index):
    assert ids(search(index, Query("pain", lesson=2)), "words") == ["voc-painaaaa"]
    assert ids(search(index, Query("maison", lesson=2)), "words") == []
    assert ids(search(index, Query("артикли", lesson=1)), "theory") == ["th-articles"]
    # темы — встречающиеся в уроке: тема «Дом» есть у слова урока 1
    assert ids(search(index, Query("дом", lesson=1)), "topics") == ["top-maisonxx"]
    assert ids(search(index, Query("дом", lesson=2)), "topics") == []


def test_topic_filter(index):
    assert ids(search(index, Query("pa", topic="top-nourritu")), "words") == ["voc-painaaaa"]
    assert ids(search(index, Query("ma", topic="top-nourritu")), "words") == []  # maison — «Дом»
    articles = search(index, Query("артикли", topic="top-articles"))
    assert set(ids(articles, "theory")) == {"th-articles", "th-extrarul"}
    assert ids(articles, "topics") == ["top-articles"]
    assert ids(search(index, Query("дом", topic="top-articles")), "topics") == []


# --- US4: фрагмент у теории (T020–T021) -------------------------------------------------------


def test_theory_snippet_around_first_match(index):
    result = search(index, Query("h aspire")).groups["theory"]
    assert not result  # в образце «h придыхательным», не «aspiré»
    extra = search(index, Query("придыхательным")).groups["theory"][0]
    assert extra.id == "th-extrarul" and extra.count == 1
    assert ("придыхательным", True) in extra.snippet


def test_theory_title_only_match_has_no_snippet(index):
    result = search(index, Query("демо", scope="theory")).groups["theory"]
    assert all(r.snippet is None or any(hit for _p, hit in r.snippet) for r in result)
