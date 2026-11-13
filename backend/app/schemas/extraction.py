from datetime import datetime

from pydantic import BaseModel


class ExtractionRunOut(BaseModel):
    run_id: int
    store_id: int
    store_name: str
    source: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    records_seen: int
    observations_created: int
    products_created: int
    prices_changed: int
    error_summary: str | None
