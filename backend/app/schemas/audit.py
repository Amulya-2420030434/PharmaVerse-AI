from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditDrugResponse(BaseModel):
    drug_id: str
    name: str
    generic_name: str | None = None
    manufacturer: str
    dosage_form: str | None = None
    strength: str | None = None
    storage_min_temp: float | None = None
    storage_max_temp: float | None = None
    storage_min_humidity: float | None = None
    storage_max_humidity: float | None = None


class AuditShipmentResponse(BaseModel):
    shipment_id: str
    source: str
    destination: str
    current_owner: str | None = None
    status: str
    expected_departure: datetime | None = None
    actual_departure: datetime | None = None
    expected_arrival: datetime | None = None
    actual_arrival: datetime | None = None
    expected_latitude: float | None = None
    expected_longitude: float | None = None
    current_latitude: float | None = None
    current_longitude: float | None = None
    created_at: datetime


class AuditQRResponse(BaseModel):
    qr_id: str
    status: str
    created_at: datetime


class AuditRFIDResponse(BaseModel):
    rfid_id: str
    status: str
    created_at: datetime


class AuditBatchResponse(BaseModel):
    trace_source: str
    batch_id: str
    drug_id: str | None = None
    manufacturing_date: date
    expiry_date: date
    quantity: int
    batch_status: str
    created_at: datetime
    drug: AuditDrugResponse | None = None
    shipments: list[AuditShipmentResponse]
    qr_records: list[AuditQRResponse]
    rfid_records: list[AuditRFIDResponse]
    fabric_history: list[dict[str, Any]] | None = None

    model_config = ConfigDict(from_attributes=True)
