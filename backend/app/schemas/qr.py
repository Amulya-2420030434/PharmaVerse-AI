from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import PublicId, normalize_tag_status


class QRCreate(BaseModel):
    qr_id: PublicId
    # Public batch identifier (Batch.batch_id), NOT the database UUID.
    batch_id: PublicId
    encoded_value: str = Field(min_length=1, max_length=500)
    status: str = "ACTIVE"

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return normalize_tag_status(value)


class QRResponse(BaseModel):
    id: UUID
    qr_id: str
    batch_id: UUID
    encoded_value: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
