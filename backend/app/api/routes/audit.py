import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.blockchain.fabric_client import (
    FabricAssetNotFoundError,
    FabricClient,
    FabricGatewayError,
    FabricUnavailableError,
)
from app.core.config import settings
from app.core.security import get_current_user
from app.database.connection import get_db
from app.models.batch import Batch
from app.models.drug import Drug
from app.models.qr_record import QRRecord
from app.models.rfid_record import RFIDRecord
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas.audit import (
    AuditBatchResponse,
    AuditDrugResponse,
    AuditQRResponse,
    AuditRFIDResponse,
    AuditShipmentResponse,
)
from app.services.batch_lookup import get_batch_or_404

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/audit",
    tags=["Audit"],
)


@router.get(
    "/batch/{batch_id}",
    response_model=AuditBatchResponse,
)
def trace_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    batch = get_batch_or_404(db, batch_id)

    drug = db.query(Drug).filter(
        Drug.id == batch.drug_id
    ).first()

    shipments = db.query(Shipment).filter(
        Shipment.batch_id == batch.id
    ).order_by(
        Shipment.created_at.desc()
    ).all()

    qr_records = db.query(QRRecord).filter(
        QRRecord.batch_id == batch.id
    ).order_by(
        QRRecord.created_at.desc()
    ).all()

    rfid_records = db.query(RFIDRecord).filter(
        RFIDRecord.batch_id == batch.id
    ).order_by(
        RFIDRecord.created_at.desc()
    ).all()

    trace_source = "POSTGRESQL"
    fabric_history = None
    if settings.fabric_enabled:
        try:
            history_data = FabricClient().get_batch_history(batch.batch_id)
            if isinstance(history_data, list):
                fabric_history = history_data
                trace_source = "POSTGRESQL_AND_FABRIC"
            elif isinstance(history_data, dict):
                fabric_history = [history_data]
                trace_source = "POSTGRESQL_AND_FABRIC"
        except (FabricAssetNotFoundError, FabricUnavailableError, FabricGatewayError) as exc:
            logger.debug("Fabric batch history not available for %s: %s", batch.batch_id, exc)
            trace_source = "POSTGRESQL"

    return AuditBatchResponse(
        trace_source=trace_source,
        batch_id=batch.batch_id,
        drug_id=drug.drug_id if drug else None,
        manufacturing_date=batch.manufacturing_date,
        expiry_date=batch.expiry_date,
        quantity=batch.quantity,
        batch_status=batch.status,
        created_at=batch.created_at,
        drug=(
            AuditDrugResponse(
                drug_id=drug.drug_id,
                name=drug.name,
                generic_name=drug.generic_name,
                manufacturer=drug.manufacturer,
                dosage_form=drug.dosage_form,
                strength=drug.strength,
                storage_min_temp=drug.storage_min_temp,
                storage_max_temp=drug.storage_max_temp,
                storage_min_humidity=drug.storage_min_humidity,
                storage_max_humidity=drug.storage_max_humidity,
            )
            if drug
            else None
        ),
        shipments=[
            AuditShipmentResponse(
                shipment_id=shipment.shipment_id,
                source=shipment.source_location,
                destination=shipment.destination_location,
                current_owner=shipment.current_owner,
                status=shipment.status,
                expected_departure=shipment.expected_departure,
                actual_departure=shipment.actual_departure,
                expected_arrival=shipment.expected_arrival,
                actual_arrival=shipment.actual_arrival,
                expected_latitude=shipment.expected_latitude,
                expected_longitude=shipment.expected_longitude,
                current_latitude=shipment.current_latitude,
                current_longitude=shipment.current_longitude,
                created_at=shipment.created_at,
            )
            for shipment in shipments
        ],
        qr_records=[
            AuditQRResponse(
                qr_id=qr_record.qr_id,
                status=qr_record.status,
                created_at=qr_record.created_at,
            )
            for qr_record in qr_records
        ],
        rfid_records=[
            AuditRFIDResponse(
                rfid_id=rfid_record.rfid_id,
                status=rfid_record.status,
                created_at=rfid_record.created_at,
            )
            for rfid_record in rfid_records
        ],
        fabric_history=fabric_history,
    )
