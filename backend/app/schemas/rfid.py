from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import PublicId, normalize_tag_status


class RFIDCreate(BaseModel):
    rfid_id: PublicId
    # Public batch identifier (Batch.batch_id), NOT the database UUID.
    batch_id: PublicId
    tag_value: str = Field(min_length=1, max_length=255)
    status: str = "ACTIVE"

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return normalize_tag_status(value)


class RFIDResponse(BaseModel):
    id: UUID
    rfid_id: str
    batch_id: UUID
    tag_value: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
