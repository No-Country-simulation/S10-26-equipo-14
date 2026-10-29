
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Raíz del repositorio PriceScope.
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Configuración de PriceScope cargada desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PriceScope API"
    database_url: str


@lru_cache
def get_settings() -> Settings:
    """Carga la configuración una sola vez durante la ejecución."""
    return Settings()


settings = get_settings()
