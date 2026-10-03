"""Выполнение упражнений уроков (contracts/ui-routes.md функции 004, US1–US3).

Действия формы решения приходят через HTMX и возвращают фрагмент `exercises/solve.html`;
без HTMX — возврат на страницу упражнения.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Form, Request
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


def reported_items(index: Any, exercise_id: str) -> set[int]:
    """Пункты упражнения с открытыми сообщениями об ошибке (010, пункт 7)."""
    return {
        r.item
        for r in index.reports()
        if r.element == exercise_id and r.status == "open" and r.item is not None
    }


def solve_context(
    request: Request, exercise: Any, attempt: Attempt | None, index: Any = None, **extra
) -> dict:
    only = attempt.item_ids if attempt and attempt.scope == "item" else None
    index = index if index is not None else request.app.state.store.get()
    reported = reported_items(index, exercise.id) | set(extra.pop("reported_extra", ()))
    return {
        "reported": reported,
        "report_notice": {},
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


@router.post("/exercises/{exercise_id}/restart")
def restart(request: Request, exercise_id: str, index: Index):
    exercise = _exercise(index, exercise_id)
    return _respond(request, exercise, attempts(request).restart(exercise))


@router.get("/exercises/{exercise_id}/history")
def history(request: Request, exercise_id: str, index: Index):
    exercise = _exercise(index, exercise_id)
    store = attempts(request)
    items = [
        store.recalculate(exercise, a) for a in store.history(exercise_id) if a.status != "draft"
    ]
    context = {"index": index, "e": exercise, "attempts": items}
    return templates.TemplateResponse(request, "exercises/history.html", context)


@router.get("/mistakes")
def mistakes_page(request: Request, index: Index, lesson: str = "", topic: str = ""):
    from french_learning.exercises.mistakes import find_mistakes

    found = find_mistakes(
        index,
        attempts(request),
        lesson=int(lesson) if lesson.isdigit() else None,
        topic=topic or None,
    )
    context = {
        "index": index,
        "mistakes": found,
        "selected": {"lesson": lesson, "topic": topic},
        "lessons": index.lessons(),
        "topics": index.all_topics(),
    }
    return templates.TemplateResponse(request, "exercises/mistakes.html", context)


@router.post("/mistakes/{exercise_id}/{item_id}")
def start_mistake(request: Request, exercise_id: str, item_id: int, index: Index):
    exercise = _exercise(index, exercise_id)
    if item_id not in {i.id for i in exercise.items}:
        raise not_found("Пункт не найден")
    attempt = attempts(request).start_item(exercise, item_id)
    return RedirectResponse(f"/mistakes/attempts/{attempt.id}", status_code=303)


@router.get("/mistakes/attempts/{attempt_id}")
def mistake_attempt(request: Request, attempt_id: int, index: Index):
    attempt = attempts(request).get(attempt_id)
    if attempt is None:
        raise not_found("Попытка не найдена")
    exercise = _exercise(index, attempt.exercise_id)
    context = {"index": index, **solve_context(request, exercise, attempt)}
    return templates.TemplateResponse(request, "exercises/mistake.html", context)


@router.post("/exercises/{exercise_id}/items/{item_id}/report")
async def report_item(request: Request, exercise_id: str, item_id: int, index: Index):
    """«Не согласна с ответом» (FR-030): сообщение агенту, ответы в форме сохраняются."""
    from french_learning.content.writer import WriteError
    from french_learning.web.routes.topics import writer
    from french_learning.web.routes.trust import REPORT_REMINDER

    exercise = _exercise(index, exercise_id)
    form = await request.form()
    comment = str(form.get(f"comment-{item_id}") or form.get("comment") or "")
    answers, attempt_id = await form_answers(request, exercise)
    store = attempts(request)
    attempt = _own_attempt(store, exercise, attempt_id) or store.current(exercise.id)
    if attempt is not None and answers:
        attempt.answers = answers
    sent = False
    if not comment.strip():
        notice = "Напишите, почему ответ неверный."
    else:
        try:
            _report, result = writer(request).create_report(
                exercise.id, item_id, comment, known_element=True
            )
            sent = True
            notice = REPORT_REMINDER
            if result.warning:
                notice += f" {result.warning[0].upper()}{result.warning[1:]}."
        except WriteError as exc:
            notice = f"Сообщение не отправлено: {exc}."
    # 010 пункт 7: ответ — у самого пункта; индекс — до записи, без перечитывания хранилища
    if not request.headers.get("HX-Request"):
        return RedirectResponse(f"/elements/{exercise.id}", status_code=303)
    context = solve_context(
        request, exercise, attempt, index, reported_extra={item_id} if sent else ()
    )
    context["report_notice"] = {item_id: (notice, sent)}
    return templates.TemplateResponse(request, "exercises/solve.html", context)


@router.post("/exercises/{exercise_id}/status")
def change_status(request: Request, exercise_id: str, index: Index, status: str = Form("main")):
    from french_learning.content.writer import WriteError
    from french_learning.web.routes.topics import redirect_after_write, writer

    _exercise(index, exercise_id)
    try:
        result = writer(request).set_exercise_status(exercise_id, status)
    except WriteError as exc:
        return redirect_after_write(f"/elements/{exercise_id}", error=str(exc))
    return redirect_after_write(f"/elements/{exercise_id}", result)
