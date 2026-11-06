from datetime import datetime

from backend.app.ai.anomaly_detector import AnomalyDetector
from backend.app.ai.models import IoTReading, StorageCondition


def test_anomaly_detector_flags_temperature_and_rfid_issues():
    reading = IoTReading(
        shipment_id="SHP-300",
        timestamp=datetime.utcnow(),
        temperature=12.0,
        humidity=80.0,
        latitude=12.1,
        longitude=77.2,
        location_name="Bengaluru",
        speed=90.0,
        sensor_id="sensor-300",
        rfid_id=None,
    )
    anomalies = AnomalyDetector().detect(reading, condition=StorageCondition(2.0, 8.0, 35.0, 65.0))
    assert any(item.type == "temperature_excursion" for item in anomalies)
    assert any(item.type == "humidity_excursion" for item in anomalies)
    assert any(item.type == "route_deviation" for item in anomalies)
    assert any(item.type == "rfid_missing" for item in anomalies)
