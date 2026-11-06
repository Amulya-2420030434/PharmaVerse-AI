"""Persist submitted AI telemetry and analysis records.

Revision ID: 20261105_ai_telemetry_analysis
Revises: 20261105_admin_notifications
Create Date: 2026-11-05 10:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261105_ai_telemetry_analysis"
down_revision: Union[str, None] = "20261105_admin_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_telemetry_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_fingerprint", name="uq_ai_telemetry_event_fingerprint"),
    )
    op.create_index(
        op.f("ix_ai_telemetry_events_batch_id"),
        "ai_telemetry_events",
        ["batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_telemetry_events_shipment_id"),
        "ai_telemetry_events",
        ["shipment_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_telemetry_shipment_time",
        "ai_telemetry_events",
        ["shipment_id", "event_time"],
        unique=False,
    )

    op.create_table(
        "ai_analysis_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column("assessed_by", sa.Uuid(), nullable=True),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("evidence_hash", sa.String(length=64), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assessed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_analysis_records_assessed_by"),
        "ai_analysis_records",
        ["assessed_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_analysis_records_shipment_id"),
        "ai_analysis_records",
        ["shipment_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_analysis_shipment_assessed",
        "ai_analysis_records",
        ["shipment_id", "assessed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_analysis_shipment_assessed", table_name="ai_analysis_records")
    op.drop_index(op.f("ix_ai_analysis_records_shipment_id"), table_name="ai_analysis_records")
    op.drop_index(op.f("ix_ai_analysis_records_assessed_by"), table_name="ai_analysis_records")
    op.drop_table("ai_analysis_records")
    op.drop_index("ix_ai_telemetry_shipment_time", table_name="ai_telemetry_events")
    op.drop_index(op.f("ix_ai_telemetry_events_shipment_id"), table_name="ai_telemetry_events")
    op.drop_index(op.f("ix_ai_telemetry_events_batch_id"), table_name="ai_telemetry_events")
    op.drop_table("ai_telemetry_events")
