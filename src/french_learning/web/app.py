"""Фабрика веб-приложения (plan.md, contracts/ui-routes.md)."""

from __future__ import annotations

import threading
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from french_learning.config import Settings
from french_learning.content.index import ContentStore
from french_learning.content.progress import NoProgress
from french_learning.exercises.attempts import AttemptStore, ExerciseProgress
from french_learning.practice.backup import start_daily_backup
from french_learning.practice.db import ProgressDB
from french_learning.practice.tts import DEFAULT_VOICE, Speaker
from french_learning.trainers.schedule import TrainerSchedule
from french_learning.trainers.sessions import TrainerSessions
from french_learning.vocab.cards import CardStore
from french_learning.vocab.sessions import SessionStore
from french_learning.web import routes
from french_learning.web.deps import ContentNotConfiguredError
from french_learning.web.templating import templates

STATIC_DIR = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None, auto_backup: bool = False) -> FastAPI:
    """auto_backup — ежедневная резервная копия прогресса в фоне и заблаговременная загрузка
    голоса озвучки (включает команда `serve`)."""
    settings = settings or Settings()
    app = FastAPI(title="French Learning", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.store = ContentStore(settings.content_dir) if settings.content_configured else None
    app.state.progress = NoProgress()
    app.state.progress_db = app.state.cards = app.state.sessions = app.state.attempts = None
    app.state.trainer_schedule = app.state.trainer_sessions = None
    if settings.content_configured:
        app.state.progress_db = ProgressDB(settings.content_dir)
        app.state.cards = CardStore(app.state.progress_db)
        app.state.sessions = SessionStore(app.state.progress_db, app.state.cards)
        app.state.attempts = AttemptStore(app.state.progress_db)
        app.state.progress = ExerciseProgress(app.state.attempts)
        app.state.trainer_schedule = TrainerSchedule(app.state.progress_db)
        app.state.trainer_sessions = TrainerSessions(
            app.state.progress_db, app.state.trainer_schedule
        )

    app.state.speaker = Speaker(settings.tts_dir)
    if auto_backup:
        voice = DEFAULT_VOICE
        if app.state.progress_db is not None:
            voice = app.state.progress_db.get_setting("voice") or DEFAULT_VOICE
        if app.state.speaker.available(voice):
            threading.Thread(target=app.state.speaker.warm_up, args=(voice,), daemon=True).start()

    if auto_backup and app.state.progress_db is not None:

        @app.middleware("http")
        async def _daily_backup(request: Request, call_next):
            start_daily_backup(app.state.progress_db, settings.content_dir)
            return await call_next(request)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    for router in routes.ALL:
        app.include_router(router)

    @app.exception_handler(ContentNotConfiguredError)
    async def _not_configured(request: Request, exc: ContentNotConfiguredError) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "not_configured.html",
            {"content_dir": settings.content_dir},
            status_code=503,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> HTMLResponse:
        message = exc.detail if exc.status_code == 404 and exc.detail != "Not Found" else None
        return templates.TemplateResponse(
            request,
            "error.html",
            {"status": exc.status_code, "message": message or "Страница не найдена"},
            status_code=exc.status_code,
        )

    return app
