from datetime import datetime

from backend.app.ai.anomaly_detector import AnomalyDetector
from backend.app.ai.models import IoTReading, StorageCondition
from backend.app.ai.risk_engine import RiskEngine


def test_risk_engine_scores_high_risk_cases():
    reading = IoTReading(
        shipment_id="SHP-500",
        timestamp=datetime.utcnow(),
        temperature=11.0,
        humidity=75.0,
        latitude=12.1,
        longitude=77.2,
        location_name="Bengaluru",
        speed=90.0,
        sensor_id="sensor-500",
        rfid_id=None,
    )
    anomalies = AnomalyDetector().detect(reading, condition=StorageCondition(2.0, 8.0, 35.0, 65.0))
    risk = RiskEngine().assess("SHP-500", anomalies)
    assert risk.score >= 45
    assert risk.risk_level in {"high", "critical"}


def test_risk_engine_counts_distinct_factors_once_and_bounds_score():
    from backend.app.ai.models import AnomalyRecord

    factors = ["environmental", "route", "delay", "identity", "expiry", "ownership"]
    anomalies = [
        AnomalyRecord(
            shipment_id="SHP-DISTINCT",
            batch_id="BATCH-DISTINCT",
            sensor_id=f"sensor-{index}",
            type=f"observation-{index}",
            severity="high",
            message=f"Observation {index}",
            timestamp=datetime.utcnow(),
            factor=factor,
            evidence={"observation": index},
        )
        for index, factor in enumerate(factors)
    ]
    anomalies.extend(
        AnomalyRecord(
            shipment_id="SHP-DISTINCT",
            batch_id="BATCH-DISTINCT",
            sensor_id=f"repeat-{index}",
            type="temperature_excursion",
            severity="high",
            message="Repeated environmental observation",
            timestamp=datetime.utcnow(),
            factor="environmental",
            evidence={"repeat": index},
        )
        for index in range(10)
    )

    risk = RiskEngine().assess("SHP-DISTINCT", anomalies)

    assert risk.score == 100.0
    assert len(risk.factor_evidence["environmental"]) == 11
    assert set(risk.factor_evidence) == set(factors)


def test_risk_engine_repeated_observations_do_not_repeat_factor_weight():
    from backend.app.ai.models import AnomalyRecord

    anomalies = [
        AnomalyRecord(
            shipment_id="SHP-REPEATED",
            batch_id="BATCH-REPEATED",
            sensor_id=f"sensor-{index}",
            type="temperature_excursion",
            severity="high",
            message="Repeated temperature excursion",
            timestamp=datetime.utcnow(),
            factor="environmental",
            evidence={"reading": index},
        )
        for index in range(5)
    ]

    risk = RiskEngine().assess("SHP-REPEATED", anomalies)

    assert risk.score == 20.0
    assert len(risk.factor_evidence["environmental"]) == 5


def test_risk_engine_uses_the_six_configured_paper_weights():
    from backend.app.ai.models import AnomalyRecord

    expected_weights = {
        "identity": 20,
        "expiry": 5,
        "environmental": 20,
        "route": 20,
        "delay": 15,
        "ownership": 10,
    }
    for factor, expected_score in expected_weights.items():
        anomaly = AnomalyRecord(
            shipment_id="SHP-WEIGHT",
            batch_id="BATCH-WEIGHT",
            sensor_id="weight-test",
            type=f"{factor}_test",
            severity="high",
            message=f"{factor} factor test",
            timestamp=datetime.utcnow(),
            factor=factor,
            evidence={"factor": factor},
        )
        risk = RiskEngine().assess("SHP-WEIGHT", [anomaly])
        assert risk.score == float(expected_score)
