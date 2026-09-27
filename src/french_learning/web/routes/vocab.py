"""Словарь и повторение карточек (функция 003, contracts/ui-routes.md)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from french_learning.content.index import ContentIndex
from french_learning.vocab import entries as vocab_entries
from french_learning.vocab.sessions import SessionParams
from french_learning.web.deps import Index, not_found
from french_learning.web.templating import templates

router = APIRouter()

MODE_NAMES = {
    "today": "Пора повторить сегодня",
    "lesson": "По уроку",
    "topic": "По теме",
    "all": "Все слова",
    "hard": "Сложные",
}
KIND_FILTERS = {
    "all": "всё вместе",
    "word": "только слова",
    "verb": "только глаголы",
    "phrase": "только фразы",
}
DIRECTIONS = {"fr_ru": "французский → русский", "ru_fr": "русский → французский"}
RATING_NAMES = {"again": "Не помню", "hard": "С трудом", "good": "Помню"}


def _practice(request: Request, index: ContentIndex):
    state = request.app.state
    if state.cards is None:
        raise not_found("Хранилище не настроено")
    state.cards.sync(index)
    return state.cards, state.sessions


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


@router.get("/practice")
def practice_setup(request: Request, index: Index):
    _cards, sessions = _practice(request, index)
    context = {
        "index": index,
        "today_count": sessions.count(index, SessionParams()),
        "modes": MODE_NAMES,
        "kinds": KIND_FILTERS,
        "directions": DIRECTIONS,
        "topics": index.all_topics(),
        "lessons": index.lessons(),
        "last_backup": request.app.state.progress_db.get_meta("last_backup_pushed"),
    }
    return templates.TemplateResponse(request, "vocab/practice_setup.html", context)


@router.post("/practice/start")
def practice_start(
    request: Request,
    index: Index,
    mode: Annotated[str, Form()] = "today",
    kind: Annotated[str, Form()] = "all",
    direction: Annotated[str, Form()] = "fr_ru",
    method: Annotated[str, Form()] = "self",
    lesson: Annotated[str, Form()] = "",
    topic: Annotated[str, Form()] = "",
):
    _cards, sessions = _practice(request, index)
    params = SessionParams(
        source="dictionary",
        mode=mode,
        kind=kind,
        direction=direction,
        method=method,
        lesson=int(lesson) if lesson else None,
        topic=topic or None,
    )
    return _redirect(f"/practice/{sessions.start(index, params)}")


@router.get("/lessons/{number}/practice")
def lesson_practice(request: Request, number: int, index: Index):
    if index.lesson(number) is None:
        raise not_found(f"Урок {number} не найден")
    _cards, sessions = _practice(request, index)
    params = SessionParams(source="lesson", mode="lesson", lesson=number)
    return _redirect(f"/practice/{sessions.start(index, params)}")


def _card_page(request: Request, index: ContentIndex, session_id: str, shown: bool, **extra):
    _cards, sessions = _practice(request, index)
    try:
        progress = sessions.progress(session_id)
    except KeyError:
        raise not_found("Сеанс не найден") from None
    params = sessions.params(session_id)
    current = sessions.current(session_id)
    context = {
        "index": index,
        "session_id": session_id,
        "progress": progress,
        "params": params,
        "mode_name": MODE_NAMES.get(params.mode, params.mode),
        "direction_name": DIRECTIONS[params.direction],
        "ratings": RATING_NAMES,
        "can_undo": sessions._load(session_id)[3] is not None,
        **extra,
    }
    if current is None:
        context["summary"] = sessions.summary(session_id)
        return templates.TemplateResponse(request, "vocab/practice_summary.html", context)
    entry = index.element(current[0])
    context.update(
        entry=entry,
        direction=current[1],
        question=vocab_entries.question(index, entry, current[1]),
        answers=vocab_entries.accepted_answers(index, entry, current[1]),
        shown=shown,
    )
    return templates.TemplateResponse(request, "vocab/practice_card.html", context)


@router.get("/practice/{session_id}")
def practice_card(request: Request, session_id: str, index: Index):
    return _card_page(request, index, session_id, shown=False)


@router.post("/practice/{session_id}/show")
def practice_show(request: Request, session_id: str, index: Index):
    return _card_page(request, index, session_id, shown=True)


@router.post("/practice/{session_id}/rate")
def practice_rate(request: Request, session_id: str, index: Index, rating: Annotated[str, Form()]):
    _cards, sessions = _practice(request, index)
    if rating not in RATING_NAMES:
        raise not_found("Неизвестная оценка")
    if sessions.current(session_id) is not None:
        sessions.rate(session_id, rating)
    return _redirect(f"/practice/{session_id}")


@router.post("/practice/{session_id}/undo")
def practice_undo(request: Request, session_id: str, index: Index):
    _cards, sessions = _practice(request, index)
    sessions.undo(session_id)
    return _redirect(f"/practice/{session_id}")


@router.post("/practice/{session_id}/continue")
def practice_continue(request: Request, session_id: str, index: Index):
    _cards, sessions = _practice(request, index)
    sessions.continue_portion(session_id)
    return _redirect(f"/practice/{session_id}")


@router.post("/backup")
def backup_now(request: Request, index: Index):
    from french_learning.practice.backup import run_backup
    from french_learning.web.routes.topics import redirect_after_write

    state = request.app.state
    if state.progress_db is None:
        raise not_found("Хранилище не настроено")
    result = run_backup(state.progress_db, state.settings.content_dir)
    if not result.committed and not result.warning:
        return _redirect("/practice?notice=Копия уже актуальна, изменений нет.")
    return redirect_after_write("/practice", result)


# --- просмотр словаря (US2) -------------------------------------------------------------------

VOCAB_FILTERS = {
    "": "все",
    "known": "«Знаю»",
    "hidden": "скрытые",
    "incomplete": "нужно дополнить",
}


@router.get("/vocab")
def vocab_list(
    request: Request,
    index: Index,
    lesson: str = "",
    topic: str = "",
    kind: str = "",
    filter: str = "",
    view: str = "cards",
):
    cards, _sessions = _practice(request, index)
    items = vocab_entries.filter_entries(
        index,
        lesson=int(lesson) if lesson else None,
        topic=topic or None,
        kind=kind or None,
        flag=filter or None,
        known_ids=cards.known_ids(),
    )
    incomplete = len(vocab_entries.filter_entries(index, flag="incomplete"))
    context = {
        "index": index,
        "items": items,
        "view": "list" if view == "list" else "cards",
        "selected": {"lesson": lesson, "topic": topic, "kind": kind, "filter": filter},
        "filters": VOCAB_FILTERS,
        "kinds": {"": "все виды", "word": "слова", "verb": "глаголы", "phrase": "фразы"},
        "lessons": index.lessons(),
        "topics": index.all_topics(),
        "incomplete": incomplete,
        "display_fr": vocab_entries.display_fr,
    }
    return templates.TemplateResponse(request, "vocab/list.html", context)


@router.get("/vocab/{entry_id}")
def vocab_entry(request: Request, entry_id: str, index: Index):
    cards, _sessions = _practice(request, index)
    entry = index.element(entry_id)
    if entry is None or entry.kind != "vocab":
        raise not_found("Слово не найдено")
    context = {
        "index": index,
        "entry": entry,
        "display_fr": vocab_entries.display_fr,
        "indefinite": vocab_entries.indefinite(entry),
        "known": entry_id in cards.known_ids(),
        "history": cards.history(entry_id),
        "pos_names": vocab_entries.POS_NAMES,
        "kind_names": vocab_entries.KIND_NAMES,
    }
    return templates.TemplateResponse(request, "vocab/entry.html", context)
