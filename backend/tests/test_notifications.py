import os

os.environ["DEBUG"] = "true"

import uuid
from app.api.routes.auth import _create_ephemeral_token
from app.models.notification import Notification
from app.models.user import User


def test_notifications_require_authentication(client):
    response = client.get("/api/notifications")
    assert response.status_code == 401

    response = client.get("/api/notifications/count")
    assert response.status_code == 401


def test_notifications_forbidden_for_non_admin_roles(client, make_user):
    non_admin_roles = ["MANUFACTURER", "DISTRIBUTOR", "PHARMACY", "TRANSPORTER", "REGULATOR", "VIEWER"]
    for role in non_admin_roles:
        _, headers = make_user(role, username=f"user_{role.lower()}")
        response = client.get("/api/notifications", headers=headers)
        assert response.status_code == 403, f"Expected 403 for role {role}, got {response.status_code}"

        count_response = client.get("/api/notifications/count", headers=headers)
        assert count_response.status_code == 403, f"Expected 403 for count with role {role}"

        read_response = client.post(f"/api/notifications/{uuid.uuid4()}/read", headers=headers)
        assert read_response.status_code == 403, f"Expected 403 for mark read with role {role}"

        alias_response = client.get("/api/admin/notifications", headers=headers)
        assert alias_response.status_code == 403, f"Expected 403 for alias with role {role}"


