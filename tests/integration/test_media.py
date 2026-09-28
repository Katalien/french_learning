"""US5: список аудио и видео урока с путём к оригиналу (FR-036, research R10)."""

from pathlib import Path

from fastapi.testclient import TestClient

from french_learning.config import Settings
from french_learning.web.app import create_app


def test_media_listed_with_full_path(content_root: Path, tmp_path: Path):
    materials = tmp_path / "materials"
    settings = Settings(_env_file=None, content_dir=content_root, source_materials_dir=materials)
    html = TestClient(create_app(settings)).get("/lessons/2/tasks?part=class").text  # 009
    assert "Video.mov" in html
    assert "видео" in html and "В классе" in html
    expected = str(materials / "Leçon 02" / "Video.mov")
    assert expected in html
    assert "Скопировать путь" in html


def test_lesson_without_media_has_no_block(client):
    assert "Медиаматериалы" not in client.get("/lessons/1/tasks?part=class").text
