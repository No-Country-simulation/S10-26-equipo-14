
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# backend/app/core/config.py -> raíz del repositorio
ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"
DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://localhost:5174",
    "https://s10-26-equipo-14.vercel.app",
    "https://pricescope-14.vercel.app",
)


class Settings(BaseSettings):
    """Configuración de PriceScope cargada desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PriceScope API"
    database_url: str
    admin_api_token: SecretStr | None = Field(default=None, repr=False)
    app_env: Literal["development", "test", "production"] = "production"
    public_read_only: bool = True
    # Keep local Vite and the deployed frontend available by default. Additional
    # explicit origins may be supplied as JSON through CORS_ORIGINS.
    cors_origins: list[str] = Field(default_factory=lambda: list(DEFAULT_CORS_ORIGINS))

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        if any("*" in origin for origin in origins):
            raise ValueError("CORS origins must be explicit origins; wildcards are not allowed")
        normalized = [origin.strip().rstrip("/") for origin in origins if origin.strip()]
        return list(dict.fromkeys([*DEFAULT_CORS_ORIGINS, *normalized]))


@lru_cache
def get_settings() -> Settings:
    """Carga la configuración una sola vez durante la ejecución."""
    return Settings()


settings = get_settings()
