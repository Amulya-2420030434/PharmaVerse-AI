from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.database.connection import get_db
from app.main import app
from app.models.user import User
from app.services.auth_service import verify_password


client = TestClient(app)


def test_malformed_jwt_subject_returns_401():
    from app.core import security

    original_decode = security.jwt.decode
    security.jwt.decode = lambda *args, **kwargs: {"sub": "not-a-uuid"}
    try:
        class EmptyQuery:
            def filter(self, *args):
                return self

            def first(self):
                raise AssertionError("Invalid subject must not query the database")

        class EmptyDB:
            def query(self, model):
                return EmptyQuery()

        try:
            get_current_user("token", EmptyDB())
        except Exception as error:
            assert error.status_code == 401
    finally:
        security.jwt.decode = original_decode


def test_malformed_password_hash_is_treated_as_invalid():
    assert verify_password("password", "not-a-valid-password-hash") is False


def test_user_responses_do_not_expose_password_hash():
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=uuid4(),
        username="user",
        email="user@example.com",
        role="VIEWER",
        organization=None,
        password_hash="secret-hash",
        is_active=True,
    )
    try:
        response = client.get("/api/auth/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "password_hash" not in response.json()
