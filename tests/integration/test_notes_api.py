"""JSON API заметок (contracts/notes-api.md, 005)."""

ANCHOR = {"exact": "un café", "prefix": "Il commande ", "suffix": " et un", "start": 45}


def create(client, **fields):
    return client.post("/notes", json=fields)


def test_create_lesson_note(client):
    r = create(client, kind="note", body="passé simple не нужен", lesson=1)
    assert r.status_code == 201
    note = r.json()
    assert note["id"] > 0 and note["lesson"] == 1 and note["element_id"] is None
    assert note["origin"] == "user" and note["anchor"] is None


def test_create_fragment_question(client):
    r = create(client, kind="question", body="почему un?", element_id="tx-aucafeaa", anchor=ANCHOR)
    assert r.status_code == 201
    note = r.json()
    assert note["lesson"] == 1 and note["element_title"] == "Au café (démo)"
    assert note["anchor"] == ANCHOR and not note["answered"]


def test_create_errors(client):
    for fields in (
        {"kind": "note", "body": " ", "lesson": 1},
        {"kind": "todo", "body": "x", "lesson": 1},
        {"kind": "note", "body": "x", "lesson": 1, "anchor": ANCHOR},
        {"kind": "note", "body": "x", "element_id": "нет"},
        {"kind": "note", "body": "x", "lesson": 1, "anchor": {"prefix": "a"}},
    ):
        r = create(client, **fields)
        assert r.status_code == 422, fields
        assert r.json()["error"]
    r = create(client, kind="note", body="x", element_id="th-extrarul")
    assert r.status_code == 422 and "только у элементов уроков" in r.json()["error"]
    assert create(client, kind="note", body="x", lesson=77).status_code == 404


def test_patch_answer_and_reopen(client):
    q = create(client, kind="question", body="вопрос", lesson=1).json()
    r = client.patch(f"/notes/{q['id']}", json={"answer": "ответ"})
    assert r.status_code == 200 and r.json()["answered"] and r.json()["answer"] == "ответ"
    r = client.patch(f"/notes/{q['id']}", json={"answered": False})
    assert not r.json()["answered"] and r.json()["answer"] == "ответ"


def test_patch_rebind_anchor(client):
    n = create(client, kind="note", body="a", element_id="tx-aucafeaa", anchor=ANCHOR).json()
    new = {**ANCHOR, "exact": "un croissant", "start": 60}
    assert client.patch(f"/notes/{n['id']}", json={"anchor": new}).json()["anchor"] == new
    assert client.patch(f"/notes/{n['id']}", json={"anchor": None}).json()["anchor"] is None


def test_patch_errors(client):
    n = create(client, kind="note", body="a", lesson=1).json()
    assert client.patch(f"/notes/{n['id']}", json={"body": " "}).status_code == 422
    assert client.patch(f"/notes/{n['id']}", json={"answer": "x"}).status_code == 422
    assert client.patch("/notes/999", json={"body": "x"}).status_code == 404


def test_delete(client):
    n = create(client, kind="note", body="a", lesson=1).json()
    assert client.delete(f"/notes/{n['id']}").status_code == 204
    assert client.delete(f"/notes/{n['id']}").status_code == 404
