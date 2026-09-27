"""Общие зависимости маршрутов."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request

from french_learning.content.index import ContentIndex


class ContentNotConfiguredError(Exception):
    """Хранилище контента не задано или не найдено (ui-routes.md)."""


def get_index(request: Request) -> ContentIndex:
    store = request.app.state.store
    if store is None:
        raise ContentNotConfiguredError
    return store.get()


def show_origin(request: Request) -> bool:
    """Переключатель происхождения (FR-040) хранится в cookie браузера."""
    return request.cookies.get("show_origin") == "1"


def not_found(what: str) -> HTTPException:
    return HTTPException(status_code=404, detail=what)


Index = Annotated[ContentIndex, Depends(get_index)]
