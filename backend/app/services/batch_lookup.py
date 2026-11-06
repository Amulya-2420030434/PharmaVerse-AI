"""Shared lookup for batches addressed by their *public* identifier.

Every API that accepts a ``batch_id`` from a client (RFID, QR, shipments,
audit, ...) means the human-readable public identifier stored in
``Batch.batch_id`` (for example ``BATCH-TEST-001``).  The database primary key
``Batch.id`` (a UUID) is an internal detail and is what the ``batch_id``
foreign-key columns on other tables point at.  Keeping the lookup in one place
guarantees that no route accidentally compares the wrong column.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.batch import Batch


BATCH_NOT_FOUND = "Batch not found"
BATCH_UUID_HINT = (
    "Batch not found: batch_id must be the public batch identifier "
    "(for example 'BATCH-TEST-001'), not the internal database UUID"
)


def normalize_public_id(value: str) -> str:
    """Return an identifier with surrounding whitespace removed."""
    return value.strip()


def find_batch_by_public_id(db: Session, public_id: str) -> Batch | None:
    """Return the batch whose public ``batch_id`` equals ``public_id``."""
    return db.query(Batch).filter(
        Batch.batch_id == normalize_public_id(public_id)
    ).first()


def get_batch_or_404(db: Session, public_id: str) -> Batch:
    """Return the batch for a public ``batch_id`` or raise HTTP 404.

    If the caller supplied the internal database UUID instead of the public
    identifier, the 404 says so explicitly.  The UUID is deliberately *not*
    accepted as an alias: public identifiers and database keys stay distinct.
    """
    batch = find_batch_by_public_id(db, public_id)
    if batch is not None:
        return batch

    detail = BATCH_NOT_FOUND
    try:
        internal_id = UUID(normalize_public_id(public_id))
    except ValueError:
        internal_id = None

    if internal_id is not None:
        by_primary_key = db.query(Batch).filter(Batch.id == internal_id).first()
        if by_primary_key is not None:
            detail = BATCH_UUID_HINT

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail,
    )
