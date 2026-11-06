"""Comprehensive tests for the PharmaVerse AI authentication, OTP, and approval workflow."""

import pytest
from sqlalchemy.orm import Session

from app.core.roles import ADMIN, DISTRIBUTOR, PHARMACY, REGULATOR
from app.models.email_otp import EmailOTP
from app.models.user import User
from app.services.auth_service import hash_password


def test_otp_send_and_verify_flow(client, db_session: Session):
    """User requests an OTP, receives it, and verifies it to obtain a short-lived verification token."""
    email = "applicant@testpharm.org"

    # 1. Send OTP
    resp_send = client.post(
        "/api/auth/otp/send",
        json={"email": email, "purpose": "registration"},
    )
    assert resp_send.status_code == 200
    assert resp_send.json()["success"] is True
    # Crucial security check: OTP must NEVER appear in the response payload!
    assert "otp" not in resp_send.text.lower() or "verification code" in resp_send.text.lower()

    # Retrieve OTP directly from DB for verification testing
    otp_entry = (
        db_session.query(EmailOTP)
        .filter(EmailOTP.email == email, EmailOTP.purpose == "registration")
        .first()
    )
    assert otp_entry is not None
    assert otp_entry.is_used is False
    # OTP is stored hashed, not plaintext
    assert len(otp_entry.otp_hash) == 64

    # 2. Try wrong OTP
    resp_bad = client.post(
        "/api/auth/otp/verify",
        json={"email": email, "otp": "000000", "purpose": "registration"},
    )
    assert resp_bad.status_code == 400

    # 3. Requesting immediately again hits rate-limit cooldown
    resp_rate = client.post(
        "/api/auth/otp/send",
        json={"email": email, "purpose": "registration"},
    )
    assert resp_rate.status_code == 429
    assert resp_rate.json()["error"]["code"] == "VALIDATION_ERROR" or "wait" in resp_rate.text.lower()


