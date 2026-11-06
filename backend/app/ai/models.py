from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def ensure_utc(value: datetime) -> datetime:
    """Return ``value`` as a timezone-aware UTC datetime.

    Naive datetimes (used by the simulator) are interpreted as UTC.  Python
    refuses to compare or subtract naive and aware datetimes, so every
    comparison of event times goes through this helper.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class CompatModel(BaseModel):
    def __init__(self, *args, **kwargs):
        if args:
            field_names = list(self.__class__.model_fields.keys())
            provided = {}
            for index, value in enumerate(args):
                if index >= len(field_names):
                    raise TypeError(f"{self.__class__.__name__} accepts at most {len(field_names)} positional arguments")
                provided[field_names[index]] = value
            provided.update(kwargs)
            super().__init__(**provided)
        else:
            super().__init__(**kwargs)


class StorageCondition(CompatModel):
    minimum_temperature: float
    maximum_temperature: float
    minimum_humidity: float
    maximum_humidity: float

    @property
    def temperature_range(self) -> tuple[float, float]:
        return (self.minimum_temperature, self.maximum_temperature)

    @property
    def humidity_range(self) -> tuple[float, float]:
        return (self.minimum_humidity, self.maximum_humidity)


class IoTReading(CompatModel):
    shipment_id: str
    timestamp: datetime
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None
    speed: Optional[float] = None
    sensor_id: str = "sensor-unknown"
    rfid_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnomalyRecord(CompatModel):
    shipment_id: str
    batch_id: Optional[str] = None
    sensor_id: str
    type: str
    severity: str
    message: str
    timestamp: Optional[datetime] = None
    factor: str = "operational"
    evidence_id: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)


class CorrelationRecord(CompatModel):
    shipment_id: str
    batch_id: Optional[str] = None
    event_types: List[str]
    factors: List[str] = Field(default_factory=list)
    confidence: float
    summary: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class RiskScore(CompatModel):
    shipment_id: str
    score: float
    risk_level: str
    drivers: List[str]
    explanation: List[str]
    evidence_count: int
    factor_evidence: Dict[str, List[str]] = Field(default_factory=dict)
    interaction_contributions: Dict[str, float] = Field(default_factory=dict)
    requires_human_review: bool = False


class Alert(CompatModel):
    shipment_id: str
    alert_type: str
    severity: str
    title: str
    summary: str
    recommendations: List[str]
    requires_human_review: bool = True
    evidence: Dict[str, Any] = Field(default_factory=dict)


class CounterfeitAssessment(CompatModel):
    shipment_id: str
    is_counterfeit_risk: bool
    risk_level: str
    reasons: List[str]
    status: str = "AUTHENTIC"
    evidence: Dict[str, Any] = Field(default_factory=dict)


class AIAnalysisResult(CompatModel):
    shipment_id: str
    anomalies: List[AnomalyRecord]
    correlations: List[CorrelationRecord]
    risk: RiskScore
    counterfeit: CounterfeitAssessment
    alerts: List[Alert]


def evidence_hash(value: Any) -> str:
    """Return a deterministic evidence hash; this is not a blockchain transaction ID."""
    import json

    encoded = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def anomaly_evidence_id(anomaly: AnomalyRecord) -> str:
    if anomaly.evidence_id:
        return anomaly.evidence_id
    return evidence_hash(
        {
            "batch_id": anomaly.batch_id,
            "shipment_id": anomaly.shipment_id,
            "sensor_id": anomaly.sensor_id,
            "type": anomaly.type,
            "factor": anomaly.factor,
            "timestamp": anomaly.timestamp,
            "evidence": anomaly.evidence,
        }
    )
