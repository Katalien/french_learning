"""Настройки приложения (research R14)."""

from pathlib import Path

from french_learning.config import Settings


def test_defaults_bind_to_localhost(monkeypatch):
    monkeypatch.delenv("CONTENT_DIR", raising=False)
    settings = Settings(_env_file=None)
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000


def test_content_dir_from_environment(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CONTENT_DIR", str(tmp_path))
    settings = Settings(_env_file=None)
    assert settings.content_dir == tmp_path
    assert settings.content_configured


def test_content_dir_from_env_file(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("CONTENT_DIR", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f"CONTENT_DIR={tmp_path}\n", encoding="utf-8")
    assert Settings(_env_file=env_file).content_dir == tmp_path


def test_missing_content_dir_is_not_configured(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("CONTENT_DIR", raising=False)
    assert not Settings(_env_file=None).content_configured
    monkeypatch.setenv("CONTENT_DIR", str(tmp_path / "missing"))
    assert not Settings(_env_file=None).content_configured


def test_deepl_key_from_environment(monkeypatch):
    # 006, research R3: ключ DeepL — только из окружения / .env, по умолчанию не задан
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)
    assert Settings(_env_file=None).deepl_api_key is None
    monkeypatch.setenv("DEEPL_API_KEY", "test-key:fx")
    assert Settings(_env_file=None).deepl_api_key == "test-key:fx"
