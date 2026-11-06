"""Role checks for blockchain write routes, without contacting Fabric."""

import pytest

from app.blockchain.fabric_client import FabricUnavailableError


ROUTES = [
    (
        "/api/blockchain/writes/drugs",
        {"drug_id": "DRUG-ROLE-TEST", "name": "Test", "strength": "1 mg", "manufacturer": "Test"},
        {"ADMIN", "REGULATOR", "MANUFACTURER"},
    ),
    (
        "/api/blockchain/writes/batches",
        {"batch_id": "BATCH-ROLE-TEST", "drug_id": "DRUG-ROLE-TEST", "manufacturer": "Test", "quantity": 1, "manufactured_date": "2026-01-01", "expiry_date": "2027-01-01"},
        {"ADMIN", "REGULATOR", "MANUFACTURER"},
    ),
    (
        "/api/blockchain/writes/identities",
        {"batch_id": "BATCH-ROLE-TEST", "qr_id": "QR-ROLE-TEST", "rfid_id": "RFID-ROLE-TEST"},
        {"ADMIN", "REGULATOR", "MANUFACTURER"},
    ),
    (
        "/api/blockchain/writes/iot-events",
        {"batch_id": "BATCH-ROLE-TEST", "shipment_id": "SHIP-ROLE-TEST", "temperature": 20, "humidity": 40, "latitude": 0, "longitude": 0, "movement": "test", "rfid_id": "RFID-ROLE-TEST"},
        {"ADMIN", "REGULATOR"},
    ),
    (
        "/api/blockchain/writes/ai-alerts",
        {"batch_id": "BATCH-ROLE-TEST", "shipment_id": "SHIP-ROLE-TEST", "alert_type": "test", "risk_score": 1, "explanation": "isolated authorization test"},
        {"ADMIN", "REGULATOR"},
    ),
    (
        "/api/blockchain/writes/flags",
        {"batch_id": "BATCH-ROLE-TEST", "reason": "test", "risk_level": "LOW"},
        {"ADMIN", "REGULATOR"},
    ),
    (
        "/api/blockchain/writes/shipments",
        {"shipment_id": "SHIP-ROLE-TEST", "batch_id": "BATCH-ROLE-TEST", "from_location": "A", "to_location": "B", "transporter": "Test"},
        {"ADMIN", "MANUFACTURER", "DISTRIBUTOR", "TRANSPORTER"},
    ),
    (
        "/api/blockchain/writes/shipments/receive",
        {"shipment_id": "SHIP-ROLE-TEST", "receiver": "Test"},
        {"ADMIN", "DISTRIBUTOR", "PHARMACY"},
    ),
    (
        "/api/blockchain/writes/transfers",
        {"batch_id": "BATCH-ROLE-TEST", "from_owner": "A", "to_owner": "B"},
        {"ADMIN", "MANUFACTURER", "DISTRIBUTOR", "PHARMACY"},
    ),
]

ROLES = ("ADMIN", "REGULATOR", "MANUFACTURER", "DISTRIBUTOR", "TRANSPORTER", "PHARMACY")


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("path,payload,allowed_roles", ROUTES)
def test_blockchain_write_role_matrix(
    client, make_user, monkeypatch, role, path, payload, allowed_roles
):
    """Allowed roles pass authorization; no request can reach a ledger write."""
    from app.blockchain.fabric_client import FabricClient

    def unavailable(self, *args, **kwargs):
        raise FabricUnavailableError("Fabric integration is disabled")

    for method in (
        "register_drug", "create_batch", "assign_identity", "record_iot_event",
        "record_ai_alert", "flag_drug", "ship_drug", "receive_drug", "transfer_drug",
    ):
        monkeypatch.setattr(FabricClient, method, unavailable)

    _, headers = make_user(role)
    response = client.post(path, json=payload, headers=headers)

    if role in allowed_roles:
        assert response.status_code == 503
        assert response.json()["error"]["message"] == "Fabric integration is disabled"
    else:
        assert response.status_code == 403
