"""Перевод выделенного (006): `/translate`, добавление из текста, переключатель и настройки.

API — contracts/translate-api.md. Ошибки — `{"error": "…"}`. Во внешний сервис уходит только
выделенное и его начальная форма (FR-008, принцип IX).
"""

from __future__ import annotations

import re
from typing import Annotated, Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from french_learning.translate.lemma import add_as
from french_learning.translate.normalize import has_cyrillic, is_multi_sentence, normalize_key
from french_learning.translate.providers import Translator, make_translator
from french_learning.translate.service import find_entry
from french_learning.vocab.entries import vocab_entries
from french_learning.web.deps import Index
from french_learning.web.routes.trust import _back

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


@router.post("/settings/translate")
def toggle_translate(request: Request, show: Annotated[str, Form()] = "1"):
    """«Перевод при выделении» в меню «⋯» — cookie браузера, по умолчанию включён (research R8)."""
    response = RedirectResponse(_back(request), status_code=303)
    response.set_cookie("translate", "0" if show == "0" else "1", max_age=10 * 365 * 24 * 3600)
    return response


def _word_before(text: str, sentence: str) -> str | None:
    """Слово прямо перед выделенным в предложении — для рода по артиклю (une crêpe)."""
    at = sentence.casefold().find(text.casefold())
    if at <= 0:
        return None
    words = re.findall(r"[\w'’]+", sentence[:at])
    return words[-1] if words else None


@router.post("/vocab/from-text")
async def vocab_from_text(request: Request, index: Index):
    """«+ В словарь» из подсказки: слово в начальной форме или фраза как есть, с переводом,
    предложением-примером и уроком; без темы (FR-012–FR-014, data-model)."""
    from french_learning.content.writer import WriteError
    from french_learning.vocab.edits import VocabEditor, VocabError

    try:
        payload: Any = await request.json()
    except ValueError:
        payload = None
    if not isinstance(payload, dict):
        return _error(422, "ожидался JSON-объект")
    text = " ".join(str(payload.get("text") or "").split())
    sentence = " ".join(str(payload.get("sentence") or "").split())
    lesson = payload.get("lesson")
    lesson = lesson if isinstance(lesson, int) and lesson > 0 else None
    if not text or has_cyrillic(text):
        return _error(422, "в словарь добавляется французский текст")
    if is_multi_sentence(text):
        return _error(422, "абзац в словарь не добавляется — выделите слово, фразу или предложение")

    entries = vocab_entries(index)
    result = request.app.state.translation.translate(text, entries)
    if result.translation is None:
        return _error(422, result.error or "перевода нет")
    target = add_as(text, before=_word_before(text, sentence))
    existing = find_entry(entries, text, target.text, result.lemma)
    translations = [t.text for t in existing.translations] if existing else [result.translation]
    origin = "service" if result.source in ("service", "cache") else "user"
    same_as_sentence = normalize_key(text) == normalize_key(sentence)
    try:
        entry_id, merged = VocabEditor(request.app.state.settings.content_dir).add_word(
            text=existing.text if existing else target.text,
            translations=translations,
            topics=[],
            article=None if existing else target.article,
            gender=None if existing else target.gender,
            entry_type=existing.entry_type if existing else target.entry_type,
            example=sentence if sentence and not same_as_sentence else None,
            source_lesson=lesson,
            translation_origin=origin,
        )
    except (VocabError, WriteError) as error:
        return _error(422, str(error))
    return JSONResponse(
        {
            "id": entry_id,
            "text": existing.text if existing else target.text,
            "translation": ", ".join(translations),
            "merged": merged,
        },
        status_code=201,
    )
