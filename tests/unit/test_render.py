"""Отрисовка Markdown и docx (research R8, R9)."""

import re
from pathlib import Path

from french_learning.content.render import docx_to_html, render_markdown


def test_table_is_rendered():
    html = render_markdown("| a | b |\n|---|---|\n| 1 | 2 |\n", image_base="lessons/001")
    assert "<table>" in html and "<td>1</td>" in html


def test_scripts_and_event_handlers_are_removed():
    html = render_markdown(
        '<script>alert(1)</script>\n\n<img src="x.png" onerror="alert(1)">\n\n**ok**',
        image_base="lessons/001",
    )
    # Сырой HTML не исполняется: он либо удалён, либо показан как экранированный текст.
    assert "<script" not in html
    assert not re.search(r"<[^>]*\bonerror\s*=", html)
    assert "<strong>ok</strong>" in html


def test_relative_image_points_to_sources_route():
    html = render_markdown("![Схема](sources/scheme.png)", image_base="lessons/001")
    assert 'src="/sources/lessons/001/sources/scheme.png"' in html


def test_external_images_are_dropped():
    html = render_markdown("![x](https://example.com/a.png)", image_base="lessons/001")
    assert "example.com" not in html


def test_docx_to_html(content_root: Path):
    html = docx_to_html(content_root / "lessons/002/sources/etre.docx")
    assert "le verbe être" in html
