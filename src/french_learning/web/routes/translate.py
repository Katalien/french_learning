"""Перевод выделенного (006): `/translate`, добавление из текста, переключатель и настройки.

API — contracts/translate-api.md. Ошибки — `{"error": "…"}`. Во внешний сервис уходит только
выделенное и его начальная форма (FR-008, принцип IX).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from french_learning.translate.providers import Translator, make_translator
from french_learning.vocab.entries import vocab_entries
from french_learning.web.deps import Index

router = APIRouter()


def _error(status: int, text: str) -> JSONResponse:
    return JSONResponse({"error": text}, status_code=status)


def translator_factory(app) -> Translator:
    """Сервис по настройкам базы прогресса; ключ DeepL — только из окружения (research R3)."""
    db = app.state.progress_db
    return make_translator(
        db.get_setting("translator") or "mymemory",
        email=db.get_setting("mymemory_email"),
        deepl_key=app.state.settings.deepl_api_key,
    )


@router.get("/translate")
def translate(request: Request, index: Index, q: str = ""):
    service = request.app.state.translation
    if service is None:
        return _error(503, "перевод недоступен: хранилище не настроено")
    try:
        result = service.translate(q, vocab_entries(index))
    except ValueError as error:
        return _error(422, str(error))
    return result.to_dict()
