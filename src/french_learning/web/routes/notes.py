"""Заметки (005): JSON API, панель вопросов, страница «Заметки к уроку».

API — contracts/notes-api.md. Ошибки — `{"error": "…"}`: 422 — нарушено правило заметки,
404 — нет заметки или урока.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from french_learning.notes.store import Anchor, NoteError, NoteStore
from french_learning.web.deps import Index

router = APIRouter()

_PATCH_FIELDS = ("body", "kind", "important", "answered", "answer")


def _store(request: Request) -> NoteStore:
    return request.app.state.notes


def _error(status: int, text: str) -> JSONResponse:
    return JSONResponse({"error": text}, status_code=status)


async def _payload(request: Request) -> dict[str, Any]:
    try:
        data = await request.json()
    except ValueError:
        data = None
    if not isinstance(data, dict):
        raise NoteError("ожидался JSON-объект")
    return data


def _anchor(value: Any) -> Anchor | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise NoteError("неверная привязка к фрагменту")
    return Anchor.from_dict(value)


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise NoteError("номер урока — число") from error


@router.post("/notes")
async def create_note(request: Request, index: Index):
    try:
        data = await _payload(request)
        lesson = _int_or_none(data.get("lesson"))
        element_id = data.get("element_id")
        if element_id is None and lesson is not None and index.lesson(lesson) is None:
            return _error(404, f"урок {lesson} не найден")
        note = _store(request).create(
            index,
            kind=data.get("kind"),
            body=data.get("body"),
            important=bool(data.get("important", False)),
            lesson=lesson,
            element_id=element_id,
            anchor=_anchor(data.get("anchor")),
        )
    except NoteError as error:
        return _error(422, str(error))
    return JSONResponse(note.to_dict(), status_code=201)


@router.patch("/notes/{note_id}")
async def update_note(request: Request, note_id: int, index: Index):
    try:
        data = await _payload(request)
        fields = {key: data[key] for key in _PATCH_FIELDS if key in data}
        if "anchor" in data:
            fields["anchor"] = _anchor(data["anchor"])
        note = _store(request).update(index, note_id, **fields)
    except LookupError as error:
        return _error(404, str(error))
    except NoteError as error:
        return _error(422, str(error))
    return JSONResponse(note.to_dict())


@router.delete("/notes/{note_id}")
def delete_note(request: Request, note_id: int):
    if not _store(request).delete(note_id):
        return _error(404, f"заметка {note_id} не найдена")
    return Response(status_code=204)


# --- страницы -------------------------------------------------------------------------------


def notes_json(request: Request, element_ids: list[str], page: str, lesson: int | None) -> str:
    """Заметки элементов для `notes.js`, безопасно для вставки в <script> (research R4)."""
    import json

    store = request.app.state.notes
    notes = store.for_elements(element_ids) if store is not None else []
    data = {"page": page, "lesson": lesson, "notes": [n.to_dict() for n in notes]}
    return (
        json.dumps(data, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def element_notes(request: Request, element_id: str) -> list:
    store = request.app.state.notes
    return store.for_elements([element_id]) if store is not None else []


@router.get("/questions")
def questions_panel(request: Request, index: Index):
    """Панель открытых вопросов всех уроков (HTMX-фрагмент, FR-014)."""
    from itertools import groupby

    from french_learning.web.templating import templates

    questions = _store(request).open_questions()
    groups = [(lesson, list(items)) for lesson, items in groupby(questions, key=lambda n: n.lesson)]
    return templates.TemplateResponse(
        request, "partials/questions.html", {"groups": groups, "index": index}
    )


@router.get("/lessons/{number}/notes")
def lesson_notes_page(request: Request, number: int, index: Index, fragment: int = 0):
    """Страница «Заметки к уроку» (вариант В1, FR-016, FR-017)."""
    from french_learning.notes.grouping import lesson_page
    from french_learning.web.deps import not_found
    from french_learning.web.routes.lessons import _context
    from french_learning.web.templating import templates

    if index.lesson(number) is None:
        raise not_found(f"Урок {number} не найден")
    tree = index.lesson_tree(number, request.app.state.progress)
    page = lesson_page(_store(request).for_lesson(number), tree)
    if fragment:
        return templates.TemplateResponse(
            request, "partials/lesson_notes.html", {"n": number, "page": page}
        )
    context = _context(request, index, number, section="notes", page=page)
    return templates.TemplateResponse(request, "lesson_notes.html", context)
