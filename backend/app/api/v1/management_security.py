"""Central read-only policy and explicit admin-token authentication."""

import hmac

from fastapi import Header, HTTPException, Request, status

from app.core.config import Settings


WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
READ_ONLY_DETAIL = "Operación bloqueada: esta API está en modo público de solo lectura."
PRIVATE_GET_PATHS = frozenset({"/api/v1/store-products"})
PRIVATE_GET_DETAIL = "Recurso no disponible en el modo público."


def writes_enabled(config: Settings) -> bool:
    """Only an explicitly writable development environment may mutate data.

    Production stays read-only even when PUBLIC_READ_ONLY is accidentally set
    to false. Test deployments are also fail-closed; tests can construct an
    isolated development app when they need to exercise writable behavior.
    """
    return config.app_env == "development" and not config.public_read_only


def admin_token_configured(config: Settings) -> bool:
    token = config.admin_api_token
    return token is not None and bool(token.get_secret_value())


def admin_token_matches(config: Settings, supplied: str | None) -> bool:
    expected = config.admin_api_token
    if expected is None or not expected.get_secret_value() or not supplied:
        return False
    return hmac.compare_digest(expected.get_secret_value(), supplied)


def require_admin_api_token(
    request: Request,
    x_admin_api_token: str | None = Header(default=None, alias="X-Admin-API-Token"),
) -> None:
    """Require a configured server-side token for every protected mutation."""
    config = request.app.state.settings
    if writes_enabled(config):
        return
    if not admin_token_configured(config):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La administración no está configurada en este entorno.",
        )
    if not admin_token_matches(config, x_admin_api_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token administrativo inválido o ausente.",
            headers={"WWW-Authenticate": "AdminToken"},
        )


def is_development(config: Settings) -> bool:
    """Whether local-only diagnostics may be returned to the caller."""
    return config.app_env == "development"
