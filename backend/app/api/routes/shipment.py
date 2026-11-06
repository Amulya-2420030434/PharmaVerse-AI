import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.blockchain.fabric_client import (
    FabricAssetNotFoundError,
    FabricClient,
    FabricDuplicateAssetError,
    FabricGatewayError,
    FabricInvalidTransitionError,
    FabricUnavailableError,
)
from app.core.config import settings
from app.core.security import get_current_user, require_roles
from app.database.connection import get_db
from app.models.batch import Batch
from app.models.shipment import Shipment
from app.models.shipment_tracking_event import ShipmentTrackingEvent
from app.models.user import User
from app.schemas.shipment import ShipmentCreate, ShipmentResponse, ShipmentTransfer
from app.services.batch_lookup import get_batch_or_404

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/shipments",
    tags=["Shipments"],
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _add_tracking_event(
    db: Session,
    shipment: Shipment,
    *,
    event_type: str,
    status_value: str,
    location_name: str | None,
    event_time: datetime,
    expected_time: datetime | None = None,
    description: str | None = None,
) -> None:
    last_sequence = (
        db.query(func.max(ShipmentTrackingEvent.sequence_number))
        .filter(ShipmentTrackingEvent.shipment_id == getattr(shipment, "id", None))
        .scalar()
        or 0
    )
    db.add(
        ShipmentTrackingEvent(
            shipment_id=shipment.id,
            event_type=event_type,
            status=status_value,
            location_name=location_name,
            latitude=(
                getattr(shipment, "current_latitude", None)
                if event_type == "CHECKPOINT"
                else None
            ),
            longitude=(
                getattr(shipment, "current_longitude", None)
                if event_type == "CHECKPOINT"
                else None
            ),
            event_time=_as_utc(event_time),
            expected_time=_as_utc(expected_time),
            description=description,
            sequence_number=last_sequence + 1,
        )
    )


def _get_shipment_or_404(shipment_id: str, db: Session) -> Shipment:
    shipment = db.query(Shipment).filter(
        Shipment.shipment_id == shipment_id.strip()
    ).first()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        )

    return shipment


@router.post(
    "",
    response_model=ShipmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_shipment(
    shipment_data: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("ADMIN", "REGULATOR", "MANUFACTURER")
    ),
):
    batch = get_batch_or_404(db, shipment_data.batch_id)

    existing_shipment = db.query(Shipment).filter(
        Shipment.shipment_id == shipment_data.shipment_id
    ).first()

    if existing_shipment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shipment ID already exists",
        )

    if (
        shipment_data.expected_departure
        and shipment_data.expected_arrival
        and shipment_data.expected_arrival <= shipment_data.expected_departure
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expected arrival must be after expected departure",
        )

    shipment = Shipment(
        shipment_id=shipment_data.shipment_id,
        batch_id=batch.id,
        source_location=shipment_data.source,
        destination_location=shipment_data.destination,
        current_owner=shipment_data.current_owner,
        status=shipment_data.status,
        expected_departure=shipment_data.expected_departure,
        expected_arrival=shipment_data.expected_arrival,
        expected_latitude=shipment_data.expected_latitude,
        expected_longitude=shipment_data.expected_longitude,
    )

    db.add(shipment)
    db.flush()
    _add_tracking_event(
        db,
        shipment,
        event_type="CREATED",
        status_value="CREATED",
        location_name=getattr(shipment, "source_location", None),
        event_time=datetime.now(timezone.utc),
        expected_time=shipment.expected_departure,
        description="Shipment created.",
    )
    db.commit()
    db.refresh(shipment)

    return shipment


@router.get(
    "",
    response_model=list[ShipmentResponse],
)
def list_shipments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Shipment).order_by(
        Shipment.created_at.desc()
    ).all()


