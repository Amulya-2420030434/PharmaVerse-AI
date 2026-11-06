"""Direct unit tests for PharmaVerse AI auth routes, hashing, JWT, and models.

These tests invoke the route handlers directly with a SQLite in-memory database,
testing the complete database models, password verification, tokens, and approval
logic deterministically.
"""

from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.routes.auth import (
    login,
    login_with_google,
    register_email,
    register_google,
    reset_password,
    send_otp,
    verify_otp,
    verify_two_factor,
)
from app.database.connection import Base
from app.models.email_otp import EmailOTP
from app.models.user import User
from app.schemas.auth import (
    EmailRegisterRequest,
    GoogleLoginRequest,
    GoogleRegisterRequest,
    PasswordResetRequest,
    SendOTPRequest,
    TwoFactorVerifyRequest,
    VerifyOTPRequest,
)
from app.services.auth_service import hash_password, verify_password
from app.services.email_service import email_service
from app.services.google_auth_service import google_auth_service


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_password_hashing_and_verification():
    raw = "MySecurePassword!123"
    hashed = hash_password(raw)
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_login_approved_user_returns_jwt(db):
    user = User(
        username="pharm_user",
        email="pharm@example.com",
        password_hash=hash_password("ValidPassword!"),
        role="PHARMACY",
        status="APPROVED",
        is_active=True,
    )
    db.add(user)
    db.commit()

    form = OAuth2PasswordRequestForm(
        grant_type="password",
        username="pharm@example.com",
        password="ValidPassword!",
        scope="",
        client_id=None,
        client_secret=None,
    )
    resp = login(form_data=form, db=db)
    assert resp.access_token is not None
    assert resp.token_type == "bearer"
    assert resp.two_factor_required is False


def test_login_invalid_password_raises_401(db):
    user = User(
        username="pharm_user2",
        email="pharm2@example.com",
        password_hash=hash_password("ValidPassword!"),
        role="PHARMACY",
        status="APPROVED",
        is_active=True,
    )
    db.add(user)
    db.commit()

    form = OAuth2PasswordRequestForm(
        grant_type="password",
        username="pharm2@example.com",
        password="WrongPassword!",
        scope="",
        client_id=None,
        client_secret=None,
    )
    with pytest.raises(HTTPException) as exc:
        login(form_data=form, db=db)
    assert exc.value.status_code == 401
    assert "Invalid email or password" in exc.value.detail


def test_login_pending_user_raises_403(db):
    user = User(
        username="pending_user",
        email="pending@example.com",
        password_hash=hash_password("ValidPassword!"),
        role="PHARMACY",
        status="PENDING",
        is_active=True,
    )
    db.add(user)
    db.commit()

    form = OAuth2PasswordRequestForm(
        grant_type="password",
        username="pending@example.com",
        password="ValidPassword!",
        scope="",
        client_id=None,
        client_secret=None,
    )
    with pytest.raises(HTTPException) as exc:
        login(form_data=form, db=db)
    assert exc.value.status_code == 403
    assert "pending administrator approval" in exc.value.detail


def test_otp_send_verify_and_register_flow(db, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        email_service,
        "send_otp_email",
        lambda recipient_email, otp, purpose: captured.update(code=otp) or True,
    )
    email = "applicant@hospital.org"

    # 1. Send OTP
    send_resp = send_otp(SendOTPRequest(email=email, purpose="registration"), db=db)
    assert send_resp["success"] is True
    actual_code = captured["code"]

    otp_rec = db.query(EmailOTP).filter_by(email=email).first()
    assert otp_rec is not None
    assert otp_rec.is_used is False

    verify_resp = verify_otp(
        VerifyOTPRequest(email=email, otp=actual_code, purpose="registration"),
        db=db,
    )
    assert verify_resp.success is True
    vtoken = verify_resp.verification_token
    assert vtoken is not None

    # 2. Rejects registration attempting ADMIN role
    with pytest.raises(HTTPException) as exc:
        register_email(
            EmailRegisterRequest(
                verification_token=vtoken,
                username="hacker_admin",
                requested_role="ADMIN",
                password="SecurePassword!123",
                confirm_password="SecurePassword!123",
            ),
            db=db,
        )
    assert exc.value.status_code == 403

    # 3. Successful registration creates PENDING user
    reg_resp = register_email(
        EmailRegisterRequest(
            verification_token=vtoken,
            username="hospital_rep",
            full_name="Dr. Jane Hospital",
            organization="City General Hospital",
            requested_role="PHARMACY",
            password="SecurePassword!123",
            confirm_password="SecurePassword!123",
        ),
        db=db,
    )
    assert reg_resp["success"] is True

    new_user = db.query(User).filter_by(email=email).first()
    assert new_user is not None
    assert new_user.status == "PENDING"
    assert new_user.role == "PHARMACY"


