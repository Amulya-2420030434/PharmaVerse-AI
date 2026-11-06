from datetime import datetime

from backend.app.ai.models import StorageCondition
from backend.app.simulation.models import Shipment, RoutePoint
from backend.app.simulation.rfid_simulator import RFIDSimulator


def test_rfid_simulator_generates_expected_events():
    shipment = Shipment(
        shipment_id="SHP-200",
        product_name="Prod-2",
        source="A",
        destination="B",
        route=[
            RoutePoint(latitude=12.0, longitude=77.0, location_name="loc-1", timestamp=datetime.utcnow()),
            RoutePoint(latitude=13.0, longitude=78.0, location_name="loc-2", timestamp=datetime.utcnow()),
        ],
        rfid_id="RFID-200",
        expected_rfid_id="RFID-200",
        storage_condition=StorageCondition(2.0, 8.0, 35.0, 65.0),
    )

    events = RFIDSimulator().generate_events(shipment, anomaly="rfid_mismatch")
    assert len(events) == 2
    assert events[0].shipment_id == "SHP-200"
    assert events[0].expected_rfid_id == "RFID-200"
