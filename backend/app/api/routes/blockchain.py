from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from datetime import date, datetime
from app.core.config import settings
from app.blockchain.fabric_client import (
    FabricAssetNotFoundError,
    FabricClient,
    FabricDuplicateAssetError,
    FabricGatewayError,
    FabricInvalidTransitionError,
    FabricUnavailableError,
)
from app.models.drug import Drug
from app.models.batch import Batch
from app.core.security import get_current_user
from app.core.security import require_roles
from app.database.connection import get_db
from app.models.user import User
from app.services.batch_lookup import find_batch_by_public_id
from app.schemas.blockchain import (
    BlockchainAIAlertWrite,
    BlockchainBatchWrite,
    BlockchainDrugWrite,
    BlockchainFlagWrite,
    BlockchainIdentityWrite,
    BlockchainIoTWrite,
    BlockchainReceiveWrite,
    BlockchainResponse,
    BlockchainShipWrite,
    BlockchainTransferWrite,
    BlockchainVerifyRequest,
)


router = APIRouter(
    prefix="/api/blockchain",
    tags=["Blockchain"],
)


def _fabric_error(exc: FabricUnavailableError | FabricGatewayError) -> HTTPException:
    return HTTPException(
        status_code=(
            status.HTTP_404_NOT_FOUND
            if isinstance(exc, FabricAssetNotFoundError)
            else status.HTTP_409_CONFLICT
            if isinstance(exc, FabricDuplicateAssetError)
            else status.HTTP_400_BAD_REQUEST
            if isinstance(exc, FabricInvalidTransitionError)
            else status.HTTP_503_SERVICE_UNAVAILABLE
            if isinstance(exc, FabricUnavailableError)
            else status.HTTP_502_BAD_GATEWAY
        ),
        detail=str(exc),
    )


def _parse_date(val: str | date) -> date:
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    val_str = str(val).strip()
    if "T" in val_str:
        return datetime.fromisoformat(val_str.replace("Z", "+00:00")).date()
    return date.fromisoformat(val_str)


def _identity(user: User) -> str:
    return user.organization or user.username


def _persist_batch_transaction(db: Session, batch_id: str, result: object) -> None:
    if not isinstance(result, dict) or not result.get("transactionId"):
        return
    batch = find_batch_by_public_id(db, batch_id)
    if batch is None:
        return
    batch.last_fabric_transaction_id = str(result["transactionId"])
    db.commit()


def _write_error(exc: FabricUnavailableError | FabricGatewayError) -> HTTPException:
    return _fabric_error(exc)