@router.get(
    "/{shipment_id}",
    response_model=ShipmentResponse,
)
def get_shipment(
    shipment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_shipment_or_404(shipment_id, db)


@router.get("/{shipment_id}/tracking")
def get_shipment_tracking(
    shipment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    shipment = _get_shipment_or_404(shipment_id, db)
    events = (
        db.query(ShipmentTrackingEvent)
        .filter(ShipmentTrackingEvent.shipment_id == shipment.id)
        .order_by(
            ShipmentTrackingEvent.sequence_number,
            ShipmentTrackingEvent.event_time,
        )
        .all()
    )
    return {
        "shipment_id": shipment.shipment_id,
        "batch_id": shipment.batch.batch_id,
        "events": events,
    }


@router.post(
    "/{shipment_id}/depart",
    response_model=ShipmentResponse,
)
def depart_shipment(
    shipment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("ADMIN", "MANUFACTURER", "DISTRIBUTOR", "TRANSPORTER")
    ),
):
    shipment = _get_shipment_or_404(shipment_id, db)

    if shipment.status != "CREATED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only shipments in CREATED status can depart "
                f"(current status: {shipment.status})"
            ),
        )

    transporter_party = (
        shipment.current_owner
        or getattr(current_user, "organization", None)
        or getattr(current_user, "username", "transporter")
    )

    batch_obj = getattr(shipment, "batch", None)
    batch_public_id = getattr(batch_obj, "batch_id", None) if batch_obj else None
    if not batch_public_id and hasattr(shipment, "batch_id"):
        try:
            batch_record = db.query(Batch).filter(Batch.id == shipment.batch_id).first()
            batch_public_id = batch_record.batch_id if batch_record else str(shipment.batch_id)
        except Exception:
            batch_public_id = str(shipment.batch_id)

    fabric_tx_id = None
    if settings.fabric_enabled and batch_public_id:
        try:
            fabric_result = FabricClient().ship_drug(
                shipmentId=shipment.shipment_id,
                batchId=batch_public_id,
                **{
                    "from": shipment.source_location,
                    "to": shipment.destination_location,
                    "transporter": transporter_party,
                },
            )
            if isinstance(fabric_result, dict):
                fabric_tx_id = fabric_result.get("transactionId")
        except FabricDuplicateAssetError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Shipment {shipment.shipment_id} already exists on the blockchain ledger",
            ) from exc
        except FabricUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Blockchain service unavailable: {exc}",
            ) from exc
        except FabricGatewayError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Fabric ledger shipment dispatch failed: {exc}",
            ) from exc

    shipment.status = "IN_TRANSIT"
    shipment.actual_departure = _utc_now()
    if fabric_tx_id:
        shipment.fabric_asset_id = shipment.shipment_id
        shipment.last_fabric_transaction_id = str(fabric_tx_id)
        if shipment.batch:
            shipment.batch.last_fabric_transaction_id = str(fabric_tx_id)

    _add_tracking_event(
        db,
        shipment,
        event_type="DEPARTED",
        status_value="IN_TRANSIT",
        location_name=getattr(shipment, "source_location", None),
        event_time=datetime.now(timezone.utc),
        expected_time=getattr(shipment, "expected_departure", None),
        description=f"Shipment departed from the source (Fabric Tx: {fabric_tx_id or 'none'}).",
    )
    db.commit()
    db.refresh(shipment)

    return shipment


