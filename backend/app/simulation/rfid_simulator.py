from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from .models import RFIDEvent, Shipment


class RFIDSimulator:
    def generate_events(self, shipment: Shipment, anomaly: str | None = None) -> List[RFIDEvent]:
        events: List[RFIDEvent] = []
        current = datetime.utcnow()
        for index, point in enumerate(shipment.route):
            rfid_id = shipment.rfid_id
            event_type = "read"
            if anomaly == "rfid_mismatch":
                rfid_id = f"{shipment.rfid_id}-tampered" if shipment.rfid_id else "rfid-tampered"
                event_type = "mismatch"
            elif anomaly == "unauthorized_transfer":
                rfid_id = "rfid-unauthorized" if shipment.rfid_id != "rfid-unauthorized" else shipment.rfid_id
                event_type = "transfer"
            elif anomaly == "qr_mismatch":
                rfid_id = shipment.rfid_id
                event_type = "qr_mismatch"

            events.append(
                RFIDEvent(
                    shipment_id=shipment.shipment_id,
                    rfid_id=rfid_id,
                    event_type=event_type,
                    location_name=point.location_name,
                    timestamp=current + timedelta(minutes=index * 20),
                    expected_rfid_id=shipment.expected_rfid_id or shipment.rfid_id,
                    qr_id=("QR-TAMPERED" if anomaly == "qr_mismatch" else shipment.expected_qr_id),
                    product_id=shipment.product_id,
                    batch_id=shipment.batch_id,
                    owner=("unknown-owner" if anomaly == "unauthorized_transfer" else shipment.owner),
                    authorized=False if anomaly == "unauthorized_transfer" else True,
                    metadata={"route_index": index},
                )
            )
        return events
