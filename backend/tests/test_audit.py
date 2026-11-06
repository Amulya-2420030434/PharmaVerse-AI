from datetime import date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes.audit import trace_batch
from app.main import app
from app.models.batch import Batch
from app.models.drug import Drug
from app.models.qr_record import QRRecord
from app.models.rfid_record import RFIDRecord
from app.models.shipment import Shipment


class FakeQuery:
    def __init__(self, model, records):
        self.model = model
        self.records = records
        self.expression = None

    def filter(self, expression):
        self.expression = expression
        return self

    def order_by(self, *args):
        return self

    def _matches(self, record):
        if self.expression is None:
            return True
        field_name = self.expression.left.key
        return getattr(record, field_name) == self.expression.right.value

    def first(self):
        return next((record for record in self.records if self._matches(record)), None)

    def all(self):
        return [record for record in self.records if self._matches(record)]


class FakeDB:
    def __init__(self, records):
        self.records = records

    def query(self, model):
        return FakeQuery(model, self.records.get(model, []))


def make_trace_records():
    drug = SimpleNamespace(
        id=uuid4(),
        drug_id="DRUG-2026-000001",
        name="Demo Medicine",
        generic_name="Demo Generic",
        manufacturer="Demo Pharma",
        dosage_form="Tablet",
        strength="500 mg",
        storage_min_temp=2.0,
        storage_max_temp=8.0,
        storage_min_humidity=30.0,
        storage_max_humidity=60.0,
    )
    batch = SimpleNamespace(
        id=uuid4(),
        batch_id="BATCH-2026-000001",
        drug_id=drug.id,
        manufacturing_date=date(2026, 9, 1),
        expiry_date=date(2027, 9, 1),
        quantity=100,
        status="ACTIVE",
        created_at=datetime(2026, 9, 1, 8),
    )
    shipment = SimpleNamespace(
        id=uuid4(),
        shipment_id="SHIP-2026-000001",
        batch_id=batch.id,
        source_location="Manufacturer",
        destination_location="Distributor",
        current_owner="distributor1",
        status="IN_TRANSIT",
        expected_departure=datetime(2026, 9, 25, 9),
        actual_departure=datetime(2026, 9, 25, 9, 5),
        expected_arrival=datetime(2026, 9, 25, 15),
        actual_arrival=None,
        expected_latitude=17.385,
        expected_longitude=78.4867,
        current_latitude=None,
        current_longitude=None,
        created_at=datetime(2026, 9, 24, 10),
    )
    qr_record = SimpleNamespace(
        qr_id="QR-MED-000001",
        batch_id=batch.id,
        status="ACTIVE",
        created_at=datetime(2026, 9, 1, 9),
    )
    rfid_record = SimpleNamespace(
        rfid_id="RFID-MED-000001",
        batch_id=batch.id,
        status="ACTIVE",
        created_at=datetime(2026, 9, 1, 10),
    )
    return {
        Batch: [batch],
        Drug: [drug],
        Shipment: [shipment],
        QRRecord: [qr_record],
        RFIDRecord: [rfid_record],
    }, batch, drug, shipment, qr_record, rfid_record


def test_authentication_is_required():
    response = TestClient(app).get(
        "/api/audit/batch/BATCH-2026-000001"
    )

    assert response.status_code == 401


def test_existing_batch_returns_complete_database_trace():
    records, batch, drug, shipment, qr_record, rfid_record = make_trace_records()

    result = trace_batch(
        batch.batch_id,
        FakeDB(records),
        SimpleNamespace(),
    )

    assert result.trace_source == "POSTGRESQL"
    assert result.batch_id == batch.batch_id
    assert result.drug.drug_id == drug.drug_id
    assert result.shipments[0].shipment_id == shipment.shipment_id
    assert result.qr_records[0].qr_id == qr_record.qr_id
    assert result.rfid_records[0].rfid_id == rfid_record.rfid_id


def test_unknown_batch_returns_404():
    with pytest.raises(Exception) as error:
        trace_batch(
            "BATCH-MISSING",
            FakeDB(
                {
                    Batch: [],
                    Drug: [],
                    Shipment: [],
                    QRRecord: [],
                    RFIDRecord: [],
                }
            ),
            SimpleNamespace(),
        )

    assert error.value.status_code == 404


def test_batch_without_related_records_returns_empty_lists():
    records, batch, drug, *_ = make_trace_records()
    records[Shipment] = []
    records[QRRecord] = []
    records[RFIDRecord] = []

    result = trace_batch(batch.batch_id, FakeDB(records), SimpleNamespace())

    assert result.drug.drug_id == drug.drug_id
    assert result.shipments == []
    assert result.qr_records == []
    assert result.rfid_records == []


def test_trace_response_serializes_dates_without_internal_uuids():
    records, batch, *_ = make_trace_records()

    result = trace_batch(batch.batch_id, FakeDB(records), SimpleNamespace())
    payload = result.model_dump(mode="json")

    assert payload["batch_id"] == "BATCH-2026-000001"
    assert payload["manufacturing_date"] == "2026-09-01"
    assert payload["created_at"].startswith("2026-09-01T08:00:00")
    assert "id" not in payload
    assert "id" not in payload["shipments"][0]
