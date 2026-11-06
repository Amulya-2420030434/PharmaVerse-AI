from datetime import date, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes.verification import verify_item
from app.blockchain.fabric_client import FabricAssetNotFoundError, FabricUnavailableError
from app.main import app
from app.models.batch import Batch
from app.models.drug import Drug
from app.models.qr_record import QRRecord
from app.models.rfid_record import RFIDRecord
from app.schemas.verification import VerificationRequest


class FakeQuery:
    def __init__(self, records):
        self.records = records
        self.value = None

    def filter(self, expression):
        self.value = expression.right.value
        return self

    def first(self):
        return next(
            (
                record
                for record in self.records
                if any(
                    getattr(record, key, None) == self.value
                    for key in ("id", "batch_id", "drug_id", "qr_id", "rfid_id")
                )
            ),
            None,
        )


class FakeDB:
    def __init__(self, records):
        self.records = records

    def query(self, model):
        return FakeQuery(self.records.get(model, []))


class MissingLedger:
    def get_batch(self, batch_id):
        raise FabricAssetNotFoundError("Ledger asset not found")


class AvailableLedger:
    def __init__(self, payload):
        self.payload = payload

    def get_batch(self, batch_id):
        return self.payload

    def get_drug(self, drug_id):
        return self.payload


class UnavailableLedger:
    def get_batch(self, batch_id):
        raise FabricUnavailableError("Fabric is unavailable")


def records_for(
    *,
    batch=None,
    drug=None,
    qr=None,
    rfid=None,
):
    return {
        Batch: [batch] if batch else [],
        Drug: [drug] if drug else [],
        QRRecord: [qr] if qr else [],
        RFIDRecord: [rfid] if rfid else [],
    }


def make_records():
    drug = SimpleNamespace(id=uuid4(), drug_id="DRUG-2026-000001")
    batch = SimpleNamespace(
        id=uuid4(),
        batch_id="BATCH-2026-000001",
        drug_id=drug.id,
        status="ACTIVE",
        expiry_date=date.today() + timedelta(days=30),
    )
    qr = SimpleNamespace(
        qr_id="QR-MED-000001",
        batch_id=batch.id,
        status="ACTIVE",
    )
    rfid = SimpleNamespace(
        rfid_id="RFID-MED-000001",
        batch_id=batch.id,
        status="ACTIVE",
    )
    return drug, batch, qr, rfid


def test_missing_identifiers_are_rejected():
    with pytest.raises(ValueError):
        VerificationRequest()


def test_unknown_identifier_returns_invalid():
    result = verify_item(
        VerificationRequest(batch_id="BATCH-MISSING"),
        FakeDB(records_for()),
        SimpleNamespace(),
        MissingLedger(),
    )

    assert result.verification_status == "INVALID"


def test_valid_batch_without_ledger_asset_is_unverified():
    drug, batch, _, _ = make_records()

    result = verify_item(
        VerificationRequest(batch_id=batch.batch_id),
        FakeDB(records_for(batch=batch, drug=drug)),
        SimpleNamespace(),
        MissingLedger(),
    )

    assert result.verification_status == "UNVERIFIED"
    assert result.database_status == "MATCHED"
    assert result.blockchain_status == "ASSET_NOT_FOUND"
    assert result.batch_id == batch.batch_id
    assert result.drug_id == drug.drug_id


def test_qr_and_rfid_resolve_consistently():
    drug, batch, qr, rfid = make_records()

    result = verify_item(
        VerificationRequest(qr_id=qr.qr_id, rfid_id=rfid.rfid_id),
        FakeDB(records_for(batch=batch, drug=drug, qr=qr, rfid=rfid)),
        SimpleNamespace(),
        MissingLedger(),
    )

    assert result.verification_status == "UNVERIFIED"
    assert result.batch_id == batch.batch_id


def test_matching_fabric_asset_is_required_for_authentic_result():
    drug, batch, qr, rfid = make_records()

    result = verify_item(
        VerificationRequest(
            batch_id=batch.batch_id,
            drug_id=drug.drug_id,
            qr_id=qr.qr_id,
            rfid_id=rfid.rfid_id,
        ),
        FakeDB(records_for(batch=batch, drug=drug, qr=qr, rfid=rfid)),
        SimpleNamespace(),
        AvailableLedger({
            "batchId": batch.batch_id,
            "drugId": drug.drug_id,
            "qrId": qr.qr_id,
            "rfidId": rfid.rfid_id,
        }),
    )

    assert result.verification_status == "AUTHENTIC"
    assert result.blockchain_status == "VERIFIED"
    assert result.database_status == "MATCHED"


def test_drug_only_verification_requires_a_matching_ledger_drug():
    drug, _, _, _ = make_records()
    result = verify_item(
        VerificationRequest(drug_id=drug.drug_id),
        FakeDB(records_for(drug=drug)),
        SimpleNamespace(),
        AvailableLedger({"drugId": drug.drug_id}),
    )
    assert result.verification_status == "AUTHENTIC"
    assert result.blockchain_status == "VERIFIED"
    assert result.batch_id is None


