"""Tests for authentication resilience, database URL normalization, and DB error handling."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.connection import get_db
from app.main import app
from app.models.user import User
from app.services.auth_service import hash_password


def test_database_url_normalization():
    """Verify that Settings normalizes Render and Supabase URL prefixes to postgresql+psycopg://."""
    s1 = Settings(database_url="postgres://user:pass@render-db.com:5432/pharmaverse")
    assert s1.database_url == "postgresql+psycopg://user:pass@render-db.com:5432/pharmaverse"

    s2 = Settings(database_url="postgresql://user:pass@supabase-pooler.com:6543/postgres")
    assert s2.database_url == "postgresql+psycopg://user:pass@supabase-pooler.com:6543/postgres"

    s3 = Settings(database_url="postgresql+psycopg2://user:pass@localhost:5432/db")
    assert s3.database_url == "postgresql+psycopg://user:pass@localhost:5432/db"

    s4 = Settings(database_url="sqlite:///test.db")
    assert s4.database_url == "sqlite:///test.db"


def test_login_supports_both_email_and_username(client, db_session: Session):
    """Users should be able to log in using either their username handle or email address."""
    user = User(
        username="demo-auditor",
        email="auditor@pharmaverse.test",
        password_hash=hash_password("AuditPassword2026!"),
        role="REGULATOR",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Login by email
    resp_email = client.post(
        "/api/auth/login",
        data={"username": "auditor@pharmaverse.test", "password": "AuditPassword2026!"},
    )
    assert resp_email.status_code == 200
    assert "access_token" in resp_email.json()

    # Login by username handle
    resp_user = client.post(
        "/api/auth/login",
        data={"username": "demo-auditor", "password": "AuditPassword2026!"},
    )
    assert resp_user.status_code == 200
    assert "access_token" in resp_user.json()


def test_login_rejects_invalid_password_or_missing_user(client, db_session: Session):
    """Invalid credentials should return HTTP 401 without revealing whether username exists."""
    user = User(
        username="active-user",
        email="active@pharmaverse.test",
        password_hash=hash_password("CorrectPassword!"),
        role="PHARMACY",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Wrong password
    resp = client.post(
        "/api/auth/login",
        data={"username": "active-user", "password": "WrongPassword!"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    # Non-existent user
    resp_missing = client.post(
        "/api/auth/login",
        data={"username": "non-existent-user", "password": "AnyPassword!"},
    )
    assert resp_missing.status_code == 401


def test_login_rejects_inactive_user(client, db_session: Session):
    """Inactive users should be blocked with HTTP 403."""
    user = User(
        username="inactive-user",
        email="inactive@pharmaverse.test",
        password_hash=hash_password("Pass123!"),
        role="PHARMACY",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    resp = client.post(
        "/api/auth/login",
        data={"username": "inactive-user", "password": "Pass123!"},
    )
    assert resp.status_code == 403
    assert "inactive" in resp.json()["error"]["message"].lower()


def test_database_operational_error_returns_service_unavailable():
    """When PostgreSQL is unreachable or drops connection, return 503 SERVICE_UNAVAILABLE."""
    def broken_db():
        raise OperationalError("connection to server failed: Connection refused", None, None)

    app.dependency_overrides[get_db] = broken_db
    try:
        test_client = TestClient(app)
        resp = test_client.post(
            "/api/auth/login",
            data={"username": "admin@pharmaverse.local", "password": "password"},
        )
        assert resp.status_code == 503
        data = resp.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "Database connection failed" in data["error"]["message"]
    finally:
        app.dependency_overrides.clear()


def test_database_programming_error_returns_schema_error():
    """When migrations have not run (table missing), return informative 500 schema error."""
    def missing_table_db():
        raise ProgrammingError('relation "users" does not exist', None, None)

    app.dependency_overrides[get_db] = missing_table_db
    try:
        test_client = TestClient(app)
        resp = test_client.post(
            "/api/auth/login",
            data={"username": "admin@pharmaverse.local", "password": "password"},
        )
        assert resp.status_code == 500
        data = resp.json()
        assert data["success"] is False
        assert "migrations" in data["error"]["message"]
    finally:
        app.dependency_overrides.clear()

