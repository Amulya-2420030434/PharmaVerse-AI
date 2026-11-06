from datetime import date
from types import SimpleNamespace

import pytest

from app.api.routes.verification import verify_item
from app.blockchain.fabric_client import FabricAssetNotFoundError
from app.models import Batch, Drug, QRRecord, RFIDRecord, Shipment
from app.schemas.verification import VerificationRequest
from scripts.seed_demo_data import (
    BATCH_IDS,
    DRUG_IDS,
    KNOWN_CASE_IDS,
    QR_IDS,
    RFID_IDS,
    SHIPMENT_IDS,
    clear,
    reset,
    seed,
)


def test_seed_creates_expected_entities_and_relationships(db_session):
    created = seed(db_session)

    assert created == {
        "drugs": 50,
        "batches": 200,
        "qr_records": 200,
        "rfid_records": 200,
        "shipments": 300,
    }
    assert db_session.query(Drug).count() == 50
    assert db_session.query(Batch).count() == 200
    assert db_session.query(QRRecord).count() == 200
    assert db_session.query(RFIDRecord).count() == 200
    assert db_session.query(Shipment).count() == 300
    assert all(batch.drug is not None for batch in db_session.query(Batch).all())
    assert all(
        db_session.get(Batch, record.batch_id) is not None
        for model in (QRRecord, RFIDRecord, Shipment)
        for record in db_session.query(model).all()
    )
    assert all(
        batch.fabric_asset_id is None
        and batch.last_fabric_transaction_id is None
        for batch in db_session.query(Batch).all()
    )


def test_repeated_seed_does_not_create_duplicates(db_session):
    seed(db_session)

    assert seed(db_session) == {
        "drugs": 0,
        "batches": 0,
        "qr_records": 0,
        "rfid_records": 0,
        "shipments": 0,
    }
    assert db_session.query(Drug).count() == 50
    assert db_session.query(Batch).count() == 200
    assert db_session.query(QRRecord).count() == 200
    assert db_session.query(RFIDRecord).count() == 200
    assert db_session.query(Shipment).count() == 300


def test_seed_refuses_partial_demo_data(db_session):
    seed(db_session)
    db_session.query(Shipment).filter(
        Shipment.shipment_id == SHIPMENT_IDS[0]
    ).delete()
    db_session.commit()

    with pytest.raises(RuntimeError, match="partial demo dataset"):
        seed(db_session)


def test_clear_removes_demo_data_and_preserves_unrelated_records(db_session):
    seed(db_session)
    unrelated_drug = Drug(
        drug_id="DRUG-UNRELATED-001",
        name="Unrelated product",
        manufacturer="Unrelated manufacturer",
    )
    db_session.add(unrelated_drug)
    db_session.commit()

    removed = clear(db_session)

    assert removed == {
        "shipments": 300,
        "qr_records": 200,
        "rfid_records": 200,
        "batches": 200,
        "drugs": 50,
    }
    assert db_session.query(Drug).filter(
        Drug.drug_id == unrelated_drug.drug_id
    ).one()
    assert not db_session.query(Batch).filter(Batch.batch_id.in_(BATCH_IDS)).count()
    assert not db_session.query(QRRecord).filter(QRRecord.qr_id.in_(QR_IDS)).count()
    assert not db_session.query(RFIDRecord).filter(
        RFIDRecord.rfid_id.in_(RFID_IDS)
    ).count()
    assert not db_session.query(Shipment).filter(
        Shipment.shipment_id.in_(SHIPMENT_IDS)
    ).count()
    assert not db_session.query(Drug).filter(Drug.drug_id.in_(DRUG_IDS)).count()


