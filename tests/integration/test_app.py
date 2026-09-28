"""Каркас веб-приложения (plan.md; ui-routes.md «Поведение при проблемах»; FR-052)."""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from french_learning.config import Settings
from french_learning.web.app import create_app

TEMPLATES = Path(__file__).parents[2] / "src/french_learning/web/templates"


def client_for(root: Path | None) -> TestClient:
    settings = Settings(_env_file=None, content_dir=root)
    return TestClient(create_app(settings))


def test_not_configured_page_explains_content_dir():
    response = client_for(None).get("/")
    assert response.status_code == 503
    assert "CONTENT_DIR" in response.text


def test_missing_folder_is_not_configured(tmp_path: Path):
    response = client_for(tmp_path / "nope").get("/")
    assert response.status_code == 503


def test_home_page_ok(content_root: Path):
    response = client_for(content_root).get("/")
    assert response.status_code == 200
    assert '<html lang="ru"' in response.text


def test_problems_page_lists_broken_file(content_root: Path):
    response = client_for(content_root).get("/problems")
    assert response.status_code == 200
    assert "lessons/002/exercises/ex-brokenaa.yaml" in response.text


def test_vendor_files_served(content_root: Path):
    client = client_for(content_root)
    for name in ("htmx.min.js", "alpine.min.js"):
        assert client.get(f"/static/vendor/{name}").status_code == 200


def test_templates_do_not_load_anything_from_internet():
    pattern = re.compile(r"""(src|href)\s*=\s*["']https?://""", re.IGNORECASE)
    offenders = [
        path.name for path in TEMPLATES.rglob("*.html") if pattern.search(path.read_text("utf-8"))
    ]
    assert offenders == []
