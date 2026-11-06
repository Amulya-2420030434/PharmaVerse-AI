import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.services.google_auth_service import google_auth_service, GoogleAuthError
from app.services.auth_service import hash_password, create_access_token

def test_google_auth_complete_lifecycle(client, db_session, monkeypatch):
    """Verifies the complete Google authentication lifecycle including:
    - ID token verification
    - Role restrictions (ADMIN/REGULATOR forbidden for public registration)
    - PENDING status enforcement
    - Administrator approval
    - Successful session issuance & protected route access
    - Prevention of automatic account linking on email collision
    """
    google_sub = "google-sub-synthetic-12345"
    google_email = "synthetic_doctor@healthcare.org"
    google_name = "Dr. Synthetic"

    # Mock Google Token Verification for this synthetic user
    def mock_verify_id_token(token: str):
        if token == "valid-synthetic-google-token":
            return {
                "google_id": google_sub,
                "email": google_email,
                "name": google_name,
                "email_verified": True,
            }
        elif token == "mismatched-aud-token":
            raise GoogleAuthError("Google token was not issued for this application")
        elif token == "expired-token":
            raise GoogleAuthError("Invalid or expired Google token")
        raise GoogleAuthError("Invalid token")

    monkeypatch.setattr(google_auth_service, "verify_id_token", mock_verify_id_token)

    # 1. Invalid or expired token rejection
    res_inv = client.post("/api/auth/google/verify", json={"id_token": "expired-token"})
    assert res_inv.status_code == 400
    assert "Invalid or expired" in res_inv.json()["error"]["message"]

    # 2. Mismatched audience rejection
    res_aud = client.post("/api/auth/google/verify", json={"id_token": "mismatched-aud-token"})
    assert res_aud.status_code == 400
    assert "not issued for this application" in res_aud.json()["error"]["message"]

    # 3. New Google user verify returns registration token
    res_verify = client.post("/api/auth/google/verify", json={"id_token": "valid-synthetic-google-token"})
    assert res_verify.status_code == 200
    verify_data = res_verify.json()
    assert verify_data["existing_user"] is False
    assert verify_data["email"] == google_email
    reg_token = verify_data["registration_token"]
    assert reg_token is not None

    # 4. Role selection: ADMIN and REGULATOR cannot be selected
    for forbidden_role in ("ADMIN", "REGULATOR"):
        res_forbidden = client.post(
            "/api/auth/register/google",
            json={
                "registration_token": reg_token,
                "username": f"user_{forbidden_role.lower()}",
                "requested_role": forbidden_role,
                "organization": "Forbidden Org",
            },
        )
        assert res_forbidden.status_code == 403
        assert "privileged roles" in res_forbidden.json()["error"]["message"]

    # 5. Allowed role registration (e.g. PHARMACY) creates PENDING account
    res_reg = client.post(
        "/api/auth/register/google",
        json={
            "registration_token": reg_token,
            "username": "synthetic_pharmacist",
            "full_name": google_name,
            "requested_role": "PHARMACY",
            "organization": "Metropolitan Dispensary",
        },
    )
    assert res_reg.status_code == 201
    assert "pending administrator approval" in res_reg.json()["message"]

    # 6. Attempt Google login while status is PENDING -> 403 Forbidden
    res_login_pending = client.post("/api/auth/google/login", json={"id_token": "valid-synthetic-google-token"})
    assert res_login_pending.status_code == 403
    assert "pending administrator approval" in res_login_pending.json()["error"]["message"]

    # 7. Admin approves user
    user_record = db_session.query(User).filter(User.google_id == google_sub).first()
    assert user_record is not None
    assert user_record.status == "PENDING"
    assert user_record.auth_provider == "google"
    user_record.status = "APPROVED"
    db_session.commit()

    # 8. Approved Google user login succeeds with JWT
    res_login_approved = client.post("/api/auth/google/login", json={"id_token": "valid-synthetic-google-token"})
    assert res_login_approved.status_code == 200
    login_data = res_login_approved.json()
    assert login_data["existing_user"] is True
    assert login_data["status"] == "APPROVED"
    assert login_data["role"] == "PHARMACY"
    assert login_data["user_id"] is not None
    jwt_token = login_data["access_token"]
    assert jwt_token is not None

    # 9. Protected route accessible with Google JWT
    res_protected = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {jwt_token}"})
    assert res_protected.status_code == 200

    # 9b. Verify /api/auth/me returns 200 with full CurrentUserResponse for Google authenticated session
    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {jwt_token}"})
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert me_data["email"] == google_email
    assert me_data["role"] == "PHARMACY"
    assert me_data["has_google_linked"] is True

    # 10. Refuse automatic account linking if a different Google account presents matching email
    def mock_attacker_token(token: str):
        return {
            "google_id": "different-google-attacker-sub",
            "email": google_email, # Same email
            "name": "Attacker",
            "email_verified": True,
        }
    monkeypatch.setattr(google_auth_service, "verify_id_token", mock_attacker_token)
    res_attack = client.post("/api/auth/google/login", json={"id_token": "attacker-token"})
    assert res_attack.status_code in (403, 409)

    # 11. Refuse Google login on local email/password account with clear directive message
    local_email = "local_pharmacist@hospital.org"
    local_user = User(
        username="local_pharmacist_user",
        email=local_email,
        password_hash=hash_password("SecurePassword!123"),
        role="PHARMACY",
        status="APPROVED",
        auth_provider="local",
        google_id=None,
        is_active=True,
    )
    db_session.add(local_user)
    db_session.commit()

    def mock_local_collision_token(token: str):
        return {
            "google_id": "some-new-google-sub",
            "email": local_email,
            "name": "Local Pharmacist Collision",
            "email_verified": True,
        }
    monkeypatch.setattr(google_auth_service, "verify_id_token", mock_local_collision_token)
    res_collision = client.post("/api/auth/google/login", json={"id_token": "collision-token"})
    assert res_collision.status_code == 409
    assert "email and password" in res_collision.json()["error"]["message"].lower()

    # 12. Secure account linking after authenticating with email/password
    login_resp = client.post(
        "/api/auth/login",
        data={"username": local_user.username, "password": "SecurePassword!123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    local_access_token = login_resp.json()["access_token"]

    # Rejection of mismatched email during secure link
    def mock_mismatched_link_token(token: str):
        return {
            "google_id": "google-linked-sub-999",
            "email": "different_email@somewhere.org",
            "name": "Different User",
            "email_verified": True,
        }
    monkeypatch.setattr(google_auth_service, "verify_id_token", mock_mismatched_link_token)
    res_mismatch_link = client.post(
        "/api/auth/google/link",
        json={"id_token": "mismatched-link-token"},
        headers={"Authorization": f"Bearer {local_access_token}"},
    )
    assert res_mismatch_link.status_code == 400
    assert "does not match" in res_mismatch_link.json()["error"]["message"].lower()

    # Successful secure linking with matching verified email
    linked_google_sub = "google-linked-sub-local-user"
    def mock_valid_link_token(token: str):
        return {
            "google_id": linked_google_sub,
            "email": local_email,
            "name": "Local Pharmacist Linked",
            "email_verified": True,
        }
    monkeypatch.setattr(google_auth_service, "verify_id_token", mock_valid_link_token)
    res_valid_link = client.post(
        "/api/auth/google/link",
        json={"id_token": "valid-link-token"},
        headers={"Authorization": f"Bearer {local_access_token}"},
    )
    assert res_valid_link.status_code == 200
    assert res_valid_link.json()["success"] is True

    # Check user record now has google_id
    db_session.refresh(local_user)
    assert local_user.google_id == linked_google_sub

    # 13. Now the linked user can sign in via Google login directly!
    res_linked_login = client.post("/api/auth/google/login", json={"id_token": "valid-link-token"})
    assert res_linked_login.status_code == 200
    assert res_linked_login.json()["existing_user"] is True
    assert res_linked_login.json()["access_token"] is not None

    # Cannot link this same Google identity to another user
    other_user = User(
        username="other_pharmacist",
        email="other@hospital.org",
        password_hash=hash_password("OtherPassword!123"),
        role="PHARMACY",
        status="APPROVED",
        auth_provider="local",
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()
    other_token = create_access_token(user_id=str(other_user.id), role=other_user.role)

    def mock_duplicate_sub_token(token: str):
        return {
            "google_id": linked_google_sub,  # already linked above
            "email": "other@hospital.org",
            "name": "Other User",
            "email_verified": True,
        }
    monkeypatch.setattr(google_auth_service, "verify_id_token", mock_duplicate_sub_token)
    res_dup_link = client.post(
        "/api/auth/google/link",
        json={"id_token": "dup-token"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert res_dup_link.status_code == 409
    assert "already linked" in res_dup_link.json()["error"]["message"].lower()
