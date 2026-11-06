from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.blockchain.fabric_client import (
    FabricAssetNotFoundError,
    FabricClient,
    FabricGatewayError,
    FabricUnavailableError,
)
from app.core.security import get_current_user
from app.database.connection import get_db
from app.models.batch import Batch
from app.models.drug import Drug
from app.models.qr_record import QRRecord
from app.models.rfid_record import RFIDRecord
from app.models.user import User
from app.schemas.verification import (
    VerificationRequest,
    VerificationResponse,
)


router = APIRouter(
    prefix="/api/verification",
    tags=["Verification"],
)


def get_fabric_client() -> FabricClient:
    return FabricClient()


def _query_first(db: Session, model, field, value):
    return db.query(model).filter(field == value).first()


def _response(
    request: VerificationRequest,
    verification_status: str,
    message: str,
    checks_performed: list[str],
    batch: Batch | None = None,
    drug: Drug | None = None,
    database_status: str | None = None,
    blockchain_status: str | None = None,
) -> VerificationResponse:
    return VerificationResponse(
        verification_status=verification_status,
        message=message,
        qr_id=request.qr_id,
        rfid_id=request.rfid_id,
        batch_id=batch.batch_id if batch else None,
        drug_id=drug.drug_id if drug else None,
        batch_status=batch.status if batch else None,
        expiry_date=batch.expiry_date if batch else None,
        checks_performed=checks_performed,
        database_status=database_status,
        blockchain_status=blockchain_status,
    )


