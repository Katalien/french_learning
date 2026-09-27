"""Настройки повторения (FR-035a, FR-035b)."""


def test_settings_page_and_save(client):
    html = client.get("/settings").text
    assert 'name="portion_size"' in html and 'value="20"' in html
    client.post("/settings", data={"portion_size": "35", "directions": "both"})
    db = client.app.state.progress_db
    assert db.get_setting("portion_size") == "35"
    assert db.get_setting("directions") == "both"


def test_invalid_portion_is_rejected(client):
    response = client.post("/settings", data={"portion_size": "0", "directions": "staged"})
    assert "Не сохранено" in response.text
    assert client.app.state.progress_db.get_setting("portion_size") == "20"
