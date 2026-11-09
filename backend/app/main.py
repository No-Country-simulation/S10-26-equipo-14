from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import router as api_router
from app.core.config import settings
from app.db.session import engine


def create_app(cors_origins: list[str] | None = None) -> FastAPI:
    """Build the API with explicit CORS origins; an empty list denies CORS."""
    application = FastAPI(
        title="PriceScope API",
        description="API para el monitoreo y análisis de precios.",
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins if cors_origins is None else cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router)

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
