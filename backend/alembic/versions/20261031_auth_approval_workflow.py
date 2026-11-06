"""Add user approval status, google auth fields, and email_otps table.

Revision ID: 20261031_auth_approval_workflow
Revises: 20261001_drug_composition
Create Date: 2026-10-31
"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "20261031_auth_approval_workflow"
down_revision: Union[str, None] = "20261001_drug_composition"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update 'users' table
    op.add_column(
        "users",
        sa.Column("full_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="APPROVED",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "auth_provider",
            sa.String(length=50),
            server_default="local",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("google_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_users_status"), "users", ["status"], unique=False)
    op.create_index(op.f("ix_users_google_id"), "users", ["google_id"], unique=True)

    # 2. Create 'email_otps' table
    op.create_table(
        "email_otps",
        sa.Column("id", sa.UUID(), primary_key=True, default=uuid.uuid4),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.String(length=50), server_default="registration", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_email_otps_email"), "email_otps", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_email_otps_email"), table_name="email_otps")
    op.drop_table("email_otps")
    op.drop_index(op.f("ix_users_google_id"), table_name="users")
    op.drop_index(op.f("ix_users_status"), table_name="users")
    op.drop_column("users", "created_at")
    op.drop_column("users", "google_id")
    op.drop_column("users", "auth_provider")
    op.drop_column("users", "status")
    op.drop_column("users", "full_name")

