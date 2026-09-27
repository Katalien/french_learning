from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from french_learning.config import Settings
from french_learning.web.app import create_app


@pytest.fixture
def client(content_root: Path) -> TestClient:
    return TestClient(
        create_app(
            Settings(_env_file=None, content_dir=content_root, tts_dir=content_root.parent / "tts")
        )
    )
