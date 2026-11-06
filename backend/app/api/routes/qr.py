from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.database.connection import get_db
from app.models.qr_record import QRRecord
from app.models.user import User
from app.schemas.qr import QRCreate, QRResponse
from app.services.batch_lookup import get_batch_or_404


router = APIRouter(
    prefix="/api/qr",
    tags=["QR"],
)


def _get_qr_or_404(qr_id: str, db: Session) -> QRRecord:
    qr_record = db.query(QRRecord).filter(
        QRRecord.qr_id == qr_id.strip()
    ).first()

    if not qr_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR record not found",
        )

    return qr_record


@router.post(
    "",
    response_model=QRResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_qr(
    qr_data: QRCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("ADMIN", "REGULATOR", "MANUFACTURER")
    ),
):
    # qr_data.batch_id is the *public* batch identifier (Batch.batch_id);
    # the QR record stores the batch's internal primary key (Batch.id).
    batch = get_batch_or_404(db, qr_data.batch_id)

    existing_qr = db.query(QRRecord).filter(
        QRRecord.qr_id == qr_data.qr_id
    ).first()

    if existing_qr:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="QR ID already exists",
        )

    qr_record = QRRecord(
        qr_id=qr_data.qr_id,
        batch_id=batch.id,
        encoded_value=qr_data.encoded_value,
        status=qr_data.status,
    )

    db.add(qr_record)
    db.commit()
    db.refresh(qr_record)

    return qr_record


@router.get(
    "",
    response_model=list[QRResponse],
)
def list_qr_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(QRRecord).order_by(
        QRRecord.created_at.desc()
    ).all()


@router.post(
    "/{qr_id}/deactivate",
    response_model=QRResponse,
)
def deactivate_qr(
    qr_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("ADMIN", "REGULATOR", "MANUFACTURER")
    ),
):
    qr_record = _get_qr_or_404(qr_id, db)

    if qr_record.status == "INACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="QR record is already inactive",
        )

    qr_record.status = "INACTIVE"
    db.commit()
    db.refresh(qr_record)

    return qr_record


@router.get(
    "/{qr_id}",
    response_model=QRResponse,
)
def get_qr(
    qr_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_qr_or_404(qr_id, db)
