"""Add Fabric tracking fields to drugs and shipments.

Revision ID: 20261104_fabric_tracking_fields
Revises: 20261104_auth_links_and_2fa
Create Date: 2026-11-04 22:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261104_fabric_tracking_fields"
down_revision: Union[str, None] = "20261104_auth_links_and_2fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "drugs",
        sa.Column("fabric_asset_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "drugs",
        sa.Column("last_fabric_transaction_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "shipments",
        sa.Column("fabric_asset_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "shipments",
        sa.Column("last_fabric_transaction_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("shipments", "last_fabric_transaction_id")
    op.drop_column("shipments", "fabric_asset_id")
    op.drop_column("drugs", "last_fabric_transaction_id")
    op.drop_column("drugs", "fabric_asset_id")

