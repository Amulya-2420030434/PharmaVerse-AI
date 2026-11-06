"""Persist shipment lifecycle and tracking events.

Revision ID: 20261001_tracking
Revises: e91345354e15
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261001_tracking"
down_revision: Union[str, Sequence[str], None] = "e91345354e15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shipment_tracking_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("location_name", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_shipment_tracking_events_shipment_id",
        "shipment_tracking_events",
        ["shipment_id"],
    )
    op.create_index(
        "ix_tracking_events_shipment_sequence",
        "shipment_tracking_events",
        ["shipment_id", "sequence_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_tracking_events_shipment_sequence", table_name="shipment_tracking_events")
    op.drop_index(
        "ix_shipment_tracking_events_shipment_id",
        table_name="shipment_tracking_events",
    )
    op.drop_table("shipment_tracking_events")
