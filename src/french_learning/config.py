"""Настройки приложения: переменные окружения и локальный файл `.env` (research R14)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    content_dir: Path | None = None
    source_materials_dir: Path | None = None
    # Конституция XII: по умолчанию приложение доступно только с этого компьютера.
    host: str = "127.0.0.1"
    port: int = 8000

    @property
    def content_configured(self) -> bool:
        return self.content_dir is not None and self.content_dir.is_dir()