@router.post(
    "/verify",
    response_model=VerificationResponse,
)
def verify_item(
    request: VerificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    fabric: FabricClient = Depends(get_fabric_client),
):
    checks: list[str] = []
    resolved_batches: list[tuple[str, Batch]] = []

    batch = None
    if request.batch_id:
        checks.append("batch_id lookup")
        batch = _query_first(db, Batch, Batch.batch_id, request.batch_id)
        if not batch:
            return _response(
                request,
                "INVALID",
                "The supplied batch ID does not exist in the database.",
                checks,
            )
        resolved_batches.append(("batch_id", batch))

    drug = None
    if request.drug_id:
        checks.append("drug_id lookup")
        drug = _query_first(db, Drug, Drug.drug_id, request.drug_id)
        if not drug:
            return _response(
                request,
                "INVALID",
                "The supplied drug ID does not exist in the database.",
                checks,
                batch=batch,
            )

    qr_record = None
    if request.qr_id:
        checks.append("qr_id lookup")
        qr_record = _query_first(db, QRRecord, QRRecord.qr_id, request.qr_id)
        if not qr_record:
            return _response(
                request,
                "INVALID",
                "The supplied QR ID does not exist in the database.",
                checks,
                batch=batch,
                drug=drug,
            )
        checks.append("QR linked batch lookup")
        qr_batch = _query_first(db, Batch, Batch.id, qr_record.batch_id)
        if not qr_batch:
            return _response(
                request,
                "INVALID",
                "The QR record points to a batch that does not exist.",
                checks,
                drug=drug,
            )
        resolved_batches.append(("qr_id", qr_batch))
        if batch is None:
            batch = qr_batch

    rfid_record = None
    if request.rfid_id:
        checks.append("rfid_id lookup")
        rfid_record = _query_first(db, RFIDRecord, RFIDRecord.rfid_id, request.rfid_id)
        if not rfid_record:
            return _response(
                request,
                "INVALID",
                "The supplied RFID ID does not exist in the database.",
                checks,
                batch=batch,
                drug=drug,
            )
        checks.append("RFID linked batch lookup")
        rfid_batch = _query_first(db, Batch, Batch.id, rfid_record.batch_id)
        if not rfid_batch:
            return _response(
                request,
                "INVALID",
                "The RFID record points to a batch that does not exist.",
                checks,
                batch=batch,
                drug=drug,
            )
        resolved_batches.append(("rfid_id", rfid_batch))
        if batch is None:
            batch = rfid_batch

    if resolved_batches:
        first_batch_id = resolved_batches[0][1].id
        if any(item.id != first_batch_id for _, item in resolved_batches[1:]):
            return _response(
                request,
                "POTENTIAL_COUNTERFEIT",
                "The supplied identifiers resolve to different batches.",
                checks + ["cross-identifier batch consistency"],
                batch=batch,
                drug=drug,
            )

    if batch:
        checks.append("batch validity")
        if drug and batch.drug_id != drug.id:
            return _response(
                request,
                "POTENTIAL_COUNTERFEIT",
                "The supplied drug and batch belong to different records.",
                checks + ["batch-to-drug consistency"],
                batch=batch,
                drug=drug,
            )

        if not drug:
            checks.append("linked drug lookup")
            drug = _query_first(db, Drug, Drug.id, batch.drug_id)
            if not drug:
                return _response(
                    request,
                    "INVALID",
                    "The batch points to a drug that does not exist.",
                    checks,
                    batch=batch,
                )

    if qr_record:
        checks.append("QR status")
        if qr_record.status.upper() != "ACTIVE":
            return _response(
                request,
                "SUSPICIOUS",
                "The QR record exists but is inactive.",
                checks,
                batch=batch,
                drug=drug,
            )

    if rfid_record:
        checks.append("RFID status")
        if rfid_record.status.upper() != "ACTIVE":
            return _response(
                request,
                "SUSPICIOUS",
                "The RFID record exists but is inactive.",
                checks,
                batch=batch,
                drug=drug,
            )

    if batch and batch.status.upper() != "ACTIVE":
        return _response(
            request,
            "SUSPICIOUS",
            "The batch exists but is inactive.",
            checks,
            batch=batch,
            drug=drug,
        )

    if batch and batch.expiry_date < date.today():
        return _response(
            request,
            "SUSPICIOUS",
            "The batch exists but its expiry date has passed.",
            checks,
            batch=batch,
            drug=drug,
        )

    # A database match alone is not evidence that an asset exists on Fabric.
    # Reserve AUTHENTIC for a matching read-only ledger result.
    checks.append("Fabric batch lookup" if batch else "Fabric drug lookup")
    try:
        ledger_batch = (
            fabric.get_batch(batch.batch_id)
            if batch
            else fabric.get_drug(drug.drug_id)
        )
    except FabricAssetNotFoundError:
        return _response(
            request,
            "UNVERIFIED",
            "Database records match, but the corresponding asset is not present on the ledger.",
            checks,
            batch=batch,
            drug=drug,
            database_status="MATCHED",
            blockchain_status="ASSET_NOT_FOUND",
        )
    except FabricUnavailableError:
        return _response(
            request,
            "UNVERIFIED",
            "Database records match, but the blockchain service is unavailable.",
            checks,
            batch=batch,
            drug=drug,
            database_status="MATCHED",
            blockchain_status="UNAVAILABLE",
        )
    except FabricGatewayError:
        return _response(
            request,
            "UNVERIFIED",
            "Database records match, but the ledger response could not be verified.",
            checks,
            batch=batch,
            drug=drug,
            database_status="MATCHED",
            blockchain_status="ERROR",
        )

    expected = {"drugId": drug.drug_id}
    if batch:
        expected["batchId"] = batch.batch_id
    if request.qr_id and batch:
        expected["qrId"] = request.qr_id
    if request.rfid_id and batch:
        expected["rfidId"] = request.rfid_id
    if not isinstance(ledger_batch, dict):
        return _response(
            request,
            "UNVERIFIED",
            "Database records match, but the ledger returned an invalid asset payload.",
            checks,
            batch=batch,
            drug=drug,
            database_status="MATCHED",
            blockchain_status="MALFORMED",
        )
    if any(ledger_batch.get(field) != value for field, value in expected.items()):
        return _response(
            request,
            "SUSPICIOUS",
            "Database and ledger identities do not match.",
            checks + ["database-to-ledger consistency"],
            batch=batch,
            drug=drug,
            database_status="MATCHED",
            blockchain_status="MISMATCH",
        )

    return _response(
        request,
        "AUTHENTIC",
        "Database records and the ledger asset resolve consistently.",
        checks + ["database-to-ledger consistency"],
        batch=batch,
        drug=drug,
        database_status="MATCHED",
        blockchain_status="VERIFIED",
    )
