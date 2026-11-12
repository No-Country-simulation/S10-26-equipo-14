from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import router as api_router
from app.api.v1.management_security import (
    PRIVATE_GET_DETAIL,
    PRIVATE_GET_PATHS,
    READ_ONLY_DETAIL,
    WRITE_METHODS,
    writes_enabled,
)
from app.core.config import Settings, settings
from app.db.session import engine


def create_app(
    cors_origins: list[str] | None = None,
    app_settings: Settings | None = None,
) -> FastAPI:
    """Build the API with explicit CORS origins; an empty list denies CORS."""
    runtime_settings = app_settings or settings
    application = FastAPI(
        title="PriceScope API",
        description="API para el monitoreo y análisis de precios.",
        version="0.1.0",
    )
    application.state.settings = runtime_settings

    @application.middleware("http")
    async def enforce_api_read_only_mode(request: Request, call_next):
        """Enforce public read visibility and reject mutations before routing."""
        config = request.app.state.settings
        if (
            request.url.path in PRIVATE_GET_PATHS
            and request.method.upper() == "GET"
            and config.app_env != "development"
        ):
            return JSONResponse(status_code=404, content={"detail": PRIVATE_GET_DETAIL})
        if (
            request.url.path.startswith("/api/")
            and request.method.upper() in WRITE_METHODS
            and not writes_enabled(config, request.headers.get("X-Admin-Token"))
        ):
            return JSONResponse(status_code=403, content={"detail": READ_ONLY_DETAIL})
        return await call_next(request)

    # Register CORS after the read-only middleware so CORS remains the outer
    # response wrapper, including for centrally rejected API mutations.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.cors_origins if cors_origins is None else cors_origins,
        # Vercel generates unique deployment hostnames for each preview. Restrict
        # the regex to this project's exact Vercel hostname prefix and domain.
        allow_origin_regex=r"^https://s10-26-equipo-14(?:-[a-z0-9-]+)?\.vercel\.app$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router)

    @application.get("/api/v1/management/access")
    def management_access(
        request: Request,
        x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    ):
        return {"can_manage": writes_enabled(request.app.state.settings, x_admin_token)}

    @application.get("/health")
    def health_check():
        return {"status": "ok"}

    @application.get("/ready")
    def ready_check():
        """Return readiness based only on a read-only database connectivity check."""
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001 - do not expose database error details
            return JSONResponse(status_code=503, content={"status": "not ready"})
        return {"status": "ready"}

    return application


app = create_app()
