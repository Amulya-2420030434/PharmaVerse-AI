from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.roles import ROLES


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str
    organization: str | None = None
    full_name: str | None = None


class UserCreate(UserBase):
    username: str = Field(min_length=1, max_length=100)
    organization: str | None = Field(default=None, max_length=255)
    # 72 bytes is bcrypt's hard input limit; longer values would be silently
    # truncated by some bcrypt builds and rejected by others.
    password: str = Field(min_length=8, max_length=72)

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("username must not be blank")
        return stripped

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in ROLES:
            raise ValueError("role must be one of: " + ", ".join(ROLES))
        return normalized


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    status: str = "APPROVED"
    auth_provider: str = "local"
    # Response serialization accepts the seeded reserved-domain demo emails
    # (e.g. *.local) that EmailStr rejects. Input validation (UserCreate)
    # remains strict via UserBase.email: EmailStr.
    email: str

    model_config = ConfigDict(from_attributes=True)
