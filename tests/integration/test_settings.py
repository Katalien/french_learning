"""Настройки (FR-035a; 010: размер подхода и направления убраны из «Настроек»)."""


def test_settings_page_has_no_portion_or_directions(client):
    html = client.get("/settings").text
    assert 'name="portion_size"' not in html
    assert 'name="directions"' not in html
    assert 'name="trainer_portion_size"' in html


def test_settings_save_without_portion_and_directions(client):
    db = client.app.state.progress_db
    response = client.post("/settings", data={"trainer_portion_size": "15", "voice": "siwis"})
    assert "Настройки сохранены" in response.text
    assert db.get_setting("trainer_portion_size") == "15"
    assert db.get_setting("portion_size") == "20"  # не трогается


def test_invalid_trainer_portion_is_rejected(client):
    response = client.post("/settings", data={"trainer_portion_size": "0"})
    assert "Не сохранено" in response.text
