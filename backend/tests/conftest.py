"""Shared fixtures for tests that exercise the real SQLAlchemy models.

Most older tests use hand-written fake sessions whose ``filter()`` ignores its
arguments, so they cannot detect a route comparing the wrong column.  The
fixtures below run the real FastAPI app against an in-memory SQLite database
created from the real models, with real JWT authentication.
"""

import os

# Ensure automated test suite runs in test/dev mode regardless of parent shell environment
os.environ["DEBUG"] = "true"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers every model on Base.metadata)
from app.api.routes.verification import get_fabric_client
from app.blockchain.fabric_client import FabricAssetNotFoundError
from app.database.connection import Base, get_db
from app.main import app
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password
from app.services.email_service import email_service


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session, monkeypatch):
    monkeypatch.setattr(email_service, "host", "smtp.gmail.com")
    monkeypatch.setattr(email_service, "user", "test@example.com")
    monkeypatch.setattr(email_service, "password", "test-only-value")
    monkeypatch.setattr(email_service, "send_otp_email", lambda *args, **kwargs: True)
    monkeypatch.setattr(email_service, "send_auth_link_email", lambda *args, **kwargs: True)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # End-to-end API tests remain deterministic and never depend on or query
    # a developer's live Fabric network. Individual tests can override this.
    app.dependency_overrides[get_fabric_client] = lambda: _MissingLedgerFixture()
    from app.blockchain.fabric_client import FabricClient, FabricUnavailableError
    from app.core.config import settings

    def _guard(fn):
        def _wrapper(self, *a, **kw):
            if not settings.fabric_enabled:
                raise FabricUnavailableError("Fabric integration is disabled")
            return fn(self, *a, **kw)
        return _wrapper

    monkeypatch.setattr(FabricClient, "register_drug", _guard(lambda *a, **kw: {"status": "SUCCESS", "transactionId": "mock-tx-drug"}))
    monkeypatch.setattr(FabricClient, "create_batch", _guard(lambda *a, **kw: {"status": "SUCCESS", "transactionId": "mock-tx-batch"}))
    monkeypatch.setattr(FabricClient, "ship_drug", _guard(lambda *a, **kw: {"status": "SUCCESS", "transactionId": "mock-tx-shipment"}))
    monkeypatch.setattr(FabricClient, "receive_drug", _guard(lambda *a, **kw: {"status": "SUCCESS", "transactionId": "mock-tx-receive"}))
    monkeypatch.setattr(FabricClient, "transfer_drug", _guard(lambda *a, **kw: {"status": "SUCCESS", "transactionId": "mock-tx-transfer"}))
    monkeypatch.setattr(FabricClient, "get_batch_history", lambda *a, **kw: [])
    monkeypatch.setattr(FabricClient, "health", lambda *a, **kw: {"status": "UP", "channel": "mychannel"})
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


class _MissingLedgerFixture:
    def get_batch(self, batch_id):
        raise FabricAssetNotFoundError("Ledger asset not found")

    def get_drug(self, drug_id):
        raise FabricAssetNotFoundError("Ledger asset not found")


@pytest.fixture()
def make_user(db_session):
    """Create a user and return (user, Authorization header)."""

    def _make(role, username=None, organization=None):
        username = username or f"{role.lower()}-user"
        user = User(
            username=username,
            email=f"{username}@example.com",
            password_hash=hash_password("Passw0rd!"),
            role=role,
            organization=organization,
        )
        db_session.add(user)
        db_session.commit()
        token = create_access_token(user_id=str(user.id), role=role)
        return user, {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture()
def seeded(client, make_user):
    """A manufacturer, a drug and a batch created through the real API."""
    _, mfr = make_user("MANUFACTURER", organization="Acme Pharma")
    assert client.post(
        "/api/drugs",
        headers=mfr,
        json={
            "drug_id": "DRUG-PARA-500",
            "name": "Paracetamol 500",
            "manufacturer": "Acme Pharma",
            "storage_min_temp": 15,
            "storage_max_temp": 25,
            "storage_min_humidity": 20,
            "storage_max_humidity": 60,
        },
    ).status_code == 201
    batch = client.post(
        "/api/batches",
        headers=mfr,
        json={
            "batch_id": "BATCH-TEST-001",
            "drug_id": "DRUG-PARA-500",
            "manufacturing_date": "2026-01-01",
            "expiry_date": "2028-01-01",
            "quantity": 100,
        },
    )
    assert batch.status_code == 201
    return {"mfr": mfr, "batch": batch.json()}