def test_email_registration_and_admin_approval_lifecycle(client, db_session: Session):
    """Full lifecycle: Send OTP -> Verify -> Register with PENDING status -> Blocked from login -> Admin approves -> Login succeeds."""
    email = "pharmacist@cityrx.com"

    # Step 1: Send OTP
    client.post("/api/auth/otp/send", json={"email": email, "purpose": "registration"})
    otp_record = db_session.query(EmailOTP).filter(EmailOTP.email == email).first()

    # Step 2: In test fixture, generate verification token
    from app.api.routes.auth import _create_ephemeral_token
    verification_token = _create_ephemeral_token(
        {"sub": email, "purpose": "email_verified"}, expires_minutes=15
    )

    # Step 3: Register account (Option 1: Email)
    reg_resp = client.post(
        "/api/auth/register/email",
        json={
            "verification_token": verification_token,
            "username": "city_pharmacist",
            "full_name": "Dr. Sarah Connor",
            "organization": "City Rx Care",
            "requested_role": "PHARMACY",
            "password": "PharmacistPass2026!",
            "confirm_password": "PharmacistPass2026!",
        },
    )
    assert reg_resp.status_code == 201
    data = reg_resp.json()
    assert data["success"] is True
    assert data["status"] == "PENDING"
    user_id = data["user_id"]

    # Step 4: User attempts to sign in while PENDING -> MUST be blocked with HTTP 403
    login_pending = client.post(
        "/api/auth/login",
        data={"username": email, "password": "PharmacistPass2026!"},
    )
    assert login_pending.status_code == 403
    assert "pending administrator approval" in login_pending.json()["error"]["message"].lower()

    # Also blocked when using username handle
    login_pending_user = client.post(
        "/api/auth/login",
        data={"username": "city_pharmacist", "password": "PharmacistPass2026!"},
    )
    assert login_pending_user.status_code == 403

    # Step 5: Admin reviews registration requests
    # Create an admin user to perform approval
    admin = User(
        username="superadmin",
        email="superadmin@pharmaverse.local",
        password_hash=hash_password("SuperAdminPass!"),
        role="ADMIN",
        status="APPROVED",
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    admin_token = client.post(
        "/api/auth/login",
        data={"username": "superadmin@pharmaverse.local", "password": "SuperAdminPass!"},
    ).json()["access_token"]

    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin lists pending requests
    pending_list = client.get("/api/admin/registration-requests?status_filter=PENDING", headers=admin_headers)
    assert pending_list.status_code == 200
    pending_users = pending_list.json()
    assert any(u["id"] == user_id for u in pending_users)

    # Admin approves user
    approve_resp = client.post(
        f"/api/admin/registration-requests/{user_id}/approve",
        headers=admin_headers,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED"

    # Step 6: User signs in with Email + Password now that they are APPROVED -> MUST succeed!
    login_approved = client.post(
        "/api/auth/login",
        data={"username": email, "password": "PharmacistPass2026!"},
    )
    assert login_approved.status_code == 200
    assert "access_token" in login_approved.json()


def test_public_registration_cannot_request_privileged_roles(client):
    """Public registration is strictly prohibited from claiming ADMIN or REGULATOR."""
    from app.api.routes.auth import _create_ephemeral_token

    v_token = _create_ephemeral_token(
        {"sub": "hacker@test.com", "purpose": "email_verified"}
    )

    # Attempt ADMIN registration
    resp_admin = client.post(
        "/api/auth/register/email",
        json={
            "verification_token": v_token,
            "username": "fake_admin",
            "requested_role": "ADMIN",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
    )
    assert resp_admin.status_code == 403

    # Attempt REGULATOR registration
    resp_regulator = client.post(
        "/api/auth/register/email",
        json={
            "verification_token": v_token,
            "username": "fake_regulator",
            "requested_role": "REGULATOR",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
    )
    assert resp_regulator.status_code == 403


def test_google_registration_and_rejection_flow(client, db_session: Session, monkeypatch):
    """Google registration verifies token, sets PENDING, and respects rejection by ADMIN."""
    from app.services.google_auth_service import google_auth_service

    google_identity = {
        "google_id": "google-uid-12345",
        "email": "supplier@distrocorp.com",
        "name": "Bob Distributor",
        "email_verified": True,
    }
    monkeypatch.setattr(google_auth_service, "verify_id_token", lambda token: google_identity)

    # Step 1: Verify Google Token on backend
    verify_resp = client.post(
        "/api/auth/google/verify",
        json={"id_token": "test-provider-token"},
    )
    assert verify_resp.status_code == 200
    data = verify_resp.json()
    assert data["success"] is True
    assert data["email"] == "supplier@distrocorp.com"
    reg_token = data["registration_token"]

    # Step 2: Complete Google registration
    reg_resp = client.post(
        "/api/auth/register/google",
        json={
            "registration_token": reg_token,
            "username": "bob_distro",
            "organization": "DistroCorp Global",
            "requested_role": "DISTRIBUTOR",
            "password": "DistroPassword2026!",
        },
    )
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["user_id"]
    assert reg_resp.json()["status"] == "PENDING"

    # Step 3: Admin rejects registration
    admin = User(
        username="admin2",
        email="admin2@pharmaverse.local",
        password_hash=hash_password("AdminPass!"),
        role="ADMIN",
        status="APPROVED",
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    admin_token = client.post(
        "/api/auth/login",
        data={"username": "admin2@pharmaverse.local", "password": "AdminPass!"},
    ).json()["access_token"]

    reject_resp = client.post(
        f"/api/admin/registration-requests/{user_id}/reject",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "REJECTED"

    # Step 4: Rejected user attempts to sign in -> Blocked with HTTP 403
    login_rejected = client.post(
        "/api/auth/login",
        data={"username": "supplier@distrocorp.com", "password": "DistroPassword2026!"},
    )
    assert login_rejected.status_code == 403
    assert "rejected" in login_rejected.json()["error"]["message"].lower()


def test_existing_approved_users_login_seamlessly(client, db_session: Session):
    """Verify that existing approved accounts continue to sign in with email or username without disruption."""
    existing_user = User(
        username="demo-transporter-corp",
        email="transporter@pharmaverse.local",
        password_hash=hash_password("TransporterPass!"),
        role="TRANSPORTER",
        status="APPROVED",
        is_active=True,
    )
    db_session.add(existing_user)
    db_session.commit()

    # Sign in with email
    resp_email = client.post(
        "/api/auth/login",
        data={"username": "transporter@pharmaverse.local", "password": "TransporterPass!"},
    )
    assert resp_email.status_code == 200
    assert "access_token" in resp_email.json()

    # Sign in with username
    resp_user = client.post(
        "/api/auth/login",
        data={"username": "demo-transporter-corp", "password": "TransporterPass!"},
    )
    assert resp_user.status_code == 200
    assert "access_token" in resp_user.json()

from scripts.bootstrap_admin import bootstrap_admin
from app.services.auth_service import create_access_token


def test_anonymous_legacy_registration_cannot_create_approved_accounts(client, db_session: Session):
    """Anonymous callers cannot create pre-approved accounts via legacy /register."""
    body = {
        "username": "attacker",
        "email": "attacker@darkweb.org",
        "password": "Password123!",
        "role": "PHARMACY",
    }
    # 1. Anonymous caller receives 401 Unauthorized
    resp_anon = client.post("/api/auth/register", json=body)
    assert resp_anon.status_code == 401

    # 2. Non-admin caller receives 403 Forbidden
    pharmacy_user = User(
        username="normal_pharmacy",
        email="pharmacy@normal.org",
        password_hash=hash_password("Pass12345!"),
        role="PHARMACY",
        status="APPROVED",
        is_active=True,
    )
    db_session.add(pharmacy_user)
    db_session.commit()
    pharmacy_token = create_access_token(user_id=str(pharmacy_user.id), role="PHARMACY")

    resp_non_admin = client.post(
        "/api/auth/register",
        headers={"Authorization": f"Bearer {pharmacy_token}"},
        json=body,
    )
    assert resp_non_admin.status_code == 403

    # 3. Authenticated ADMIN can create accounts
    admin_user = User(
        username="super_admin",
        email="admin@pharmaverse.local",
        password_hash=hash_password("AdminPass123!"),
        role="ADMIN",
        status="APPROVED",
        is_active=True,
    )
    db_session.add(admin_user)
    db_session.commit()
    admin_token = create_access_token(user_id=str(admin_user.id), role="ADMIN")

    resp_admin = client.post(
        "/api/auth/register",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=body,
    )
    assert resp_admin.status_code == 201
    assert resp_admin.json()["username"] == "attacker"


def test_pending_and_rejected_users_cannot_authenticate_with_jwt(client, db_session: Session):
    """Users in PENDING or REJECTED status cannot authenticate against protected endpoints even with a JWT."""
    pending_user = User(
        username="pending_tester",
        email="pending@test.com",
        password_hash=hash_password("Password123!"),
        role="PHARMACY",
        status="PENDING",
        is_active=True,
    )
    rejected_user = User(
        username="rejected_tester",
        email="rejected@test.com",
        password_hash=hash_password("Password123!"),
        role="DISTRIBUTOR",
        status="REJECTED",
        is_active=False,
    )
    db_session.add_all([pending_user, rejected_user])
    db_session.commit()

    token_pending = create_access_token(user_id=str(pending_user.id), role="PHARMACY")
    token_rejected = create_access_token(user_id=str(rejected_user.id), role="DISTRIBUTOR")

    # Protected endpoint /api/auth/me rejects pending user
    resp_pending = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token_pending}"},
    )
    assert resp_pending.status_code == 401

    # Protected endpoint /api/auth/me rejects rejected user
    resp_rejected = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token_rejected}"},
    )
    assert resp_rejected.status_code == 401


def test_rejected_users_are_deactivated(client, db_session: Session):
    """When an administrator rejects a registration request, user.is_active is set to False."""
    applicant = User(
        username="suspicious_entity",
        email="suspicious@untrusted.org",
        password_hash=hash_password("Password123!"),
        role="PHARMACY",
        status="PENDING",
        is_active=True,
    )
    admin = User(
        username="compliance_lead",
        email="compliance@pharmaverse.local",
        password_hash=hash_password("CompliancePass!"),
        role="ADMIN",
        status="APPROVED",
        is_active=True,
    )
    db_session.add_all([applicant, admin])
    db_session.commit()

    admin_token = create_access_token(user_id=str(admin.id), role="ADMIN")
    reject_resp = client.post(
        f"/api/admin/registration-requests/{applicant.id}/reject",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reject_resp.status_code == 200

    # Verify user state in DB
    refreshed_user = db_session.query(User).filter(User.id == applicant.id).first()
    assert refreshed_user.status == "REJECTED"
    assert refreshed_user.is_active is False


def test_cli_bootstrap_refuses_duplicate_admin(db_session: Session):
    """The CLI bootstrap script creates the first administrator, but strictly refuses any subsequent creation."""
    # Ensure no admin exists initially in test session
    db_session.query(User).filter(User.role == "ADMIN").delete()
    db_session.commit()

    # Step 1: Initial creation succeeds
    result1 = bootstrap_admin(
        username="founding_admin",
        email="founder@pharmaverse.local",
        password="FounderPassword2026!",
        organization="PharmaVerse Core",
        db=db_session,
    )
    assert result1 is True

    # Step 2: Attempting to create a second initial admin is refused
    result2 = bootstrap_admin(
        username="second_admin",
        email="second@pharmaverse.local",
        password="SecondPassword2026!",
        organization="Another Org",
        db=db_session,
    )
    assert result2 is False



from app.schemas.auth import GoogleLoginRequest
from app.api.routes.auth import login_with_google
from fastapi import HTTPException


def test_google_login_approved_regular_user_succeeds(db_session: Session, monkeypatch):
    """Approved Google-linked user signs in by verified Google subject."""
    from app.services.google_auth_service import google_auth_service

    user = User(
        username="distributor_lead",
        email="distributor@testpharma.org",
        full_name="Distributor Lead",
        password_hash=hash_password("Password123!"),
        role="DISTRIBUTOR",
        google_id="gid-12345",
        status="APPROVED",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    monkeypatch.setattr(
        google_auth_service,
        "verify_id_token",
        lambda token: {
            "google_id": "gid-12345",
            "email": user.email,
            "name": "Distributor Lead",
            "email_verified": True,
        },
    )
    req = GoogleLoginRequest(id_token="provider-issued-test-token")
    res = login_with_google(req, db_session)
    assert res.success is True
    assert res.existing_user is True
    assert res.access_token is not None

    # Google subject matches the persisted identity; no email-based linking occurs.
    db_session.refresh(user)
    assert user.google_id == "gid-12345"


def test_google_login_refuses_email_only_match_for_admin(db_session: Session, monkeypatch):
    """A matching email alone never links Google to an existing ADMIN account."""
    from app.services.google_auth_service import google_auth_service

    admin = User(
        username="security_admin",
        email="admin@pharmaverse.local",
        password_hash=hash_password("AdminSecretPass2026!"),
        role="ADMIN",
        status="APPROVED",
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    monkeypatch.setattr(
        google_auth_service,
        "verify_id_token",
        lambda token: {
            "google_id": "gid-admin-fake",
            "email": admin.email,
            "name": "Fake Admin Attempt",
            "email_verified": True,
        },
    )
    req = GoogleLoginRequest(id_token="provider-issued-test-token")
    try:
        login_with_google(req, db_session)
        assert False, "Expected 403 Forbidden for admin auto-link attempt"
    except HTTPException as exc:
        assert exc.status_code == 409
        assert "email and password" in exc.detail.lower()

    # Verify admin google_id was NOT modified
    db_session.refresh(admin)
    assert admin.google_id is None


def test_google_login_never_links_regular_account_by_email(db_session: Session, monkeypatch):
    """Regular local accounts also require explicit Google subject linkage."""
    from app.services.google_auth_service import google_auth_service

    user = User(
        username="local_pharmacy",
        email="local.pharmacy@example.com",
        password_hash=hash_password("LocalPassword!123"),
        role="PHARMACY",
        status="APPROVED",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    monkeypatch.setattr(
        google_auth_service,
        "verify_id_token",
        lambda token: {
            "google_id": "different-google-subject",
            "email": user.email,
            "name": "Local Pharmacy",
            "email_verified": True,
        },
    )

    try:
        login_with_google(GoogleLoginRequest(id_token="provider-issued-test-token"), db_session)
        assert False, "Email equality must not link a Google identity"
    except HTTPException as exc:
        assert exc.status_code == 409

    db_session.refresh(user)
    assert user.google_id is None


def test_google_login_unregistered_user_returns_registration_token(db_session: Session, monkeypatch):
    """Unregistered Google identity returns existing_user=False and a registration token to complete role selection."""
    from app.services.google_auth_service import google_auth_service

    new_email = "newcomer@hospital-chain.org"
    monkeypatch.setattr(
        google_auth_service,
        "verify_id_token",
        lambda token: {
            "google_id": "gid-new-999",
            "email": new_email,
            "name": "New Pharmacist",
            "email_verified": True,
        },
    )
    req = GoogleLoginRequest(id_token="provider-issued-test-token")

    res = login_with_google(req, db_session)
    assert res.success is False
    assert res.existing_user is False
    assert res.registration_token is not None
    assert res.email == new_email
