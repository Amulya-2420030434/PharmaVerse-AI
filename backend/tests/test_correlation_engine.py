from datetime import datetime, timezone

from backend.app.ai.anomaly_detector import AnomalyDetector
from backend.app.ai.correlation_engine import CorrelationEngine
from backend.app.ai.models import IoTReading, StorageCondition


def test_correlation_engine_groups_related_anomalies():
    readings = [
        IoTReading(
            shipment_id="SHP-400",
            timestamp=datetime.utcnow(),
            temperature=12.0,
            humidity=70.0,
            latitude=12.1,
            longitude=77.2,
            location_name="Bengaluru",
            speed=95.0,
            sensor_id="sensor-400",
            rfid_id="RFID-400",
        ),
        IoTReading(
            shipment_id="SHP-400",
            timestamp=datetime.utcnow(),
            temperature=9.0,
            humidity=72.0,
            latitude=12.2,
            longitude=77.3,
            location_name="Hub",
            speed=88.0,
            sensor_id="sensor-401",
            rfid_id="RFID-400",
        ),
    ]
    anomalies = AnomalyDetector().detect_many(readings, condition=StorageCondition(2.0, 8.0, 35.0, 65.0))
    for anomaly in anomalies:
        anomaly.batch_id = "BATCH-400"
    correlations = CorrelationEngine().correlate(anomalies, datetime.now(timezone.utc))
    assert len(correlations) == 1
    assert correlations[0].shipment_id == "SHP-400"
    assert correlations[0].batch_id == "BATCH-400"
