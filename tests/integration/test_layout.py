"""009: шапка, меню «⋯», тема оформления (FR-001, FR-002, FR-004; SC-001)."""

import re

MAIN = ["Уроки", "Словарь", "Практика", "Темы"]


def header(html: str) -> str:
    return html.split('<header class="topbar"', 1)[1].split("</header>", 1)[0]


def body(html: str) -> str:
    """Тело страницы без хлебных крошек (путь — не дублирующая кнопка)."""
    rest = html.split("</header>", 1)[1]
    return re.sub(r'<p class="crumbs".*?</p>', "", rest, flags=re.S)


def main_links(html: str) -> list[tuple[str, str]]:
    nav = header(html).split('class="mainnav"', 1)[1].split("</nav>", 1)[0]
    return re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', nav)


def test_header_has_four_sections_and_more_menu(client):
    html = client.get("/lessons/1").text
    assert [name for _href, name in main_links(html)] == MAIN
    menu = header(html).split('class="more"', 1)[1]
    for item in (
        "Дополнительные материалы",
        "Требует проверки",
        "Сообщения об ошибках",
        "Настройки",
        "Происхождение",
        "Оформление",
    ):
        assert item in menu, item


def test_header_links_not_duplicated_in_body(client):
    for page in ("/lessons", "/lessons/1"):
        html = client.get(page).text
        for href, _name in main_links(html):
            assert f'href="{href}"' not in body(html), (page, href)


def test_no_pico_and_local_fonts(client):
    html = client.get("/lessons/1").text
    assert "pico" not in html
    assert "/static/css/tokens.css" in html
    css = client.get("/static/css/tokens.css").text
    assert "InterVariable.woff2" in css and "Lora.ttf" in css
    assert "googleapis" not in css
    assert client.get("/static/fonts/InterVariable.woff2").status_code == 200


def test_theme_cookie(client):
    assert 'data-theme="system"' in client.get("/lessons/1").text
    response = client.post(
        "/settings/theme",
        data={"theme": "dark"},
        headers={"referer": "http://testserver/lessons/1"},
    )
    assert response.url.path == "/lessons/1"
    assert 'data-theme="dark"' in client.get("/lessons/1").text
    html = client.get("/lessons/1").text
    # меню «⋯»: оформление — три значка, выбранный отмечен (макет 2026-09-30, Е1)
    assert re.search(r'name="theme" value="dark" class="on"[^>]*aria-pressed="true"', html)
    assert 'title="Светлое"' in html and 'title="Как в системе"' in html
    client.post("/settings/theme", data={"theme": "neon"})
    assert 'data-theme="system"' in client.get("/lessons/1").text
