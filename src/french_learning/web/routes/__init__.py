"""Маршруты приложения (contracts/ui-routes.md)."""

from french_learning.web.routes import (
    elements,
    exercises,
    lessons,
    notes,
    problems,
    search,
    sources,
    speech,
    topics,
    trainers,
    translate,
    trust,
    vocab,
)

ALL = [
    lessons.router,
    elements.router,
    exercises.router,
    notes.router,
    problems.router,
    search.router,
    sources.router,
    speech.router,
    topics.router,
    trainers.router,
    translate.router,
    trust.router,
    vocab.router,
]
