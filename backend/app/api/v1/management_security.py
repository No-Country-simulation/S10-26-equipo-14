"""Central read-only policy for HTTP API mutations."""

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


def is_development(config: Settings) -> bool:
    """Whether local-only diagnostics may be returned to the caller."""
    return config.app_env == "development"
