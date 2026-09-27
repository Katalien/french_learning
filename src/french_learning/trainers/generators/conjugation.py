"""Тренажёр «Спряжение»: форма глагола для местоимения (FR-045).

Время входит в ключ вопроса (`conjugation:<id>:present:nous`), поэтому другие времена
добавятся без смены формата. Сейчас — только настоящее время.
"""

from __future__ import annotations

from french_learning.trainers.questions import (
    Question,
    TrainerData,
    elides,
    from_entry,
    translation,
)

TENSES = {"present": "présent"}
MISSING = (
    "В словаре нет глаголов со спряжением. Добавьте глаголы в словарь и попросите агента "
    "дополнить их командой /complete-words."
)


def _with_pronoun(pronoun: str, form: str) -> str:
    if pronoun == "je" and elides(form):
        return f"j'{form}"
    return f"{pronoun} {form}"


def accepted(pronoun_key: str, form: str) -> list[str]:
    """Форма без местоимения и с местоимением (`parlons` и `nous parlons`)."""
    pronouns = pronoun_key.split("/")
    form = form.strip()
    lowered = form.casefold()
    for pronoun in pronouns:
        for prefix in (f"{pronoun} ", "j'" if pronoun == "je" else None):
            if prefix and lowered.startswith(prefix):
                bare = form[len(prefix) :].strip()
                return [form, bare]
    return [form, *(_with_pronoun(p, form) for p in pronouns)]


def generate(data: TrainerData) -> list[Question]:
    questions = []
    for entry in data.vocab:
        if entry.verb is None:
            continue
        for tense, table in entry.verb.conjugation.items():
            if tense not in TENSES:
                continue
            for pronoun, form in table.items():
                if not form:
                    continue
                answers = accepted(pronoun, form)
                shown = pronoun.split("/")[0]
                questions.append(
                    Question(
                        key=f"conjugation:{entry.id}:{tense}:{pronoun}",
                        prompt=f"{entry.text} — {shown}",
                        answers=answers,
                        hint=f"{translation(entry)} · {TENSES[tense]}",
                        full=answers[0]
                        if " " in answers[0] or "'" in answers[0]
                        else _with_pronoun(shown, answers[0]),
                        **from_entry(entry),
                    )
                )
    return questions
