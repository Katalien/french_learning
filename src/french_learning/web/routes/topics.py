"""Темы, дополнительные материалы и правки из интерфейса (FR-012–FR-014, FR-035, FR-038)."""

import datetime as dt
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from french_learning.content.writer import ContentWriter, WriteError, WriteResult
from french_learning.web.deps import Index, not_found, show_origin
from french_learning.web.templating import templates

router = APIRouter()


def redirect_after_write(url: str, result: WriteResult | None = None, error: str | None = None):
    """Вернуть пользователя на страницу с сообщением о результате правки."""
    params = {}
    if error:
        params["error"] = error
    elif result is not None and result.warning:
        params["notice"] = f"Сохранено. {result.warning[0].upper()}{result.warning[1:]}."
    elif result is not None:
        params["notice"] = "Сохранено."
    target = f"{url}?{urlencode(params)}" if params else url
    return RedirectResponse(target, status_code=303)


def writer(request: Request) -> ContentWriter:
    return ContentWriter(request.app.state.settings.content_dir)


@router.get("/topics")
def topics_page(request: Request, index: Index):
    context = {
        "index": index,
        "sections": index.topics_by_section(only_vocab_with_words=True),
        "untopiced": len(index.untopiced_elements()),
    }
    return templates.TemplateResponse(request, "topics.html", context)


def _default_tab(topic, tab: str, keys: list[str]) -> str:
    """Выбранная вкладка; иначе у тем раздела «Лексика» — «Слова», у остальных — первая."""
    if tab in keys:
        return tab
    if topic is not None and topic.section == "vocabulary" and "words" in keys:
        return "words"
    return keys[0] if keys else ""


@router.get("/topics/{topic_id}")
def topic_page(request: Request, topic_id: str, index: Index, tab: str = ""):
    if topic_id == "none":
        topic, elements = None, index.untopiced_elements()
    else:
        topic = index.topic(topic_id)
        if topic is None:
            raise not_found("Тема не найдена")
        elements = index.topic_elements(topic_id)
    tabs = index.topic_tabs(elements)
    keys = [key for key, _name, _items in tabs]
    context = {
        "index": index,
        "topic": topic,
        "elements": elements,
        "tabs": tabs,
        "current_tab": _default_tab(topic, tab, keys),
        "all_topics": index.all_topics(),
        "show_origin": show_origin(request),
    }
    return templates.TemplateResponse(request, "topic.html", context)


@router.post("/topics/{topic_id}/rename")
def rename_topic(request: Request, topic_id: str, name: Annotated[str, Form()]):
    try:
        result = writer(request).rename_topic(topic_id, name)
    except WriteError as exc:
        return redirect_after_write(f"/topics/{topic_id}", error=str(exc))
    return redirect_after_write(f"/topics/{topic_id}", result)


@router.post("/topics/{topic_id}/merge")
def merge_topic(request: Request, topic_id: str, target: Annotated[str, Form()]):
    try:
        result = writer(request).merge_topics(topic_id, target)
    except WriteError as exc:
        return redirect_after_write(f"/topics/{topic_id}", error=str(exc))
    return redirect_after_write(f"/topics/{target}", result)


@router.get("/extras")
def extras_page(request: Request, index: Index, tab: str = ""):
    from french_learning.vocab.entries import display_fr

    context = {
        "index": index,
        "elements": index.extras(),
        "show_origin": show_origin(request),
        "display_fr": display_fr,
        "tab": tab,
    }
    return templates.TemplateResponse(request, "extras.html", context)


@router.post("/lessons/{number}/date")
def set_lesson_date(request: Request, number: int, date: Annotated[str, Form()] = ""):
    try:
        value = dt.date.fromisoformat(date) if date else None
        result = writer(request).set_lesson_date(number, value)
    except ValueError:
        return redirect_after_write(f"/lessons/{number}", error="неверная дата")
    except WriteError as exc:
        return redirect_after_write(f"/lessons/{number}", error=str(exc))
    return redirect_after_write(f"/lessons/{number}", result)


@router.post("/elements/{element_id}/topics")
def set_element_topics(
    request: Request,
    element_id: str,
    topics: Annotated[list[str] | None, Form()] = None,
    new_topic: Annotated[str, Form()] = "",
    new_section: Annotated[str, Form()] = "grammar",
):
    try:
        result = writer(request).set_element_topics(
            element_id, topics or [], new_topic=(new_topic, new_section) if new_topic else None
        )
    except WriteError as exc:
        return redirect_after_write(f"/elements/{element_id}", error=str(exc))
    return redirect_after_write(f"/elements/{element_id}", result)
