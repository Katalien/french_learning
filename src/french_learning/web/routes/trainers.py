"""Тренажёры: каталог, запуск, задания порциями (contracts/ui-routes.md функции 004, US4, US5)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from french_learning.content.index import ContentIndex
from french_learning.practice.checking import FRENCH_SYMBOLS, check_french, normalize_keyboard
from french_learning.trainers.catalog import Trainer, catalog, get_trainer
from french_learning.trainers.questions import Question, TrainerData
from french_learning.trainers.sessions import TrainerSessions
from french_learning.web.deps import Index, not_found
from french_learning.web.templating import templates

router = APIRouter()

SCOPES = {"all": "весь словарь", "lesson": "урок", "topic": "тема", "hard": "сложные"}


def _sessions(request: Request) -> TrainerSessions:
    return request.app.state.trainer_sessions


def _trainer(index: ContentIndex, trainer_id: str) -> Trainer:
    trainer = get_trainer(index, trainer_id)
    if trainer is None:
        raise not_found("Тренажёр не найден")
    return trainer


def trainer_questions(request: Request, index: ContentIndex, trainer: Trainer) -> list[Question]:
    """Вопросы тренажёра: встроенные — от генератора, с источником «агент» — из пула."""
    if trainer.source == "builtin":
        return trainer.questions(TrainerData.from_index(index))
    from french_learning.trainers.pools import pool_questions

    return pool_questions(index, request.app.state.trainer_schedule, trainer.id)


def _scoped(questions: list[Question], params: dict, hard: set[str]) -> list[Question]:
    scope = params.get("scope", "all")
    if scope == "lesson" and params.get("lesson"):
        return [q for q in questions if int(params["lesson"]) in q.lessons]
    if scope == "topic" and params.get("topic"):
        return [q for q in questions if params["topic"] in q.topics]
    if scope == "hard":
        return [q for q in questions if q.key in hard]
    return questions


@router.get("/trainers")
def trainers_page(request: Request, index: Index):
    schedule = request.app.state.trainer_schedule
    rows = []
    for trainer in catalog(index):
        questions = trainer_questions(request, index, trainer)
        keys = [q.key for q in questions]
        rows.append(
            {
                "trainer": trainer,
                "total": len(keys),
                "due": schedule.due_count(trainer.id, keys) if trainer.progress == "srs" else 0,
            }
        )
    return templates.TemplateResponse(
        request, "trainers/catalog.html", {"index": index, "rows": rows}
    )


@router.get("/trainers/{trainer_id}")
def trainer_setup(request: Request, trainer_id: str, index: Index):
    trainer = _trainer(index, trainer_id)
    questions = trainer_questions(request, index, trainer)
    schedule = request.app.state.trainer_schedule
    lessons = sorted({n for q in questions for n in q.lessons})
    topics = {t for q in questions for t in q.topics}
    context = {
        "index": index,
        "trainer": trainer,
        "total": len(questions),
        "due": schedule.due_count(trainer.id, [q.key for q in questions]),
        "hard": len(schedule.hard_keys(trainer.id) & {q.key for q in questions}),
        "lessons": lessons,
        "topics": [t for t in index.all_topics() if t.id in topics],
        "scopes": SCOPES,
        "portion": _sessions(request).portion_size(),
    }
    if trainer.source == "agent":
        from french_learning.trainers.pools import pool_summary

        context["pool"] = pool_summary(index, schedule, trainer.id)
    return templates.TemplateResponse(request, "trainers/setup.html", context)


@router.post("/trainers/{trainer_id}/start")
def trainer_start(
    request: Request,
    trainer_id: str,
    index: Index,
    scope: Annotated[str, Form()] = "all",
    lesson: Annotated[str, Form()] = "",
    topic: Annotated[str, Form()] = "",
):
    trainer = _trainer(index, trainer_id)
    params = {"scope": scope if scope in SCOPES else "all", "lesson": lesson, "topic": topic}
    if trainer.source == "agent":
        params = {"scope": "all", "pool": True}
    hard = request.app.state.trainer_schedule.hard_keys(trainer.id)
    keys = [q.key for q in _scoped(trainer_questions(request, index, trainer), params, hard)]
    session_id = _sessions(request).start(trainer.id, params, keys)
    return RedirectResponse(f"/trainers/s/{session_id}", status_code=303)


def _session_state(request: Request, index: ContentIndex, session_id: str):
    sessions = _sessions(request)
    try:
        trainer_id = sessions.trainer_id(session_id)
    except KeyError:
        raise not_found("Подход не найден") from None
    trainer = _trainer(index, trainer_id)
    questions = {q.key: q for q in trainer_questions(request, index, trainer)}
    key = sessions.current(session_id)
    return sessions, trainer, questions, key


def _page(request: Request, index: ContentIndex, session_id: str, **extra):
    sessions, trainer, questions, key = _session_state(request, index, session_id)
    answered, total, correct = sessions.progress(session_id)
    context = {
        "index": index,
        "trainer": trainer,
        "session_id": session_id,
        "answered": answered,
        "total": total,
        "correct": correct,
        "symbols": FRENCH_SYMBOLS,
        **extra,
    }
    if "result" in extra:
        return templates.TemplateResponse(request, "trainers/result.html", context)
    if key is None or key not in questions:
        if key is not None:  # вопрос исчез (слово удалено) — пропустить
            sessions.record(session_id, key, correct=False, answer=None, srs=False)
            return _page(request, index, session_id, **extra)
        return templates.TemplateResponse(request, "trainers/summary.html", context)
    context["q"] = questions[key]
    return templates.TemplateResponse(request, "trainers/question.html", context)


@router.get("/trainers/s/{session_id}")
def trainer_question(request: Request, session_id: str, index: Index):
    return _page(request, index, session_id)


def _grade(q: Question, answer: str) -> tuple[str, list[str]]:
    """correct / wrong / choose (+ варианты написания)."""
    if q.mode in ("buttons", "order"):
        given = normalize_keyboard(answer)
        ok = any(given == normalize_keyboard(a) for a in q.answers)
        return ("correct" if ok else "wrong"), []
    result = check_french(answer, q.answers)
    if result.status == "choose_spelling":
        return "choose", result.variants
    return result.status, []


def _record(
    request: Request, index: ContentIndex, session_id: str, form_key: str | None, **kwargs
) -> Any:
    sessions, trainer, questions, key = _session_state(request, index, session_id)
    if key is None or (form_key and form_key != key):  # повторная отправка формы
        return RedirectResponse(f"/trainers/s/{session_id}", status_code=303), None
    sessions.record(session_id, key, srs=trainer.progress == "srs", **kwargs)
    return None, questions.get(key)


def _grade_gaps(q: Question, form: dict[str, str]) -> tuple[str, dict[str, list[str]]]:
    """Несколько пропусков: неверный любой — ошибка; только акценты — выбор написания."""
    choose: dict[str, list[str]] = {}
    for gap, accepted in q.gaps.items():
        chosen = form.get(f"g{gap}~choice")
        if chosen:
            if chosen not in accepted:
                return "wrong", {}
            continue
        result = check_french(form.get(f"g{gap}", ""), accepted)
        if result.status == "wrong":
            return "wrong", {}
        if result.status == "choose_spelling":
            choose[gap] = result.variants
    return ("choose" if choose else "correct"), choose


@router.post("/trainers/s/{session_id}/answer")
async def trainer_answer(request: Request, session_id: str, index: Index):
    form = {k: v for k, v in (await request.form()).items() if isinstance(v, str)}
    answer = form.get("answer", "")
    *_, questions, key = _session_state(request, index, session_id)
    if key is None or key not in questions:
        return RedirectResponse(f"/trainers/s/{session_id}", status_code=303)
    q = questions[key]
    if q.mode == "gaps":
        status, choose = _grade_gaps(q, form)
        answer = " / ".join(form.get(f"g{g}~choice") or form.get(f"g{g}", "") for g in q.gaps)
        if status == "choose":
            return _page(request, index, session_id, choose=choose, given=form)
    else:
        status, variants = _grade(q, answer)
        if status == "choose":
            return _page(request, index, session_id, choose=variants, given=answer)
    redirect, q = _record(
        request, index, session_id, form.get("key"), correct=status == "correct", answer=answer
    )
    return redirect or _page(
        request, index, session_id, result=status == "correct", q=q, given=answer
    )


@router.post("/trainers/s/{session_id}/spelling")
def trainer_spelling(
    request: Request,
    session_id: str,
    index: Index,
    answer: Annotated[str, Form()] = "",
    choice: Annotated[str, Form()] = "",
    key: Annotated[str, Form()] = "",
):
    _s, _t, questions, key = _session_state(request, index, session_id)
    if key is None or key not in questions:
        return RedirectResponse(f"/trainers/s/{session_id}", status_code=303)
    ok = choice in questions[key].answers
    redirect, q = _record(request, index, session_id, key, correct=ok, answer=choice or answer)
    return redirect or _page(request, index, session_id, result=ok, q=q, given=choice or answer)


@router.post("/trainers/s/{session_id}/reveal")
def trainer_reveal(
    request: Request, session_id: str, index: Index, key: Annotated[str, Form()] = ""
):
    redirect, q = _record(request, index, session_id, key, correct=False, revealed=True, answer="")
    return redirect or _page(request, index, session_id, result=False, q=q, given="", revealed=True)


@router.post("/trainers/s/{session_id}/continue")
def trainer_continue(request: Request, session_id: str, index: Index):
    sessions, trainer, questions, _key = _session_state(request, index, session_id)
    params = sessions.params(session_id)
    hard = request.app.state.trainer_schedule.hard_keys(trainer.id)
    keys = [q.key for q in _scoped(list(questions.values()), params, hard)]
    sessions.continue_with(session_id, keys)
    return RedirectResponse(f"/trainers/s/{session_id}", status_code=303)
