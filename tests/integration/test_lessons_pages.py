"""Страницы US1: главная, урок, вкладки заданий, резерв (FR-022, FR-026, FR-030–FR-032)."""

import re


def test_home_lists_lessons_newest_first_with_summaries(client):
    html = client.get("/lessons").text
    positions = [html.index(f'href="/lessons/{n}"') for n in (4, 2, 1)]
    assert positions == sorted(positions)
    assert "1 сентября 2026" in html
    assert "дата не указана" in html
    assert "0 из 4" in html  # домашка урока 1
    assert 'href="/topics"' in html  # шапка
    assert 'href="/extras"' in html  # меню «⋯»


def test_lesson_page_has_sections(client):
    html = client.get("/lessons/2").text
    for section in ("Теория", "Тексты", "Задания"):
        assert section in html
    assert 'href="/lessons/2/tasks?part=class"' in html


def test_homework_tab_titles_and_optional_mark(client):
    html = client.get("/lessons/1/tasks?part=homework").text
    # 009: номер — один раз, заголовок — описание, тема и тип — второй строкой
    assert re.search(r'class="num">1</span>.*?Вставить артикли в предложения.*?Артикли', html, re.S)
    assert re.search(r"Выбрать форму.*?необязательное", html, re.S)
    assert "Рассказать о своём завтраке" not in html  # резерв
    assert 'href="/lessons/1/reserve"' in html


def test_class_tab(client):
    html = client.get("/lessons/1/tasks?part=class").text
    assert re.search(r'class="num[^"]*">1</span>.*?Вставить определённый артикль', html, re.S)
    assert "Спрягать" not in html  # это урок 2


def test_reserve_page(client):
    html = client.get("/lessons/1/reserve").text
    assert "Рассказать о своём завтраке" in html
    assert "Вставить артикли в предложения" not in html


def test_lesson_without_main_homework_suggests_reserve(client):
    html = client.get("/lessons/4/tasks?part=homework").text
    assert "Основных заданий нет" in html
    assert 'href="/lessons/4/reserve"' in html


def test_lesson_without_theory(client):
    assert "Нет материалов" in client.get("/lessons/4/theory").text


def test_unknown_lesson_404(client):
    assert client.get("/lessons/99").status_code == 404


def test_class_exercises_always_done(client):
    """010 пункт 12: упражнения «В классе» выполнены без попыток; домашка — как раньше."""
    html = client.get("/lessons/1/tasks?part=class").text
    for exercise_id in ("ex-choicecf", "ex-gapchoic", "ex-gapinput", "ex-truefals"):
        row = html.split(f'class="ex-item" href="/elements/{exercise_id}"', 1)[1].split("</a>", 1)[
            0
        ]
        assert "✓ выполнено" in row, exercise_id
    homework = client.get("/lessons/1/tasks?part=homework").text
    assert "✓ выполнено" not in homework
    menu = client.get("/elements/ex-gapchoic").text
    drawer = menu.split('id="lesson-menu"', 1)[1]
    row = drawer.split('href="/elements/ex-gapinput"', 1)[1].split("</a>", 1)[0]
    assert 'class="done"' in row
