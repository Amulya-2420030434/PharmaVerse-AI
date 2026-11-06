import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger(__name__)


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_pending_approval_notification(db: Session, user: User) -> Notification | None:
    """Create a persistent notification for admin when a new user registers with PENDING status.
    
    Prevents duplicate notifications for the same pending registration.
    """
    if not user or not user.id:
        return None

    # Check if a pending approval notification already exists for this user
    existing = (
        db.query(Notification)
        .filter(
            Notification.user_id == user.id,
            Notification.type == "PENDING_APPROVAL",
            Notification.status == "PENDING",
        )
        .first()
    )
    if existing:
        return existing

    display_name = user.full_name or user.username or user.email
    auth_label = user.auth_provider.capitalize() if user.auth_provider else "Local"
    role_label = user.role or "UNASSIGNED"

    notification = Notification(
        user_id=user.id,
        type="PENDING_APPROVAL",
        title="Pending Account Approval",
        message=(
            f"New {auth_label} registration for {display_name} "
            f"({user.email}) requesting role {role_label}."
        ),
        applicant_name=display_name,
        applicant_email=user.email,
        applicant_role=role_label,
        status="PENDING",
        is_read=False,
        created_at=_utc_now_naive(),
    )

    db.add(notification)
    try:
        db.commit()
        db.refresh(notification)
    except Exception as exc:
        db.rollback()
        logger.warning(
            f"Failed to persist admin notification for user {user.id}: {exc}"
        )
        return None

    return notification


def update_notification_on_approval_decision(
    db: Session, user_id: uuid.UUID, decision: str
) -> int:
    """Update all pending approval notifications when an admin approves or rejects a registration request.
    
    decision: 'APPROVED' or 'REJECTED'
    """
    notifications = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.type == "PENDING_APPROVAL",
            Notification.status == "PENDING",
        )
        .all()
    )
    updated_count = 0
    now = _utc_now_naive()
    for notif in notifications:
        notif.status = decision.upper()
        notif.is_read = True
        notif.handled_at = now
        updated_count += 1

    if updated_count > 0:
        db.commit()

    return updated_count


def get_notification_counts(db: Session) -> dict[str, int]:
    """Return counts for the admin badge: pending approvals, unread, and total."""
    pending_count = (
        db.query(Notification)
        .filter(
            Notification.type == "PENDING_APPROVAL",
            Notification.status == "PENDING",
        )
        .count()
    )
    unread_count = (
        db.query(Notification)
        .filter(Notification.is_read == False)  # noqa: E712
        .count()
    )
    total_count = db.query(Notification).count()

    return {
        "pending": pending_count,
        "unread": unread_count,
        "total": total_count,
    }


def list_notifications(
    db: Session,
    status_filter: str | None = None,
    limit: int = 50,
) -> list[Notification]:
    """Retrieve notifications ordered by creation date descending."""
    query = db.query(Notification)
    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(Notification.status == status_filter.upper())

    return query.order_by(Notification.created_at.desc()).limit(limit).all()


def mark_notification_read(db: Session, notification_id: uuid.UUID) -> bool:
    """Mark a single notification as read."""
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        return False
    notif.is_read = True
    db.commit()
    return True


def mark_all_notifications_read(db: Session) -> int:
    """Mark all unread notifications as read."""
    count = (
        db.query(Notification)
        .filter(Notification.is_read == False)  # noqa: E712
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    return count

