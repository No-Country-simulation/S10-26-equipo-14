"""Central read-only policy for HTTP API mutations."""

import hmac

from app.core.config import Settings


WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
READ_ONLY_DETAIL = "Operación bloqueada: esta API está en modo público de solo lectura."
PRIVATE_GET_PATHS = frozenset({"/api/v1/store-products"})
PRIVATE_GET_DETAIL = "Recurso no disponible en el modo público."


def writes_enabled(config: Settings, supplied_token: str | None = None) -> bool:
    """Allow local writes or authenticated production administration.

    Production mutations require a separately configured secret and a
    constant-time token comparison. Test environments remain fail-closed.
    """
    if config.app_env == "development" and not config.public_read_only:
        return True
    if config.app_env != "production" or config.admin_api_token is None or not supplied_token:
        return False
    return hmac.compare_digest(
        config.admin_api_token.get_secret_value(), supplied_token
    )


def is_development(config: Settings) -> bool:
    """Whether local-only diagnostics may be returned to the caller."""
    return config.app_env == "development"
