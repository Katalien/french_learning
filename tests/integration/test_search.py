"""Поиск в интерфейсе (007, contracts/search-routes.md, contracts/ui.md)."""

import re
from html import unescape


def panel(client, **params):
    response = client.get("/search/panel", params=params)
    assert response.status_code == 200
    return unescape(response.text)


def page(client, **params):
    response = client.get("/search", params=params)
    assert response.status_code == 200
    return unescape(response.text)


# --- US1 ---------------------------------------------------------------------------------------


def test_header_has_search_form_on_every_page(client):
    for path in ("/", "/lessons", "/vocab", "/topics", "/elements/th-articles"):
        html = client.get(path).text
        form = re.search(r"<form[^>]*role=\"search\"[^>]*>", html)
        assert form, path
        assert 'action="/search"' in form[0] and 'hx-get="/search/panel"' in form[0]
        assert re.search(r'<input[^>]*name="q"[^>]*autocomplete="off"', html), path


def test_panel_groups_and_counts(client):
    html = panel(client, q="дом")
    assert "<html" not in html
    assert "Слова" in html and "Темы" in html
    assert 'href="/vocab/voc-maisonaa"' in html and 'href="/topics/top-maisonxx"' in html
    assert re.search(r'lang="fr"[^>]*>la maison<', html)
    assert "дом" in html  # перевод у слова
    assert 'href="/search?q=' in html and "Все результаты" in html


def test_panel_shows_three_per_group_and_show_all(client):
    html = panel(client, q="le")  # теория: артикли, être, доп. материал — всё с «le»
    theory = re.findall(r'href="/elements/th-', html)
    assert 0 < len(theory) <= 3
    page_html = page(client, q="le")
    assert len(re.findall(r'href="/elements/th-', page_html)) >= len(theory)


def test_show_all_link_when_more_than_three(client, content_root):
    for n in "abcd":
        (content_root / "vocabulary" / f"voc-mot{n}xxxx.yaml").write_text(
            f"id: voc-mot{n}xxxx\nkind: vocab\nentry_type: word\ntext: mot{n}\n"
            "translations:\n  - {text: слово, origin: user}\ntopics: []\norigin: user\n",
            encoding="utf-8",
        )
    html = panel(client, q="mot")
    assert len(re.findall(r'href="/vocab/voc-mot', html)) == 3
    assert "Показать все (4)" in html and "scope=words" in html
    assert len(re.findall(r'href="/vocab/voc-mot', page(client, q="mot"))) == 4


def test_empty_states(client):
    assert "Введите хотя бы 2 буквы" in panel(client, q="m")
    assert "Ничего не найдено" in panel(client, q="zzzz")
    assert "Ничего не найдено" in page(client, q="zzzz")


def test_page_lists_groups_as_blocks(client):
    html = page(client, q="дом")
    assert "<html" in html and 'href="/vocab/voc-maisonaa"' in html
    assert re.search(r'<input[^>]*name="q"[^>]*value="дом"', html)


def test_search_writes_nothing(client, content_root):
    db = client.app.state.progress_db
    before = db.conn.execute("select count(*) from settings").fetchone()[0]
    files = sorted(p.stat().st_mtime for p in content_root.rglob("*") if p.is_file())
    panel(client, q="maison")
    page(client, q="maison", scope="words", lesson="1")
    assert db.conn.execute("select count(*) from settings").fetchone()[0] == before
    assert sorted(p.stat().st_mtime for p in content_root.rglob("*") if p.is_file()) == files


# --- US2 ---------------------------------------------------------------------------------------


def test_scope_and_filters(client):
    words = panel(client, q="дом", scope="words")
    assert 'href="/vocab/voc-maisonaa"' in words and 'href="/topics/' not in words
    lesson2 = panel(client, q="maison", lesson="2")
    assert "Ничего не найдено" in lesson2
    topic = page(client, q="артикли", topic="top-articles")
    assert 'href="/elements/th-articles' in topic


def test_controls_reflect_current_values(client):
    html = panel(client, q="дом", scope="theory", lesson="1", topic="top-articles")
    assert re.search(r'name="scope" value="theory"[^>]*checked', html)
    assert re.search(r'<option value="1"[^>]*selected', html)
    assert re.search(r'<option value="top-articles"[^>]*selected', html)
    default = panel(client, q="дом")
    assert re.search(r'name="scope" value="all"[^>]*checked', default)


def test_bad_params_are_ignored(client):
    html = panel(client, q="дом", scope="nonsense", lesson="abc", topic="")
    assert 'href="/vocab/voc-maisonaa"' in html


# --- US3: ссылки --------------------------------------------------------------------------------


def test_result_links(client):
    html = panel(client, q="il y a") + panel(client, q="артикли")
    assert re.search(r'href="/elements/th-articles\?hl=%D0%B0%D1%80', html)
    assert 'href="/vocab/voc-maisonaa"' in panel(client, q="maison")
    assert 'href="/topics/top-maisonxx"' in panel(client, q="дом")
