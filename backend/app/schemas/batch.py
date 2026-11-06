from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import PublicId


class BatchCreate(BaseModel):
    batch_id: PublicId
    # Public drug identifier (Drug.drug_id), NOT the database UUID.
    drug_id: PublicId
    manufacturing_date: date
    expiry_date: date
    quantity: int = Field(gt=0)
    status: str = Field(default="ACTIVE", min_length=1, max_length=50)

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("status must not be blank")
        return normalized


class BatchResponse(BaseModel):
    id: UUID
    batch_id: str
    drug_id: UUID
    manufacturing_date: date
    expiry_date: date
    quantity: int
    status: str
    fabric_asset_id: str | None = None
    last_fabric_transaction_id: str | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