def test_admin_can_access_notifications(client, make_user):
    _, headers = make_user("ADMIN", username="admin_notif_tester")
    response = client.get("/api/notifications", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    count_response = client.get("/api/notifications/count", headers=headers)
    assert count_response.status_code == 200
    counts = count_response.json()
    assert "pending" in counts
    assert "unread" in counts
    assert "total" in counts


def test_email_registration_creates_pending_approval_notification(client, db_session, make_user):
    _, admin_headers = make_user("ADMIN", username="admin_reviewer_1")

    # Generate verified token
    token = _create_ephemeral_token({"sub": "applicant.email@example.com", "purpose": "email_verified"})

    # Register via email
    reg_resp = client.post(
        "/api/auth/register/email",
        json={
            "verification_token": token,
            "username": "applicant_email_user",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "requested_role": "MANUFACTURER",
            "full_name": "Applicant Alice",
            "organization": "Alice Pharma",
        },
    )
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["user_id"]

    # Check notification via Admin API
    notif_resp = client.get("/api/notifications", headers=admin_headers)
    assert notif_resp.status_code == 200
    notifs = notif_resp.json()
    assert len(notifs) >= 1

    app_notif = next((n for n in notifs if n["user_id"] == user_id), None)
    assert app_notif is not None
    assert app_notif["applicant_name"] == "Applicant Alice"
    assert app_notif["applicant_email"] == "applicant.email@example.com"
    assert app_notif["applicant_role"] == "MANUFACTURER"
    assert app_notif["status"] == "PENDING"
    assert app_notif["is_read"] is False
    assert "password" not in str(app_notif).lower()

    # Check counts
    counts = client.get("/api/notifications/count", headers=admin_headers).json()
    assert counts["pending"] >= 1


def test_google_registration_creates_pending_approval_notification(client, db_session, make_user):
    _, admin_headers = make_user("ADMIN", username="admin_reviewer_2")

    google_token = _create_ephemeral_token(
        {"sub": "google-sub-applicant-999", "email": "google.applicant@example.com", "name": "Google Bob", "purpose": "google_verified"}
    )

    reg_resp = client.post(
        "/api/auth/register/google",
        json={
            "registration_token": google_token,
            "username": "applicant_google_user",
            "password": "SecurePassword123!",
            "requested_role": "DISTRIBUTOR",
            "full_name": "Google Bob",
            "organization": "Bob Logistics",
        },
    )
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["user_id"]

    # Check notification via Admin API
    notif_resp = client.get("/api/notifications", headers=admin_headers)
    assert notif_resp.status_code == 200
    notifs = notif_resp.json()

    app_notif = next((n for n in notifs if n["user_id"] == user_id), None)
    assert app_notif is not None
    assert app_notif["applicant_name"] == "Google Bob"
    assert app_notif["applicant_email"] == "google.applicant@example.com"
    assert app_notif["applicant_role"] == "DISTRIBUTOR"
    assert app_notif["status"] == "PENDING"
    assert app_notif["is_read"] is False


def test_avoid_duplicate_notifications_for_same_user(client, db_session, make_user):
    from app.services.notification_service import create_pending_approval_notification
    from app.models.user import User

    test_user = User(
        username="dupe_test_user",
        email="dupe@example.com",
        password_hash="fake",
        role="PHARMACY",
        status="PENDING",
        auth_provider="local",
        is_active=True,
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    notif1 = create_pending_approval_notification(db_session, test_user)
    notif2 = create_pending_approval_notification(db_session, test_user)

    assert notif1.id == notif2.id

    all_for_user = db_session.query(Notification).filter(Notification.user_id == test_user.id).all()
    assert len(all_for_user) == 1


def test_approval_updates_notification_status_and_badge_count(client, db_session, make_user):
    _, admin_headers = make_user("ADMIN", username="admin_reviewer_3")

    from app.services.notification_service import create_pending_approval_notification
    pending_user = User(
        username="user_to_approve",
        email="approve.me@example.com",
        password_hash="fake",
        role="TRANSPORTER",
        status="PENDING",
        auth_provider="local",
        is_active=True,
    )
    db_session.add(pending_user)
    db_session.commit()
    db_session.refresh(pending_user)
    create_pending_approval_notification(db_session, pending_user)

    # Initial pending count
    before_counts = client.get("/api/notifications/count", headers=admin_headers).json()
    initial_pending = before_counts["pending"]
    assert initial_pending >= 1

    # Approve the user
    approve_resp = client.post(f"/api/admin/registration-requests/{pending_user.id}/approve", headers=admin_headers)
    assert approve_resp.status_code == 200

    # Notification status should now be APPROVED
    notif = db_session.query(Notification).filter(Notification.user_id == pending_user.id).first()
    assert notif.status == "APPROVED"
    assert notif.is_read is True
    assert notif.handled_at is not None

    # Pending count should decrease by 1
    after_counts = client.get("/api/notifications/count", headers=admin_headers).json()
    assert after_counts["pending"] == initial_pending - 1


def test_rejection_updates_notification_status_and_badge_count(client, db_session, make_user):
    _, admin_headers = make_user("ADMIN", username="admin_reviewer_4")

    from app.services.notification_service import create_pending_approval_notification
    pending_user = User(
        username="user_to_reject",
        email="reject.me@example.com",
        password_hash="fake",
        role="PHARMACY",
        status="PENDING",
        auth_provider="local",
        is_active=True,
    )
    db_session.add(pending_user)
    db_session.commit()
    db_session.refresh(pending_user)
    create_pending_approval_notification(db_session, pending_user)

    before_counts = client.get("/api/notifications/count", headers=admin_headers).json()
    initial_pending = before_counts["pending"]

    # Reject the user
    reject_resp = client.post(f"/api/admin/registration-requests/{pending_user.id}/reject", headers=admin_headers)
    assert reject_resp.status_code == 200

    # Notification status should now be REJECTED
    notif = db_session.query(Notification).filter(Notification.user_id == pending_user.id).first()
    assert notif.status == "REJECTED"
    assert notif.is_read is True
    assert notif.handled_at is not None

    # Pending count should decrease by 1
    after_counts = client.get("/api/notifications/count", headers=admin_headers).json()
    assert after_counts["pending"] == initial_pending - 1


def test_mark_notification_as_read(client, db_session, make_user):
    _, admin_headers = make_user("ADMIN", username="admin_reviewer_5")

    notif = Notification(
        title="Test Notification",
        message="A test message",
        type="PENDING_APPROVAL",
        status="PENDING",
        is_read=False,
    )
    db_session.add(notif)
    db_session.commit()
    db_session.refresh(notif)

    read_resp = client.post(f"/api/notifications/{notif.id}/read", headers=admin_headers)
    assert read_resp.status_code == 200

    db_session.refresh(notif)
    assert notif.is_read is True

    # Mark all read
    all_read_resp = client.post("/api/notifications/read-all", headers=admin_headers)
    assert all_read_resp.status_code == 200
