from datetime import datetime

from pydantic import BaseModel


class FDASourceStatus(BaseModel):
    name: str
    status: str
    freshness: str
    source_endpoint: str
    retrieved_at: datetime | None = None
    source_last_updated: str | None = None
    count: int | None = None
    cached: bool = False
    error: str | None = None


class FDALiveSummaryResponse(BaseModel):
    checked_at: datetime
    sources: dict[str, FDASourceStatus]