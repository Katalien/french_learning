"""Каталог тренажёров: встроенные + trainers.yaml (FR-040, FR-046, FR-060, FR-062)."""

from pathlib import Path

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content
from french_learning.content.schema import BUILTIN_TRAINERS
from french_learning.trainers.catalog import catalog, get_trainer
from french_learning.trainers.questions import TrainerData


def index_of(root: Path) -> ContentIndex:
    return ContentIndex(load_content(root))


def test_builtin_and_own_trainers(clean_content_root: Path):
    trainers = catalog(index_of(clean_content_root))
    ids = [t.id for t in trainers]
    assert ids[: len(BUILTIN_TRAINERS)] == list(BUILTIN_TRAINERS)
    assert "negation" in ids
    negation = get_trainer(index_of(clean_content_root), "negation")
    assert negation.source == "agent" and negation.progress == "stats" and not negation.builtin
    assert negation.exercise_type == "transform"


def test_builtin_override_rules_and_source(clean_content_root: Path):
    articles = get_trainer(index_of(clean_content_root), "articles")
    assert articles.builtin and articles.source == "builtin" and articles.progress == "srs"
    assert "h придыхательное" in articles.rules
    (clean_content_root / "trainers.yaml").write_text(
        "trainers:\n  - {id: numbers, source: agent}\n", encoding="utf-8"
    )
    numbers = get_trainer(index_of(clean_content_root), "numbers")
    assert numbers.source == "agent" and numbers.progress == "stats"
    assert numbers.exercise_type == BUILTIN_TRAINERS["numbers"]


def test_missing_data_messages(clean_content_root: Path):
    index = index_of(clean_content_root)
    empty = TrainerData()
    conj = get_trainer(index, "conjugation")
    assert conj.questions(empty) == [] and "/complete-words" in conj.missing
    for trainer in catalog(index):
        if trainer.builtin and trainer.id not in ("numbers",):
            assert trainer.missing, trainer.id
    assert get_trainer(index, "numbers").questions(empty)
    assert get_trainer(index, "unknown") is None


def test_own_trainer_without_code_change(clean_content_root: Path):
    # SC-007: запись в каталоге с существующим типом → тренажёр доступен
    (clean_content_root / "trainers.yaml").write_text(
        "trainers:\n"
        "  - {id: est-ce-que, name: Вопросы с est-ce que, description: d,"
        " exercise_type: transform, rules: r}\n",
        encoding="utf-8",
    )
    trainer = get_trainer(index_of(clean_content_root), "est-ce-que")
    assert trainer is not None and trainer.source == "agent" and trainer.progress == "stats"
