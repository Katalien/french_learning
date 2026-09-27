"""Тренажёры «Притяжательные» (mon / ma / mes …) и «Указательные» (ce / cet / cette / ces).

Правила: перед гласной и h немым у женского рода — mon / ton / son (mon amie); cet перед
мужским родом на гласную или h немое; у слов только во множественном числе — mes … / ces.
У слов обоих родов засчитываются формы обоих родов.
"""

from __future__ import annotations

from typing import Any

from french_learning.trainers.generators.articles import nouns
from french_learning.trainers.questions import (
    Question,
    TrainerData,
    elides,
    from_entry,
    translation,
)

# лицо → (м. р., ж. р., мн. ч.) и русские подсказки (м., ж., мн.)
OWNERS = {
    1: (("mon", "ma", "mes"), ("мой", "моя", "мои")),
    2: (("ton", "ta", "tes"), ("твой", "твоя", "твои")),
    3: (("son", "sa", "ses"), ("его / её", "его / её", "его / её")),
    4: (("notre", "notre", "nos"), ("наш", "наша", "наши")),
    5: (("votre", "votre", "vos"), ("ваш", "ваша", "ваши")),
    6: (("leur", "leur", "leurs"), ("их", "их", "их")),
}
DEMONSTRATIVES = ["ce", "cet", "cette", "ces"]
MISSING = (
    "В словаре нет существительных с известным родом. Попросите агента дополнить слова "
    "командой /complete-words."
)


def _possessive(entry: Any, forms: tuple[str, str, str]) -> list[str]:
    masc, fem, plural = forms
    if entry.flags.plural_only:
        return [plural]
    vowel = elides(entry.text, entry.flags.h_aspire)
    genders = ["m", "f"] if entry.gender == "both" else [entry.gender]
    result = [masc if g == "m" or vowel else fem for g in genders]
    return list(dict.fromkeys(result))


def _hint_index(entry: Any) -> int:
    if entry.flags.plural_only:
        return 2
    return 1 if entry.gender == "f" else 0


def generate_possessives(data: TrainerData) -> list[Question]:
    questions = []
    for entry in nouns(data):
        for person, (forms, hints) in OWNERS.items():
            answers = _possessive(entry, forms)
            questions.append(
                Question(
                    key=f"possessives:{entry.id}:{person}",
                    prompt=f"___ {entry.text}",
                    answers=answers,
                    hint=f"{hints[_hint_index(entry)]} · {translation(entry)}",
                    full=" / ".join(f"{a} {entry.text}" for a in answers),
                    **from_entry(entry),
                )
            )
    return questions


def _demonstrative(entry: Any) -> list[str]:
    if entry.flags.plural_only:
        return ["ces"]
    masc = "cet" if elides(entry.text, entry.flags.h_aspire) else "ce"
    return {"m": [masc], "f": ["cette"], "both": [masc, "cette"]}[entry.gender]


def generate_demonstratives(data: TrainerData) -> list[Question]:
    return [
        Question(
            key=f"demonstratives:{entry.id}",
            prompt=f"___ {entry.text}",
            answers=(answers := _demonstrative(entry)),
            mode="buttons",
            options=DEMONSTRATIVES,
            hint=translation(entry),
            full=" / ".join(f"{a} {entry.text}" for a in answers),
            **from_entry(entry),
        )
        for entry in nouns(data)
    ]
