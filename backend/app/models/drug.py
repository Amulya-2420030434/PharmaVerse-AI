import uuid

from sqlalchemy import Date, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.database.connection import Base


class Drug(Base):
    __tablename__ = "drugs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    drug_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    generic_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    manufacturer: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    dosage_form: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    strength: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    storage_min_temp: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    storage_max_temp: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    storage_min_humidity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    storage_max_humidity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    composition: Mapped[str | None] = mapped_column(Text, nullable=True)

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    expiry_period_days: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    fabric_asset_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    last_fabric_transaction_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    batches = relationship(
        "Batch",
        back_populates="drug",
        cascade="all, delete-orphan",
    )
