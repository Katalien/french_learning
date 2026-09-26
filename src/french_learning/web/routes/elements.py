"""Просмотр отдельного элемента: теория, текст, упражнение (FR-023–FR-027)."""

from fastapi import APIRouter, Request

from french_learning.web.deps import Index, not_found, show_origin
from french_learning.web.templating import templates

router = APIRouter()


@router.get("/elements/{element_id}")
def element_page(request: Request, element_id: str, index: Index):
    element = index.element(element_id)
    if element is None:
        error = index.content.error_for(element_id)
        if error is None:
            raise not_found(f"Элемент {element_id} не найден")
        return templates.TemplateResponse(
            request, "element_error.html", {"index": index, "error": error}, status_code=200
        )
    context = {
        "index": index,
        "element": element,
        "path": index.element_path(element_id),
        "show_origin": show_origin(request),
        "linked": index.linked_exercises(element_id),
    }
    return templates.TemplateResponse(request, "element.html", context)
