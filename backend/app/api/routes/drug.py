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
from app.models.drug import Drug
from app.models.user import User
from app.schemas.drug import DrugCreate, DrugResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/drugs",
    tags=["Drugs"],
)


@router.post(
    "",
    response_model=DrugResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_drug(
    drug_data: DrugCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("ADMIN", "REGULATOR", "MANUFACTURER")
    ),
):
    existing_drug = db.query(Drug).filter(
        Drug.drug_id == drug_data.drug_id
    ).first()

    if existing_drug:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Drug ID already exists",
        )

    fabric_tx_id = None
    if settings.fabric_enabled:
        try:
            fabric_result = FabricClient().register_drug(
                drug_id=drug_data.drug_id,
                name=drug_data.name,
                strength=drug_data.strength or "Standard",
                manufacturer=drug_data.manufacturer,
            )
            if isinstance(fabric_result, dict):
                fabric_tx_id = fabric_result.get("transactionId")
        except FabricDuplicateAssetError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Drug {drug_data.drug_id} already exists on the blockchain ledger",
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

    drug = Drug(
        drug_id=drug_data.drug_id,
        name=drug_data.name,
        generic_name=drug_data.generic_name,
        manufacturer=drug_data.manufacturer,
        dosage_form=drug_data.dosage_form,
        strength=drug_data.strength,
        storage_min_temp=drug_data.storage_min_temp,
        storage_max_temp=drug_data.storage_max_temp,
        storage_min_humidity=drug_data.storage_min_humidity,
        storage_max_humidity=drug_data.storage_max_humidity,
        description=drug_data.description,
        expiry_period_days=drug_data.expiry_period_days,
        fabric_asset_id=drug_data.drug_id if fabric_tx_id else None,
        last_fabric_transaction_id=str(fabric_tx_id) if fabric_tx_id else None,
    )

    try:
        db.add(drug)
        db.commit()
        db.refresh(drug)
    except Exception as exc:
        db.rollback()
        if fabric_tx_id:
            logger.error(
                "CRITICAL: Fabric transaction %s committed for drug %s but PostgreSQL persistence failed: %s",
                fabric_tx_id, drug_data.drug_id, exc,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ledger committed transaction {fabric_tx_id}, but database persistence failed. Reconciliation required.",
            ) from exc
        raise

    return drug


@router.get(
    "",
    response_model=list[DrugResponse],
)
def list_drugs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Drug).order_by(Drug.created_at.desc()).all()


@router.get(
    "/{drug_id}",
    response_model=DrugResponse,
)
def get_drug(
    drug_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    drug = db.query(Drug).filter(
        Drug.drug_id == drug_id.strip()
    ).first()

    if not drug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drug not found",
        )

    return drug
