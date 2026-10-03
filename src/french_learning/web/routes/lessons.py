"""Главная, урок и его разделы (FR-030–FR-039, contracts/ui-routes.md)."""

from typing import Literal

from fastapi import APIRouter, Request

from french_learning.content.index import ContentIndex, exercise_done
from french_learning.web.deps import Index, not_found, show_origin
from french_learning.web.templating import templates

router = APIRouter()


def _lesson_or_404(index: ContentIndex, number: int):
    lesson = index.lesson(number)
    if lesson is None:
        raise not_found(f"Урок {number} не найден")
    return lesson


def _list_view(request: Request) -> str:
    """Вид списка заданий из «Настроек» (009, FR-020a): rows | tiles."""
    db = request.app.state.progress_db
    value = db.get_setting("exercise_list_view") if db is not None else None
    return value if value in ("rows", "tiles") else "rows"


def _counts(index: ContentIndex, number: int) -> dict[str, int]:
    """Счётчики для панели разделов урока (009)."""
    new_words, repeat_words = index.lesson_vocabulary(number)
    exercises = [e for e in index.elements(number, kind="exercise") if e.status != "reserve"]
    return {
        "theory": len(index.elements(number, kind="theory")),
        "texts": len(index.elements(number, kind="text")),
        "vocab": len(new_words) + len(repeat_words),
        "tasks": len(exercises),
    }


def _context(request: Request, index: ContentIndex, number: int, **extra) -> dict:
    _lesson_or_404(index, number)
    counts = _counts(index, number)
    notes = request.app.state.notes
    counts["notes"] = notes.lesson_counts().get(number, 0) if notes is not None else 0
    return {
        "index": index,
        "counts": counts,
        "summary": index.lesson_summary(number, request.app.state.progress),
        "show_origin": show_origin(request),
        "materials_dir": request.app.state.settings.source_materials_dir,
        **extra,
    }


@router.get("/")
def today_page(request: Request, index: Index):
    """Экран «Сегодня» (009, FR-003)."""
    import datetime as dt

    from french_learning.web.today import build_today

    state = request.app.state
    today = build_today(index, state.cards, state.sessions, state.progress, state.trainer_schedule)
    context = {"index": index, "t": today, "today_date": dt.date.today()}
    return templates.TemplateResponse(request, "today.html", context)


@router.get("/lessons")
def home(request: Request, index: Index):
    progress = request.app.state.progress
    summaries = [index.lesson_summary(lesson.number, progress) for lesson in index.lessons()]
    return templates.TemplateResponse(
        request, "home.html", {"index": index, "summaries": summaries}
    )


@router.get("/lessons/{number}")
def lesson_page(request: Request, number: int, index: Index):
    return templates.TemplateResponse(
        request, "lesson.html", _context(request, index, number, section="overview")
    )


@router.get("/lessons/{number}/tasks")
def lesson_tasks(
    request: Request,
    number: int,
    index: Index,
    part: Literal["class", "homework"] = "class",
):
    exercises = index.elements(number, part=part, kind="exercise")
    visible = [e for e in exercises if e.status != "reserve"]
    context = _context(
        request,
        index,
        number,
        section="tasks",
        part=part,
        exercises=visible,
        has_reserve=len(visible) < len(exercises),
        done={e.id for e in visible if exercise_done(e, request.app.state.progress)},
        list_view=_list_view(request),
    )
    template = "partials/task_list.html" if request.headers.get("HX-Request") else "tasks.html"
    return templates.TemplateResponse(request, template, context)


@router.get("/lessons/{number}/reserve")
def lesson_reserve(request: Request, number: int, index: Index):
    reserve = [e for e in index.elements(number, kind="exercise") if e.status == "reserve"]
    return templates.TemplateResponse(
        request,
        "reserve.html",
        _context(request, index, number, section="tasks", exercises=reserve),
    )


def _reading_notes(request: Request, items: list, number: int) -> str:
    from french_learning.web.routes.notes import notes_json

    return notes_json(request, [e.id for e in items], page="reading", lesson=number)


@router.get("/lessons/{number}/theory")
def lesson_theory(request: Request, number: int, index: Index):
    theory = index.elements(number, kind="theory")
    context = _context(
        request,
        index,
        number,
        section="theory",
        theory=theory,
        notes_json=_reading_notes(request, theory, number),
    )
    return templates.TemplateResponse(request, "theory.html", context)


@router.get("/lessons/{number}/vocab")
def lesson_vocab(request: Request, number: int, index: Index):
    """Раздел «Лексика» (009, FR-011)."""
    new_words, repeat_words = index.lesson_vocabulary(number)
    context = _context(
        request, index, number, section="vocab", new_words=new_words, repeat_words=repeat_words
    )
    return templates.TemplateResponse(request, "lesson_vocab.html", context)


@router.get("/lessons/{number}/texts")
def lesson_texts(request: Request, number: int, index: Index):
    texts = index.elements(number, kind="text")
    context = _context(
        request,
        index,
        number,
        section="texts",
        texts=texts,
        notes_json=_reading_notes(request, texts, number),
    )
    return templates.TemplateResponse(request, "texts.html", context)
