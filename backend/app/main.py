from fastapi import FastAPI

app = FastAPI(
    title="PriceScope API",
    description="API para el monitoreo y análisis de precios.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
