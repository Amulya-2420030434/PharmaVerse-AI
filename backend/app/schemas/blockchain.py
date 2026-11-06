from typing import Any

from pydantic import BaseModel, Field, model_validator


class BlockchainVerifyRequest(BaseModel):
    batch_id: str = Field(min_length=1, max_length=100)
    qr_id: str = Field(min_length=1, max_length=100)
    rfid_id: str = Field(min_length=1, max_length=100)


class BlockchainDrugWrite(BaseModel):
    drug_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    strength: str = Field(min_length=1, max_length=100)
    manufacturer: str = Field(min_length=1, max_length=255)


class BlockchainBatchWrite(BaseModel):
    batch_id: str = Field(min_length=1, max_length=100)
    drug_id: str = Field(min_length=1, max_length=100)
    manufacturer: str = Field(min_length=1, max_length=255)
    quantity: int = Field(gt=0)
    manufactured_date: str = Field(min_length=1, max_length=50)
    expiry_date: str = Field(min_length=1, max_length=50)
    qr_id: str | None = Field(default=None, min_length=1, max_length=100)
    rfid_id: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def require_identity_pair(self):
        if (self.qr_id is None) != (self.rfid_id is None):
            raise ValueError("qr_id and rfid_id must be supplied together")
        return self


class BlockchainIdentityWrite(BaseModel):
    batch_id: str = Field(min_length=1, max_length=100)
    qr_id: str = Field(min_length=1, max_length=100)
    rfid_id: str = Field(min_length=1, max_length=100)


class BlockchainIoTWrite(BaseModel):
    batch_id: str = Field(min_length=1, max_length=100)
    shipment_id: str = Field(min_length=1, max_length=100)
    temperature: float
    humidity: float
    latitude: float
    longitude: float
    movement: str = Field(min_length=1, max_length=100)
    rfid_id: str = Field(min_length=1, max_length=100)


class BlockchainAIAlertWrite(BaseModel):
    batch_id: str = Field(min_length=1, max_length=100)
    shipment_id: str = Field(min_length=1, max_length=100)
    alert_type: str = Field(min_length=1, max_length=100)
    risk_score: float = Field(ge=0, le=100)
    explanation: str = Field(min_length=1, max_length=5000)


class BlockchainFlagWrite(BaseModel):
    batch_id: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=1000)
    risk_level: str = Field(min_length=1, max_length=50)


class BlockchainShipWrite(BaseModel):
    shipment_id: str = Field(min_length=1, max_length=100)
    batch_id: str = Field(min_length=1, max_length=100)
    from_location: str = Field(min_length=1, max_length=255)
    to_location: str = Field(min_length=1, max_length=255)
    transporter: str = Field(min_length=1, max_length=255)


class BlockchainReceiveWrite(BaseModel):
    shipment_id: str = Field(min_length=1, max_length=100)
    receiver: str = Field(min_length=1, max_length=255)


class BlockchainTransferWrite(BaseModel):
    batch_id: str = Field(min_length=1, max_length=100)
    from_owner: str = Field(min_length=1, max_length=255)
    to_owner: str = Field(min_length=1, max_length=255)


class BlockchainResponse(BaseModel):
    data: Any
