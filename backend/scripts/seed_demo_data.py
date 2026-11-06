"""Seed and reset the deterministic PharmaVerse PostgreSQL demo dataset."""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database.connection import SessionLocal  # noqa: E402
from app.models import Batch, Drug, QRRecord, RFIDRecord, Shipment  # noqa: E402


DRUG_COUNT = 50
BATCH_COUNT = 200
QR_COUNT = 200
RFID_COUNT = 200
SHIPMENT_COUNT = 300
UUID_NAMESPACE = uuid.UUID("8e9cba89-ec82-4f9c-a86e-06cd150b5182")
REFERENCE_TIME = datetime(2026, 9, 1, 8, 0)

DRUG_IDS = tuple(f"DRUG-2026-{i:06d}" for i in range(1, DRUG_COUNT + 1))
BATCH_IDS = tuple(f"BATCH-2026-{i:06d}" for i in range(1, BATCH_COUNT + 1))
QR_IDS = tuple(f"QR-MED-{i:06d}" for i in range(1, QR_COUNT + 1))
RFID_IDS = tuple(f"RFID-MED-{i:06d}" for i in range(1, RFID_COUNT + 1))
SHIPMENT_IDS = tuple(
    f"SHIP-2026-{i:06d}" for i in range(1, SHIPMENT_COUNT + 1)
)

DRUG_NAMES = (
    ("acetaminophen", "500 mg"),
    ("amoxicillin", "500 mg"),
    ("atorvastatin", "20 mg"),
    ("azithromycin", "250 mg"),
    ("cetirizine", "10 mg"),
    ("metformin", "500 mg"),
    ("omeprazole", "20 mg"),
    ("ibuprofen", "200 mg"),
    ("losartan", "50 mg"),
    ("vitamin D3", "1000 IU"),
    ("salbutamol", "100 mcg"),
    ("insulin glargine", "100 units/mL"),
)
MANUFACTURERS = (
    "Asterion Pharmaceuticals",
    "Northstar Generics",
    "Meridian Biologics",
    "Cedarline Therapeutics",
    "SummitCare Laboratories",
)
DOSAGE_FORMS = (
    "Tablet",
    "Capsule",
    "Oral suspension",
    "Injection",
    "Inhaler",
)
STORAGE_RANGES = (
    (15.0, 25.0, 20.0, 60.0),
    (2.0, 8.0, 20.0, 60.0),
    (10.0, 30.0, 25.0, 65.0),
)
SOURCE_SITES = (
    "Asterion Plant - Hyderabad",
    "Northstar Facility - Pune",
    "Meridian Plant - Ahmedabad",
    "Cedarline Facility - Bengaluru",
)
DESTINATIONS = (
    "Central Distribution - Mumbai",
    "Regional Depot - Delhi",
    "City Hospital Pharmacy - Chennai",
    "Community Pharmacy - Kochi",
    "Regional Depot - Kolkata",
)
LOGISTICS_PARTNERS = (
    "BlueRoute Cold Chain",
    "TransMed Logistics",
    "HealthLink Distribution",
)

# The first six batches and corresponding records are stable manual test cases.
KNOWN_CASE_IDS = {
    "authentic": {
        "batch_id": BATCH_IDS[0],
        "qr_id": QR_IDS[0],
        "rfid_id": RFID_IDS[0],
    },
    "qr_mismatch": {
        "batch_id": BATCH_IDS[0],
        "mismatched_qr_id": QR_IDS[1],
    },
    "rfid_mismatch": {
        "batch_id": BATCH_IDS[0],
        "mismatched_rfid_id": RFID_IDS[2],
    },
    "expired_batch": {
        "batch_id": BATCH_IDS[3],
        "qr_id": QR_IDS[3],
        "rfid_id": RFID_IDS[3],
    },
    "inactive_qr": {
        "batch_id": BATCH_IDS[4],
        "qr_id": QR_IDS[4],
        "rfid_id": RFID_IDS[4],
    },
    "inactive_rfid": {
        "batch_id": BATCH_IDS[5],
        "qr_id": QR_IDS[5],
        "rfid_id": RFID_IDS[5],
    },
}


def _uuid_for(public_id: str) -> uuid.UUID:
    return uuid.uuid5(UUID_NAMESPACE, public_id)


