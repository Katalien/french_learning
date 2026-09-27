"""Доверие к контенту: происхождение, «требует проверки», сообщения об ошибках (FR-040–FR-043)."""

from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from french_learning.content.writer import WriteError
from french_learning.web.deps import Index
from french_learning.web.routes.topics import redirect_after_write, writer
from french_learning.web.templating import templates

router = APIRouter()

REPORT_REMINDER = (
    "Сообщение сохранено. Сообщения разбирает агент — когда будет удобно, скажите ему "
    "в Claude Code: «разбери сообщения об ошибках»."
)


def _back(request: Request, fallback: str = "/") -> str:
    referer = request.headers.get("referer", "")
    base = str(request.base_url)
    return referer.removeprefix(base.rstrip("/")) if referer.startswith(base) else fallback


@router.post("/settings/origin")
def toggle_origin(request: Request, show: Annotated[str, Form()] = "0"):
    response = RedirectResponse(_back(request), status_code=303)
    response.set_cookie("show_origin", "1" if show == "1" else "0", max_age=10 * 365 * 24 * 3600)
    return response


@router.get("/review")
def review_page(request: Request, index: Index):
    return templates.TemplateResponse(
        request, "review.html", {"index": index, "reviews": index.needs_review()}
    )


@router.post("/elements/{element_id}/verified")
def mark_verified(request: Request, element_id: str, item: Annotated[str, Form()] = ""):
    try:
        result = writer(request).mark_verified(element_id, int(item) if item else None)
    except (WriteError, ValueError) as exc:
        return redirect_after_write(f"/elements/{element_id}", error=str(exc))
    if request.headers.get("HX-Request"):  # кнопка внутри формы решения — обновить страницу
        return Response(headers={"HX-Refresh": "true"})
    return redirect_after_write(f"/elements/{element_id}", result)


@router.get("/reports")
def reports_page(request: Request, index: Index):
    return templates.TemplateResponse(
        request, "reports.html", {"index": index, "reports": index.reports()}
    )


@router.post("/elements/{element_id}/report")
def create_report(
    request: Request,
    element_id: str,
    comment: Annotated[str, Form()] = "",
    item: Annotated[str, Form()] = "",
):
    try:
        _report, result = writer(request).create_report(
            element_id, int(item) if item else None, comment
        )
    except (WriteError, ValueError) as exc:
        return redirect_after_write(f"/elements/{element_id}", error=str(exc))
    notice = REPORT_REMINDER
    if result.warning:
        notice += f" {result.warning[0].upper()}{result.warning[1:]}."
    return RedirectResponse(
        f"/elements/{element_id}?{urlencode({'notice': notice})}", status_code=303
    )
