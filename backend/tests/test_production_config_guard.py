"""Tests for minimal production configuration safety guards."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_localhost_database():
    """In production (debug=False), falling back to localhost or 127.0.0.1 must halt startup."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            debug=False,
            database_url="postgresql+psycopg://postgres:password@localhost:5432/pharmaverse",
            jwt_secret="a" * 32,
        )
    assert "DATABASE_URL must be explicitly configured" in str(exc_info.value)
    assert "Default localhost database is forbidden when DEBUG=false" in str(exc_info.value)

    # 127.0.0.1 is also rejected in production
    with pytest.raises(ValidationError) as exc_info2:
        Settings(
            debug=False,
            database_url="postgresql+psycopg://postgres:password@127.0.0.1:5432/pharmaverse",
            jwt_secret="a" * 32,
        )
    assert "DATABASE_URL must be explicitly configured" in str(exc_info2.value)


def test_production_rejects_default_or_weak_jwt_secret():
    """In production (debug=False), CHANGE_THIS_SECRET or secrets shorter than 32 chars must halt startup."""
    valid_db = "postgresql://user:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

    # Default placeholder
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            debug=False,
            database_url=valid_db,
            jwt_secret="CHANGE_THIS_SECRET",
        )
    assert "JWT_SECRET must be explicitly configured" in str(exc_info.value)

    # Too short (< 32 chars)
    with pytest.raises(ValidationError) as exc_info2:
        Settings(
            debug=False,
            database_url=valid_db,
            jwt_secret="too_short_key",
        )
    assert "at least 32 characters" in str(exc_info2.value)


def test_production_accepts_valid_configuration():
    """When valid remote database and 32+ character JWT_SECRET are provided, production initializes safely."""
    s = Settings(
        debug=False,
        database_url="postgresql://user:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres",
        jwt_secret="9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e",
    )
    assert s.debug is False
    assert s.database_url.startswith("postgresql+psycopg://")
    assert s.jwt_secret == "9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e"


def test_development_and_tests_permit_localhost_and_short_secrets():
    """Local development and test fixtures (debug=True) continue to work with localhost or SQLite."""
    s_local = Settings(
        debug=True,
        database_url="postgresql+psycopg://postgres:postgres@localhost:5432/pharmaverse",
        jwt_secret="short_test_secret",
    )
    assert s_local.debug is True

    s_sqlite = Settings(
        debug=True,
        database_url="sqlite://",
        jwt_secret="CHANGE_THIS_SECRET",
    )
    assert s_sqlite.database_url == "sqlite://"


def test_secrets_never_exposed_in_error_messages():
    """Error messages must never reveal the attempted password or secret values."""
    sensitive_db = "postgresql://user:SUPER_SECRET_DB_PASSWORD@localhost:5432/pharmaverse"
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            debug=False,
            database_url=sensitive_db,
            jwt_secret="a" * 32,
        )
    error_msg = str(exc_info.value)
    assert "SUPER_SECRET_DB_PASSWORD" not in error_msg

