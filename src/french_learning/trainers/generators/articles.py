"""Тренажёр «Артикли»: определённый и неопределённый артикль к слову (FR-042–FR-044).

Два вопроса на существительное с известным родом: `def` (элизия, h придыхательное) и
`indef` (род). Неопределённый артикль выводится из рода и признаков, не хранится (003).
"""

from __future__ import annotations

from typing import Any

from french_learning.trainers.questions import (
    Question,
    TrainerData,
    elides,
    from_entry,
    translation,
)

DEFINITE = ["le", "la", "l'", "les"]
INDEFINITE = ["un", "une", "des"]
MISSING = (
    "В словаре нет существительных с известным родом. Попросите агента дополнить слова "
    "командой /complete-words."
)


def is_noun(entry: Any) -> bool:
    return entry.entry_type == "word" and (entry.pos == "nom" or entry.article is not None)


def has_gender(entry: Any) -> bool:
    return entry.gender in ("m", "f", "both") or entry.flags.plural_only


def definite(entry: Any) -> list[str]:
    if entry.flags.plural_only:
        return ["les"]
    if elides(entry.text, entry.flags.h_aspire):
        return ["l'"]
    return {"m": ["le"], "f": ["la"], "both": ["le", "la"]}[entry.gender]


def indefinite(entry: Any) -> list[str]:
    if entry.flags.plural_only:
        return ["des"]
    return {"m": ["un"], "f": ["une"], "both": ["un", "une"]}[entry.gender]


def with_article(article: str, text: str) -> str:
    return f"{article}{text}" if article.endswith("'") else f"{article} {text}"


def nouns(data: TrainerData) -> list[Any]:
    return [e for e in data.vocab if is_noun(e) and has_gender(e)]


def generate(data: TrainerData) -> list[Question]:
    questions = []
    for entry in nouns(data):
        common = {"prompt": f"___ {entry.text}", "mode": "buttons", "hint": translation(entry)}
        for kind, answers, options in (
            ("def", definite(entry), DEFINITE),
            ("indef", indefinite(entry), INDEFINITE),
        ):
            questions.append(
                Question(
                    key=f"articles:{entry.id}:{kind}",
                    answers=answers,
                    options=options,
                    full=" / ".join(with_article(a, entry.text) for a in answers),
                    **common,
                    **from_entry(entry),
                )
            )
    return questions
