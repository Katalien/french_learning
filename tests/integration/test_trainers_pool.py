"""US5: задания от агента — пул, архив, «Ошибки», статистика (FR-050a–FR-053)."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from french_learning.config import Settings
from french_learning.web.app import create_app

ANSWERS = {
    "Je suis fatiguée.": "Je ne suis pas fatiguée.",
    "Il mange du pain.": "Il ne mange pas de pain.",
    "Nous aimons le beurre.": "Nous n'aimons pas le beurre.",
    "Tu es à la maison.": "Tu n'es pas à la maison.",
    "Elle boit de l'eau.": "Elle ne boit pas d'eau.",
}


def prompt(html):
    from html import unescape

    return unescape(re.search(r'class="trainer-prompt"[^>]*>\s*([^<]+?)\s*<', html)[1])


def key_of(html):
    return re.search(r'name="key" value="([^"]+)"', html)[1]


def solve_all(client, wrong: set[str] = frozenset()):
    session = client.post("/trainers/negation/start").url.path.rsplit("/", 1)[-1]
    while True:
        html = client.get(f"/trainers/s/{session}").text
        if "trainer-prompt" not in html:
            return session, html
        text = prompt(html)
        answer = "faux" if text in wrong else ANSWERS[text]
        client.post(f"/trainers/s/{session}/answer", data={"answer": answer, "key": key_of(html)})


def test_pool_flow(client):
    setup = client.get("/trainers/negation").text
    assert "В пуле: <strong>5</strong>" in setup and "Начать" in setup
    first = client.get(
        f"/trainers/s/{client.post('/trainers/negation/start').url.path.rsplit('/', 1)[-1]}"
    ).text
    assert "Сделайте предложение отрицательным." in first

    _session, summary = solve_all(client, wrong={"Elle boit de l'eau."})
    assert "4 из 5" in summary or "Верно" in summary
    setup = client.get("/trainers/negation").text
    assert "В пуле: <strong>1</strong>" in setup and "Ошибки (1)" in setup
    mistakes = client.get("/trainers/negation/mistakes").text
    assert "Elle boit de l" in mistakes and "faux" in mistakes
    stats = client.get("/trainers/negation/stats").text
    assert "80%" in stats

    solve_all(client)
    empty = client.get("/trainers/negation").text
    assert "Заданий нет" in empty and "/generate-tasks negation" in empty


def test_new_words_hint_and_review_note(client):
    session = client.post("/trainers/negation/start").url.path.rsplit("/", 1)[-1]
    seen = []
    for _ in range(5):
        html = client.get(f"/trainers/s/{session}").text
        seen.append(html)
        client.post(
            f"/trainers/s/{session}/answer",
            data={"answer": ANSWERS[prompt(html)], "key": key_of(html)},
        )
    joined = "\n".join(seen)
    assert "le beurre — масло" in joined
    assert "Агент не уверен" in joined


@pytest.fixture
def git_client(content_root: Path, tmp_path: Path):
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
    ):
        subprocess.run(["git", "-C", str(content_root), *args], check=True, capture_output=True)
    return TestClient(
        create_app(Settings(_env_file=None, content_dir=content_root, tts_dir=tmp_path / "tts"))
    )


def test_disagree_with_task(git_client, content_root):
    session = git_client.post("/trainers/negation/start").url.path.rsplit("/", 1)[-1]
    html = git_client.get(f"/trainers/s/{session}").text
    result = git_client.post(
        f"/trainers/s/{session}/answer", data={"answer": "faux", "key": key_of(html)}
    ).text
    url = re.search(r'action="(/trainers/tasks/tb-negaaaaa/\d+/report)"', result)[1]
    after = git_client.post(url, data={"comment": "Ответ неверный"}, follow_redirects=True)
    assert "разбери сообщения" in after.text
    reports = [p.read_text("utf-8") for p in (content_root / "reports").glob("rep-*.yaml")]
    assert any("element: tb-negaaaaa" in r for r in reports)
    from french_learning.agent.reports import reports_list

    [listed] = [r for r in reports_list(content_root) if r["element"] == "tb-negaaaaa"]
    assert listed["element_path"] == "trainers/negation/tb-negaaaaa.yaml"


def test_builtin_switched_to_agent_uses_pool(client, content_root):
    (content_root / "trainers.yaml").write_text(
        "trainers:\n  - {id: numbers, source: agent}\n", encoding="utf-8"
    )
    shutil.rmtree(content_root / "trainers" / "negation")
    html = client.get("/trainers/numbers").text
    assert "/generate-tasks numbers" in html
