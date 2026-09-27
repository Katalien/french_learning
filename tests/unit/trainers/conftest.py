"""Данные для генераторов тренажёров: словарь строится прямо в тестах."""

import pytest

from french_learning.content import schema
from french_learning.trainers.questions import TrainerData


def make_vocab(key: str, text: str, **fields) -> schema.VocabEntry:
    data = {
        "id": f"voc-{key:a<8}"[:12],
        "kind": "vocab",
        "entry_type": "word",
        "text": text,
        "translations": [{"text": fields.pop("ru", "перевод"), "origin": "user"}],
        "topics": ["top-abcdefgh"],
        "origin": "user",
        **fields,
    }
    return schema.VocabEntry.model_validate(data)


@pytest.fixture
def vocab():
    return make_vocab


@pytest.fixture
def data():
    def build(*entries, exercises=(), texts=()):
        return TrainerData(vocab=list(entries), exercises=list(exercises), texts=list(texts))

    return build
