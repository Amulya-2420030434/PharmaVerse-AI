from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.routes.shipment import (
    create_shipment,
    depart_shipment,
    get_shipment,
    list_shipments,
    receive_shipment,
    transfer_shipment,
)
from app.models.batch import Batch
from app.models.shipment import Shipment
from app.models.shipment_tracking_event import ShipmentTrackingEvent
from app.schemas.shipment import ShipmentCreate, ShipmentTransfer


class FakeQuery:
    def __init__(self, first_result, all_result=None):
        self.first_result = first_result
        self.all_result = all_result if all_result is not None else first_result

    def filter(self, *args):
        return self

    def first(self):
        return self.first_result

    def scalar(self):
        return 0

    def order_by(self, *args):
        return self

    def all(self):
        return self.all_result


class FakeDB:
    def __init__(self, batch=None, shipment=None, shipments=None):
        self.batch = batch
        self.shipment = shipment
        self.shipments = shipments or []
        self.added = None

    def query(self, model):
        if model is Batch:
            return FakeQuery(self.batch)
        if model is Shipment:
            return FakeQuery(self.shipment, self.shipments)
        if model is ShipmentTrackingEvent or getattr(model, "name", None) == "max":
            return FakeQuery(None)
        return FakeQuery(None)

    def add(self, value):
        self.added = value

    def flush(self):
        return None

    def commit(self):
        return None

    def refresh(self, value):
        return None


def shipment_data(shipment_id="SHIP-2026-000001"):
    return ShipmentCreate(
        shipment_id=shipment_id,
        batch_id="BATCH-2026-000001",
        source="Manufacturer",
        destination="Distributor",
        current_owner="manufacturer1",
        status="created",
        expected_departure=datetime(2026, 9, 25, 9),
        expected_arrival=datetime(2026, 9, 25, 15),
    )


def test_create_shipment_with_valid_batch():
    batch = SimpleNamespace(id=uuid4(), batch_id="BATCH-2026-000001")
    db = FakeDB(batch=batch)

    created = create_shipment(
        shipment_data(), db, SimpleNamespace(role="MANUFACTURER")
    )

    assert created.batch_id == batch.id
    assert created.source_location == "Manufacturer"
    assert created.status == "CREATED"
    assert isinstance(db.added, ShipmentTrackingEvent)
    assert db.added.event_type == "CREATED"


def test_create_shipment_rejects_nonexistent_batch():
    db = FakeDB()

    with pytest.raises(Exception) as error:
        create_shipment(
            shipment_data(), db, SimpleNamespace(role="MANUFACTURER")
        )

    assert error.value.status_code == 404


def test_create_shipment_rejects_duplicate_id():
    batch = SimpleNamespace(id=uuid4(), batch_id="BATCH-2026-000001")
    existing = SimpleNamespace(shipment_id="SHIP-2026-000001")
    db = FakeDB(batch=batch, shipment=existing)

    with pytest.raises(Exception) as error:
        create_shipment(
            shipment_data(), db, SimpleNamespace(role="MANUFACTURER")
        )

    assert error.value.status_code == 409


def test_list_and_lookup_shipments():
    shipment = SimpleNamespace(shipment_id="SHIP-2026-000001")
    db = FakeDB(shipment=shipment, shipments=[shipment])

    assert list_shipments(db, SimpleNamespace()) == [shipment]
    assert get_shipment(shipment.shipment_id, db, SimpleNamespace()) is shipment


def test_depart_receive_and_transfer_shipment():
    shipment = SimpleNamespace(
        id=uuid4(),
        shipment_id="SHIP-2026-000001",
        status="CREATED",
        actual_departure=None,
        actual_arrival=None,
        current_owner="manufacturer1",
        source_location="Manufacturer",
        destination_location="Pharmacy",
        expected_departure=None,
        expected_arrival=None,
    )
    db = FakeDB(shipment=shipment)

    admin = SimpleNamespace(role="ADMIN", username="admin", organization=None)

    departed = depart_shipment(shipment.shipment_id, db, admin)
    assert departed.status == "IN_TRANSIT"
    assert departed.actual_departure is not None

    received = receive_shipment(shipment.shipment_id, db, admin)
    assert received.status == "DELIVERED"
    assert received.actual_arrival is not None

    transferred = transfer_shipment(
        shipment.shipment_id,
        ShipmentTransfer(new_owner="pharmacy1"),
        db,
        admin,
    )
    assert transferred.current_owner == "pharmacy1"
