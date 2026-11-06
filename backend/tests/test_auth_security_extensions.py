from app.models.user import User
from app.services.auth_service import hash_password
from app.services.email_service import EmailService, email_service
from app.services.google_auth_service import GoogleAuthError, GoogleAuthService


def test_email_verification_link_is_hashed_one_time_and_keeps_user_pending(
    client, db_session, monkeypatch
):
    delivered = {}

    def capture_email(email, token, purpose):
        delivered.update(email=email, token=token, purpose=purpose)
        return True

    monkeypatch.setattr(email_service, "send_auth_link_email", capture_email)
    response = client.post(
        "/api/auth/email-verification/send",
        json={"email": "new@applicant.example"},
    )
    assert response.status_code == 200
    assert "token" not in response.text.lower()
    assert delivered["purpose"] == "email_verification"

    confirmation = client.post(
        "/api/auth/email-verification/confirm",
        json={"token": delivered["token"]},
    )
    assert confirmation.status_code == 200
    assert confirmation.json()["email"] == "new@applicant.example"
    assert delivered["token"] not in confirmation.text

    registration = client.post(
        "/api/auth/register/email",
        json={
            "verification_token": confirmation.json()["verification_token"],
            "username": "new_applicant",
            "requested_role": "PHARMACY",
            "password": "SecurePassword!123",
            "confirm_password": "SecurePassword!123",
        },
    )
    assert registration.status_code == 201
    assert registration.json()["status"] == "PENDING"
    assert db_session.query(User).filter_by(email="new@applicant.example").one().status == "PENDING"

    reused = client.post(
        "/api/auth/email-verification/confirm",
        json={"token": delivered["token"]},
    )
    assert reused.status_code == 400


def test_password_reset_link_changes_password_and_cannot_be_reused(
    client, db_session, monkeypatch
):
    delivered = {}
    user = User(
        username="reset_user",
        email="reset@example.com",
        password_hash=hash_password("OldPassword!123"),
        role="PHARMACY",
        status="APPROVED",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    def capture_email(email, token, purpose):
        delivered.update(email=email, token=token, purpose=purpose)
        return True

    monkeypatch.setattr(email_service, "send_auth_link_email", capture_email)
    response = client.post(
        "/api/auth/forgot-password",
        json={"email": user.email},
    )
    assert response.status_code == 200
    assert delivered["purpose"] == "password_reset"
    assert delivered["token"] not in response.text

    reset = client.post(
        "/api/auth/reset-password",
        json={
            "token": delivered["token"],
            "new_password": "NewPassword!456",
            "confirm_password": "NewPassword!456",
        },
    )
    assert reset.status_code == 200
    login = client.post(
        "/api/auth/login",
        data={"username": user.email, "password": "NewPassword!456"},
    )
    assert login.status_code == 200

    reused = client.post(
        "/api/auth/reset-password",
        json={
            "token": delivered["token"],
            "new_password": "AnotherPassword!789",
            "confirm_password": "AnotherPassword!789",
        },
    )
    assert reused.status_code == 400


def test_login_requires_email_otp_when_two_factor_is_enabled(client, db_session, monkeypatch):
    delivered = {}
    user = User(
        username="two_factor_user",
        email="twofactor@example.com",
        password_hash=hash_password("StrongPassword!123"),
        role="DISTRIBUTOR",
        status="APPROVED",
        is_active=True,
        two_factor_enabled=True,
    )
    db_session.add(user)
    db_session.commit()

    def capture_otp(email, code, purpose):
        delivered.update(email=email, code=code, purpose=purpose)
        return True

    monkeypatch.setattr(email_service, "send_otp_email", capture_otp)
    response = client.post(
        "/api/auth/login",
        data={"username": user.email, "password": "StrongPassword!123"},
    )
    assert response.status_code == 200
    assert response.json()["two_factor_required"] is True
    assert response.json().get("access_token") is None
    assert delivered["purpose"] == "login_2fa"
    assert delivered["code"] not in response.text

    invalid = client.post(
        "/api/auth/2fa/verify",
        json={"email": user.email, "otp": "000000"},
    )
    assert invalid.status_code == 400
    verified = client.post(
        "/api/auth/2fa/verify",
        json={"email": user.email, "otp": delivered["code"]},
    )
    assert verified.status_code == 200
    assert verified.json()["access_token"]

    replay = client.post(
        "/api/auth/2fa/verify",
        json={"email": user.email, "otp": delivered["code"]},
    )
    assert replay.status_code == 400


def test_two_factor_settings_require_auth_and_smtp(client, db_session, monkeypatch):
    monkeypatch.setattr(email_service, "user", "")
    monkeypatch.setattr(email_service, "password", "")
    user = User(
        username="settings_user",
        email="settings@example.com",
        password_hash=hash_password("StrongPassword!123"),
        role="PHARMACY",
        status="APPROVED",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    anonymous = client.patch("/api/auth/2fa", json={"enabled": True})
    assert anonymous.status_code == 401

    login = client.post(
        "/api/auth/login",
        data={"username": user.email, "password": "StrongPassword!123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    unavailable = client.patch(
        "/api/auth/2fa",
        headers=headers,
        json={"enabled": True},
    )
    assert unavailable.status_code == 503

    monkeypatch.setattr(email_service, "user", "configured@example.test")
    monkeypatch.setattr(email_service, "password", "test-only-value")
    enabled = client.patch(
        "/api/auth/2fa",
        headers=headers,
        json={"enabled": True},
    )
    assert enabled.status_code == 200
    assert enabled.json()["two_factor_enabled"] is True

    disabled = client.patch(
        "/api/auth/2fa",
        headers=headers,
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["two_factor_enabled"] is False


def test_email_service_does_not_report_delivery_without_gmail_credentials():
    service = EmailService(host="smtp.gmail.com", user="", password="")
    assert service.send_otp_email("person@example.com", "123456", "login_2fa") is False


def test_google_auth_rejects_non_provider_tokens(monkeypatch):
    class RejectedResponse:
        status_code = 400

    class MockClient:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, params):
            assert url.endswith("/tokeninfo")
            return RejectedResponse()

    monkeypatch.setattr("app.services.google_auth_service.httpx.Client", MockClient)
    service = GoogleAuthService(client_id="configured-client-id")
    try:
        service.verify_id_token("mock-google-token:subject:person@example.com:Person")
    except GoogleAuthError as exc:
        assert "Invalid or expired" in str(exc)
    else:
        raise AssertionError("A non-provider token must never authenticate")
