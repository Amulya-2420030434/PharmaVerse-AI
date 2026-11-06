from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.routes.qr import (
    create_qr,
    deactivate_qr,
    get_qr,
    list_qr_records,
)
from app.models.batch import Batch
from app.models.qr_record import QRRecord
from app.schemas.qr import QRCreate, QRResponse


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
    def __init__(self, batch=None, qr_record=None, qr_records=None):
        self.batch = batch
        self.qr_record = qr_record
        self.qr_records = qr_records or []
        self.added = None

    def query(self, model):
        if model is Batch:
            return FakeQuery(self.batch)
        if model is QRRecord:
            return FakeQuery(self.qr_record, self.qr_records)
        raise AssertionError(f"Unexpected model: {model}")

    def add(self, value):
        self.added = value

    def commit(self):
        return None

    def refresh(self, value):
        return None


def qr_data(qr_id="QR-MED-000001"):
    return QRCreate(
        qr_id=qr_id,
        batch_id="BATCH-2026-000001",
        encoded_value="PHARMAVERSE:BATCH-2026-000001",
        status="active",
    )


def test_create_qr_with_valid_batch():
    batch = SimpleNamespace(id=uuid4(), batch_id="BATCH-2026-000001")
    db = FakeDB(batch=batch)

    created = create_qr(qr_data(), db, SimpleNamespace(role="MANUFACTURER"))

    assert created.batch_id == batch.id
    assert created.status == "ACTIVE"
    assert db.added is created


def test_create_qr_rejects_nonexistent_batch():
    with pytest.raises(Exception) as error:
        create_qr(qr_data(), FakeDB(), SimpleNamespace(role="MANUFACTURER"))

    assert error.value.status_code == 404


def test_create_qr_rejects_duplicate_id():
    batch = SimpleNamespace(id=uuid4(), batch_id="BATCH-2026-000001")
    existing = SimpleNamespace(qr_id="QR-MED-000001")
    db = FakeDB(batch=batch, qr_record=existing)

    with pytest.raises(Exception) as error:
        create_qr(qr_data(), db, SimpleNamespace(role="MANUFACTURER"))

    assert error.value.status_code == 409


def test_list_and_lookup_qr_records():
    qr_record = SimpleNamespace(qr_id="QR-MED-000001")
    db = FakeDB(qr_record=qr_record, qr_records=[qr_record])

    assert list_qr_records(db, SimpleNamespace()) == [qr_record]
    assert get_qr(qr_record.qr_id, db, SimpleNamespace()) is qr_record


def test_deactivate_qr():
    qr_record = SimpleNamespace(qr_id="QR-MED-000001", status="ACTIVE")
    db = FakeDB(qr_record=qr_record)

    result = deactivate_qr(qr_record.qr_id, db, SimpleNamespace())

    assert result.status == "INACTIVE"


def test_qr_response_serializes_uuid_fields():
    response = QRResponse.model_validate(
        SimpleNamespace(
            id=uuid4(),
            qr_id="QR-MED-000001",
            batch_id=uuid4(),
            encoded_value="PHARMAVERSE:BATCH-2026-000001",
            status="ACTIVE",
            created_at=datetime.utcnow(),
        )
    )

    assert isinstance(response.id, type(uuid4()))
    assert isinstance(response.batch_id, type(uuid4()))
