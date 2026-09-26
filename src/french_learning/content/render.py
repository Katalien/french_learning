"""Отрисовка контента в безопасный HTML: Markdown (research R8) и docx (research R9)."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

import mammoth
import nh3
from markdown_it import MarkdownIt

_ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "hr", "strong", "em", "b", "i", "u", "s",
    "sub", "sup", "code", "pre", "blockquote", "ul", "ol", "li", "table", "thead", "tbody",
    "tr", "th", "td", "img", "a", "span",
}  # fmt: skip
_ALLOWED_ATTRIBUTES = {
    "img": {"src", "alt", "title"},
    "a": {"href", "title"},
    "th": {"align"},
    "td": {"align"},
    "h1": {"id"},
    "h2": {"id"},
    "h3": {"id"},
}

_md = MarkdownIt("commonmark", {"html": False}).enable("table").enable("strikethrough")


def _image_url(src: str, image_base: str) -> str | None:
    """Относительная картинка из хранилища → адрес маршрута /sources; внешние — убираются."""
    if "://" in src or src.startswith(("/", "data:")):
        return None
    path = PurePosixPath(image_base) / src
    if ".." in path.parts:
        return None
    return f"/sources/{path.as_posix()}"


def render_markdown(text: str, image_base: str) -> str:
    tokens = _md.parse(text)
    for token in tokens:
        for child in token.children or []:
            if child.type == "image":
                url = _image_url(child.attrGet("src") or "", image_base)
                if url is None:
                    child.type = "text"
                    child.content = ""
                else:
                    child.attrSet("src", url)
    html = _md.renderer.render(tokens, _md.options, {})
    return nh3.clean(
        html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRIBUTES, url_schemes={"http", "https"}
    )


def docx_to_html(path: Path) -> str:
    with path.open("rb") as file:
        result = mammoth.convert_to_html(file)
    return nh3.clean(result.value, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRIBUTES)
