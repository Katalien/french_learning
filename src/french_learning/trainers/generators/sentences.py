"""Тренажёр «Собери предложение» (FR-041; research R11).

Предложения — из пунктов упражнений уроков с подставленными правильными ответами и из
текстов уроков, длиной 4–12 слов. Допустимые порядки — варианты ответов пункта; у текстов —
только исходный. Слова перемешиваются детерминированно по ключу.
"""

from __future__ import annotations

import hashlib
import itertools
import random
import re
from typing import Any

from french_learning.content.schema import GAP_RE
from french_learning.trainers.questions import Question, TrainerData

MIN_WORDS, MAX_WORDS = 4, 12
MAX_VARIANTS = 6
MISSING = "В упражнениях и текстах уроков пока нет подходящих предложений."
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")
_MARKUP = re.compile(r"^\s*(#+|>|[-*+]\s|\d+\.\s|[—–]\s)")


def _fits(sentence: str) -> bool:
    words = sentence.split()
    return MIN_WORDS <= len(words) <= MAX_WORDS and not GAP_RE.search(sentence)


def _item_sentences(exercise: Any, item: Any) -> list[str]:
    if exercise.type in ("gap_choice", "gap_input", "multi_gap", "two_forms"):
        gaps = item.gaps
        options = [item.answers[g] for g in gaps]
        variants = []
        for combo in itertools.islice(itertools.product(*options), MAX_VARIANTS):
            text = item.text
            for gap, value in zip(gaps, combo, strict=True):
                text = text.replace(f"{{{{{gap}}}}}", value, 1)
            variants.append(_capitalize(" ".join(text.split())))
        return variants
    if exercise.type in ("transform", "picture"):
        return [" ".join(a.split()) for a in item.answers]
    return []


def _capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]


def _text_sentences(body: str) -> list[str]:
    found = []
    for line in body.splitlines():
        if not line.strip() or _MARKUP.match(line) or "|" in line:
            continue
        clean = re.sub(r"[*_`]", "", line).strip()
        found += [s.strip() for s in _SENTENCE_END.split(clean) if s.strip()]
    return found


def _shuffled(words: list[str], key: str) -> list[str]:
    rng = random.Random(key)
    tokens = list(words)
    for _ in range(10):
        rng.shuffle(tokens)
        if tokens != words or len(set(words)) == 1:
            break
    return tokens


def _question(sentences: list[str], element: Any, suffix: str) -> Question:
    first = sentences[0]
    key = "sentence-builder:" + hashlib.sha1(first.encode()).hexdigest()[:12]
    return Question(
        key=key,
        prompt="Соберите предложение",
        answers=sentences,
        mode="order",
        tokens=_shuffled(first.split(), key),
        full=first,
        source=element.id,
        lessons=[element.lesson] if element.lesson else [],
        topics=list(element.topics),
        hint=suffix,
    )


def generate(data: TrainerData) -> list[Question]:
    questions: dict[str, Question] = {}
    for exercise in data.exercises:
        for item in exercise.items:
            variants = [s for s in _item_sentences(exercise, item) if _fits(s)]
            if variants:
                q = _question(list(dict.fromkeys(variants)), exercise, "из упражнения")
                questions.setdefault(q.key, q)
    for text in data.texts:
        for sentence in _text_sentences(text.body):
            if _fits(sentence):
                q = _question([sentence], text, "из текста урока")
                questions.setdefault(q.key, q)
    return list(questions.values())
