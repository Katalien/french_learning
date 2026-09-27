"""US3: «Не согласна с ответом» и статус упражнения (FR-030, FR-032)."""

import subprocess
from pathlib import Path

import pytest

HX = {"HX-Request": "true"}


@pytest.fixture(autouse=True)
def git_repo(content_root: Path):
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
    ):
        subprocess.run(["git", "-C", str(content_root), *args], check=True, capture_output=True)


def test_disagree_creates_report_for_item(client, content_root):
    html = client.post("/exercises/ex-gapchoic/check", data={"i1.1": "la"}, headers=HX).text
    assert "Не согласна с ответом" in html
    assert "материал урока" in html or "создано ИИ" in html  # происхождение ответа видно всегда
    result = client.post(
        "/exercises/ex-gapchoic/items/1/report",
        data={"i1.1": "la", "comment-1": "На листе написано la"},
        headers=HX,
    ).text
    assert "разбери сообщения" in result  # напоминание (001, FR-043)
    reports = [p.read_text("utf-8") for p in (content_root / "reports").glob("rep-*.yaml")]
    assert any("element: ex-gapchoic" in r and "item: 1" in r and "На листе" in r for r in reports)
    assert 'value="la"' in result  # ответы в форме не потерялись


def test_disagree_needs_comment(client):
    client.post("/exercises/ex-gapchoic/check", data={"i1.1": "la"}, headers=HX)
    html = client.post(
        "/exercises/ex-gapchoic/items/1/report", data={"comment-1": " "}, headers=HX
    ).text
    assert "опишите" in html


def test_change_status_recounts_lesson(client):
    before = client.get("/lessons/1").text
    total_before = int(before.split("Домашка: <strong>")[1].split(" из ")[1].split("<")[0])
    page = client.get("/elements/ex-multigap").text
    assert 'name="status"' in page
    response = client.post("/exercises/ex-multigap/status", data={"status": "reserve"})
    assert response.url.path == "/elements/ex-multigap"
    after = client.get("/lessons/1").text
    total_after = int(after.split("Домашка: <strong>")[1].split(" из ")[1].split("<")[0])
    assert total_after == total_before - 1
    assert "ex-multigap" in client.get("/lessons/1/reserve").text
