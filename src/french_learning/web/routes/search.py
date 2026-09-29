"""Поиск (007): панель под строкой в шапке и страница всех результатов.

Контракт — contracts/search-routes.md. Поиск только читает контент и ничего не сохраняет
(FR-014): ни запросов, ни выбранной области.
"""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Request

from french_learning.search.index import search_index
from french_learning.search.query import Query, Results, search
from french_learning.web.deps import Index
from french_learning.web.templating import templates

router = APIRouter()

PANEL_LIMIT = 3  # результатов в группе на панели (уточнение 2026-09-29)
GROUP_NAMES = {"words": "Слова", "topics": "Темы", "theory": "Теория"}
SCOPE_NAMES = {"all": "Всё", "words": "Словарь", "theory": "Теория", "topics": "Темы"}


def _query(q: str, scope: str, lesson: str, topic: str) -> Query:
    return Query(q, scope, int(lesson) if lesson.isdigit() else None, topic or None)


def _results(request: Request, index, query: Query) -> Results:
    db = request.app.state.progress_db
    show = db is None or db.get_setting("search_translations") != "0"
    return search(search_index(index), query, show_translation=show)


def _link(query: Query, **changes) -> str:
    params = {"q": query.q, "scope": query.scope, "lesson": query.lesson, "topic": query.topic}
    params.update(changes)
    return "/search?" + urlencode({k: v for k, v in params.items() if v not in (None, "", "all")})


def _context(request: Request, index, query: Query, limit: int | None) -> dict:
    return {
        "index": index,
        "results": _results(request, index, query),
        "query": query,
        "limit": limit,
        "group_names": GROUP_NAMES,
        "scope_names": SCOPE_NAMES,
        "lessons": index.lessons(),
        "topics": index.all_topics(),
        "search_link": lambda **changes: _link(query, **changes),
    }


@router.get("/search/panel")
def search_panel(
    request: Request,
    index: Index,
    q: str = "",
    scope: str = "all",
    lesson: str = "",
    topic: str = "",
):
    query = _query(q, scope, lesson, topic)
    context = _context(request, index, query, PANEL_LIMIT)
    return templates.TemplateResponse(request, "search/panel.html", context)


@router.get("/search")
def search_page(
    request: Request,
    index: Index,
    q: str = "",
    scope: str = "all",
    lesson: str = "",
    topic: str = "",
):
    query = _query(q, scope, lesson, topic)
    context = _context(request, index, query, None)
    return templates.TemplateResponse(request, "search/page.html", context)
