"""Выполнение упражнений уроков (contracts/ui-routes.md функции 004, US1–US3).

Действия формы решения приходят через HTMX и возвращают фрагмент `exercises/solve.html`;
без HTMX — возврат на страницу упражнения.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from french_learning.content.index import ContentIndex
from french_learning.exercises.attempts import Answers, Attempt, AttemptStore
from french_learning.exercises.grading import CHOICE_SUFFIX, checkable
from french_learning.practice.checking import FRENCH_SYMBOLS
from french_learning.web.deps import Index, not_found, show_origin
from french_learning.web.templating import templates

router = APIRouter()


def attempts(request: Request) -> AttemptStore:
    return request.app.state.attempts


def _exercise(index: ContentIndex, exercise_id: str) -> Any:
    exercise = index.element(exercise_id)
    if exercise is None or exercise.kind != "exercise":
        raise not_found("Упражнение не найдено")
    return exercise


async def form_answers(request: Request, exercise: Any) -> tuple[Answers, int | None]:
    """Поля формы `i<пункт>.<поле>` → ответы; у `choice` значения собираются в список."""
    form = await request.form()
    answers: Answers = {}
    for key, value in form.multi_items():
        if not key.startswith("i") or "." not in key or not isinstance(value, str):
            continue
        item, name = key[1:].split(".", 1)
        fields = answers.setdefault(item, {})
        if exercise.type == "choice" and name == "a":
            fields.setdefault(name, []).append(value)
        elif name.endswith(CHOICE_SUFFIX) or value.strip() or name not in fields:
            fields[name] = value
    attempt_id = form.get("attempt")
    return answers, int(attempt_id) if attempt_id and attempt_id.isdigit() else None


def _own_attempt(store: AttemptStore, exercise: Any, attempt_id: int | None) -> Attempt | None:
    attempt = store.get(attempt_id) if attempt_id else None
    return attempt if attempt and attempt.exercise_id == exercise.id else None


def solve_context(request: Request, exercise: Any, attempt: Attempt | None, **extra) -> dict:
    only = attempt.item_ids if attempt and attempt.scope == "item" else None
    return {
        "e": exercise,
        "attempt": attempt,
        "symbols": FRENCH_SYMBOLS,
        "base": f"/exercises/{exercise.id}",
        "report_url": f"/exercises/{exercise.id}/items",
        "only_items": only,
        "checkable": checkable(exercise),
        "show_origin": show_origin(request),
        **extra,
    }


def _respond(request: Request, exercise: Any, attempt: Attempt | None, **extra):
    if not request.headers.get("HX-Request"):
        return RedirectResponse(f"/elements/{exercise.id}", status_code=303)
    context = solve_context(request, exercise, attempt, **extra)
    return templates.TemplateResponse(request, "exercises/solve.html", context)


@router.post("/exercises/{exercise_id}/draft")
async def save_draft(request: Request, exercise_id: str, index: Index):
    exercise = _exercise(index, exercise_id)
    answers, attempt_id = await form_answers(request, exercise)
    store = attempts(request)
    attempt = _own_attempt(store, exercise, attempt_id)
    if attempt is not None:
        attempt.answers = answers
        store._save(attempt)
    else:
        store.save_draft(exercise, answers)
    return {"saved": True}


@router.post("/exercises/{exercise_id}/check")
async def check(request: Request, exercise_id: str, index: Index):
    exercise = _exercise(index, exercise_id)
    answers, attempt_id = await form_answers(request, exercise)
    store = attempts(request)
    attempt = store.check(exercise, answers, _own_attempt(store, exercise, attempt_id))
    return _respond(request, exercise, attempt)


@router.post("/exercises/{exercise_id}/reveal/{item_id}")
async def reveal(request: Request, exercise_id: str, item_id: int, index: Index):
    exercise = _exercise(index, exercise_id)
    answers, attempt_id = await form_answers(request, exercise)
    store = attempts(request)
    attempt = _own_attempt(store, exercise, attempt_id) or store.current(exercise.id)
    if attempt is None:
        attempt = store.save_draft(exercise, answers)
    attempt.answers = answers or attempt.answers
    attempt = store.reveal(exercise, item_id, attempt)
    return _respond(request, exercise, attempt)


@router.post("/exercises/{exercise_id}/save")
async def save_open(request: Request, exercise_id: str, index: Index):
    exercise = _exercise(index, exercise_id)
    answers, _attempt_id = await form_answers(request, exercise)
    attempt = attempts(request).save_open(exercise, answers)
    return _respond(request, exercise, attempt)
