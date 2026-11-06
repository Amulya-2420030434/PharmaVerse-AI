"""End-to-end API tests (real models, in-memory DB, real JWTs)."""

import json
from datetime import datetime, timezone

from app.ml.model import FEATURE_NAMES, RiskModel

SHIPMENT = {
    "shipment_id": "SHP-001",
    "batch_id": "BATCH-TEST-001",
    "source": "Hyderabad Plant",
    "destination": "Mumbai DC",
    "current_owner": "Acme Pharma",
    "expected_departure": "2026-09-25T08:00:00",
    "expected_arrival": "2026-09-26T08:00:00",
}


# ----------------------------------------------------------------- auth

def _register(client, **overrides):
    headers = overrides.pop("headers", None)
    body = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "Passw0rd!",
        "role": "DISTRIBUTOR",
        **overrides,
    }
    return client.post("/api/auth/register", json=body, headers=headers)


def test_register_login_me_roundtrip_hides_password_hash(client, make_user):
    _, admin_headers = make_user("ADMIN", username="admin_actor")
    assert _register(client, headers=admin_headers).status_code == 201
    login = client.post(
        "/api/auth/login",
        data={"username": "newuser@example.com", "password": "Passw0rd!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert "password" not in me.text and "hash" not in me.text


def test_register_rejects_unknown_role_and_weak_password(client, make_user):
    _, admin_headers = make_user("ADMIN", username="admin_actor2")
    assert _register(client, headers=admin_headers, role="SUPERUSER").status_code == 422
    assert _register(client, headers=admin_headers, password="").status_code == 422
    assert _register(client, headers=admin_headers, password="short").status_code == 422
    body = _register(client, headers=admin_headers, password="").json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_anonymous_cannot_register_privileged_roles(client, make_user):
    make_user("ADMIN", username="root")  # an ADMIN already exists
    # Anonymous requests are rejected with 401 Unauthorized
    assert _register(client, username="a", email="a@example.com", role="ADMIN").status_code in (401, 403)
    assert _register(client, username="r", email="r@example.com", role="REGULATOR").status_code in (401, 403)


def test_first_admin_can_bootstrap_then_admin_creates_regulator(client, make_user):
    _, admin_headers = make_user("ADMIN", username="boot_admin")
    regulator = client.post(
        "/api/auth/register",
        headers=admin_headers,
        json={"username": "reg", "email": "reg@example.com", "password": "Passw0rd!", "role": "REGULATOR"},
    )
    assert regulator.status_code == 201
    assert regulator.json()["role"] == "REGULATOR"
    # ...but anonymous registration is refused
    assert _register(client, username="x", email="x@example.com", role="ADMIN").status_code in (401, 403)


def test_bad_tokens_are_rejected(client):
    for header in ("Bearer abc.def", "Bearer !!!", "Basic abc"):
        assert client.get("/api/auth/me", headers={"Authorization": header}).status_code == 401
    assert client.get("/api/auth/me").status_code == 401
    # a bad token on the optional-auth register endpoint is a 401, not anonymous
    assert client.post(
        "/api/auth/register",
        headers={"Authorization": "Bearer garbage"},
        json={"username": "u", "email": "u@example.com", "password": "Passw0rd!", "role": "DISTRIBUTOR"},
    ).status_code == 401


# ------------------------------------------------------------ shipments

def _create_shipment(client, seeded, **overrides):
    return client.post(
        "/api/shipments", headers=seeded["mfr"], json={**SHIPMENT, **overrides}
    )


def test_shipment_full_lifecycle_and_invalid_transitions(client, seeded, make_user):
    _, distributor = make_user("DISTRIBUTOR", organization="Acme Distribution")
    _, pharmacy = make_user("PHARMACY", organization="City Pharmacy")
    mfr = seeded["mfr"]

    assert _create_shipment(client, seeded).status_code == 201
    assert _create_shipment(client, seeded).status_code == 409
    # cannot receive before departing
    assert client.post("/api/shipments/SHP-001/receive", headers=distributor).status_code == 400
    # pharmacy may not depart it
    assert client.post("/api/shipments/SHP-001/depart", headers=pharmacy).status_code == 403

    departed = client.post("/api/shipments/SHP-001/depart", headers=mfr)
    assert departed.status_code == 200 and departed.json()["status"] == "IN_TRANSIT"
    # cannot depart twice
    assert client.post("/api/shipments/SHP-001/depart", headers=mfr).status_code == 400
    # manufacturer may not receive
    assert client.post("/api/shipments/SHP-001/receive", headers=mfr).status_code == 403

    received = client.post("/api/shipments/SHP-001/receive", headers=distributor)
    assert received.status_code == 200 and received.json()["status"] == "DELIVERED"
    assert client.post("/api/shipments/SHP-001/receive", headers=distributor).status_code == 400
    assert client.post("/api/shipments/SHP-001/depart", headers=mfr).status_code == 400


def test_shipment_transfer_requires_current_owner(client, seeded, make_user):
    _, distributor = make_user("DISTRIBUTOR", organization="Acme Distribution")
    _, pharmacy = make_user("PHARMACY", organization="City Pharmacy")
    _, admin = make_user("ADMIN")
    _create_shipment(client, seeded)

    def transfer(headers, owner):
        return client.post(
            "/api/shipments/SHP-001/transfer", headers=headers, json={"new_owner": owner}
        )

    # a party that does not own the shipment cannot hijack it
    assert transfer(pharmacy, "City Pharmacy").status_code == 403
    assert transfer(distributor, "Acme Distribution").status_code == 403
    # the owner (matched by organization) can hand it over
    assert transfer(seeded["mfr"], "Acme Distribution").json()["current_owner"] == "Acme Distribution"
    assert transfer(seeded["mfr"], "City Pharmacy").status_code == 403  # no longer the owner
    assert transfer(distributor, "City Pharmacy").status_code == 200
    # blank / same-owner / admin override
    assert transfer(pharmacy, "   ").status_code == 400
    assert transfer(pharmacy, "city pharmacy").status_code == 400
    assert transfer(admin, "Acme Pharma").status_code == 200
    assert client.post("/api/shipments/NOPE/transfer", headers=admin, json={"new_owner": "x"}).status_code == 404


def test_shipment_creation_validation(client, seeded):
    assert _create_shipment(client, seeded, status="delivered").status_code == 422
    assert _create_shipment(client, seeded, shipment_id="S2", expected_latitude=999).status_code == 422
    assert _create_shipment(client, seeded, shipment_id="S3", batch_id="NOPE").status_code == 404
    assert _create_shipment(
        client, seeded, shipment_id="S4",
        expected_departure="2026-09-27T00:00:00",
    ).status_code == 400


# --------------------------------------------------------- verification

def _seed_identities(client, seeded):
    mfr = seeded["mfr"]
    client.post("/api/qr", headers=mfr, json={"qr_id": "QR-1", "batch_id": "BATCH-TEST-001", "encoded_value": "v"})
    client.post("/api/rfid", headers=mfr, json={"rfid_id": "RFID-1", "batch_id": "BATCH-TEST-001", "tag_value": "t"})


def _verify(client, headers, body):
    return client.post("/api/verification/verify", headers=headers, json=body)


def test_verification_empty_body_is_422_not_500(client, seeded):
    for body in ({}, {"qr_id": "   "}):
        response = _verify(client, seeded["mfr"], body)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_verification_outcomes(client, seeded):
    _seed_identities(client, seeded)
    mfr = seeded["mfr"]
    client.post("/api/batches", headers=mfr, json={
        "batch_id": "B-OTHER", "drug_id": "DRUG-PARA-500",
        "manufacturing_date": "2026-01-01", "expiry_date": "2028-01-01", "quantity": 1})
    client.post("/api/batches", headers=mfr, json={
        "batch_id": "B-EXPIRED", "drug_id": "DRUG-PARA-500",
        "manufacturing_date": "2019-01-01", "expiry_date": "2020-01-01", "quantity": 1})
    client.post("/api/qr", headers=mfr, json={"qr_id": "QR-OTHER", "batch_id": "B-OTHER", "encoded_value": "v"})

    def status_of(body):
        response = _verify(client, mfr, body)
        assert response.status_code == 200, response.text
        return response.json()["verification_status"]

    verified = _verify(client, mfr, {
        "qr_id": "QR-1", "rfid_id": "RFID-1",
        "batch_id": "BATCH-TEST-001", "drug_id": "DRUG-PARA-500",
    })
    assert verified.status_code == 200
    assert verified.json()["verification_status"] == "UNVERIFIED"
    assert verified.json()["database_status"] == "MATCHED"
    assert verified.json()["blockchain_status"] == "ASSET_NOT_FOUND"
    assert status_of({"qr_id": "UNKNOWN"}) == "INVALID"
    assert status_of({"rfid_id": "UNKNOWN"}) == "INVALID"
    assert status_of({"qr_id": "QR-OTHER", "rfid_id": "RFID-1"}) == "POTENTIAL_COUNTERFEIT"  # conflicting
    assert status_of({"qr_id": "QR-1", "batch_id": "B-OTHER"}) == "POTENTIAL_COUNTERFEIT"     # incorrect batch
    assert status_of({"batch_id": "B-EXPIRED"}) == "SUSPICIOUS"                               # expired

    client.post("/api/rfid/RFID-1/deactivate", headers=mfr)
    assert status_of({"rfid_id": "RFID-1"}) == "SUSPICIOUS"


# -------------------------------------------------------------- audit/AI

def test_audit_trace_links_records(client, seeded):
    _seed_identities(client, seeded)
    _create_shipment(client, seeded)

    trace = client.get("/api/audit/batch/BATCH-TEST-001", headers=seeded["mfr"])
    assert trace.status_code == 200
    body = trace.json()
    assert [q["qr_id"] for q in body["qr_records"]] == ["QR-1"]
    assert [r["rfid_id"] for r in body["rfid_records"]] == ["RFID-1"]
    assert [s["shipment_id"] for s in body["shipments"]] == ["SHP-001"]
    assert client.get("/api/audit/batch/NOPE", headers=seeded["mfr"]).status_code == 404


def test_ai_analyze_accepts_timezone_aware_and_naive_timestamps(client, seeded):
    _seed_identities(client, seeded)
    _create_shipment(client, seeded)
    body = {
        "shipment_id": "SHP-001",
        "actual_rfid_id": "RFID-FAKE",
        "readings": [
            {"timestamp": "2026-09-25T10:00:00Z", "temperature": 40, "humidity": 90, "latitude": 17.4, "longitude": 78.5},
            {"timestamp": "2026-09-25T11:00:00", "temperature": 41, "humidity": 90, "latitude": 17.4, "longitude": 78.5},
        ],
    }
    response = client.post("/api/ai/analyze", headers=seeded["mfr"], json=body)

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["risk"]["score"] > 0
    assert result["blockchain"]["status"] == "NOT_SUBMITTED"
    assert result["blockchain"]["transaction_id"] is None
    assert result["ml_assessment"]["available"] in (True, False)
    assert "laboratory" in result["ml_assessment"]["disclaimer"]
    assert client.post("/api/ai/analyze", headers=seeded["mfr"], json={**body, "shipment_id": "NOPE"}).status_code == 404
    assert client.post("/api/ai/analyze", json=body).status_code == 401


def test_ai_analysis_persists_observations_and_history_without_duplicate_events(
    client,
    seeded,
    db_session,
):
    from app.models.ai_telemetry_event import AIAnalysisRecord, AITelemetryEvent

    _seed_identities(client, seeded)
    _create_shipment(client, seeded)
    observer = seeded["mfr"]
    timestamp = "2026-11-05T05:30:00Z"
    body = {
        "shipment_id": "SHP-001",
        "readings": [
            {
                "timestamp": timestamp,
                "temperature": 42,
                "humidity": 90,
                "latitude": 17.4,
                "longitude": 78.5,
                "sensor_id": "ai-persistence-test",
            },
            {
                "timestamp": timestamp,
                "temperature": 42,
                "humidity": 90,
                "latitude": 17.4,
                "longitude": 78.5,
                "sensor_id": "ai-persistence-test",
            },
        ],
        "actual_rfid_id": "RFID-OBSERVED-TEST",
    }

    first = client.post("/api/ai/analyze", headers=observer, json=body)
    second = client.post("/api/ai/analyze", headers=observer, json=body)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["persistence"]["persisted_event_count"] == 1
    assert first.json()["persistence"]["duplicate_event_count"] == 1
    assert second.json()["persistence"]["persisted_event_count"] == 0
    assert second.json()["persistence"]["duplicate_event_count"] == 2
    assert db_session.query(AITelemetryEvent).count() == 1
    assert db_session.query(AIAnalysisRecord).count() == 2
    assert db_session.query(AIAnalysisRecord).order_by(AIAnalysisRecord.created_at.desc()).first().result["risk"]["score"] > 0

    history = client.get("/api/ai/shipments/SHP-001/history", headers=observer)
    assert history.status_code == 200
    assert len(history.json()) == 2


def test_ai_simulator_generates_batch_linked_events_for_selected_shipment(
    client,
    seeded,
):
    _seed_identities(client, seeded)
    _create_shipment(client, seeded)

    generated = client.post(
        "/api/ai/simulate",
        headers=seeded["mfr"],
        json={"shipment_id": "SHP-001", "scenario": "rfid_mismatch"},
    )

    assert generated.status_code == 200, generated.text
    data = generated.json()
    assert data["shipment_id"] == "SHP-001"
    assert data["actual_rfid_id"].endswith("-SIMULATED-MISMATCH")
    assert all(item["batch_id"] == "BATCH-TEST-001" for item in data["rfid_events"])
    assert len(data["rfid_events"]) > 1
    assert all(item["event_type"] for item in data["rfid_events"])
    assert len(data["planned_route"]) > 1

    analysis = client.post("/api/ai/analyze", headers=seeded["mfr"], json=data)

    assert analysis.status_code == 200, analysis.text
    assert "identity" in analysis.json()["risk"]["factor_evidence"]


def test_ai_normal_simulator_uses_selected_drug_storage_limits(client, seeded):
    _seed_identities(client, seeded)
    _create_shipment(client, seeded)

    generated = client.post(
        "/api/ai/simulate",
        headers=seeded["mfr"],
        json={"shipment_id": "SHP-001", "scenario": "normal"},
    )

    assert generated.status_code == 200, generated.text
    for reading in generated.json()["readings"]:
        assert 15 <= reading["temperature"] <= 25
        assert 20 <= reading["humidity"] <= 60


def test_ai_simulator_can_generate_an_expiry_violation_without_changing_batch_data(
    client,
    seeded,
):
    _seed_identities(client, seeded)
    _create_shipment(client, seeded)

    generated = client.post(
        "/api/ai/simulate",
        headers=seeded["mfr"],
        json={"shipment_id": "SHP-001", "scenario": "expiry_violation"},
    )

    assert generated.status_code == 200, generated.text
    data = generated.json()
    assert data["actual_expiry_date"] < datetime.now(timezone.utc).date().isoformat()
    analysis = client.post("/api/ai/analyze", headers=seeded["mfr"], json=data)
    assert analysis.status_code == 200, analysis.text
    assert "expiry" in analysis.json()["risk"]["factor_evidence"]


# ------------------------------------------------------ ML / sim / fabric

def test_ml_endpoints_report_unavailable_without_artifact(client, seeded, monkeypatch):
    monkeypatch.delenv("PHARMAVERSE_ML_ARTIFACT", raising=False)
    monkeypatch.setattr("app.core.config.settings.pharmaverse_ml_artifact", None)
    mfr = seeded["mfr"]
    status = client.get("/api/ml/status", headers=mfr).json()
    assert status["available"] is False
    assert client.get("/api/ml/metrics", headers=mfr).json() == {"available": False, "metrics": {}}
    prediction = client.post("/api/ml/predict", headers=mfr, json={"anomaly_count": 2}).json()
    assert prediction["available"] is False and prediction["probability"] is None
    assert client.get("/api/ml/status").status_code == 401


def test_ml_artifact_loading_and_metadata(tmp_path, monkeypatch):
    import joblib
    from sklearn.linear_model import LogisticRegression

    x = [[0, 0, 0, 0], [1, 0, 0, 1], [5, 3, 2, 3], [6, 4, 3, 3]]
    model = LogisticRegression().fit(x, [0, 0, 1, 1])

    good = tmp_path / "good.joblib"
    joblib.dump({"model": model, "metrics": {"f1": 0.5}, "feature_names": list(FEATURE_NAMES), "model_name": "LogReg"}, good)
    loaded = RiskModel(good)
    assert loaded.status.available and loaded.status.model_name == "LogReg"
    assert loaded.metrics() == {"f1": 0.5}
    prediction = loaded.predict({"anomaly_count": 6, "high_severity_count": 4})
    assert prediction.available and 0.0 <= prediction.probability <= 1.0

    wrong_features = tmp_path / "wrong.joblib"
    joblib.dump({"model": model, "feature_names": ["a", "b"]}, wrong_features)
    assert RiskModel(wrong_features).status.available is False

    corrupt = tmp_path / "corrupt.joblib"
    corrupt.write_bytes(b"not a pickle")
    broken = RiskModel(corrupt)  # must not raise
    assert broken.status.available is False and "could not be loaded" in broken.status.reason
    assert broken.predict({"anomaly_count": 1}).available is False


def test_simulation_is_restricted_to_admin_and_regulator(client, make_user):
    for role, expected in (
        ("MANUFACTURER", 403), ("DISTRIBUTOR", 403), ("PHARMACY", 403),
        ("TRANSPORTER", 403), ("REGULATOR", 200), ("ADMIN", 200),
    ):
        _, headers = make_user(role)
        assert client.get("/api/simulation/status", headers=headers).status_code == expected, role
    _, distributor = make_user("DISTRIBUTOR", username="d2")
    assert client.post("/api/simulation/start", headers=distributor, json={"scenario": "normal"}).status_code == 403


def test_blockchain_disabled_is_explicit_503_with_no_transaction(client, make_user, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "fabric_enabled", False)
    _, mfr = make_user("MANUFACTURER")
    response = client.post(
        "/api/blockchain/writes/drugs",
        headers=mfr,
        json={"drug_id": "D", "name": "n", "strength": "s", "manufacturer": "m"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "transactionId" not in response.text


def test_unknown_route_uses_standard_error_envelope(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["success"] is False
