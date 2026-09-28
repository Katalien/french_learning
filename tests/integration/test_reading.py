"""009 US4: оглавление по всем теориям и текстам, таблицы, «Теория рядом» (FR-030–FR-032)."""

from pathlib import Path

SECOND = """---
id: th-secondaa
kind: theory
title: Вторая теория
lesson: 1
part: class
topics: [top-articles]
origin: material
sources:
  - {file: lessons/001/sources/sheet.jpg, original: sheet.jpg}
---
## Первый раздел

Текст.

## Второй раздел

| a | b |
|---|---|
| 1 | 2 |
"""


def add_second_theory(content_root: Path) -> None:
    (content_root / "lessons/001/theory/th-secondaa.md").write_text(SECOND, encoding="utf-8")


def test_toc_lists_all_theories_and_headings(client, content_root):
    add_second_theory(content_root)
    html = client.get("/lessons/1/theory").text
    toc = html.split('class="reading-toc', 1)[1].split("</nav>", 1)[0]
    assert 'href="#th-articles"' in toc and 'href="#th-secondaa"' in toc
    assert 'href="#th-secondaa-2"' in toc and "Второй раздел" in toc
    assert 'id="th-secondaa"' in html and 'id="th-secondaa-2"' in html


def test_toc_for_texts(client):
    html = client.get("/lessons/1/texts").text
    toc = html.split('class="reading-toc', 1)[1].split("</nav>", 1)[0]
    assert 'href="#tx-aucafeaa"' in toc


def test_tables_are_wrapped(client):
    html = client.get("/lessons/1/theory").text
    assert '<div class="table-wrap"><table>' in html


def test_fragment_for_side_pane(client):
    html = client.get("/elements/th-articles?fragment=1").text
    assert "<header" not in html and "topbar" not in html  # только тело
    assert "Элизия" in html and 'class="side-pane-body' in html
    assert client.get("/elements/ex-gapchoic?fragment=1").status_code == 404


def test_open_theory_beside_exercise(client):
    html = client.get("/elements/ex-gapchoic").text  # links.theory: th-articles
    assert 'hx-get="/elements/th-articles?fragment=1"' in html
    assert "Теория рядом" in html
    text_linked = client.get("/elements/ex-truefals").text  # links.text: tx-aucafeaa
    assert (
        'hx-get="/elements/tx-aucafeaa?fragment=1"' in text_linked and "Текст рядом" in text_linked
    )


def test_lesson_menu_offers_side_by_side(client):
    html = client.get("/elements/ex-gapchoic").text
    menu = html.split('id="lesson-menu"', 1)[1].split("</aside>", 1)[0]
    assert 'hx-get="/elements/th-articles?fragment=1"' in menu


def test_side_pane_can_be_closed(client):
    html = client.get("/elements/ex-gapchoic").text
    assert "Скрыть теорию" in html and "✕ Закрыть" in html
    assert 'class="side-pane-bar"' in html
