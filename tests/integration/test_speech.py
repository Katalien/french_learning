"""Озвучка через сервер приложения и выбор голоса в настройках."""

import pytest

from french_learning.practice.tts import TTSUnavailable


class FakeSpeaker:
    def __init__(self, tmp_path):
        self.tmp_path = tmp_path
        self.requests: list[tuple[str, str]] = []

    def available(self, voice):
        return True

    def audio(self, text, voice):
        self.requests.append((text, voice))
        path = self.tmp_path / "a.wav"
        path.write_bytes(b"RIFF....WAVE")
        return path


@pytest.fixture
def fake(client, tmp_path):
    speaker = FakeSpeaker(tmp_path)
    client.app.state.speaker = speaker
    return speaker


def test_tts_returns_wav_with_voice_from_settings(client, fake):
    response = client.get("/tts", params={"text": "l'ananas"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert fake.requests == [("l'ananas", "siwis")]
    client.post("/settings", data={"portion_size": "20", "directions": "staged", "voice": "tom"})
    client.get("/tts", params={"text": "chat"})
    assert fake.requests[-1] == ("chat", "tom")


def test_tts_bad_text_is_400(client, fake):
    fake.audio = lambda text, voice: (_ for _ in ()).throw(ValueError("пустой текст"))
    assert client.get("/tts", params={"text": ""}).status_code == 400


def test_tts_without_models_is_503(client, fake):
    def unavailable(text, voice):
        raise TTSUnavailable("голос не скачан: french-learning tts-download")

    fake.audio = unavailable
    response = client.get("/tts", params={"text": "chat"})
    assert response.status_code == 503
    assert "tts-download" in response.text


def test_settings_offer_both_voices(client):
    html = client.get("/settings").text
    assert 'name="voice" value="siwis"' in html and 'name="voice" value="tom"' in html


def test_unknown_voice_rejected(client):
    data = {"portion_size": "20", "directions": "staged", "voice": "robot"}
    assert "Не сохранено" in client.post("/settings", data=data).text


def test_speak_buttons_on_entry_and_flashcard(client):
    assert 'data-speak="la maison"' in client.get("/vocab/voc-maisonaa").text
    data = {"mode": "all", "kind": "all", "direction": "fr_ru", "method": "self"}
    card = client.post("/practice/start", data=data).text
    assert "data-speak=" in card
    assert "/static/js/speech.js" in card
