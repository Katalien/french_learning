"""Озвучка локальной нейросетью Piper: кеш, выбор голоса, ошибки (правка приёмки 003)."""

import wave

import pytest

from french_learning.practice.tts import VOICES, Speaker, TTSUnavailable


class FakeEngine:
    def __init__(self):
        self.calls: list[str] = []

    def synthesize_wav(self, text, wav_file):
        self.calls.append(text)
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"\0\0" * 10)


@pytest.fixture
def speaker(tmp_path):
    engines: dict[str, FakeEngine] = {}

    def loader(model_path):
        return engines.setdefault(model_path.name, FakeEngine())

    for code, _name in VOICES.values():
        (tmp_path / "voices").mkdir(exist_ok=True)
        (tmp_path / "voices" / f"{code}.onnx").write_bytes(b"model")
    result = Speaker(tmp_path, loader=loader)
    result.engines = engines
    return result


def test_audio_is_wav_and_cached(speaker):
    first = speaker.audio("l'ananas", "siwis")
    with wave.open(str(first)) as wav:
        assert wav.getframerate() == 22050
    assert speaker.audio("  l'ananas ", "siwis") == first
    [engine] = speaker.engines.values()
    assert engine.calls == ["l'ananas"]


def test_voices_are_separate(speaker):
    assert speaker.audio("chat", "siwis") != speaker.audio("chat", "tom")
    assert len(speaker.engines) == 2


def test_unknown_voice_and_bad_text(speaker):
    with pytest.raises(ValueError):
        speaker.audio("chat", "robot")
    with pytest.raises(ValueError):
        speaker.audio("   ", "siwis")
    with pytest.raises(ValueError):
        speaker.audio("a" * 1001, "siwis")


def test_missing_model_reports_command(tmp_path):
    speaker = Speaker(tmp_path, loader=lambda path: FakeEngine())
    assert not speaker.available("siwis")
    with pytest.raises(TTSUnavailable, match="tts-download"):
        speaker.audio("chat", "siwis")
