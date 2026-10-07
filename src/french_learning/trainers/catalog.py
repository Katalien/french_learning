"""Каталог тренажёров (FR-040, FR-060–FR-062; research R8 функции 004).

Встроенные тренажёры описаны здесь; `trainers.yaml` в хранилище добавляет свои тренажёры
(задания от агента) и переопределяет у встроенных источник, тип заданий и правила.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from french_learning.content.index import ContentIndex
from french_learning.content.schema import BUILTIN_TRAINERS
from french_learning.trainers.generators import (
    agreement,
    articles,
    conjugation,
    determiners,
    forms,
    numbers,
    sentences,
)
from french_learning.trainers.questions import Question, TrainerData

Generator = Callable[[TrainerData], list[Question]]


@dataclass
class Builtin:
    name: str
    description: str
    generator: Generator
    missing: str
    uses_vocab: bool = True


BUILTINS: dict[str, Builtin] = {
    "articles": Builtin(
        "Артикли",
        "Определённый и неопределённый артикль к словам словаря: le / la / l' / les, "
        "un / une / des",
        articles.generate,
        articles.MISSING,
    ),
    "conjugation": Builtin(
        "Спряжение",
        "Форма глагола в настоящем времени для местоимения",
        conjugation.generate,
        conjugation.MISSING,
    ),
    "feminine": Builtin(
        "Женский род",
        "Форма женского рода прилагательных и существительных",
        forms.generate_feminine,
        forms.MISSING_FEMININE,
    ),
    "plural": Builtin(
        "Множественное число",
        "Форма множественного числа",
        forms.generate_plural,
        forms.MISSING_PLURAL,
    ),
    "possessives": Builtin(
        "Притяжательные",
        "mon / ma / mes, ton / ta / tes …",
        determiners.generate_possessives,
        determiners.MISSING,
    ),
    "demonstratives": Builtin(
        "Указательные",
        "ce / cet / cette / ces",
        determiners.generate_demonstratives,
        determiners.MISSING,
    ),
    "adjective-agreement": Builtin(
        "Согласование прилагательного",
        "Прилагательное в роде и числе существительного",
        agreement.generate,
        agreement.MISSING,
    ),
    "numbers": Builtin(
        "Числа",
        "Числа от 0 до 1000: записать словами по-французски или цифрами",
        numbers.generate,
        "",
        uses_vocab=False,
    ),
    "sentence-builder": Builtin(
        "Собери предложение",
        "Расставьте слова предложений из уроков по порядку",
        sentences.generate,
        sentences.MISSING,
        uses_vocab=False,
    ),
}
assert list(BUILTINS) == list(BUILTIN_TRAINERS)


@dataclass
class Trainer:
    id: str
    name: str
    description: str
    source: str  # builtin | agent
    exercise_type: str
    rules: str
    builtin: bool
    origin: str
    generator: Generator | None = None
    missing: str = ""
    uses_vocab: bool = False

    @property
    def progress(self) -> str:
        """Встроенные с генерацией приложением — FSRS; задания от агента — статистика."""
        return "srs" if self.source == "builtin" else "stats"

    def questions(self, data: TrainerData) -> list[Question]:
        return self.generator(data) if self.generator and self.source == "builtin" else []


def catalog(index: ContentIndex) -> list[Trainer]:
    entries = {t.id: t for t in index.trainer_entries}
    trainers = []
    for trainer_id, builtin in BUILTINS.items():
        entry = entries.pop(trainer_id, None)
        trainers.append(
            Trainer(
                id=trainer_id,
                name=builtin.name,
                description=builtin.description,
                source=(entry.source if entry and entry.source else "builtin"),
                exercise_type=(entry.exercise_type if entry and entry.exercise_type else None)
                or BUILTIN_TRAINERS[trainer_id],
                rules=(entry.rules if entry and entry.rules else ""),
                builtin=True,
                origin="user",
                generator=builtin.generator,
                missing=builtin.missing,
                uses_vocab=builtin.uses_vocab,
            )
        )
    for entry in entries.values():
        trainers.append(
            Trainer(
                id=entry.id,
                name=entry.name,
                description=entry.description,
                source="agent",
                exercise_type=entry.exercise_type,
                rules=entry.rules or "",
                builtin=False,
                origin=entry.origin,
            )
        )
    return trainers


def get_trainer(index: ContentIndex, trainer_id: str) -> Trainer | None:
    return next((t for t in catalog(index) if t.id == trainer_id), None)
