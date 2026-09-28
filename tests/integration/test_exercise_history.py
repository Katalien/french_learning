"""US2: «Решить заново», история попыток, «Мои ошибки» (FR-021, FR-021a, FR-031)."""

import re

HX = {"HX-Request": "true"}
ALL_RIGHT = {"i1.1": "le", "i2.1": "l'", "i3.1": "les"}


def check(client, exercise_id, data, attempt=None):
    if attempt:
        data = {**data, "attempt": str(attempt)}
    return client.post(f"/exercises/{exercise_id}/check", data=data, headers=HX).text


def test_restart_and_history(client):
    check(client, "ex-gapchoic", {**ALL_RIGHT, "i1.1": "la"})
    html = check(client, "ex-gapchoic", ALL_RIGHT)
    assert "Решить заново" in html and "/exercises/ex-gapchoic/history" in html
    fresh = client.post("/exercises/ex-gapchoic/restart", headers=HX).text
    assert 'id="item-1" class="item item-none"' in fresh and "Верно сразу" not in fresh
    check(client, "ex-gapchoic", ALL_RIGHT)
    history = client.get("/exercises/ex-gapchoic/history").text
    assert history.count('class="attempt"') == 2
    assert "2 из 3" in history and "3 из 3" in history
    assert "исправлено самостоятельно" in history


def test_last_attempt_shown_by_default(client):
    check(client, "ex-gapchoic", ALL_RIGHT)
    html = client.get("/elements/ex-gapchoic").text
    assert "Верно сразу: 3 из 3" in html and "Решить заново" in html


def test_mistakes_list_filter_and_solve_item(client):
    check(client, "ex-gapchoic", {**ALL_RIGHT, "i1.1": "la"})
    check(client, "ex-gapinput", {"i1.1": "x", "i2.1": "sommes"})
    listing = client.get("/mistakes").text
    assert listing.count('class="mistake"') == 2
    assert client.get("/mistakes?topic=top-etreverb").text.count('class="mistake"') == 1
    assert client.get("/mistakes?lesson=2").text.count('class="mistake"') == 0

    page = client.post("/mistakes/ex-gapchoic/1", follow_redirects=True).text
    attempt = re.search(r'name="attempt" value="(\d+)"', page)[1]
    assert 'id="item-1"' in page and 'id="item-2"' not in page  # только этот пункт
    result = check(client, "ex-gapchoic", {"i1.1": "le"}, attempt=attempt)
    assert "item-correct" in result
    assert client.get("/mistakes").text.count('class="mistake"') == 1
    assert 'id="item-1"' in client.get("/exercises/ex-gapchoic/history").text


def test_mistakes_reachable_from_practice(client):
    assert 'href="/practice"' in client.get("/lessons").text  # «Мои ошибки» — в «Практике»
