"""009 US3: страница упражнения, список заданий, переходы (FR-020–FR-026, FR-020a)."""

import re

HX = {"HX-Request": "true"}


def cut(html: str, element_id: str) -> tuple[str, str]:
    """(содержимое блока с этим id, страница без него)."""
    start = html.index(f'id="{element_id}"')
    start = html.rindex("<", 0, start)
    end = html.index("</section>", start) + len("</section>")
    return html[start:end], html[:start] + html[end:]


def test_path_and_single_topics(client):
    html = client.get("/elements/ex-gapchoic").text
    assert "☰ Урок 1" in html
    assert 'href="/lessons/1/tasks?part=class"' in html and "№ 1" in html
    _settings, rest = cut(html, "exercise-settings")
    assert rest.count('href="/topics/top-articles"') == 1  # тема — один раз, у заголовка
    assert "<summary>Темы:" not in html  # старого блока «Темы» внизу нет


def test_settings_behind_gear(client):
    html = client.get("/elements/ex-gapchoic").text
    settings, rest = cut(html, "exercise-settings")
    assert 'name="status"' in settings and "на листе: упр. 1" in settings
    assert "Открыть оригинал" in settings
    assert 'action="/elements/ex-gapchoic/topics"' in settings
    assert 'action="/elements/ex-gapchoic/report"' in settings
    for thing in ('name="status"', "Открыть оригинал", 'action="/elements/ex-gapchoic/report"'):
        assert thing not in rest
    assert re.search(r'<section id="exercise-settings"[^>]*x-show', html)


def test_origin_behind_info(client):
    html = client.get("/elements/ex-gapchoic").text
    origin, rest = cut(html, "exercise-origin")
    assert "материал урока" in origin and "создано ИИ" in origin
    assert "origin-badge" not in rest  # без переключателя меток на странице нет
    client.post("/settings/origin", data={"show": "1"})
    assert "origin-badge" in cut(client.get("/elements/ex-gapchoic").text, "exercise-origin")[1]


def test_arrows_to_neighbours(client):
    html = client.get("/elements/ex-gapinput").text
    assert 'class="arrow prev" href="/elements/ex-gapchoic"' in html
    assert 'class="arrow next" href="/elements/ex-truefals"' in html
    first = client.get("/elements/ex-gapchoic").text
    assert 'class="arrow prev disabled"' in first


def test_lesson_menu(client):
    client.post("/exercises/ex-multigap/check", data={"i1.1": "le", "i1.2": "la"}, headers=HX)
    html = client.get("/elements/ex-gapchoic").text
    menu = html.split('id="lesson-menu"', 1)[1].split("</aside>", 1)[0]
    for target in ("th-articles", "tx-aucafeaa", "ex-choicecf", "ex-multigap", "ex-openansw"):
        assert f'href="/elements/{target}"' in menu, target
    assert re.search(r'href="/elements/ex-multigap"[^<]*<[^>]*>[^<]*✓|ex-multigap.*?✓', menu, re.S)
    assert "Резерв" in menu


def test_task_list_titles(client):
    html = client.get("/lessons/1/tasks?part=homework").text
    assert "1 — Артикли — " not in html
    assert "Вставить артикли в предложения" in html
    row = html.split("Вставить артикли в предложения", 1)[1][:400]
    assert "Артикли" in row and "несколько пропусков" in row
    assert "на листе: упр. a" not in html  # номер на листе — в настройках упражнения


def test_toolbar_buttons_same_style(client):
    html = client.post(
        "/exercises/ex-gapinput/check", data={"i1.1": "suis", "i2.1": "x"}, headers=HX
    ).text
    toolbar = html.split('class="exercise-toolbar"', 1)[1].split("</div>", 1)[0]
    classes = re.findall(r'<(?:a|button)[^>]*class="([^"]+)"', toolbar)
    assert len(classes) == 2 and len(set(classes)) == 1


def test_list_view_setting(client):
    assert 'class="ex-list rows"' in client.get("/lessons/1/tasks?part=class").text
    page = client.get("/settings").text
    assert 'name="exercise_list_view"' in page
    client.post(
        "/settings",
        data={"portion_size": "20", "directions": "staged", "exercise_list_view": "tiles"},
    )
    assert 'class="ex-list tiles"' in client.get("/lessons/1/tasks?part=class").text
    assert client.app.state.progress_db.get_setting("exercise_list_view") == "tiles"
