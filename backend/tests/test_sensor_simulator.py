from datetime import datetime

from backend.app.ai.models import StorageCondition
from backend.app.simulation.models import Shipment, RoutePoint
from backend.app.simulation.sensor_simulator import SensorSimulator


def test_sensor_simulator_generates_temperature_and_humidity_data():
    shipment = Shipment(
        shipment_id="SHP-100",
        product_name="Prod-1",
        source="A",
        destination="B",
        route=[
            RoutePoint(latitude=12.0, longitude=77.0, location_name="loc-1", timestamp=datetime.utcnow()),
            RoutePoint(latitude=13.0, longitude=78.0, location_name="loc-2", timestamp=datetime.utcnow()),
        ],
        rfid_id="RFID-100",
        storage_condition=StorageCondition(2.0, 8.0, 35.0, 65.0),
    )

    readings = SensorSimulator().generate_readings(shipment, hours=1, interval_minutes=30)
    assert len(readings) >= 2
    assert readings[0].shipment_id == "SHP-100"
    assert readings[0].temperature is not None
    assert readings[0].humidity is not None