def _make_drugs() -> list[Drug]:
    records = []
    for index, drug_id in enumerate(DRUG_IDS):
        generic_name, strength = DRUG_NAMES[index % len(DRUG_NAMES)]
        temp_min, temp_max, humidity_min, humidity_max = STORAGE_RANGES[
            index % len(STORAGE_RANGES)
        ]
        records.append(
            Drug(
                id=_uuid_for(drug_id),
                drug_id=drug_id,
                name=f"{generic_name.title()} {strength}",
                generic_name=generic_name,
                manufacturer=MANUFACTURERS[index % len(MANUFACTURERS)],
                dosage_form=DOSAGE_FORMS[index % len(DOSAGE_FORMS)],
                strength=strength,
                storage_min_temp=temp_min,
                storage_max_temp=temp_max,
                storage_min_humidity=humidity_min,
                storage_max_humidity=humidity_max,
                description=(
                    f"Demo product: {generic_name} in {DOSAGE_FORMS[index % len(DOSAGE_FORMS)].lower()} form."
                ),
                expiry_period_days=730 + (index % 4) * 180,
                created_at=REFERENCE_TIME,
            )
        )
    return records


def _make_batches(drugs: list[Drug]) -> list[Batch]:
    records = []
    for index, batch_id in enumerate(BATCH_IDS):
        expired = index == 3 or (index >= 6 and index % 10 == 0)
        manufacturing_date = date(2021, 1, 1) + timedelta(days=(index * 17) % 900)
        expiry_date = (
            date(2025, 12, 31)
            if index == 3
            else (
                date(2025, 1, 1) + timedelta(days=(index * 13) % 330)
                if expired
                else date(2028, 1, 1) + timedelta(days=(index * 11) % 900)
            )
        )
        records.append(
            Batch(
                id=_uuid_for(batch_id),
                batch_id=batch_id,
                drug_id=drugs[index % len(drugs)].id,
                manufacturing_date=manufacturing_date,
                expiry_date=expiry_date,
                quantity=500 + (index * 137) % 9500,
                status="EXPIRED" if expired and index != 3 else "ACTIVE",
                fabric_asset_id=None,
                last_fabric_transaction_id=None,
                created_at=REFERENCE_TIME + timedelta(minutes=index),
            )
        )
    return records


def _make_qr_records(batches: list[Batch]) -> list[QRRecord]:
    return [
        QRRecord(
            id=_uuid_for(qr_id),
            qr_id=qr_id,
            batch_id=batches[index].id,
            encoded_value=f"pharmaverse://verification?qr_id={qr_id}",
            status="INACTIVE" if index == 4 else "ACTIVE",
            created_at=REFERENCE_TIME + timedelta(minutes=index),
        )
        for index, qr_id in enumerate(QR_IDS)
    ]


def _make_rfid_records(batches: list[Batch]) -> list[RFIDRecord]:
    return [
        RFIDRecord(
            id=_uuid_for(rfid_id),
            rfid_id=rfid_id,
            batch_id=batches[index].id,
            tag_value=f"PV-RFID-{index + 1:06d}",
            status="INACTIVE" if index == 5 else "ACTIVE",
            created_at=REFERENCE_TIME + timedelta(minutes=index),
        )
        for index, rfid_id in enumerate(RFID_IDS)
    ]


def _make_shipments(batches: list[Batch]) -> list[Shipment]:
    records = []
    for index, shipment_id in enumerate(SHIPMENT_IDS):
        status = ("CREATED", "IN_TRANSIT", "DELIVERED")[index % 3]
        source = SOURCE_SITES[index % len(SOURCE_SITES)]
        destination = DESTINATIONS[index % len(DESTINATIONS)]
        departure = REFERENCE_TIME + timedelta(days=index % 45)
        arrival = departure + timedelta(hours=18 + index % 30)
        owner = (
            source
            if status == "CREATED"
            else (
                LOGISTICS_PARTNERS[index % len(LOGISTICS_PARTNERS)]
                if status == "IN_TRANSIT"
                else destination
            )
        )
        records.append(
            Shipment(
                id=_uuid_for(shipment_id),
                shipment_id=shipment_id,
                batch_id=batches[index % len(batches)].id,
                source_location=source,
                destination_location=destination,
                current_owner=owner,
                status=status,
                expected_departure=departure,
                actual_departure=(
                    departure if status in ("IN_TRANSIT", "DELIVERED") else None
                ),
                expected_arrival=arrival,
                actual_arrival=arrival if status == "DELIVERED" else None,
                expected_latitude=10.0 + (index % 25) * 0.4,
                expected_longitude=72.0 + (index % 30) * 0.5,
                current_latitude=10.1 + (index % 25) * 0.4,
                current_longitude=72.1 + (index % 30) * 0.5,
                created_at=REFERENCE_TIME + timedelta(minutes=index),
            )
        )
    return records


