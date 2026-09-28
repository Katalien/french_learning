"""009 US2: страница урока — одна панель разделов, «Лексика», медиа, настройки (FR-010–FR-013)."""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from french_learning.config import Settings
from french_learning.web.app import create_app

SECTIONS = ["Обзор", "Теория", "Тексты", "Лексика", "Задания"]


def section_links(html: str) -> list[str]:
    return re.findall(r'href="(/lessons/2(?:/(?:theory|texts|vocab|tasks)[^"]*)?)"', html)


def test_single_sections_panel(client):
    html = client.get("/lessons/2").text
    panel = html.split('class="lside', 1)[1].split("</aside>", 1)[0]
    for name in SECTIONS:
        assert name in panel
    # каждая ссылка на раздел — ровно один раз на странице (без дублей-блоков)
    links = section_links(html.split("</header>", 1)[1])
    assert len(links) == len(set(links)), links
    assert 'class="section-cards"' not in html


def test_panel_closable(client):
    html = client.get("/lessons/2/theory").text
    assert "скрыть" in html and "☰ Разделы урока" in html


def test_vocab_section(client):
    html = client.get("/lessons/2/vocab").text
    new_part, repeat_part = html.split("На повторение")
    assert "l'eau" in new_part.replace("&#39;", "'")
    assert "le pain" in repeat_part
    assert 'href="/lessons/2/practice"' in html  # «Повторить слова урока»
    theory = client.get("/lessons/1/theory").text
    assert "Новые слова" not in theory and "Лексика урока" not in theory


def test_media_only_in_tasks(content_root: Path, tmp_path: Path):
    settings = Settings(
        _env_file=None,
        content_dir=content_root,
        source_materials_dir=tmp_path / "m",
        tts_dir=tmp_path / "tts",
    )
    client = TestClient(create_app(settings))
    assert "Video.mov" not in client.get("/lessons/2").text
    tasks = client.get("/lessons/2/tasks?part=class").text
    assert "Медиаматериалы" in tasks and "Video.mov" in tasks


def test_lesson_settings_behind_gear(client):
    html = client.get("/lessons/1").text
    settings = html.split('id="lesson-settings"', 1)[1].split("</section>", 1)[0]
    assert 'action="/lessons/1/date"' in settings
    assert "Требует проверки" in settings
    before = html.split('id="lesson-settings"', 1)[0]
    assert 'action="/lessons/1/date"' not in before
    assert re.search(r'<section id="lesson-settings"[^>]*x-show', html)  # скрыто до нажатия «⚙»


def test_overview_counters(client):
    html = client.get("/lessons/1").text
    assert "0 из 4" in html  # домашка
    assert "Новых слов" in html


def test_empty_section(client):
    assert "Нет материалов" in client.get("/lessons/4/vocab").text