def test_reset_replaces_demo_records_without_duplicates(db_session):
    seed(db_session)
    db_session.query(Shipment).filter(
        Shipment.shipment_id == SHIPMENT_IDS[0]
    ).delete()
    db_session.commit()

    deleted, created = reset(db_session)

    assert deleted["shipments"] == 299
    assert created == {
        "drugs": 50,
        "batches": 200,
        "qr_records": 200,
        "rfid_records": 200,
        "shipments": 300,
    }
    assert db_session.query(Drug).filter(Drug.drug_id.in_(DRUG_IDS)).count() == 50
    assert db_session.query(Batch).filter(Batch.batch_id.in_(BATCH_IDS)).count() == 200
    assert db_session.query(QRRecord).filter(QRRecord.qr_id.in_(QR_IDS)).count() == 200
    assert db_session.query(RFIDRecord).filter(
        RFIDRecord.rfid_id.in_(RFID_IDS)
    ).count() == 200
    assert db_session.query(Shipment).filter(
        Shipment.shipment_id.in_(SHIPMENT_IDS)
    ).count() == 300


def test_required_public_ids_and_batch_references_exist(db_session):
    seed(db_session)

    assert db_session.query(Drug).filter(Drug.drug_id.in_(DRUG_IDS)).count() == 50
    assert db_session.query(Batch).filter(Batch.batch_id.in_(BATCH_IDS)).count() == 200
    assert db_session.query(QRRecord).filter(QRRecord.qr_id.in_(QR_IDS)).count() == 200
    assert db_session.query(RFIDRecord).filter(
        RFIDRecord.rfid_id.in_(RFID_IDS)
    ).count() == 200
    assert db_session.query(Shipment).filter(
        Shipment.shipment_id.in_(SHIPMENT_IDS)
    ).count() == 300

    existing_batch_ids = {batch.id for batch in db_session.query(Batch).all()}
    assert all(
        record.batch_id in existing_batch_ids
        for model in (QRRecord, RFIDRecord, Shipment)
        for record in db_session.query(model).all()
    )
    assert {shipment.status for shipment in db_session.query(Shipment)} == {
        "CREATED",
        "IN_TRANSIT",
        "DELIVERED",
    }


def _verify(db_session, **identifiers):
    class MissingLedger:
        def get_batch(self, batch_id):
            raise FabricAssetNotFoundError("Ledger asset not found")

    return verify_item(
        VerificationRequest(**identifiers),
        db_session,
        SimpleNamespace(),
        MissingLedger(),
    )


def test_known_positive_and_negative_verification_cases_exist(db_session):
    seed(db_session)
    authentic = KNOWN_CASE_IDS["authentic"]
    qr_mismatch = KNOWN_CASE_IDS["qr_mismatch"]
    rfid_mismatch = KNOWN_CASE_IDS["rfid_mismatch"]
    expired = KNOWN_CASE_IDS["expired_batch"]
    inactive_qr = KNOWN_CASE_IDS["inactive_qr"]
    inactive_rfid = KNOWN_CASE_IDS["inactive_rfid"]

    assert _verify(
        db_session,
        qr_id=authentic["qr_id"],
        rfid_id=authentic["rfid_id"],
    ).verification_status == "UNVERIFIED"
    assert _verify(
        db_session,
        batch_id=qr_mismatch["batch_id"],
        qr_id=qr_mismatch["mismatched_qr_id"],
    ).verification_status == "POTENTIAL_COUNTERFEIT"
    assert _verify(
        db_session,
        batch_id=rfid_mismatch["batch_id"],
        rfid_id=rfid_mismatch["mismatched_rfid_id"],
    ).verification_status == "POTENTIAL_COUNTERFEIT"
    assert _verify(
        db_session,
        batch_id=expired["batch_id"],
    ).verification_status == "SUSPICIOUS"
    assert db_session.query(Batch).filter(
        Batch.batch_id == expired["batch_id"],
        Batch.expiry_date < date.today(),
    ).one()
    assert _verify(
        db_session,
        qr_id=inactive_qr["qr_id"],
    ).verification_status == "SUSPICIOUS"
    assert _verify(
        db_session,
        rfid_id=inactive_rfid["rfid_id"],
    ).verification_status == "SUSPICIOUS"