def test_google_login_approved_user(db, monkeypatch):
    google_id = "google-uid-12345"
    email = "google.partner@pharma-distributor.com"
    user = User(
        username="gpartner",
        email=email,
        password_hash=hash_password("GeneratedPass!"),
        role="DISTRIBUTOR",
        status="APPROVED",
        is_active=True,
        auth_provider="google",
        google_id=google_id,
    )
    db.add(user)
    db.commit()

    monkeypatch.setattr(
        google_auth_service,
        "verify_id_token",
        lambda token: {"google_id": google_id, "email": email, "name": "Google Partner"},
    )

    resp = login_with_google(GoogleLoginRequest(id_token="valid-google-jwt"), db=db)
    assert resp.success is True
    assert resp.access_token is not None
    assert resp.existing_user is True


def test_google_login_refuses_auto_link_to_admin(db, monkeypatch):
    admin_email = "admin@pharmaverse.internal"
    admin = User(
        username="superadmin",
        email=admin_email,
        password_hash=hash_password("SuperSecret!123"),
        role="ADMIN",
        status="APPROVED",
        is_active=True,
    )
    db.add(admin)
    db.commit()

    monkeypatch.setattr(
        google_auth_service,
        "verify_id_token",
        lambda token: {"google_id": "attacker-google-id", "email": admin_email, "name": "Attacker"},
    )

    with pytest.raises(HTTPException) as exc:
        login_with_google(GoogleLoginRequest(id_token="forged-google-jwt"), db=db)
    assert exc.value.status_code in (403, 409)


def test_google_unregistered_user_returns_registration_token(db, monkeypatch):
    new_google_email = "newdoctor@hospital.net"
    google_id = "google-uid-99999"

    monkeypatch.setattr(
        google_auth_service,
        "verify_id_token",
        lambda token: {"google_id": google_id, "email": new_google_email, "name": "Dr. Smith"},
    )

    resp = login_with_google(GoogleLoginRequest(id_token="valid-new-google-jwt"), db=db)
    assert resp.success is False
    assert resp.existing_user is False
    assert resp.status == "UNREGISTERED"
    assert resp.registration_token is not None

    # Now complete registration
    reg_resp = register_google(
        GoogleRegisterRequest(
            registration_token=resp.registration_token,
            username="dr_smith",
            organization="Memorial Hospital",
            requested_role="PHARMACY",
            password="SecurePassword!123",
        ),
        db=db,
    )
    assert reg_resp["success"] is True

    created = db.query(User).filter_by(google_id=google_id).first()
    assert created is not None
    assert created.status == "PENDING"
    assert created.role == "PHARMACY"


def test_two_factor_login_flow(db, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        email_service,
        "send_otp_email",
        lambda recipient_email, otp, purpose: captured.update(code=otp) or True,
    )
    email = "twofa@security.org"
    user = User(
        username="twofa_user",
        email=email,
        password_hash=hash_password("ValidPassword!"),
        role="PHARMACY",
        status="APPROVED",
        is_active=True,
        two_factor_enabled=True,
    )
    db.add(user)
    db.commit()

    form = OAuth2PasswordRequestForm(
        grant_type="password",
        username=email,
        password="ValidPassword!",
        scope="",
        client_id=None,
        client_secret=None,
    )
    login_resp = login(form_data=form, db=db)
    assert login_resp.two_factor_required is True
    assert login_resp.access_token is None
    actual_code = captured["code"]

    # Invalid code fails
    with pytest.raises(HTTPException) as exc:
        verify_two_factor(TwoFactorVerifyRequest(email=email, otp="000000"), db=db)
    assert exc.value.status_code == 400

    # Valid code issues token
    token_resp = verify_two_factor(TwoFactorVerifyRequest(email=email, otp=actual_code), db=db)
    assert token_resp.access_token is not None


def test_password_reset_with_otp(db, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        email_service,
        "send_otp_email",
        lambda recipient_email, otp, purpose: captured.update(code=otp) or True,
    )
    email = "forgotten@account.org"
    user = User(
        username="forgotten_user",
        email=email,
        password_hash=hash_password("OldPassword!123"),
        role="PHARMACY",
        status="APPROVED",
        is_active=True,
    )
    db.add(user)
    db.commit()

    # Request reset OTP
    send_resp = send_otp(SendOTPRequest(email=email, purpose="password_reset"), db=db)
    assert send_resp["success"] is True
    actual_code = captured["code"]

    reset_resp = reset_password(
        PasswordResetRequest(
            email=email,
            otp=actual_code,
            new_password="NewSecurePassword!123",
            confirm_password="NewSecurePassword!123",
        ),
        db=db,
    )
    assert reset_resp["success"] is True

    db.refresh(user)
    assert verify_password("NewSecurePassword!123", user.password_hash) is True
    assert verify_password("OldPassword!123", user.password_hash) is False
