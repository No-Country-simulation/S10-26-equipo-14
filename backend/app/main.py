from fastapi import FastAPI
from app.api.v1.router import router as api_router

app = FastAPI(
    title="PriceScope API",
    description="API para el monitoreo y análisis de precios.",
    version="0.1.0",
)
app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
