from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import PublicId


class ShipmentCreate(BaseModel):
    shipment_id: PublicId
    # Public batch identifier (Batch.batch_id), NOT the database UUID.
    batch_id: PublicId

    source: str = Field(min_length=1, max_length=255)
    destination: str = Field(min_length=1, max_length=255)

    current_owner: str | None = Field(default=None, max_length=255)
    status: str = "CREATED"

    expected_departure: datetime | None = None
    expected_arrival: datetime | None = None

    expected_latitude: float | None = Field(default=None, ge=-90, le=90)
    expected_longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("status")
    @classmethod
    def validate_initial_status(cls, value: str) -> str:
        # Lifecycle states after CREATED are reached only through the
        # depart/receive endpoints, never by choosing them at creation time.
        normalized = value.strip().upper()
        if normalized != "CREATED":
            raise ValueError(
                "a new shipment must have status CREATED; use the depart "
                "and receive endpoints to change its lifecycle state"
            )
        return normalized


class ShipmentTransfer(BaseModel):
    new_owner: str = Field(max_length=255)


class ShipmentResponse(BaseModel):
    id: UUID
    shipment_id: str
    batch_id: UUID
    source: str = Field(validation_alias="source_location")
    destination: str = Field(validation_alias="destination_location")
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
    fabric_asset_id: str | None = None
    last_fabric_transaction_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
