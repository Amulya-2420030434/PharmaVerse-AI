"""Add optional composition to drug records.

Revision ID: 20261001_drug_composition
Revises: 20261001_qr_payload
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261001_drug_composition"
down_revision: Union[str, None] = "20261001_qr_payload"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("drugs", sa.Column("composition", sa.Text(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE drugs
            SET composition = :composition
            WHERE drug_id = :drug_id
              AND composition IS NULL
            """
        ).bindparams(
            composition="Acetaminophen 500 mg (demo active ingredient; excipients unspecified)",
            drug_id="DRUG-2026-000001",
        )
    )


def downgrade() -> None:
    op.drop_column("drugs", "composition")