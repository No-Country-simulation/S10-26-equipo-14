"""Public access policy for the PriceScope simulation demo."""

# Public demo: catalog, monitoring, and extraction routes are accessible
# without an administrative credential.
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
READ_ONLY_DETAIL = "Operación no disponible."
PRIVATE_GET_PATHS: frozenset[str] = frozenset()
PRIVATE_GET_DETAIL = "Recurso no disponible."


def writes_enabled(config, supplied_token: str | None = None) -> bool:
    """Allow demo operations without an administrative token."""
    return True


def is_development(config) -> bool:
    """Whether local-only diagnostics may be returned to the caller."""
    return config.app_env == "development"