def test_ledger_identity_mismatch_is_suspicious():
    drug, batch, qr, rfid = make_records()

    result = verify_item(
        VerificationRequest(batch_id=batch.batch_id, qr_id=qr.qr_id),
        FakeDB(records_for(batch=batch, drug=drug, qr=qr)),
        SimpleNamespace(),
        AvailableLedger({
            "batchId": batch.batch_id,
            "drugId": drug.drug_id,
            "qrId": "QR-DIFFERENT",
            "rfidId": rfid.rfid_id,
        }),
    )

    assert result.verification_status == "SUSPICIOUS"
    assert result.blockchain_status == "MISMATCH"


def test_unavailable_ledger_never_returns_authentic():
    drug, batch, _, _ = make_records()
    result = verify_item(
        VerificationRequest(batch_id=batch.batch_id),
        FakeDB(records_for(batch=batch, drug=drug)),
        SimpleNamespace(),
        UnavailableLedger(),
    )
    assert result.verification_status == "UNVERIFIED"
    assert result.blockchain_status == "UNAVAILABLE"


def test_malformed_ledger_payload_is_unverified():
    drug, batch, _, _ = make_records()
    result = verify_item(
        VerificationRequest(batch_id=batch.batch_id),
        FakeDB(records_for(batch=batch, drug=drug)),
        SimpleNamespace(),
        AvailableLedger("not-a-ledger-object"),
    )
    assert result.verification_status == "UNVERIFIED"
    assert result.blockchain_status == "MALFORMED"


def test_qr_and_rfid_mismatch_is_potential_counterfeit():
    drug, batch_a, qr, _ = make_records()
    batch_b = SimpleNamespace(
        id=uuid4(),
        batch_id="BATCH-2026-000002",
        drug_id=drug.id,
        status="ACTIVE",
        expiry_date=date.today() + timedelta(days=30),
    )
    rfid = SimpleNamespace(
        rfid_id="RFID-MED-000001",
        batch_id=batch_b.id,
        status="ACTIVE",
    )

    result = verify_item(
        VerificationRequest(qr_id=qr.qr_id, rfid_id=rfid.rfid_id),
        FakeDB(
            {
                Batch: [batch_a, batch_b],
                Drug: [drug],
                QRRecord: [qr],
                RFIDRecord: [rfid],
            }
        ),
        SimpleNamespace(),
    )

    assert result.verification_status == "POTENTIAL_COUNTERFEIT"
    assert "different batches" in result.message


def test_drug_and_batch_mismatch_is_potential_counterfeit():
    drug, batch, _, _ = make_records()
    other_drug = SimpleNamespace(id=uuid4(), drug_id="DRUG-2026-000002")

    result = verify_item(
        VerificationRequest(
            batch_id=batch.batch_id,
            drug_id=other_drug.drug_id,
        ),
        FakeDB(
            {
                Batch: [batch],
                Drug: [drug, other_drug],
                QRRecord: [],
                RFIDRecord: [],
            }
        ),
        SimpleNamespace(),
    )

    assert result.verification_status == "POTENTIAL_COUNTERFEIT"


def test_expired_batch_is_suspicious():
    drug, batch, _, _ = make_records()
    batch.expiry_date = date.today() - timedelta(days=1)

    result = verify_item(
        VerificationRequest(batch_id=batch.batch_id),
        FakeDB(records_for(batch=batch, drug=drug)),
        SimpleNamespace(),
        MissingLedger(),
    )

    assert result.verification_status == "SUSPICIOUS"
    assert "expiry" in result.message


def test_inactive_qr_is_suspicious():
    drug, batch, qr, _ = make_records()
    qr.status = "INACTIVE"

    result = verify_item(
        VerificationRequest(qr_id=qr.qr_id),
        FakeDB(records_for(batch=batch, drug=drug, qr=qr)),
        SimpleNamespace(),
    )

    assert result.verification_status == "SUSPICIOUS"


def test_inactive_rfid_is_suspicious():
    drug, batch, _, rfid = make_records()
    rfid.status = "INACTIVE"

    result = verify_item(
        VerificationRequest(rfid_id=rfid.rfid_id),
        FakeDB(records_for(batch=batch, drug=drug, rfid=rfid)),
        SimpleNamespace(),
    )

    assert result.verification_status == "SUSPICIOUS"


def test_verification_requires_authentication():
    response = TestClient(app).post(
        "/api/verification/verify",
        json={"batch_id": "BATCH-2026-000001"},
    )

    assert response.status_code == 401


def test_verification_response_serializes_without_internal_uuids():
    drug, batch, _, _ = make_records()

    result = verify_item(
        VerificationRequest(batch_id=batch.batch_id),
        FakeDB(records_for(batch=batch, drug=drug)),
        SimpleNamespace(),
        MissingLedger(),
    )

    payload = result.model_dump()
    assert payload["batch_id"] == batch.batch_id
    assert payload["drug_id"] == drug.drug_id
