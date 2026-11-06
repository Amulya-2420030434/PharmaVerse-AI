from datetime import datetime

from app.api.routes import admin as admin_routes
from app.models import Shipment, ShipmentTrackingEvent
from scripts.seed_demo_data import seed


def test_admin_dashboard_requires_admin_role(client, make_user):
    response = client.get("/api/admin/dashboard/summary")
    assert response.status_code == 401

    _, headers = make_user("REGULATOR")
    response = client.get("/api/admin/dashboard/summary", headers=headers)
    assert response.status_code == 403


def test_admin_dashboard_aggregates_database_records(
    client,
    db_session,
    make_user,
    monkeypatch,
):
    _, headers = make_user("ADMIN")
    seed(db_session)
    monkeypatch.setattr(
        admin_routes.fda_service,
        "live_summary",
        lambda: {
            "checked_at": datetime(2026, 10, 1),
            "sources": {
                name: {"status": "available"}
                for name in ("ndc", "shortages", "enforcement")
            },
        },
    )

    response = client.get("/api/admin/dashboard/summary", headers=headers)

    assert response.status_code == 200
    result = response.json()
    counts = result["counts"]
    assert counts["total_users"] == 1
    assert counts["users_by_role"] == {"ADMIN": 1}
    assert counts["total_drugs"] == 50
    assert counts["total_batches"] == 200
    assert counts["expired_batches"] > 0
    assert counts["inactive_qr_records"] == 1
    assert counts["inactive_rfid_records"] == 1
    assert counts["active_shipments"] == 100
    assert counts["delivered_shipments"] == 100
    assert counts["created_shipments"] == 100
    assert result["verification_history"]["persisted"] is False
    assert result["system_status"]["database"] == "operational"
    assert result["system_status"]["fda"] == {
        "ndc": "available",
        "shortages": "available",
        "enforcement": "available",
    }
    assert all(
        activity["shipment_id"].startswith("SHIP-2026-")
        for activity in result["recent_activity"]
    )


def test_shipment_tracking_records_create_depart_transfer_and_receive(
    client,
    db_session,
    make_user,
    seeded,
):
    _, manufacturer = make_user(
        "MANUFACTURER", username="tracking-manufacturer", organization="Factory"
    )
    _, transporter = make_user("TRANSPORTER", username="tracking-transporter")
    _, pharmacy = make_user(
        "PHARMACY", username="tracking-pharmacy", organization="Destination"
    )
    _, admin = make_user("ADMIN", username="tracking-admin")
    shipment_id = "SHIP-2026-TRACK-0001"
    create_response = client.post(
        "/api/shipments",
        headers=manufacturer,
        json={
            "shipment_id": shipment_id,
            "batch_id": "BATCH-TEST-001",
            "source": "Factory",
            "destination": "Destination",
            "current_owner": "Factory",
            "expected_departure": "2026-10-01T10:00:00",
            "expected_arrival": "2026-10-02T10:00:00",
        },
    )
    assert create_response.status_code == 201

    assert client.post(
        f"/api/shipments/{shipment_id}/depart",
        headers=transporter,
    ).status_code == 200
    assert client.post(
        f"/api/shipments/{shipment_id}/transfer",
        headers=admin,
        json={"new_owner": "Destination"},
    ).status_code == 200
    assert client.post(
        f"/api/shipments/{shipment_id}/receive",
        headers=pharmacy,
    ).status_code == 200

    tracking_response = client.get(
        f"/api/shipments/{shipment_id}/tracking",
        headers=manufacturer,
    )
    assert tracking_response.status_code == 200
    events = tracking_response.json()["events"]
    assert [event["event_type"] for event in events] == [
        "CREATED",
        "DEPARTED",
        "TRANSFERRED",
        "DELIVERED",
    ]
    assert [event["sequence_number"] for event in events] == [1, 2, 3, 4]
    assert events[0]["location_name"] == "Factory"
    assert events[-1]["location_name"] == "Destination"
    assert events[1]["event_time"] is not None
    assert events[-1]["event_time"] is not None
    assert db_session.query(Shipment).filter(
        Shipment.shipment_id == shipment_id,
        Shipment.status == "DELIVERED",
        Shipment.actual_departure.isnot(None),
        Shipment.actual_arrival.isnot(None),
        Shipment.current_owner == "Destination",
    ).one()
    assert db_session.query(ShipmentTrackingEvent).filter(
        ShipmentTrackingEvent.shipment_id
        == db_session.query(Shipment.id)
        .filter(Shipment.shipment_id == shipment_id)
        .scalar_subquery()
    ).count() == 4


def test_tracking_does_not_invent_route_checkpoints(client, db_session, make_user, seeded):
    _, headers = make_user("MANUFACTURER", username="no-fake-checkpoints")
    shipment_id = "SHIP-2026-NO-CHECKPOINTS"
    response = client.post(
        "/api/shipments",
        headers=headers,
        json={
            "shipment_id": shipment_id,
            "batch_id": "BATCH-TEST-001",
            "source": "Recorded source",
            "destination": "Recorded destination",
            "current_owner": "Recorded source",
        },
    )
    assert response.status_code == 201

    result = client.get(
        f"/api/shipments/{shipment_id}/tracking",
        headers=headers,
    ).json()
    assert [event["event_type"] for event in result["events"]] == ["CREATED"]
    assert all(event["event_type"] != "CHECKPOINT" for event in result["events"])
