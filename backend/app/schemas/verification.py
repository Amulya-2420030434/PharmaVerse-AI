from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class VerificationRequest(BaseModel):
    qr_id: str | None = None
    rfid_id: str | None = None
    batch_id: str | None = None
    drug_id: str | None = None

    @field_validator("qr_id", "rfid_id", "batch_id", "drug_id")
    @classmethod
    def strip_identifier(cls, value: str | None) -> str | None:
        # Surrounding whitespace is never part of a public identifier.
        # A blank value is treated as "not supplied".
        if value is None:
            return None
        stripped = value.strip()
        if len(stripped) > 100:
            raise ValueError("identifiers must be at most 100 characters")
        return stripped or None

    @model_validator(mode="after")
    def require_identifier(self):
        if not any(
            (self.qr_id, self.rfid_id, self.batch_id, self.drug_id)
        ):
            raise ValueError("At least one identifier must be supplied")
        return self


class VerificationResponse(BaseModel):
    verification_status: str
    message: str
    qr_id: str | None = None
    rfid_id: str | None = None
    batch_id: str | None = None
    drug_id: str | None = None
    batch_status: str | None = None
    expiry_date: date | None = None
    checks_performed: list[str]
    # Additive fields: existing clients can continue consuming the legacy
    # verification_status while newer clients can distinguish its evidence.
    database_status: str | None = None
    blockchain_status: str | None = None

    model_config = ConfigDict(from_attributes=True)
