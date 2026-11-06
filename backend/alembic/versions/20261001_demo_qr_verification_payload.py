"""Encode seed QR identities as verifiable QR IDs.

Revision ID: 20261001_qr_payload
Revises: 20261001_tracking
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261001_qr_payload"
down_revision: Union[str, Sequence[str], None] = "20261001_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE qr_records
            SET encoded_value = 'pharmaverse://verification?qr_id=' || qr_id
            WHERE qr_id >= 'QR-MED-000001'
              AND qr_id <= 'QR-MED-000200'
              AND encoded_value LIKE 'pharmaverse://batch/BATCH-2026-%'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE qr_records AS qr
            SET encoded_value = 'pharmaverse://batch/' || batches.batch_id
            FROM batches
            WHERE qr.batch_id = batches.id
              AND qr.qr_id >= 'QR-MED-000001'
              AND qr.qr_id <= 'QR-MED-000200'
              AND qr.encoded_value LIKE 'pharmaverse://verification?qr_id=%'
            """
        )
    )
