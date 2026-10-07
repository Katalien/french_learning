"""Озвучка французского локальной нейросетью Piper (правка приёмки 003).

Работает без интернета (конституция IX): модели голосов скачиваются один раз командой
`french-learning tts-download` в TTS_DIR/voices, готовый звук кешируется в TTS_DIR/cache —
повторное воспроизведение не требует синтеза.
"""

from __future__ import annotations

import hashlib
import io
import os
import threading
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any

# ключ голоса → (код модели Piper, название для настроек)
VOICES = {
    "siwis": ("fr_FR-siwis-medium", "женский (Siwis)"),
    "tom": ("fr_FR-tom-medium", "мужской (Tom)"),
}
DEFAULT_VOICE = "siwis"
MAX_TEXT = 1000
# 012, пункт 4: тишина в начале звука. Наушники (особенно Bluetooth) и звук Windows после паузы
# «просыпаются» 0,2–0,5 с и съедали начало слова. Версия входит в ключ кеша: старые файлы
# без тишины больше не используются и пересоздаются при первом нажатии
LEAD_SILENCE = 0.35
CACHE_VERSION = "pad1"


class TTSUnavailable(Exception):
    """Модель голоса не скачана или не загружается."""


def _load_piper(model_path: Path) -> Any:
    from piper import PiperVoice

    return PiperVoice.load(model_path)


def download_voices(tts_dir: Path) -> None:
    from piper.download_voices import download_voice

    voices_dir = tts_dir / "voices"
    voices_dir.mkdir(parents=True, exist_ok=True)
    for code, _name in VOICES.values():
        download_voice(code, voices_dir)


class Speaker:
    def __init__(self, tts_dir: Path, loader: Callable[[Path], Any] = _load_piper) -> None:
        self.voices_dir = tts_dir / "voices"
        self.cache_dir = tts_dir / "cache"
        self._loader = loader
        self._engines: dict[str, Any] = {}
        self._lock = threading.Lock()

    def _model(self, voice: str) -> Path:
        return self.voices_dir / f"{VOICES[voice][0]}.onnx"

    def available(self, voice: str) -> bool:
        return voice in VOICES and self._model(voice).exists()

    def _engine(self, voice: str) -> Any:
        if voice not in self._engines:
            if not self.available(voice):
                raise TTSUnavailable(
                    "голос не скачан — выполните в терминале: uv run french-learning tts-download"
                )
            try:
                self._engines[voice] = self._loader(self._model(voice))
            except Exception as exc:  # повреждённая модель, нет библиотеки и т. п.
                raise TTSUnavailable(f"голос не загружается: {exc}") from exc
        return self._engines[voice]

    def warm_up(self, voice: str) -> None:
        """Загрузить модель заранее (около 3 секунд), чтобы первое нажатие не ждало."""
        with self._lock:
            self._engine(voice)

    def audio(self, text: str, voice: str) -> Path:
        text = " ".join(text.split())
        if voice not in VOICES:
            raise ValueError(f"неизвестный голос: {voice}")
        if not text or len(text) > MAX_TEXT:
            raise ValueError("текст для озвучки пустой или слишком длинный")
        source = f"{CACHE_VERSION}\n{VOICES[voice][0]}\n{text}"
        key = hashlib.sha256(source.encode()).hexdigest()[:32]
        path = self.cache_dir / voice / f"{key}.wav"
        if path.exists():
            return path
        with self._lock:
            if path.exists():
                return path
            engine = self._engine(voice)
            path.parent.mkdir(parents=True, exist_ok=True)
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wav_file:
                engine.synthesize_wav(text, wav_file)
            buffer.seek(0)
            with wave.open(buffer, "rb") as spoken:
                params = spoken.getparams()
                frames = spoken.readframes(spoken.getnframes())
            frame_size = params.sampwidth * params.nchannels
            silence = b"\0" * (int(params.framerate * LEAD_SILENCE) * frame_size)
            temp = path.with_suffix(".tmp")
            with wave.open(str(temp), "wb") as wav_file:
                wav_file.setparams(params)
                wav_file.writeframes(silence + frames)
            os.replace(temp, path)
        return path
