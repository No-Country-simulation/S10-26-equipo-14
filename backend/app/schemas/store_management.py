from datetime import datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


IntegrationStatus = Literal["pending", "analyzing", "configuration_required", "active", "error"]


class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    base_url: AnyHttpUrl
    country: str = Field(min_length=2, max_length=100)
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("name", "country")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El campo no puede estar vacío.")
        return value

    @field_validator("base_url")
    @classmethod
    def validate_public_root_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.scheme != "https" or not value.host or value.username or value.password:
            raise ValueError("La tienda debe usar una URL HTTPS pública sin credenciales.")
        if value.path not in {"", "/"} or value.query or value.fragment:
            raise ValueError("Introduce la URL principal del sitio, sin rutas, parámetros ni fragmentos.")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if not value.isascii() or not value.isalpha():
            raise ValueError("La moneda debe usar tres letras ASCII.")
        return value


class StoreBaseURLUpdate(BaseModel):
    base_url: AnyHttpUrl

    @field_validator("base_url")
    @classmethod
    def validate_public_root_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.scheme != "https" or not value.host or value.username or value.password:
            raise ValueError("La tienda debe usar una URL HTTPS p?blica sin credenciales.")
        if value.path not in {"", "/"} or value.query or value.fragment:
            raise ValueError("Introduce la URL principal del sitio, sin rutas, par?metros ni fragmentos.")
        return value


class CategoryCandidateOut(BaseModel):
    name: str
    source_url: str
    category_id: int | None


class MonitoringUpdate(BaseModel):
    category_ids: list[int] = Field(default_factory=list, max_length=100)
    currency: str = Field(min_length=3, max_length=3)
    interval_hours: int = Field(ge=1, le=720)
    enabled: bool

    @field_validator("category_ids")
    @classmethod
    def unique_category_ids(cls, value: list[int]) -> list[int]:
        if any(category_id <= 0 for category_id in value) or len(set(value)) != len(value):
            raise ValueError("Las categorías deben ser IDs positivos y no repetidos.")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if not value.isascii() or not value.isalpha():
            raise ValueError("La moneda debe usar tres letras ASCII.")
        return value


class StoreManagementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    base_url: str
    country: str | None
    is_active: bool
    created_at: datetime
    integration_status: IntegrationStatus
    analyzer_key: str | None
    analysis_message: str | None
    analysis_candidates: list[CategoryCandidateOut]
    last_analysis_at: datetime | None
    currency: str
    interval_hours: int
    monitoring_enabled: bool
    category_ids: list[int]
    last_extraction_at: datetime | None
    last_extraction_status: str | None
    connector_available: bool
    connector_name: str | None
    connector_configured: bool
    is_operational: bool
    coverage_status: str
    operational_at: datetime | None
    extraction_disabled_reason: str | None
