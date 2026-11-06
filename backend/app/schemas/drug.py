from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)
from typing import Annotated

from app.schemas.common import PublicId


def _text(max_length: int):
    return Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=max_length),
    ]


class DrugCreate(BaseModel):
    drug_id: PublicId
    name: _text(255)
    generic_name: _text(255) | None = None
    manufacturer: _text(255)
    dosage_form: _text(100) | None = None
    strength: _text(100) | None = None

    storage_min_temp: float | None = None
    storage_max_temp: float | None = None

    storage_min_humidity: float | None = None
    storage_max_humidity: float | None = None

    description: str | None = None
    expiry_period_days: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_storage_ranges(self):
        if (
            self.storage_min_temp is not None
            and self.storage_max_temp is not None
            and self.storage_min_temp > self.storage_max_temp
        ):
            raise ValueError(
                "storage_min_temp must not exceed storage_max_temp"
            )
        if (
            self.storage_min_humidity is not None
            and self.storage_max_humidity is not None
            and self.storage_min_humidity > self.storage_max_humidity
        ):
            raise ValueError(
                "storage_min_humidity must not exceed storage_max_humidity"
            )
        return self


class DrugResponse(BaseModel):
    """Response shape.  Deliberately not derived from ``DrugCreate`` so that
    stricter *input* validation can never make previously stored rows
    unserializable."""

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

    description: str | None = None
    expiry_period_days: int | None = None

    fabric_asset_id: str | None = None
    last_fabric_transaction_id: str | None = None

    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
