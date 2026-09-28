"""US4: происхождение, «требует проверки», сообщения об ошибках (FR-040–FR-043, SC-005)."""

import subprocess
from pathlib import Path

import pytest

ELEMENT_IDS = [
    "th-articles",
    "tx-aucafeaa",
    "ex-gapchoic",
    "ex-transfor",
    "th-extrarul",
]


@pytest.fixture
def git_repo(content_root: Path):
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
    ):
        subprocess.run(["git", "-C", str(content_root), *args], check=True, capture_output=True)


def test_origin_hidden_by_default(client):
    html = client.get("/elements/ex-gapchoic").text
    assert "origin-badge" not in html


def test_origin_toggle_shows_labels_everywhere(client):
    client.post("/settings/origin", data={"show": "1"})
    for element_id in ELEMENT_IDS:
        assert "origin-badge" in client.get(f"/elements/{element_id}").text, element_id
    html = client.get("/elements/ex-gapchoic").text
    assert "Complétez avec le, la, l" in html  # оригинальная формулировка
    assert "перевод: создано ИИ" in html
    client.post("/settings/origin", data={"show": "0"})
    assert "origin-badge" not in client.get("/elements/ex-gapchoic").text


def test_review_badge_explains_doubt(client):
    html = client.get("/elements/ex-gapchoic").text
    assert "review-badge" in html
    assert "«eau» или «eaux»" in html


def test_review_list(client):
    html = client.get("/review").text
    assert 'href="/elements/ex-gapchoic"' in html
    assert "пункт 2" in html


@pytest.mark.usefixtures("git_repo")
def test_mark_verified_removes_badge(client):
    client.post("/elements/ex-gapchoic/verified", data={"item": "2"})
    assert "review-badge" not in client.get("/elements/ex-gapchoic").text
    assert 'href="/elements/ex-gapchoic"' not in client.get("/review").text


@pytest.mark.usefixtures("git_repo")
def test_report_shows_reminder_and_counter(client):
    counter = 'Сообщения об ошибках <span class="chip">{}</span>'
    assert counter.format(1) in client.get("/lessons").text  # меню «⋯»
    response = client.post("/elements/ex-gapinput/report", data={"item": "1", "comment": "не так"})
    assert "разбери сообщения об ошибках" in response.text
    assert counter.format(2) in client.get("/lessons").text


def test_reports_page_open_first(client):
    html = client.get("/reports").text
    assert "Кажется, на фото «eaux»" in html
    assert 'href="/elements/ex-gapchoic"' in html
