
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# backend/app/core/config.py -> raíz del repositorio
ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    """Configuración de PriceScope cargada desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PriceScope API"
    database_url: str
    # Empty is safe in every environment. Pydantic Settings reads list values
    # from the environment as JSON, e.g. ["https://pricescope.vercel.app"].
    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        if any("*" in origin for origin in origins):
            raise ValueError("CORS origins must be explicit origins; wildcards are not allowed")
        return [origin.strip().rstrip("/") for origin in origins if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Carga la configuración una sola vez durante la ejecución."""
    return Settings()


settings = get_settings()
