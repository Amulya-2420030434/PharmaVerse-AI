from datetime import datetime, timezone

from backend.app.ai.anomaly_detector import AnomalyDetector
from backend.app.ai.counterfeit_detector import CounterfeitDetector
from backend.app.ai.models import IoTReading, StorageCondition


def test_counterfeit_detector_reports_mismatch_risk():
    reading = IoTReading(
        shipment_id="SHP-600",
        timestamp=datetime.utcnow(),
        temperature=10.0,
        humidity=60.0,
        latitude=12.1,
        longitude=77.2,
        location_name="Bengaluru",
        speed=95.0,
        sensor_id="sensor-600",
        rfid_id="RFID-ALT",
    )
    anomalies = AnomalyDetector().detect(reading, condition=StorageCondition(2.0, 8.0, 35.0, 65.0))
    assessment = CounterfeitDetector().assess("SHP-600", anomalies, expected_rfid_id="RFID-PRIMARY", actual_rfid_id="RFID-ALT")
    assert assessment.is_counterfeit_risk is True
    assert assessment.risk_level in {"medium", "high", "critical"}


def test_counterfeit_detector_does_not_treat_expected_database_values_as_observations():
    assessment = CounterfeitDetector().assess(
        "SHP-601",
        [],
        expected_rfid_id="RFID-EXPECTED",
        expected_qr_id="QR-EXPECTED",
        expected_product_id="DRUG-EXPECTED",
        expected_batch_id="BATCH-EXPECTED",
        expected_owner="manufacturer",
    )

    assert assessment.status == "UNVERIFIED"
    assert assessment.is_counterfeit_risk is False
    assert assessment.evidence["identity_checked"] is False


def test_expiry_assessment_uses_event_time_for_historical_analysis():
    assessment = CounterfeitDetector().assess(
        "SHP-HISTORICAL",
        [],
        expected_rfid_id="RFID-1",
        actual_rfid_id="RFID-1",
        expiry_date=datetime(2020, 6, 2, tzinfo=timezone.utc),
        assessment_time=datetime(2020, 6, 1, tzinfo=timezone.utc),
    )

    assert assessment.status == "AUTHENTIC"
    assert assessment.is_counterfeit_risk is False
