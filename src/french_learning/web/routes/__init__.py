"""Маршруты приложения (contracts/ui-routes.md)."""

from french_learning.web.routes import (
    elements,
    exercises,
    lessons,
    problems,
    sources,
    speech,
    topics,
    trainers,
    trust,
    vocab,
)

ALL = [
    lessons.router,
    elements.router,
    exercises.router,
    problems.router,
    sources.router,
    speech.router,
    topics.router,
    trainers.router,
    trust.router,
    vocab.router,
]
