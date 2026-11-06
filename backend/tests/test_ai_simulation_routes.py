from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes import ai as ai_routes
from app.api.routes import simulation as simulation_routes
from app.core.security import get_current_user
from app.database.connection import get_db
from app.main import app
from app.services.ai_adapter import AIAdapter


client = TestClient(app)


def _override_user(role: str = "VIEWER"):
    return lambda: SimpleNamespace(role=role, is_active=True, id=uuid4())


def _ai_result(shipment_id: str = "SHIP-2026-000001"):
    return {
        "shipment_id": shipment_id,
        "anomalies": [],
        "correlations": [],
        "risk": {
            "shipment_id": shipment_id,
            "score": 0,
            "risk_level": "low",
            "drivers": [],
            "explanation": [],
            "evidence_count": 0,
            "requires_human_review": False,
        },
        "counterfeit": {
            "shipment_id": shipment_id,
            "is_counterfeit_risk": False,
            "risk_level": "low",
            "reasons": [],
            "status": "AUTHENTIC",
            "evidence": {},
        },
        "alerts": [],
        "explanations": [],
        "explainability": {
            "what_happened": [],
            "why_suspicious": [],
            "evidence": {"shipment_id": shipment_id},
            "assessment_time": datetime.now(timezone.utc).isoformat(),
            "risk_score": 0,
            "recommended_action": [],
            "requires_human_review": False,
        },
        "blockchain": {
            "status": "NOT_SUBMITTED",
            "transaction_id": None,
            "evidence_hash": "evidence-hash",
        },
        "persistence": {
            "analysis_id": "test-analysis-id",
            "persisted_event_count": 1,
            "duplicate_event_count": 0,
        },
    }


def teardown_function():
    app.dependency_overrides.clear()
    simulation_routes.simulation_manager.stop()


def test_ai_requires_authentication():
    response = client.post(
        "/api/ai/analyze",
        json={"shipment_id": "SHIP-2026-000001"},
    )

    assert response.status_code == 401


