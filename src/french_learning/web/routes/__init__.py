"""Маршруты приложения (contracts/ui-routes.md)."""

from french_learning.web.routes import elements, lessons, problems, sources

ALL = [lessons.router, elements.router, problems.router, sources.router]
