"""Add secure authentication links and email 2FA settings."""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "20261104_auth_links_and_2fa"
down_revision: Union[str, None] = "20261031_auth_approval_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "two_factor_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.UUID(), primary_key=True, default=uuid.uuid4),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_auth_tokens_email", "auth_tokens", ["email"])
    op.create_index("ix_auth_tokens_purpose", "auth_tokens", ["purpose"])


def downgrade() -> None:
    op.drop_index("ix_auth_tokens_purpose", table_name="auth_tokens")
    op.drop_index("ix_auth_tokens_email", table_name="auth_tokens")
    op.drop_table("auth_tokens")
    op.drop_column("users", "two_factor_enabled")