def test_ai_returns_adapter_result_and_blockchain_metadata(monkeypatch):
    app.dependency_overrides[get_current_user] = _override_user()
    app.dependency_overrides[get_db] = lambda: object()

    def analyze(self, request, db, assessed_by=None):
        assert request.shipment_id == "SHIP-2026-000001"
        assert assessed_by is not None
        return _ai_result(request.shipment_id)

    monkeypatch.setattr(ai_routes.AIAdapter, "analyze", analyze)

    response = client.post(
        "/api/ai/analyze",
        json={
            "shipment_id": "SHIP-2026-000001",
            "readings": [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "temperature": 5.0,
                    "humidity": 45.0,
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["blockchain"] == {
        "status": "NOT_SUBMITTED",
        "transaction_id": None,
        "evidence_hash": "evidence-hash",
    }
    assert response.json()["persistence"]["persisted_event_count"] == 1


def test_ai_simulator_returns_scenario_events_for_selected_shipment(monkeypatch):
    app.dependency_overrides[get_current_user] = _override_user()
    app.dependency_overrides[get_db] = lambda: object()

    def simulate(self, shipment_id, scenario, db):
        assert shipment_id == "SHIP-2026-000001"
        assert scenario == "temperature_excursion"
        return {
            "shipment_id": shipment_id,
            "readings": [{"temperature": 15.0, "timestamp": datetime.now(timezone.utc).isoformat()}],
            "rfid_events": [],
            "planned_route": [],
        }

    monkeypatch.setattr(ai_routes.AIAdapter, "simulate", simulate)

    response = client.post(
        "/api/ai/simulate",
        json={"shipment_id": "SHIP-2026-000001", "scenario": "temperature_excursion"},
    )

    assert response.status_code == 200
    assert response.json()["shipment_id"] == "SHIP-2026-000001"
    assert response.json()["readings"][0]["temperature"] == 15.0


def test_ai_rejects_invalid_request():
    app.dependency_overrides[get_current_user] = _override_user()

    response = client.post("/api/ai/analyze", json={"shipment_id": ""})

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_ai_missing_shipment_is_explicit(monkeypatch):
    app.dependency_overrides[get_current_user] = _override_user()
    app.dependency_overrides[get_db] = lambda: object()

    def analyze(self, request, db, assessed_by=None):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Shipment not found")

    monkeypatch.setattr(ai_routes.AIAdapter, "analyze", analyze)

    response = client.post(
        "/api/ai/analyze",
        json={"shipment_id": "SHIP-MISSING"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Shipment not found"


def test_ai_adapter_maps_public_postgres_data_to_ai_inputs():
    shipment = SimpleNamespace(
        id=uuid4(),
        shipment_id="SHIP-2026-000001",
        batch_id="batch-db-id",
        current_owner="manufacturer",
        expected_departure=None,
        expected_arrival=None,
    )
    drug = SimpleNamespace(
        drug_id="DRUG-2026-000001",
        storage_min_temp=2.0,
        storage_max_temp=8.0,
        storage_min_humidity=35.0,
        storage_max_humidity=65.0,
    )
    batch = SimpleNamespace(
        id=uuid4(),
        batch_id="BATCH-2026-000001",
        drug=drug,
        expiry_date=datetime(2027, 1, 1).date(),
    )
    qr = SimpleNamespace(qr_id="QR-MED-000001")
    rfid = SimpleNamespace(rfid_id="RFID-MED-000001")

    class Query:
        def __init__(self, value):
            self.value = value

        def filter(self, *args):
            return self

        def order_by(self, *args):
            return self

        def first(self):
            return self.value

    class Database:
        def __init__(self):
            self.added = []

        def query(self, model):
            values = {
                "Shipment": shipment,
                "Batch": batch,
                "QRRecord": qr,
                "RFIDRecord": rfid,
            }
            return Query(values[model.__name__])

        def scalars(self, statement):
            return SimpleNamespace(all=lambda: [])

        def add(self, item):
            self.added.append(item)

        def commit(self):
            pass

        def rollback(self):
            raise AssertionError("Unexpected rollback")

    captured = {}

    class Service:
        def analyze_readings(self, **kwargs):
            captured.update(kwargs)
            result = _ai_result(kwargs["shipment_id"])
            result["blockchain"]["evidence_hash"] = "0" * 64
            return result

    database = Database()
    result = AIAdapter(Service()).analyze(
        request=ai_routes.AIAnalysisRequest(shipment_id=shipment.shipment_id),
        db=database,
    )

    assert result["shipment_id"] == shipment.shipment_id
    assert captured["expected_batch_id"] == "BATCH-2026-000001"
    assert captured["expected_product_id"] == "DRUG-2026-000001"
    assert captured["expected_qr_id"] == "QR-MED-000001"
    assert captured["expected_rfid_id"] == "RFID-MED-000001"
    assert captured["storage_condition"].minimum_temperature == 2.0
    assert captured["actual_rfid_id"] is None
    assert captured["actual_qr_id"] is None
    assert captured["actual_product_id"] is None
    assert captured["actual_batch_id"] is None
    assert captured["actual_owner"] is None
    assert len(database.added) == 1
    assert database.added[0].__class__.__name__ == "AIAnalysisRecord"


def test_simulation_forbids_unapproved_role():
    app.dependency_overrides[get_current_user] = _override_user("VIEWER")

    response = client.get("/api/simulation/status")

    assert response.status_code == 403


def test_simulation_lifecycle_and_scenario_execution():
    app.dependency_overrides[get_current_user] = _override_user("ADMIN")

    status_response = client.get("/api/simulation/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "stopped"

    start_response = client.post(
        "/api/simulation/start",
        json={"scenario": "normal"},
    )
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"

    duplicate_response = client.post(
        "/api/simulation/start",
        json={"scenario": "normal"},
    )
    assert duplicate_response.status_code == 409

    stop_response = client.post("/api/simulation/stop")
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "stopped"

    scenario_response = client.post(
        "/api/simulation/scenario",
        json={"scenario": "normal"},
    )
    assert scenario_response.status_code == 200
    assert scenario_response.json()["scenario"] == "normal"
    assert "analysis" in scenario_response.json()


def test_simulation_rejects_unknown_scenario():
    app.dependency_overrides[get_current_user] = _override_user("REGULATOR")

    response = client.post(
        "/api/simulation/scenario",
        json={"scenario": "not-a-scenario"},
    )

    assert response.status_code == 400
