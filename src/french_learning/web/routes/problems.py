"""Ошибки загрузки контента (FR-005)."""

from fastapi import APIRouter, Request

from french_learning.web.deps import Index
from french_learning.web.templating import templates

router = APIRouter()


@router.get("/problems")
def problems(request: Request, index: Index):
    return templates.TemplateResponse(request, "problems.html", {"index": index})
