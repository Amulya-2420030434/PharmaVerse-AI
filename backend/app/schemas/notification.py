import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: uuid.UUID | str
    user_id: uuid.UUID | str | None = None
    type: str
    title: str
    message: str
    applicant_name: str | None = None
    applicant_email: str | None = None
    applicant_role: str | None = None
    status: str
    is_read: bool
    created_at: datetime
    handled_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationCountResponse(BaseModel):
    pending: int
    unread: int
    total: int


class NotificationActionResponse(BaseModel):
    success: bool
    message: str
    notification_id: str | None = None

