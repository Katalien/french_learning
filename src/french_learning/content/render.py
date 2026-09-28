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
    **{f"h{level}": {"id"} for level in range(1, 7)},
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


def headings(text: str) -> list[tuple[int, str]]:
    """Заголовки Markdown по порядку: (уровень, текст) — для оглавления."""
    tokens = _md.parse(text)
    return [
        (int(token.tag[1]), tokens[i + 1].content)
        for i, token in enumerate(tokens)
        if token.type == "heading_open"
    ]


def render_markdown(text: str, image_base: str, heading_prefix: str | None = None) -> str:
    """Markdown → безопасный HTML. С heading_prefix заголовки получают id «prefix-N» (N с 1)."""
    tokens = _md.parse(text)
    heading_number = 0
    for token in tokens:
        if heading_prefix and token.type == "heading_open":
            heading_number += 1
            token.attrSet("id", f"{heading_prefix}-{heading_number}")
        for child in token.children or []:
            if child.type == "image":
                url = _image_url(child.attrGet("src") or "", image_base)
                if url is None:
                    child.type = "text"
                    child.content = ""
                else:
                    child.attrSet("src", url)
    html = _md.renderer.render(tokens, _md.options, {})
    clean = nh3.clean(
        html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRIBUTES, url_schemes={"http", "https"}
    )
    # таблица отделена от текста и прокручивается внутри себя на узком экране (009, FR-031)
    return clean.replace("<table>", '<div class="table-wrap"><table>').replace(
        "</table>", "</table></div>"
    )


def docx_to_html(path: Path) -> str:
    with path.open("rb") as file:
        result = mammoth.convert_to_html(file)
    return nh3.clean(result.value, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRIBUTES)
