"""Озвучка французского локальной нейросетью Piper (practice/tts.py)."""

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, PlainTextResponse

from french_learning.practice.tts import DEFAULT_VOICE, TTSUnavailable

router = APIRouter()


def current_voice(request: Request) -> str:
    db = request.app.state.progress_db
    return (db.get_setting("voice") if db is not None else None) or DEFAULT_VOICE


@router.get("/tts")
def tts(request: Request, text: str = "", voice: str = ""):
    try:
        path = request.app.state.speaker.audio(text, voice or current_voice(request))
    except ValueError as exc:
        return PlainTextResponse(str(exc), status_code=400)
    except TTSUnavailable as exc:
        return PlainTextResponse(f"Озвучка недоступна: {exc}", status_code=503)
    # звук для одного текста не меняется — браузер может кешировать надолго
    headers = {"Cache-Control": "max-age=31536000, immutable"}
    return FileResponse(path, media_type="audio/wav", headers=headers)
