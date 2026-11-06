from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.ai.models import ensure_utc


class _UTCTimestampMixin(BaseModel):
    """Normalize the ``timestamp`` field to timezone-aware UTC.

    Clients may send "Z"/offset timestamps or naive ones; mixing them made the
    correlation and delay logic raise ``TypeError`` (HTTP 500).
    """

    @field_validator("timestamp", check_fields=False)
    @classmethod
    def _timestamp_to_utc(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class AIReadingInput(_UTCTimestampMixin):
    timestamp: datetime
    temperature: float | None = Field(default=None, ge=-100, le=150)
    humidity: float | None = Field(default=None, ge=0, le=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_name: str | None = Field(default=None, max_length=255)
    speed: float | None = Field(default=None, ge=0, le=500)
    sensor_id: str = Field(default="api-sensor", max_length=100)
    rfid_id: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIRoutePointInput(_UTCTimestampMixin):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    location_name: str = Field(min_length=1, max_length=255)
    timestamp: datetime


class AIRFIDEventInput(_UTCTimestampMixin):
    event_type: str = Field(min_length=1, max_length=50)
    location_name: str = Field(min_length=1, max_length=255)
    timestamp: datetime
    rfid_id: str | None = Field(default=None, max_length=255)
    expected_rfid_id: str | None = Field(default=None, max_length=255)
    qr_id: str | None = Field(default=None, max_length=255)
    product_id: str | None = Field(default=None, max_length=255)
    batch_id: str | None = Field(default=None, max_length=255)
    owner: str | None = Field(default=None, max_length=255)
    authorized: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIAnalysisRequest(BaseModel):
    shipment_id: str = Field(min_length=1, max_length=100)
    readings: list[AIReadingInput] = Field(default_factory=list, max_length=500)
    rfid_events: list[AIRFIDEventInput] = Field(default_factory=list, max_length=500)
    planned_route: list[AIRoutePointInput] = Field(default_factory=list, max_length=100)
    actual_rfid_id: str | None = Field(default=None, max_length=255)
    actual_qr_id: str | None = Field(default=None, max_length=255)
    actual_product_id: str | None = Field(default=None, max_length=255)
    actual_batch_id: str | None = Field(default=None, max_length=255)
    actual_owner: str | None = Field(default=None, max_length=255)
    actual_expiry_date: date | None = None
    expected_duration_hours: float | None = Field(default=None, gt=0)
    delay_tolerance_hours: float = Field(default=1.0, ge=0)
    route_threshold_km: float = Field(default=25.0, gt=0)


class AIBlockchainMetadata(BaseModel):
    status: str
    transaction_id: str | None = None
    evidence_hash: str


class AISimulationRequest(BaseModel):
    shipment_id: str = Field(min_length=1, max_length=100)
    scenario: str = Field(min_length=1, max_length=50)


class AIAnalysisPersistence(BaseModel):
    analysis_id: str
    persisted_event_count: int
    duplicate_event_count: int


class AIAnalysisHistoryItem(BaseModel):
    analysis_id: str
    assessed_at: datetime
    risk_score: float
    risk_level: str
    evidence_hash: str
    result: dict[str, Any]


class AIAnalysisResponse(BaseModel):
    shipment_id: str
    anomalies: list[dict[str, Any]]
    correlations: list[dict[str, Any]]
    risk: dict[str, Any]
    counterfeit: dict[str, Any]
    alerts: list[dict[str, Any]]
    explanations: list[str]
    explainability: dict[str, Any]
    blockchain: AIBlockchainMetadata
    ml_assessment: dict[str, Any] | None = None
    persistence: AIAnalysisPersistence
