"""Маршруты приложения (contracts/ui-routes.md)."""

from french_learning.web.routes import (
    elements,
    lessons,
    problems,
    sources,
    speech,
    topics,
    trust,
    vocab,
)

ALL = [
    lessons.router,
    elements.router,
    problems.router,
    sources.router,
    speech.router,
    topics.router,
    trust.router,
    vocab.router,
]
