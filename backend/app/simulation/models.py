from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..ai.models import CompatModel, StorageCondition


class RoutePoint(CompatModel):
    latitude: float
    longitude: float
    location_name: str
    timestamp: datetime


class Shipment(CompatModel):
    shipment_id: str
    product_name: str
    source: str
    destination: str
    route: List[RoutePoint]
    rfid_id: str
    expected_rfid_id: Optional[str] = None
    expected_qr_id: Optional[str] = None
    product_id: Optional[str] = None
    batch_id: Optional[str] = None
    expected_owner: Optional[str] = None
    owner: Optional[str] = None
    expiry_date: Optional[datetime] = None
    expected_duration_hours: float = 6.0
    delay_tolerance_hours: float = 1.0
    route_threshold_km: float = 25.0
    status: str = "in_transit"
    eta_hours: float = 24.0
    product_type: str = "pharmaceutical"
    storage_condition: StorageCondition = Field(
        default_factory=lambda: StorageCondition(
            minimum_temperature=2.0,
            maximum_temperature=8.0,
            minimum_humidity=35.0,
            maximum_humidity=65.0,
        )
    )


class RFIDEvent(CompatModel):
    shipment_id: str
    rfid_id: Optional[str] = None
    event_type: str
    location_name: str
    timestamp: datetime
    expected_rfid_id: Optional[str] = None
    qr_id: Optional[str] = None
    product_id: Optional[str] = None
    batch_id: Optional[str] = None
    owner: Optional[str] = None
    authorized: Optional[bool] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScenarioResult(CompatModel):
    name: str
    description: str
    shipments: List[Shipment]
    sensor_readings: List[Dict[str, Any]]
    rfid_events: List[Dict[str, Any]]
