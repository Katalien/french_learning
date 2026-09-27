"""Тренажёр «Согласование прилагательного»: прилагательное из словаря к существительному.

Для каждого прилагательного с формами — вопрос с существительным женского рода
(`une maison ___ (grand)` → grande) и с существительным во множественном числе
(`des livres ___ (grand)` → grands). Существительное выбирается детерминированно,
чтобы ключ вопроса не менялся.
"""

from __future__ import annotations

import hashlib
from typing import Any

from french_learning.trainers.generators.articles import nouns
from french_learning.trainers.questions import Question, TrainerData, translation

MISSING = (
    "Нужны прилагательные с формами и существительные с родом. Добавьте прилагательные "
    "в словарь и попросите агента дополнить слова командой /complete-words."
)


def _pick(candidates: list[Any], salt: str) -> Any | None:
    if not candidates:
        return None
    digest = int(hashlib.sha1(salt.encode()).hexdigest(), 16)
    return candidates[digest % len(candidates)]


def generate(data: TrainerData) -> list[Question]:
    adjectives = [e for e in data.vocab if e.pos == "adj" and (e.forms.feminine or e.forms.plural)]
    known = [n for n in nouns(data) if not n.flags.plural_only]
    feminine = [n for n in known if n.gender == "f"]
    plural = [n for n in known if n.forms.plural]
    questions = []
    for adj in adjectives:
        noun = _pick(feminine, adj.id + ":f")
        if adj.forms.feminine and noun is not None:
            article = "une"
            questions.append(
                Question(
                    key=f"adjective-agreement:{adj.id}:{noun.id}:f",
                    prompt=f"{article} {noun.text} ___ ({adj.text})",
                    answers=[adj.forms.feminine],
                    hint=f"{translation(adj)} — {translation(noun)}",
                    full=f"{article} {noun.text} {adj.forms.feminine}",
                    source=adj.id,
                    lessons=sorted(set(adj.lessons) | set(noun.lessons)),
                    topics=sorted(set(adj.topics) | set(noun.topics)),
                )
            )
        noun = _pick(plural, adj.id + ":pl")
        if adj.forms.plural and noun is not None:
            form = adj.forms.plural if noun.gender != "f" else None
            if form is None:  # женский род во множественном — форма не хранится
                continue
            questions.append(
                Question(
                    key=f"adjective-agreement:{adj.id}:{noun.id}:pl",
                    prompt=f"des {noun.forms.plural} ___ ({adj.text})",
                    answers=[form],
                    hint=f"{translation(adj)} — {translation(noun)}, мн. ч.",
                    full=f"des {noun.forms.plural} {form}",
                    source=adj.id,
                    lessons=sorted(set(adj.lessons) | set(noun.lessons)),
                    topics=sorted(set(adj.topics) | set(noun.topics)),
                )
            )
    return questions
