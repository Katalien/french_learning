"""US3: добавление слов в интерфейсе (FR-020–FR-024)."""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _git(content_root: Path):
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
    ):
        subprocess.run(["git", "-C", str(content_root), *args], check=True, capture_output=True)


def test_add_page_has_both_forms(client):
    html = client.get("/vocab/add").text
    assert 'action="/vocab/add"' in html and 'action="/vocab/import"' in html


def test_add_single_word_redirects_to_entry(client):
    response = client.post(
        "/vocab/add",
        data={"text": "fromage", "article": "le", "translations": "сыр", "topic": "top-nourritu"},
    )
    assert response.status_code == 200
    assert "/vocab/voc-" in str(response.url)
    assert "le fromage" in response.text


def test_add_without_translation_shows_error(client):
    response = client.post("/vocab/add", data={"text": "fromage", "topic": "top-nourritu"})
    assert "Не сохранено" in response.text


def test_import_list_report(client):
    response = client.post(
        "/vocab/import",
        data={"text": "le fromage — сыр\nla maison — жилище\nchat кот", "topic": "top-maisonxx"},
    )
    html = response.text
    assert "Добавлено: 1" in html and "Объединено: 1" in html
    assert "Не распознано: 1" in html and "chat кот" in html


def test_complete_page_shows_count_and_command(client):
    client.post("/vocab/import", data={"text": "parler (v) — говорить", "topic": "top-etreverb"})
    html = client.get("/vocab/complete").text
    assert "/complete-words" in html
    assert "Нужно дополнить: 1" in html


def test_add_single_word_from_one_line(client, content_root):
    response = client.post(
        "/vocab/add", data={"quick": "une, pomme - яблоко, яблочко", "topic": "top-nourritu"}
    )
    assert "/vocab/voc-" in str(response.url)
    assert "la pomme" in response.text
    files = (content_root / "vocabulary").glob("*.yaml")
    [path] = [p for p in files if "pomme" in p.read_text("utf-8")]
    text = path.read_text("utf-8")
    assert "article: la" in text and "gender: f" in text and "яблочко" in text


def test_one_line_unrecognized_shows_error(client):
    response = client.post("/vocab/add", data={"quick": "pomme яблоко", "topic": "top-nourritu"})
    assert "Не сохранено" in response.text and "разделител" in response.text
