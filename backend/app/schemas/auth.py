from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str | None = None
    role: str
    organization: str | None = None
    status: str | None = "APPROVED"
    auth_provider: str | None = "local"
    two_factor_enabled: bool = False
    has_google_linked: bool = False

    model_config = ConfigDict(from_attributes=True)


class EmailLinkRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+$")


class EmailLinkConfirmRequest(BaseModel):
    token: str = Field(..., min_length=32, max_length=128)


class PasswordLinkResetRequest(BaseModel):
    token: str = Field(..., min_length=32, max_length=128)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)


class TwoFactorVerifyRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    otp: str = Field(..., min_length=6, max_length=6)


class TwoFactorSettingsRequest(BaseModel):
    enabled: bool


class LoginResponse(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    two_factor_required: bool = False
    email: str | None = None


class SendOTPRequest(BaseModel):
    email: EmailStr
    purpose: str = "registration"


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=10)
    purpose: str = "registration"


class VerifyOTPResponse(BaseModel):
    success: bool
    verification_token: str
    message: str


class EmailRegisterRequest(BaseModel):
    verification_token: str
    username: str = Field(..., min_length=3, max_length=100)
    full_name: str | None = None
    organization: str | None = None
    requested_role: str
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)


class GoogleVerifyRequest(BaseModel):
    id_token: str


class GoogleVerifyResponse(BaseModel):
    success: bool
    email: str
    name: str
    registration_token: str
    existing_user: bool = False
    status: str | None = None
    auth_provider: str | None = None


class GoogleLoginRequest(BaseModel):
    id_token: str


class GoogleLinkRequest(BaseModel):
    id_token: str


class GoogleLoginResponse(BaseModel):
    success: bool
    access_token: str | None = None
    token_type: str = "bearer"
    two_factor_required: bool = False
    existing_user: bool = True
    status: str | None = None
    email: str | None = None
    name: str | None = None
    role: str | None = None
    user_id: str | None = None
    registration_token: str | None = None
    message: str | None = None


class GoogleRegisterRequest(BaseModel):
    registration_token: str
    username: str = Field(..., min_length=3, max_length=100)
    full_name: str | None = None
    organization: str | None = None
    requested_role: str
    password: str | None = Field(default=None, min_length=8)


class PasswordResetRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=10)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)


class RegistrationRequestItem(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str | None = None
    organization: str | None = None
    role: str
    status: str
    auth_provider: str
    created_at: datetime
