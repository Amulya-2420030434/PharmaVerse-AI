import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    shipment_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("batches.id"),
        nullable=False,
        index=True,
    )

    source_location: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    destination_location: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    current_owner: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="CREATED",
        nullable=False,
        index=True,
    )

    expected_departure: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    actual_departure: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    expected_arrival: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    actual_arrival: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    expected_latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    expected_longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    current_latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    current_longitude: Mapped[float | None] = mapped_column(
        Float,
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

    batch = relationship(
        "Batch",
        back_populates="shipments",
    )
