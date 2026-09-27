"""Поиск слов против дублей (FR-021; research R9)."""

from pathlib import Path

from french_learning.agent.vocab import vocab_find


def test_exact_match(store: Path):
    [hit] = vocab_find(store, "maison")
    assert hit["id"] == "voc-maisonaa"
    assert hit["exact"] is True
    assert hit["translations"] == ["дом"]
    assert hit["lessons"] == [1]


def test_case_and_diacritics_insensitive_candidates(store: Path):
    for query in ("Maison", "maisón"):
        [hit] = vocab_find(store, query)
        assert hit["id"] == "voc-maisonaa"
        assert hit["exact"] is (query == "Maison")


def test_filters(store: Path):
    assert vocab_find(store, "maison", gender="m") == []
    assert vocab_find(store, "maison", pos="verbe") == []
    assert vocab_find(store, "maison", gender="f", pos="nom")


def test_staging_is_searched(store: Path):
    staged = store / ".staging/op1/vocabulary/voc-stagedaa.yaml"
    staged.parent.mkdir(parents=True)
    staged.write_text(
        "id: voc-stagedaa\nkind: vocab\nentry_type: word\ntext: fromage\narticle: le\ngender: m\n"
        "translations: [{text: сыр, origin: ai}]\ntopics: [top-nourritu]\norigin: user\n",
        encoding="utf-8",
    )
    [hit] = vocab_find(store, "fromage")
    assert hit["id"] == "voc-stagedaa" and hit["staged"] is True
