from datetime import datetime, timedelta, timezone

from backend.app.ai.correlation_engine import CorrelationEngine
from backend.app.ai.models import AnomalyRecord
from backend.app.simulation.manager import SimulationManager


def _anomaly(kind: str, timestamp: datetime, factor: str) -> AnomalyRecord:
    return AnomalyRecord(
        shipment_id="audit",
        batch_id="audit-batch",
        sensor_id="audit-sensor",
        type=kind,
        severity="high",
        message=kind,
        timestamp=timestamp,
        factor=factor,
        evidence={"source": "audit"},
    )


def test_scenarios_expose_evidence_backed_results():
    manager = SimulationManager()
    normal = manager.run_scenario("normal")["analysis"]
    route = manager.run_scenario("route_deviation")["analysis"]
    delayed = manager.run_scenario("delayed_shipment")["analysis"]

    assert normal["risk"]["score"] == 0
    assert "route_deviation" in {item["type"] for item in route["anomalies"]}
    assert "shipment_delay" in {item["type"] for item in delayed["anomalies"]}
    assert route["anomalies"][0]["evidence"]["nearest_route_distance_km"] > 25


def test_correlation_window_changes_the_score():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    close = [
        _anomaly("temperature_excursion", start, "environmental"),
        _anomaly("route_deviation", start + timedelta(minutes=10), "route"),
        _anomaly("shipment_delay", start + timedelta(minutes=20), "delay"),
    ]
    distant = [
        _anomaly("temperature_excursion", start, "environmental"),
        _anomaly("route_deviation", start + timedelta(hours=2), "route"),
        _anomaly("shipment_delay", start + timedelta(hours=4), "delay"),
    ]
    engine = CorrelationEngine()
    close_records = engine.correlate(close, start + timedelta(minutes=20))
    distant_records = engine.correlate(distant, start + timedelta(hours=4))

    assert len(close_records) == 1
    assert close_records[0].factors == ["delay", "environmental", "route"]
    assert distant_records == []


def test_correlation_uses_exact_backward_window_and_same_batch_only():
    assessment_time = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    anomalies = [
        _anomaly("at_window_boundary", assessment_time - timedelta(minutes=60), "environmental"),
        _anomaly("current_event", assessment_time, "route"),
        _anomaly("outside_window", assessment_time - timedelta(minutes=60, microseconds=1), "delay"),
        _anomaly("future_event", assessment_time + timedelta(seconds=1), "identity"),
        AnomalyRecord(
            shipment_id="other-shipment",
            batch_id="other-batch",
            sensor_id="other-sensor",
            type="cross_batch_event",
            severity="high",
            message="Must not correlate across batches",
            timestamp=assessment_time,
            factor="ownership",
        ),
    ]

    selected = CorrelationEngine.events_for_event(anomalies, "audit-batch", assessment_time)
    correlation = CorrelationEngine().correlate(anomalies, assessment_time)

    assert {item.type for item in selected} == {"at_window_boundary", "current_event"}
    assert len(correlation) == 1
    assert correlation[0].factors == ["environmental", "route"]
    assert correlation[0].evidence["window_minutes"] == 60
