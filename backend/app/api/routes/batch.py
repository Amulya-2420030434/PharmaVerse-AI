import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.blockchain.fabric_client import (
    FabricAssetNotFoundError,
    FabricClient,
    FabricDuplicateAssetError,
    FabricGatewayError,
    FabricUnavailableError,
)
from app.core.config import settings
from app.core.security import get_current_user, require_roles
from app.database.connection import get_db
from app.models.batch import Batch
from app.models.drug import Drug
from app.models.user import User
from app.schemas.batch import BatchCreate, BatchResponse
from app.services.batch_lookup import get_batch_or_404

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/batches",
    tags=["Batches"],
)


@router.post(
    "",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_batch(
    batch_data: BatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("ADMIN", "REGULATOR", "MANUFACTURER")
    ),
):
    # Check Drug exists in PostgreSQL
    drug = db.query(Drug).filter(
        Drug.drug_id == batch_data.drug_id
    ).first()

    if not drug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drug not found",
        )

    # Check Batch ID uniqueness
    existing_batch = db.query(Batch).filter(
        Batch.batch_id == batch_data.batch_id
    ).first()

    if existing_batch:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Batch ID already exists",
        )

    # Validate dates
    if batch_data.expiry_date <= batch_data.manufacturing_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expiry date must be after manufacturing date",
        )

    fabric_tx_id = None
    if settings.fabric_enabled:
        try:
            fabric_result = FabricClient().create_batch(
                batch_id=batch_data.batch_id,
                drug_id=drug.drug_id,
                manufacturer=drug.manufacturer,
                quantity=batch_data.quantity,
                manufactured_date=str(batch_data.manufacturing_date),
                expiry_date=str(batch_data.expiry_date),
            )
            if isinstance(fabric_result, dict):
                fabric_tx_id = fabric_result.get("transactionId")
        except FabricDuplicateAssetError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Batch {batch_data.batch_id} already exists on the blockchain ledger",
            ) from exc
        except FabricUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Blockchain service unavailable: {exc}",
            ) from exc
        except FabricGatewayError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Fabric ledger transaction failed: {exc}",
            ) from exc

    batch = Batch(
        batch_id=batch_data.batch_id,
        drug_id=drug.id,
        manufacturing_date=batch_data.manufacturing_date,
        expiry_date=batch_data.expiry_date,
        quantity=batch_data.quantity,
        status=batch_data.status,
        fabric_asset_id=batch_data.batch_id if fabric_tx_id else None,
        last_fabric_transaction_id=str(fabric_tx_id) if fabric_tx_id else None,
    )

    try:
        db.add(batch)
        db.commit()
        db.refresh(batch)
    except Exception as exc:
        db.rollback()
        if fabric_tx_id:
            logger.error(
                "CRITICAL: Fabric transaction %s committed for batch %s but PostgreSQL persistence failed: %s",
                fabric_tx_id, batch_data.batch_id, exc,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ledger committed transaction {fabric_tx_id}, but database persistence failed. Reconciliation required.",
            ) from exc
        raise

    return batch


@router.get(
    "",
    response_model=list[BatchResponse],
)
def list_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Batch).order_by(
        Batch.created_at.desc()
    ).all()


@router.get(
    "/{batch_id}",
    response_model=BatchResponse,
)
def get_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_batch_or_404(db, batch_id)
