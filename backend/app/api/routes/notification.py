import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.database.connection import get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationActionResponse,
    NotificationCountResponse,
    NotificationResponse,
)
from app.services.notification_service import (
    get_notification_counts,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse])
def get_notifications(
    status_filter: Optional[str] = Query(None, description="Filter by status: PENDING, APPROVED, REJECTED, or ALL"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    """Retrieve notifications. ADMIN only."""
    return list_notifications(db, status_filter=status_filter, limit=limit)


@router.get("/count", response_model=NotificationCountResponse)
def get_counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    """Get count of pending approvals, unread, and total notifications for badge display. ADMIN only."""
    return get_notification_counts(db)


@router.get("/pending", response_model=list[NotificationResponse])
def get_pending_notifications(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    """Retrieve only pending approval notifications. ADMIN only."""
    return list_notifications(db, status_filter="PENDING", limit=limit)


@router.post("/{notification_id}/read", response_model=NotificationActionResponse)
def mark_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    """Mark a notification as read. ADMIN only."""
    try:
        notif_uuid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid notification ID format",
        )

    success = mark_notification_read(db, notif_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return {
        "success": True,
        "message": "Notification marked as read",
        "notification_id": str(notif_uuid),
    }


@router.post("/read-all", response_model=NotificationActionResponse)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    """Mark all unread notifications as read. ADMIN only."""
    count = mark_all_notifications_read(db)
    return {
        "success": True,
        "message": f"Marked {count} notifications as read",
    }

