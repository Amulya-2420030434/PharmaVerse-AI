from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.database.connection import get_db
from app.models.rfid_record import RFIDRecord
from app.models.user import User
from app.schemas.rfid import RFIDCreate, RFIDResponse
from app.services.batch_lookup import get_batch_or_404


router = APIRouter(
    prefix="/api/rfid",
    tags=["RFID"],
)


def _get_rfid_or_404(rfid_id: str, db: Session) -> RFIDRecord:
    rfid_record = db.query(RFIDRecord).filter(
        RFIDRecord.rfid_id == rfid_id.strip()
    ).first()

    if not rfid_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFID record not found",
        )

    return rfid_record


@router.post(
    "",
    response_model=RFIDResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rfid(
    rfid_data: RFIDCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("ADMIN", "REGULATOR", "MANUFACTURER")
    ),
):
    # rfid_data.batch_id is the *public* batch identifier (Batch.batch_id);
    # the RFID record stores the batch's internal primary key (Batch.id).
    batch = get_batch_or_404(db, rfid_data.batch_id)

    existing_rfid = db.query(RFIDRecord).filter(
        RFIDRecord.rfid_id == rfid_data.rfid_id
    ).first()

    if existing_rfid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="RFID ID already exists",
        )

    rfid_record = RFIDRecord(
        rfid_id=rfid_data.rfid_id,
        batch_id=batch.id,
        tag_value=rfid_data.tag_value,
        status=rfid_data.status,
    )

    db.add(rfid_record)
    db.commit()
    db.refresh(rfid_record)

    return rfid_record


@router.get(
    "",
    response_model=list[RFIDResponse],
)
def list_rfid_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(RFIDRecord).order_by(
        RFIDRecord.created_at.desc()
    ).all()


@router.get(
    "/{rfid_id}",
    response_model=RFIDResponse,
)
def get_rfid(
    rfid_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_rfid_or_404(rfid_id, db)


@router.post(
    "/{rfid_id}/deactivate",
    response_model=RFIDResponse,
)
def deactivate_rfid(
    rfid_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("ADMIN", "REGULATOR", "MANUFACTURER")
    ),
):
    rfid_record = _get_rfid_or_404(rfid_id, db)
    rfid_record.status = "INACTIVE"

    db.commit()
    db.refresh(rfid_record)

    return rfid_record
