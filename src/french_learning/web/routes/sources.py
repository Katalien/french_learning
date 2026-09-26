"""«Открыть оригинал»: отдача сжатых копий исходников из хранилища (FR-034, research R9)."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from french_learning.content.render import docx_to_html
from french_learning.web.deps import Index
from french_learning.web.templating import templates

router = APIRouter()

# Отдаются только исходники, а не файлы контента (YAML, Markdown).
SOURCE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".pdf": "application/pdf",
}


def _resolve(root: Path, relative: str) -> Path | None:
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        return None
    if candidate.suffix.lower() not in {*SOURCE_TYPES, ".docx"}:
        return None
    return candidate


@router.get("/sources/{relative:path}")
def source_file(request: Request, relative: str, index: Index):
    path = _resolve(index.content.root, relative)
    if path is None or not path.is_file():
        return templates.TemplateResponse(
            request, "source_missing.html", {"relative": relative}, status_code=404
        )
    if path.suffix.lower() == ".docx":
        return templates.TemplateResponse(
            request, "docx.html", {"name": path.name, "html": docx_to_html(path)}
        )
    return FileResponse(path, media_type=SOURCE_TYPES[path.suffix.lower()])
