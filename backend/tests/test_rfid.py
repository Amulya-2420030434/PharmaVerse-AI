from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.routes.rfid import (
    create_rfid,
    deactivate_rfid,
    get_rfid,
    list_rfid_records,
)
from app.models.batch import Batch
from app.models.rfid_record import RFIDRecord
from app.schemas.rfid import RFIDCreate, RFIDResponse


class FakeQuery:
    def __init__(self, first_result, all_result=None):
        self.first_result = first_result
        self.all_result = all_result if all_result is not None else first_result

    def filter(self, *args):
        return self

    def first(self):
        return self.first_result

    def order_by(self, *args):
        return self

    def all(self):
        return self.all_result


class FakeDB:
    def __init__(self, batch=None, rfid_record=None, rfid_records=None):
        self.batch = batch
        self.rfid_record = rfid_record
        self.rfid_records = rfid_records or []
        self.added = None

    def query(self, model):
        if model is Batch:
            return FakeQuery(self.batch)
        if model is RFIDRecord:
            return FakeQuery(self.rfid_record, self.rfid_records)
        raise AssertionError(f"Unexpected model: {model}")

    def add(self, value):
        self.added = value

    def commit(self):
        return None

    def refresh(self, value):
        return None


def rfid_data(rfid_id="RFID-MED-000001"):
    return RFIDCreate(
        rfid_id=rfid_id,
        batch_id="BATCH-2026-000001",
        tag_value="TAG-VALUE-001",
        status="active",
    )


def test_create_rfid_uses_human_readable_batch_id():
    batch = SimpleNamespace(id=uuid4(), batch_id="BATCH-2026-000001")
    db = FakeDB(batch=batch)

    created = create_rfid(
        rfid_data(),
        db,
        SimpleNamespace(role="MANUFACTURER"),
    )

    assert created.batch_id == batch.id
    assert created.status == "ACTIVE"
    assert db.added is created


def test_create_rfid_rejects_missing_batch():
    with pytest.raises(Exception) as error:
        create_rfid(
            rfid_data(),
            FakeDB(),
            SimpleNamespace(role="MANUFACTURER"),
        )

    assert error.value.status_code == 404


def test_create_rfid_rejects_duplicate_id():
    batch = SimpleNamespace(id=uuid4(), batch_id="BATCH-2026-000001")
    existing = SimpleNamespace(rfid_id="RFID-MED-000001")
    db = FakeDB(batch=batch, rfid_record=existing)

    with pytest.raises(Exception) as error:
        create_rfid(
            rfid_data(),
            db,
            SimpleNamespace(role="MANUFACTURER"),
        )

    assert error.value.status_code == 409


def test_list_and_lookup_rfid_records():
    rfid_record = SimpleNamespace(rfid_id="RFID-MED-000001")
    db = FakeDB(rfid_record=rfid_record, rfid_records=[rfid_record])

    assert list_rfid_records(db, SimpleNamespace()) == [rfid_record]
    assert get_rfid(rfid_record.rfid_id, db, SimpleNamespace()) is rfid_record


def test_get_rfid_rejects_missing_record():
    with pytest.raises(Exception) as error:
        get_rfid("RFID-MED-MISSING", FakeDB(), SimpleNamespace())

    assert error.value.status_code == 404


def test_deactivate_rfid():
    rfid_record = SimpleNamespace(rfid_id="RFID-MED-000001", status="ACTIVE")
    db = FakeDB(rfid_record=rfid_record)

    result = deactivate_rfid(rfid_record.rfid_id, db, SimpleNamespace())

    assert result.status == "INACTIVE"


def test_rfid_response_serializes_uuid_fields():
    response = RFIDResponse.model_validate(
        SimpleNamespace(
            id=uuid4(),
            rfid_id="RFID-MED-000001",
            batch_id=uuid4(),
            tag_value="TAG-VALUE-001",
            status="ACTIVE",
            created_at=datetime.now(),
        )
    )

    assert isinstance(response.id, type(uuid4()))
    assert isinstance(response.batch_id, type(uuid4()))