def _counts(session: Session) -> dict[str, int]:
    return {
        "drugs": session.query(Drug).filter(Drug.drug_id.in_(DRUG_IDS)).count(),
        "batches": session.query(Batch).filter(Batch.batch_id.in_(BATCH_IDS)).count(),
        "qr_records": session.query(QRRecord).filter(QRRecord.qr_id.in_(QR_IDS)).count(),
        "rfid_records": session.query(RFIDRecord).filter(
            RFIDRecord.rfid_id.in_(RFID_IDS)
        ).count(),
        "shipments": session.query(Shipment).filter(
            Shipment.shipment_id.in_(SHIPMENT_IDS)
        ).count(),
    }


def _expected_counts() -> dict[str, int]:
    return {
        "drugs": DRUG_COUNT,
        "batches": BATCH_COUNT,
        "qr_records": QR_COUNT,
        "rfid_records": RFID_COUNT,
        "shipments": SHIPMENT_COUNT,
    }


def seed(session: Session) -> dict[str, int]:
    """Create the demo dataset once; refuse to extend an incomplete prior seed."""
    current = _counts(session)
    expected = _expected_counts()
    if current == expected:
        return {key: 0 for key in expected}
    if any(current.values()):
        raise RuntimeError(
            "A partial demo dataset already exists. Run 'clear' or "
            "'reset' before seeding again."
        )

    drugs = _make_drugs()
    batches = _make_batches(drugs)
    try:
        session.add_all(drugs)
        session.flush()
        session.add_all(batches)
        session.flush()
        session.add_all(_make_qr_records(batches))
        session.add_all(_make_rfid_records(batches))
        session.add_all(_make_shipments(batches))
        session.commit()
    except Exception:
        session.rollback()
        raise
    return expected


def clear(session: Session) -> dict[str, int]:
    """Remove only records whose public identifiers are generated by this seed."""
    deleted = {}
    try:
        for label, model, column, identifiers in (
            ("shipments", Shipment, Shipment.shipment_id, SHIPMENT_IDS),
            ("qr_records", QRRecord, QRRecord.qr_id, QR_IDS),
            ("rfid_records", RFIDRecord, RFIDRecord.rfid_id, RFID_IDS),
            ("batches", Batch, Batch.batch_id, BATCH_IDS),
            ("drugs", Drug, Drug.drug_id, DRUG_IDS),
        ):
            deleted[label] = (
                session.query(model).filter(column.in_(identifiers)).delete(
                    synchronize_session=False
                )
            )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return deleted


def reset(session: Session) -> tuple[dict[str, int], dict[str, int]]:
    """Recreate the dataset after removing only the seed's generated records."""
    deleted = clear(session)
    created = seed(session)
    return deleted, created


def _print_summary(command: str, counts: dict[str, int]) -> None:
    print(f"Demo data {command} complete:")
    for entity, count in counts.items():
        print(f"  {entity}: {count}")
    if command in ("seed", "reset"):
        print("Known manual verification cases:")
        for case_name, identifiers in KNOWN_CASE_IDS.items():
            print(f"  {case_name}: " + ", ".join(
                f"{key}={value}" for key, value in identifiers.items()
            ))
        print("  QR mismatch test: batch_id with mismatched_qr_id")
        print("  RFID mismatch test: batch_id with mismatched_rfid_id")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("seed", "clear", "reset"))
    args = parser.parse_args(argv)
    with SessionLocal() as session:
        if args.command == "seed":
            counts = seed(session)
        elif args.command == "clear":
            counts = clear(session)
        else:
            deleted, created = reset(session)
            counts = {f"deleted_{key}": value for key, value in deleted.items()}
            counts.update({f"created_{key}": value for key, value in created.items()})
    _print_summary(args.command, counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
