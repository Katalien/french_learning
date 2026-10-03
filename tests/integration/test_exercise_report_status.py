"""US3: «Не согласна с ответом» и статус упражнения (FR-030, FR-032)."""

import re
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
    assert "Напишите, почему ответ неверный" in html  # 010: подсказка у пункта


def test_change_status_recounts_lesson(client):
    before = client.get("/lessons/1").text
    total_before = int(re.search(r"Домашка</span><strong>\d+ из (\d+)", before)[1])
    page = client.get("/elements/ex-multigap").text
    assert 'name="status"' in page
    response = client.post("/exercises/ex-multigap/status", data={"status": "reserve"})
    assert response.url.path == "/elements/ex-multigap"
    after = client.get("/lessons/1").text
    total_after = int(re.search(r"Домашка</span><strong>\d+ из (\d+)", after)[1])
    assert total_after == total_before - 1
    assert "ex-multigap" in client.get("/lessons/1/reserve").text


# --- 010 пункт 7: видно, что сообщение отправлено ---------------------------------------------


def item_block(html: str, item_id: int) -> str:
    start = html.index(f'id="item-{item_id}"')
    end = html.find('id="item-', start + 10)
    return html[start : end if end != -1 else html.index("</ol>", start)]


def report(client, comment: str) -> str:
    client.post("/exercises/ex-gapchoic/check", data={"i1.1": "la"}, headers=HX)
    return client.post(
        "/exercises/ex-gapchoic/items/1/report",
        data={"i1.1": "la", "comment-1": comment},
        headers=HX,
    ).text


def test_report_confirmation_inside_item(client, content_root):
    before = len(list((content_root / "reports").glob("rep-*.yaml")))
    html = report(client, "На листе написано la")
    block = item_block(html, 1)
    assert 'class="report-status' in block and "Сообщение сохранено" in block
    assert "сообщение отправлено" in block
    assert 'value="la"' in block
    assert len(list((content_root / "reports").glob("rep-*.yaml"))) == before + 1
    # метка остаётся и при следующем открытии упражнения
    assert "сообщение отправлено" in item_block(client.get("/elements/ex-gapchoic").text, 1)


def test_report_empty_comment_hint_inside_item(client, content_root):
    before = len(list((content_root / "reports").glob("rep-*.yaml")))
    block = item_block(report(client, "  "), 1)
    assert "Напишите, почему ответ неверный" in block
    assert len(list((content_root / "reports").glob("rep-*.yaml"))) == before


def test_report_write_error_inside_item(client, monkeypatch):
    from french_learning.content.writer import ContentWriter, WriteError

    def broken(*_args, **_kwargs):
        raise WriteError("диск недоступен")

    monkeypatch.setattr(ContentWriter, "create_report", broken)
    block = item_block(report(client, "текст"), 1)
    assert "Сообщение не отправлено: диск недоступен" in block


def test_report_button_shows_sending_state(client):
    html = client.post("/exercises/ex-gapchoic/check", data={"i1.1": "la"}, headers=HX).text
    assert 'hx-disabled-elt="this"' in html and "Отправляю…" in html