@router.post(
    "/{shipment_id}/receive",
    response_model=ShipmentResponse,
)
def receive_shipment(
    shipment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("ADMIN", "DISTRIBUTOR", "PHARMACY")
    ),
):
    shipment = _get_shipment_or_404(shipment_id, db)

    if shipment.status != "IN_TRANSIT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only shipments in transit can be received",
        )

    receiver_party = (
        getattr(current_user, "organization", None)
        or getattr(current_user, "username", "receiver")
    )

    fabric_tx_id = None
    has_fabric_record = bool(getattr(shipment, "fabric_asset_id", None) or getattr(shipment, "last_fabric_transaction_id", None))
    if settings.fabric_enabled and has_fabric_record:
        try:
            fabric_result = FabricClient().receive_drug(
                shipment_id=shipment.shipment_id,
                receiver=receiver_party,
            )
            if isinstance(fabric_result, dict):
                fabric_tx_id = fabric_result.get("receiveTransactionId") or fabric_result.get("transactionId")
        except FabricInvalidTransitionError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ledger transition: {exc}",
            ) from exc
        except FabricUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Blockchain service unavailable: {exc}",
            ) from exc
        except FabricGatewayError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Fabric ledger shipment receipt failed: {exc}",
            ) from exc

    shipment.status = "DELIVERED"
    shipment.actual_arrival = _utc_now()
    if fabric_tx_id:
        shipment.last_fabric_transaction_id = str(fabric_tx_id)
        if shipment.batch:
            shipment.batch.last_fabric_transaction_id = str(fabric_tx_id)

    _add_tracking_event(
        db,
        shipment,
        event_type="DELIVERED",
        status_value="DELIVERED",
        location_name=getattr(shipment, "destination_location", None),
        event_time=datetime.now(timezone.utc),
        expected_time=getattr(shipment, "expected_arrival", None),
        description=f"Shipment received at its destination (Fabric Tx: {fabric_tx_id or 'none'}).",
    )
    db.commit()
    db.refresh(shipment)

    return shipment


def _normalize_party(value: str | None) -> str:
    return (value or "").strip().casefold()


def _is_current_owner(user: User, shipment: Shipment) -> bool:
    owner = _normalize_party(shipment.current_owner)
    if not owner:
        return False
    return owner in {
        _normalize_party(getattr(user, "organization", None)),
        _normalize_party(getattr(user, "username", None)),
    } - {""}


@router.post(
    "/{shipment_id}/transfer",
    response_model=ShipmentResponse,
)
def transfer_shipment(
    shipment_id: str,
    transfer_data: ShipmentTransfer,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("ADMIN", "MANUFACTURER", "DISTRIBUTOR", "PHARMACY")
    ),
):
    shipment = _get_shipment_or_404(shipment_id, db)
    new_owner = transfer_data.new_owner.strip()

    if not new_owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New owner cannot be empty",
        )

    if current_user.role != "ADMIN" and not _is_current_owner(
        current_user, shipment
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the current owner or an ADMIN can transfer this shipment",
        )

    if _normalize_party(new_owner) == _normalize_party(shipment.current_owner):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New owner is already the current owner",
        )

    batch_obj = getattr(shipment, "batch", None)
    batch_public_id = getattr(batch_obj, "batch_id", None) if batch_obj else None
    if not batch_public_id and hasattr(shipment, "batch_id"):
        try:
            batch_record = db.query(Batch).filter(Batch.id == shipment.batch_id).first()
            batch_public_id = batch_record.batch_id if batch_record else str(shipment.batch_id)
        except Exception:
            batch_public_id = str(shipment.batch_id)

    fabric_tx_id = None
    has_fabric_record = bool(getattr(shipment, "fabric_asset_id", None) or getattr(shipment, "last_fabric_transaction_id", None))
    if settings.fabric_enabled and batch_public_id and has_fabric_record:
        try:
            fabric_result = FabricClient().transfer_drug(
                batch_id=batch_public_id,
                from_owner=shipment.current_owner or "",
                to_owner=new_owner,
            )
            if isinstance(fabric_result, dict):
                fabric_tx_id = fabric_result.get("transactionId")
        except FabricInvalidTransitionError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ledger custody transfer: {exc}",
            ) from exc
        except FabricUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Blockchain service unavailable: {exc}",
            ) from exc
        except FabricGatewayError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Fabric ledger custody transfer failed: {exc}",
            ) from exc

    shipment.current_owner = new_owner
    if fabric_tx_id:
        shipment.last_fabric_transaction_id = str(fabric_tx_id)
        if shipment.batch:
            shipment.batch.last_fabric_transaction_id = str(fabric_tx_id)

    _add_tracking_event(
        db,
        shipment,
        event_type="TRANSFERRED",
        status_value=shipment.status,
        location_name=None,
        event_time=datetime.now(timezone.utc),
        description=f"Shipment custody transferred to {new_owner} (Fabric Tx: {fabric_tx_id or 'none'}).",
    )
    db.commit()
    db.refresh(shipment)

    return shipment
