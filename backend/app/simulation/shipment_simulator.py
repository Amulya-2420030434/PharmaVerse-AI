from __future__ import annotations

from datetime import datetime

from ..ai.models import StorageCondition
from .models import Shipment, RoutePoint


class ShipmentSimulator:
    def create_shipment(
        self,
        shipment_id: str,
        source: str,
        destination: str,
        product_name: str = "Medication X",
        rfid_id: str = "RFID-001",
        expected_rfid_id: str | None = None,
        expected_qr_id: str | None = "QR-001",
        product_id: str | None = "DRUG-001",
        batch_id: str | None = "BATCH-001",
        expected_owner: str | None = "manufacturer",
        owner: str | None = "manufacturer",
        expected_duration_hours: float = 6.0,
        product_type: str = "pharmaceutical",
        storage_condition: StorageCondition | None = None,
    ) -> Shipment:
        route = [
            RoutePoint(latitude=12.9716, longitude=77.5946, location_name="Bengaluru", timestamp=datetime.utcnow()),
            RoutePoint(latitude=13.0674, longitude=77.1200, location_name="Mysuru", timestamp=datetime.utcnow()),
            RoutePoint(latitude=12.2958, longitude=76.6394, location_name="Coimbatore", timestamp=datetime.utcnow()),
            RoutePoint(latitude=13.0827, longitude=80.2707, location_name="Chennai", timestamp=datetime.utcnow()),
        ]
        return Shipment(
            shipment_id=shipment_id,
            product_name=product_name,
            source=source,
            destination=destination,
            route=route,
            rfid_id=rfid_id,
            expected_rfid_id=expected_rfid_id or rfid_id,
            expected_qr_id=expected_qr_id,
            product_id=product_id,
            batch_id=batch_id,
            expected_owner=expected_owner,
            owner=owner,
            expected_duration_hours=expected_duration_hours,
            status="in_transit",
            eta_hours=24.0,
            product_type=product_type,
            storage_condition=storage_condition or StorageCondition(
                minimum_temperature=2.0,
                maximum_temperature=8.0,
                minimum_humidity=35.0,
                maximum_humidity=65.0,
            ),
        )
