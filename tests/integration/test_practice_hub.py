"""009 US6: «Практика» — повторение, мои ошибки, тренажёры (FR-041, FR-042)."""

HX = {"HX-Request": "true"}


def block(html: str, name: str) -> str:
    return html.split(f'data-block="{name}"', 1)[1].split("</section>", 1)[0]


def test_hub_blocks(client):
    html = client.get("/practice").text
    repeat = block(html, "repeat")
    assert "Повторение слов" in repeat and "4" in repeat
    assert 'action="/practice/start"' in repeat and 'href="/practice/setup"' in repeat
    mistakes = block(html, "mistakes")
    assert 'href="/mistakes"' in mistakes
    trainers = block(html, "trainers")
    assert 'href="/trainers/articles"' in trainers and 'href="/trainers/negation"' in trainers


def test_mistakes_counter(client):
    client.post("/exercises/ex-gapinput/check", data={"i1.1": "x", "i2.1": "sommes"}, headers=HX)
    assert "1 пункт" in block(client.get("/practice").text, "mistakes")


def test_setup_moved_and_old_pages_work(client):
    setup = client.get("/practice/setup").text
    assert 'name="mode"' in setup and "Резервная копия" in setup
    assert client.get("/trainers").status_code == 200
    assert client.get("/mistakes").status_code == 200