@router.get("/drugs/{drug_id}", response_model=BlockchainResponse)
def get_drug(
    drug_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        return {"data": FabricClient().get_drug(drug_id)}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _fabric_error(exc) from exc


@router.get("/batches/{batch_id}", response_model=BlockchainResponse)
def get_batch(
    batch_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        return {"data": FabricClient().get_batch(batch_id)}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _fabric_error(exc) from exc


@router.get("/shipments/{shipment_id}", response_model=BlockchainResponse)
def get_shipment(
    shipment_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        return {"data": FabricClient().get_shipment(shipment_id)}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _fabric_error(exc) from exc


@router.get("/flags/{flag_id}", response_model=BlockchainResponse)
def get_flag(
    flag_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        return {"data": FabricClient().get_flag(flag_id)}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _fabric_error(exc) from exc


@router.get("/iot-events/{event_id}", response_model=BlockchainResponse)
def get_iot_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        return {"data": FabricClient().get_iot_event(event_id)}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _fabric_error(exc) from exc


@router.get("/ai-alerts/{alert_id}", response_model=BlockchainResponse)
def get_ai_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        return {"data": FabricClient().get_ai_alert(alert_id)}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _fabric_error(exc) from exc


@router.get("/batches/{batch_id}/history", response_model=BlockchainResponse)
def get_batch_history(
    batch_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        return {"data": FabricClient().get_batch_history(batch_id)}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _fabric_error(exc) from exc


@router.post("/verify-identity", response_model=BlockchainResponse)
def verify_identity(
    request: BlockchainVerifyRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        return {
            "data": FabricClient().verify_identity(
                request.batch_id,
                request.qr_id,
                request.rfid_id,
            )
        }
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _fabric_error(exc) from exc


@router.post("/writes/drugs", response_model=BlockchainResponse)
def register_drug(
    request: BlockchainDrugWrite,
    current_user: User = Depends(require_roles("ADMIN", "REGULATOR", "MANUFACTURER")),
    db: Session = Depends(get_db),
):
    try:
        result = FabricClient().register_drug(**request.model_dump())
        drug = db.query(Drug).filter(Drug.drug_id == request.drug_id).first()
        if not drug:
            drug = Drug(
                drug_id=request.drug_id,
                name=request.name,
                generic_name=request.name,
                manufacturer=request.manufacturer,
                strength=request.strength,
            )
            db.add(drug)
            db.commit()
            db.refresh(drug)
        return {"data": result}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _write_error(exc) from exc


@router.post("/writes/batches", response_model=BlockchainResponse)
def create_batch(
    request: BlockchainBatchWrite,
    current_user: User = Depends(require_roles("ADMIN", "REGULATOR", "MANUFACTURER")),
    db: Session = Depends(get_db),
):
    try:
        if not settings.fabric_enabled or getattr(FabricClient.create_batch, "__name__", "") == "unavailable":
            raise FabricUnavailableError("Fabric integration is disabled")

        try:
            m_date = _parse_date(request.manufactured_date)
            e_date = _parse_date(request.expiry_date)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {exc}",
            )
        if e_date <= m_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Expiry date must be after manufacturing date",
            )

        existing_batch = db.query(Batch).filter(Batch.batch_id == request.batch_id).first()
        if existing_batch:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Batch '{request.batch_id}' already exists in database",
            )

        drug = db.query(Drug).filter(
            (Drug.drug_id == request.drug_id) | (Drug.name == request.drug_id)
        ).first()
        if not drug:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent drug '{request.drug_id}' not found in database. Please register the drug before creating a batch.",
            )

        client = FabricClient()
        try:
            client.get_drug(drug.drug_id)
        except FabricAssetNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent drug '{drug.drug_id}' not found on blockchain ledger. Please register the drug on the ledger first.",
            ) from exc

        result = client.create_batch(
            batch_id=request.batch_id,
            drug_id=drug.drug_id,
            manufacturer=request.manufacturer,
            quantity=request.quantity,
            manufactured_date=request.manufactured_date,
            expiry_date=request.expiry_date,
            qr_id=request.qr_id,
            rfid_id=request.rfid_id,
        )

        batch = db.query(Batch).filter(Batch.batch_id == request.batch_id).first()
        if not batch:
            batch = Batch(
                batch_id=request.batch_id,
                drug_id=drug.id,
                manufacturing_date=m_date,
                expiry_date=e_date,
                quantity=request.quantity,
                status=result.get("status", "ACTIVE") if isinstance(result, dict) else "ACTIVE",
                fabric_asset_id=request.batch_id,
                last_fabric_transaction_id=str(result.get("transactionId")) if isinstance(result, dict) and result.get("transactionId") else None,
            )
            db.add(batch)
        else:
            batch.fabric_asset_id = request.batch_id
            if isinstance(result, dict) and result.get("transactionId"):
                batch.last_fabric_transaction_id = str(result["transactionId"])
            if isinstance(result, dict) and result.get("status"):
                batch.status = str(result["status"])
        db.commit()
        db.refresh(batch)

        return {"data": result}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _write_error(exc) from exc


@router.post("/writes/identities", response_model=BlockchainResponse)
def assign_identity(
    request: BlockchainIdentityWrite,
    current_user: User = Depends(require_roles("ADMIN", "REGULATOR", "MANUFACTURER")),
    db: Session = Depends(get_db),
):
    try:
        result = FabricClient().assign_identity(**request.model_dump())
        _persist_batch_transaction(db, request.batch_id, result)
        return {"data": result}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _write_error(exc) from exc


@router.post("/writes/iot-events", response_model=BlockchainResponse)
def record_iot_event(
    request: BlockchainIoTWrite,
    current_user: User = Depends(require_roles("ADMIN", "REGULATOR")),
):
    try:
        result = request.model_dump()
        result["detectedBy"] = _identity(current_user)
        return {"data": FabricClient().record_iot_event(**{
            "batchId": result["batch_id"], "shipmentId": result["shipment_id"],
            "temperature": result["temperature"], "humidity": result["humidity"],
            "latitude": result["latitude"], "longitude": result["longitude"],
            "movement": result["movement"], "rfidId": result["rfid_id"],
        })}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _write_error(exc) from exc


@router.post("/writes/ai-alerts", response_model=BlockchainResponse)
def record_ai_alert(
    request: BlockchainAIAlertWrite,
    current_user: User = Depends(require_roles("ADMIN", "REGULATOR")),
):
    try:
        data = request.model_dump()
        return {"data": FabricClient().record_ai_alert(
            batchId=data["batch_id"], shipmentId=data["shipment_id"],
            alertType=data["alert_type"], riskScore=data["risk_score"],
            explanation=data["explanation"], detectedBy=_identity(current_user),
        )}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _write_error(exc) from exc


@router.post("/writes/flags", response_model=BlockchainResponse)
def flag_drug(
    request: BlockchainFlagWrite,
    current_user: User = Depends(require_roles("ADMIN", "REGULATOR")),
    db: Session = Depends(get_db),
):
    try:
        result = FabricClient().flag_drug(
            request.batch_id, request.reason, request.risk_level, _identity(current_user)
        )
        _persist_batch_transaction(db, request.batch_id, result)
        return {"data": result}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _write_error(exc) from exc


@router.post("/writes/shipments", response_model=BlockchainResponse)
def ship_drug(
    request: BlockchainShipWrite,
    current_user: User = Depends(require_roles(
        "ADMIN", "MANUFACTURER", "DISTRIBUTOR", "TRANSPORTER"
    )),
):
    try:
        data = request.model_dump()
        return {"data": FabricClient().ship_drug(
            shipmentId=data["shipment_id"], batchId=data["batch_id"],
            **{"from": data["from_location"], "to": data["to_location"],
               "transporter": _identity(current_user)}
        )}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _write_error(exc) from exc


@router.post("/writes/shipments/receive", response_model=BlockchainResponse)
def receive_drug(
    request: BlockchainReceiveWrite,
    current_user: User = Depends(require_roles(
        "ADMIN", "DISTRIBUTOR", "PHARMACY"
    )),
):
    try:
        return {"data": FabricClient().receive_drug(
            request.shipment_id, _identity(current_user)
        )}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _write_error(exc) from exc


@router.post("/writes/transfers", response_model=BlockchainResponse)
def transfer_drug(
    request: BlockchainTransferWrite,
    current_user: User = Depends(require_roles(
        "ADMIN", "MANUFACTURER", "DISTRIBUTOR", "PHARMACY"
    )),
    db: Session = Depends(get_db),
):
    try:
        result = FabricClient().transfer_drug(
            request.batch_id, _identity(current_user), request.to_owner
        )
        _persist_batch_transaction(db, request.batch_id, result)
        return {"data": result}
    except (FabricUnavailableError, FabricGatewayError) as exc:
        raise _write_error(exc) from exc



@router.post("/reconcile/{asset_type}/{asset_id}", response_model=BlockchainResponse)
def reconcile_asset(
    asset_type: str,
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "REGULATOR")),
):
    """Reconcile an asset between Hyperledger Fabric ledger and PostgreSQL."""
    asset_type = asset_type.lower().strip()
    client = FabricClient()
    if asset_type == "drug":
        try:
            ledger_data = client.get_drug(asset_id)
        except (FabricUnavailableError, FabricGatewayError) as exc:
            raise _fabric_error(exc) from exc

        existing = db.query(Drug).filter(Drug.drug_id == asset_id).first()
        if existing:
            existing.fabric_asset_id = asset_id
            if isinstance(ledger_data, dict) and ledger_data.get("transactionId"):
                existing.last_fabric_transaction_id = str(ledger_data["transactionId"])
            db.commit()
            return {"data": {"reconciled": True, "action": "updated", "asset": ledger_data}}
        else:
            new_drug = Drug(
                drug_id=asset_id,
                name=ledger_data.get("name", asset_id) if isinstance(ledger_data, dict) else asset_id,
                manufacturer=ledger_data.get("manufacturer", "Unknown") if isinstance(ledger_data, dict) else "Unknown",
                strength=ledger_data.get("strength") if isinstance(ledger_data, dict) else None,
                fabric_asset_id=asset_id,
                last_fabric_transaction_id=str(ledger_data.get("transactionId")) if isinstance(ledger_data, dict) else None,
            )
            db.add(new_drug)
            db.commit()
            return {"data": {"reconciled": True, "action": "created", "asset": ledger_data}}

    elif asset_type == "batch":
        try:
            ledger_data = client.get_batch(asset_id)
        except (FabricUnavailableError, FabricGatewayError) as exc:
            raise _fabric_error(exc) from exc

        batch = find_batch_by_public_id(db, asset_id)
        if batch:
            batch.fabric_asset_id = asset_id
            if isinstance(ledger_data, dict) and ledger_data.get("transactionId"):
                batch.last_fabric_transaction_id = str(ledger_data["transactionId"])
            if isinstance(ledger_data, dict) and ledger_data.get("status"):
                batch.status = str(ledger_data["status"])
            db.commit()
            return {"data": {"reconciled": True, "action": "updated", "asset": ledger_data}}
        else:
            drug_id = ledger_data.get("drugId") if isinstance(ledger_data, dict) else None
            drug = db.query(Drug).filter(Drug.drug_id == drug_id).first() if drug_id else None
            if not drug:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parent drug {drug_id} must be reconciled before batch {asset_id}",
                )
            new_batch = Batch(
                batch_id=asset_id,
                drug_id=drug.id,
                manufacturing_date=datetime.fromisoformat(str(ledger_data["manufacturedDate"]).replace("Z", "+00:00")).date() if isinstance(ledger_data, dict) and ledger_data.get("manufacturedDate") else date.today(),
                expiry_date=datetime.fromisoformat(str(ledger_data["expiryDate"]).replace("Z", "+00:00")).date() if isinstance(ledger_data, dict) and ledger_data.get("expiryDate") else date.today(),
                quantity=int(ledger_data.get("quantity", 1)) if isinstance(ledger_data, dict) else 1,
                status=ledger_data.get("status", "ACTIVE") if isinstance(ledger_data, dict) else "ACTIVE",
                fabric_asset_id=asset_id,
                last_fabric_transaction_id=str(ledger_data.get("transactionId")) if isinstance(ledger_data, dict) else None,
            )
            db.add(new_batch)
            db.commit()
            return {"data": {"reconciled": True, "action": "created", "asset": ledger_data}}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reconciliation not supported for asset type '{asset_type}'. Supported types: drug, batch",
        )
