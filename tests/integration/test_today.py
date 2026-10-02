"""009 US1: экран «Сегодня» (FR-003)."""

import datetime as dt

HX = {"HX-Request": "true"}


def test_today_is_home(client):
    html = client.get("/").text
    assert "Сегодня" in html or "Bonjour" in html
    # не показываются: список уроков, «Мои ошибки», «Продолжить»
    assert 'class="lesson-grid"' not in html
    assert "Мои ошибки" not in html and "Продолжить" not in html


def test_cards_due_and_repeat_button(client):
    html = client.get("/").text
    # карточки создаются для всех слов словаря образца — все «пора»
    assert "8 карточек" in html  # 010: 4 слова × 2 направления
    assert 'action="/practice/start"' in html and 'name="mode" value="today"' in html


def test_homework_of_two_latest_lessons(client):
    html = client.get("/").text
    # уроки с основной домашкой: 2 и 1 (у урока 4 — только резерв)
    for exercise_id in ("ex-hwlessbb", "ex-multigap", "ex-transfor", "ex-grouping"):
        assert f'href="/elements/{exercise_id}"' in html, exercise_id
    assert "ex-twoforms" not in html  # необязательное
    assert "ex-openansw" not in html  # резерв
    # выполненное пропадает
    client.post("/exercises/ex-multigap/check", data={"i1.1": "x", "i1.2": "y"}, headers=HX)
    assert 'href="/elements/ex-multigap"' not in client.get("/").text


def test_trainers_due(client):
    schedule = client.app.state.trainer_schedule
    past = dt.datetime(2020, 1, 1, tzinfo=dt.UTC)
    schedule.answer("numbers", "numbers:5", correct=False, now=past)
    schedule.answer("numbers", "numbers:6", correct=False, now=past)
    html = client.get("/").text
    assert 'href="/trainers/numbers"' in html and "пора: 2" in html
    assert 'href="/trainers/articles"' not in html  # вопросов «пора» нет


def test_empty_state(client, content_root):
    import shutil

    shutil.rmtree(content_root / "vocabulary")
    for exercise in (content_root / "lessons").rglob("ex-*.yaml"):
        exercise.unlink()
    html = client.get("/").text
    assert 'href="/lessons"' in html  # приветствие со ссылками
    assert "На сегодня всё" in html


def test_lessons_page(client):
    html = client.get("/lessons").text
    assert 'href="/lessons/1"' in html and 'class="lesson-grid"' in html


def test_homework_shows_five_then_more_button():
    # первые 5 упражнений видны, остальные — по кнопке «Показать ещё» (пожелание 2026-09-30)
    import re
    from types import SimpleNamespace as NS

    from french_learning.web.templating import templates

    exercises = [NS(id=f"ex-{n}", description_ru=f"Упражнение {n}", number=n) for n in range(7)]
    t = NS(empty=False, due=0, homework=[NS(number=3, exercises=exercises)], trainers=[])
    html = templates.env.get_template("today.html").render(
        t=t,
        today_date=dt.date(2026, 9, 30),
        request=NS(url=NS(path="/"), cookies={}, query_params={}, app=NS(state=NS(notes=None))),
        nav_counts=lambda r: {"questions": 0, "review": 0, "reports": 0},
    )
    items = re.findall(r'<li( x-show="more" x-cloak)?>\s*<a href="/elements/ex-\d+"', html)
    assert len(items) == 7 and [bool(x) for x in items] == [False] * 5 + [True] * 2
    assert "Показать ещё (2)" in html
