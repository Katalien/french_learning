"""US3: темы, дополнительные материалы, правки тем и даты (FR-012–FR-014, FR-035, FR-038)."""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def git_repo(content_root: Path):
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
    ):
        subprocess.run(["git", "-C", str(content_root), *args], check=True, capture_output=True)


def test_topics_grouped_by_section_with_counts(client):
    html = client.get("/topics").text
    grammar, rest = html.split("Лексика", 1)
    assert "Грамматика" in grammar and "Артикли" in grammar
    assert "Еда" in rest
    assert 'Артикли</a> <span class="count">7</span>' in html


def test_topic_page_lists_all_lessons_and_extras(client):
    html = client.get("/topics/top-articles").text
    assert "Урок 1" in html and "Урок 2" in html
    assert "Артикли перед h" in html
    assert "дополнительный материал" in html


def test_extras_page(client):
    html = client.get("/extras").text
    assert "Артикли перед h" in html
    assert "chat" in html
    assert "Определённые артикли (демо)" not in html


@pytest.mark.usefixtures("git_repo")
def test_rename_topic_is_visible_everywhere(client):
    response = client.post("/topics/top-articles/rename", data={"name": "Артикли le/la"})
    assert response.status_code == 200
    assert "Артикли le/la" in client.get("/lessons/1").text
    assert "Артикли le/la" in client.get("/topics").text


@pytest.mark.usefixtures("git_repo")
def test_merge_topics(client):
    client.post("/topics/top-nasalson/merge", data={"target": "top-articles"})
    html = client.get("/topics").text
    assert "Носовые звуки" not in html
    assert "Урок 4" in client.get("/topics/top-articles").text


@pytest.mark.usefixtures("git_repo")
def test_change_lesson_date(client):
    client.post("/lessons/2/date", data={"date": "2026-09-08"})
    assert "8 сентября 2026" in client.get("/lessons/2").text


@pytest.mark.usefixtures("git_repo")
def test_change_element_topics_with_new_topic(client):
    client.post(
        "/elements/ex-gapinput/topics",
        data={"topics": ["top-etreverb"], "new_topic": "Спряжение", "new_section": "grammar"},
    )
    html = client.get("/elements/ex-gapinput").text
    assert "Спряжение" in html


@pytest.mark.usefixtures("git_repo")
def test_duplicate_topic_name_shows_message(client):
    response = client.post("/topics/top-etreverb/rename", data={"name": "артикли"})
    assert "уже есть" in response.text
