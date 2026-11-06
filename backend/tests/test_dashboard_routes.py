"""Tests for GET /api/dashboard/summary.

Uses the same conftest fixtures (in-memory SQLite, real JWT auth) as the rest
of the integration test suite.  Two main scenarios are covered:

1. Empty database  — every counter is zero, charts have appropriate values,
                      system_status fields are present.
2. Seeded database — counters reflect the actual records created.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


# ---------------------------------------------------------------------------
# Unauthenticated guard
# ---------------------------------------------------------------------------

def test_dashboard_summary_requires_authentication():
    """The endpoint must reject requests without a Bearer token."""
    client = TestClient(app)
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Empty-database case
# ---------------------------------------------------------------------------

def test_dashboard_summary_empty_db(client, make_user, monkeypatch):
    """With an empty database every counter is 0 and structure is complete."""
    monkeypatch.setattr(settings, "fabric_enabled", False)
    _, auth = make_user("PHARMACY")
    response = client.get("/api/dashboard/summary", headers=auth)

    assert response.status_code == 200
    body = response.json()

    # ── top-level keys ──────────────────────────────────────────────────────
    assert "stats" in body
    assert "risk_distribution" in body
    assert "shipment_status_distribution" in body
    assert "recent_alerts" in body
    assert "recent_activity" in body
    assert "system_status" in body

    # ── stats all zero in empty db ──────────────────────────────────────────
    stats = body["stats"]
    assert stats["total_drugs"] == 0
    assert stats["active_shipments"] == 0
    assert stats["verified_medicines"] == 0
    assert stats["potential_counterfeits"] == 0
    assert stats["active_anomalies"] == 0        # always 0 — no anomaly table
    assert stats["high_risk_shipments"] == 0

    # ── charts ──────────────────────────────────────────────────────────────
    # risk_distribution returns all four slices (all zero) when DB is empty so
    # the pie chart has a defined structure to render.
    assert isinstance(body["risk_distribution"], list)
    for item in body["risk_distribution"]:
        assert "name" in item
        assert "value" in item
        assert "fill" in item

    assert body["shipment_status_distribution"] == []   # no shipments
    assert body["recent_alerts"] == []                  # no alert table
    assert body["recent_activity"] == []                # no shipments

    # ── system_status ────────────────────────────────────────────────────────
    ss = body["system_status"]
    for key in ("api", "database", "blockchain", "ai_engine", "iot_simulator"):
        assert key in ss, f"system_status missing key: {key}"
        svc = ss[key]
        assert "name" in svc
        assert "status" in svc
        assert "detail" in svc

    # API and database are always operational when the endpoint responds.
    assert ss["api"]["status"] == "operational"
    assert ss["database"]["status"] == "operational"

    # This scenario explicitly disables Fabric and does not depend on local .env.
    assert ss["blockchain"]["status"] == "disabled"

    # The AI engine is in-process; IoT is explicitly outside project scope.
    assert ss["ai_engine"]["status"] == "operational"
    assert ss["iot_simulator"]["status"] == "disabled"


# ---------------------------------------------------------------------------
# Seeded database case — uses the shared `seeded` fixture from conftest.py
# ---------------------------------------------------------------------------

def test_dashboard_summary_with_seeded_data(client, make_user, seeded):
    """Stats reflect the drug + batch created by the `seeded` fixture."""
    _, auth = make_user("DISTRIBUTOR")
    response = client.get("/api/dashboard/summary", headers=auth)

    assert response.status_code == 200
    body = response.json()
    stats = body["stats"]

    # The seeded fixture creates exactly one drug and one batch.
    assert stats["total_drugs"] == 1

    # No shipments created → active_shipments stays 0.
    assert stats["active_shipments"] == 0

    # The batch has no QR or RFID records yet → verified_medicines = 0.
    assert stats["verified_medicines"] == 0

    # The batch status is ACTIVE → potential_counterfeits = 0.
    assert stats["potential_counterfeits"] == 0

    # active_anomalies is always 0 (no anomaly table).
    assert stats["active_anomalies"] == 0


def test_dashboard_summary_verified_medicines_counted_after_qr(client, make_user, seeded):
    """verified_medicines increments when a QR record is added to a batch."""
    mfr = seeded["mfr"]
    batch = seeded["batch"]
    batch_id = batch["batch_id"]

    # Create a QR record for the seeded batch.
    qr_resp = client.post(
        "/api/qr",
        headers=mfr,
        json={
            "qr_id": "QR-DASH-TEST-001",
            "batch_id": batch_id,
            "encoded_value": "qr-encoded-value",
            "status": "ACTIVE",
        },
    )
    assert qr_resp.status_code == 201

    _, auth = make_user("PHARMACY")
    response = client.get("/api/dashboard/summary", headers=auth)
    assert response.status_code == 200
    stats = response.json()["stats"]

    assert stats["verified_medicines"] == 1


def test_dashboard_summary_potential_counterfeits_after_inactive_batch(
    client, make_user, seeded
):
    """potential_counterfeits counts INACTIVE batches."""
    mfr = seeded["mfr"]

    # Create a second drug + batch and deactivate the batch by setting status
    # via the drug/batch creation.  We cannot set INACTIVE at creation, so we
    # create a second batch and then (via the existing drug endpoint pattern)
    # use the QR deactivation path as a proxy — BUT the correct way is to
    # create the batch with status ACTIVE and then check that the counter
    # only changes when the batch itself is INACTIVE.
    #
    # The batch.status field is set on creation.  The existing batch creation
    # endpoint validates that status == "ACTIVE" only… wait, it allows any
    # non-blank string.  So we can create a batch with status="INACTIVE" to
    # represent a flagged batch.
    inactive_batch = client.post(
        "/api/batches",
        headers=mfr,
        json={
            "batch_id": "BATCH-FLAGGED-001",
            "drug_id": "DRUG-PARA-500",
            "manufacturing_date": "2025-01-01",
            "expiry_date": "2027-01-01",
            "quantity": 50,
            "status": "INACTIVE",
        },
    )
    assert inactive_batch.status_code == 201

    _, auth = make_user("PHARMACY")
    response = client.get("/api/dashboard/summary", headers=auth)
    assert response.status_code == 200
    stats = response.json()["stats"]

    assert stats["potential_counterfeits"] == 1


def test_dashboard_summary_shipment_status_distribution(client, make_user, seeded):
    """shipment_status_distribution mirrors the actual status breakdown."""
    mfr = seeded["mfr"]
    batch_id = seeded["batch"]["batch_id"]

    # Create one shipment in CREATED status.
    shipment_resp = client.post(
        "/api/shipments",
        headers=mfr,
        json={
            "shipment_id": "SHP-DASH-001",
            "batch_id": batch_id,
            "source": "Bengaluru",
            "destination": "Chennai",
            "current_owner": "Acme Pharma",
        },
    )
    assert shipment_resp.status_code == 201

    _, auth = make_user("PHARMACY")
    response = client.get("/api/dashboard/summary", headers=auth)
    assert response.status_code == 200

    dist = response.json()["shipment_status_distribution"]
    names = {item["name"] for item in dist}
    assert "Created" in names

    created_item = next(item for item in dist if item["name"] == "Created")
    assert created_item["value"] == 1


def test_dashboard_summary_recent_activity_contains_shipments(
    client, make_user, seeded
):
    """recent_activity is populated once a shipment exists."""
    mfr = seeded["mfr"]
    batch_id = seeded["batch"]["batch_id"]

    client.post(
        "/api/shipments",
        headers=mfr,
        json={
            "shipment_id": "SHP-DASH-002",
            "batch_id": batch_id,
            "source": "Mumbai",
            "destination": "Delhi",
            "current_owner": "Acme Pharma",
        },
    )

    _, auth = make_user("PHARMACY")
    response = client.get("/api/dashboard/summary", headers=auth)
    assert response.status_code == 200

    activity = response.json()["recent_activity"]
    assert len(activity) >= 1
    first = activity[0]
    assert "id" in first
    assert "description" in first
    assert "timestamp" in first
    assert "SHP-DASH-002" in first["description"]


def test_dashboard_summary_recent_alerts_always_empty(client, make_user):
    """recent_alerts is always [] because no alert table exists in the schema."""
    _, auth = make_user("ADMIN")
    response = client.get("/api/dashboard/summary", headers=auth)
    assert response.status_code == 200
    assert response.json()["recent_alerts"] == []


def test_dashboard_summary_active_anomalies_always_zero(client, make_user):
    """active_anomalies is always 0 because anomalies are not persisted."""
    _, auth = make_user("MANUFACTURER")
    response = client.get("/api/dashboard/summary", headers=auth)
    assert response.status_code == 200
    assert response.json()["stats"]["active_anomalies"] == 0


def test_dashboard_summary_all_roles_can_access(client, make_user):
    """Any authenticated role can call the summary endpoint (read-only)."""
    for role in ("ADMIN", "REGULATOR", "MANUFACTURER", "DISTRIBUTOR", "PHARMACY", "TRANSPORTER"):
        _, auth = make_user(role, username=f"user-{role.lower()}")
        response = client.get("/api/dashboard/summary", headers=auth)
        assert response.status_code == 200, f"role {role!r} was unexpectedly denied"


def test_dashboard_summary_risk_distribution_items_have_fill_colours(
    client, make_user, seeded
):
    """Every risk_distribution item exposes a hex fill colour for the pie chart."""
    _, auth = make_user("PHARMACY")
    response = client.get("/api/dashboard/summary", headers=auth)
    assert response.status_code == 200

    for item in response.json()["risk_distribution"]:
        assert item["fill"].startswith("#"), (
            f"fill colour for {item['name']!r} is not a hex colour: {item['fill']!r}"
        )
