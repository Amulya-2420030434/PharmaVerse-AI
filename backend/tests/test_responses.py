from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.core.responses import (
    AUTHENTICATION_REQUIRED,
    FORBIDDEN,
    RESOURCE_ALREADY_EXISTS,
    RESOURCE_NOT_FOUND,
    VALIDATION_ERROR,
    error_response,
)
from app.core.security import get_current_user
from app.database.connection import get_db
from app.models.drug import Drug
from app.main import app


client = TestClient(app)


def test_unauthenticated_error_uses_standard_format():
    response = client.get("/api/drugs")

    assert response.status_code == 401
    assert response.json() == {
        "success": False,
        "error": {
            "code": AUTHENTICATION_REQUIRED,
            "message": "Not authenticated",
        },
    }


def test_validation_error_uses_standard_format():
    response = client.post(
        "/api/auth/login",
        data={},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == VALIDATION_ERROR
    assert body["error"]["message"] == "Request validation failed"
    assert body["error"]["details"]


def test_common_error_codes_are_mapped_consistently():
    assert error_response(
        RESOURCE_NOT_FOUND,
        "Drug not found",
    ) == {
        "success": False,
        "error": {
            "code": RESOURCE_NOT_FOUND,
            "message": "Drug not found",
        },
    }
    assert error_response(
        RESOURCE_ALREADY_EXISTS,
        "Drug ID already exists",
    )["error"]["code"] == RESOURCE_ALREADY_EXISTS
    assert error_response(
        FORBIDDEN,
        "You do not have permission to perform this action",
    )["error"]["code"] == FORBIDDEN


def test_not_found_error_uses_standard_format():
    def override_db():
        class EmptyQuery:
            def filter(self, *args):
                return self

            def first(self):
                return None

        class EmptyDB:
            def query(self, model):
                return EmptyQuery()

        yield EmptyDB()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(role="VIEWER", is_active=True)
    )
    try:
        response = client.get("/api/audit/batch/BATCH-MISSING")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error"]["code"] == RESOURCE_NOT_FOUND


def test_forbidden_error_uses_standard_format():
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(role="VIEWER", is_active=True)
    )
    try:
        response = client.post(
            "/api/drugs",
            json={
                "drug_id": "DRUG-NEW",
                "name": "Medicine",
                "manufacturer": "Manufacturer",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error"]["code"] == FORBIDDEN


def test_duplicate_error_uses_standard_format():
    class ExistingQuery:
        def filter(self, *args):
            return self

        def first(self):
            return SimpleNamespace(id="existing")

    class ExistingDB:
        def query(self, model):
            assert model is Drug
            return ExistingQuery()

    app.dependency_overrides[get_db] = lambda: ExistingDB()
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(role="MANUFACTURER", is_active=True)
    )
    try:
        response = client.post(
            "/api/drugs",
            json={
                "drug_id": "DRUG-EXISTING",
                "name": "Medicine",
                "manufacturer": "Manufacturer",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["error"]["code"] == RESOURCE_ALREADY_EXISTS


def test_existing_success_response_shape_remains_unchanged():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "success" not in response.json()
