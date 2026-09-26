"""Фабрика веб-приложения (plan.md, contracts/ui-routes.md)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from french_learning.config import Settings
from french_learning.content.index import ContentStore
from french_learning.content.progress import NoProgress
from french_learning.web import routes
from french_learning.web.deps import ContentNotConfiguredError
from french_learning.web.templating import templates

STATIC_DIR = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="French Learning", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.store = ContentStore(settings.content_dir) if settings.content_configured else None
    app.state.progress = NoProgress()

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

    return app
