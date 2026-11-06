from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Sequence

from .alert_engine import AlertEngine
from .anomaly_detector import AnomalyDetector
from .correlation_engine import CORRELATION_WINDOW_MINUTES, CorrelationEngine
from .counterfeit_detector import CounterfeitDetector
from .explainability import ExplainabilityEngine
from .models import (
    AIAnalysisResult,
    AnomalyRecord,
    IoTReading,
    StorageCondition,
    anomaly_evidence_id,
    ensure_utc,
    evidence_hash,
)
from .risk_engine import RiskEngine
from ..simulation.models import RFIDEvent, RoutePoint
from ..ml.model import ML_DISCLAIMER, RiskModel


class AIService:
    def __init__(
        self,
        anomaly_detector: Optional[AnomalyDetector] = None,
        correlation_engine: Optional[CorrelationEngine] = None,
        risk_engine: Optional[RiskEngine] = None,
        counterfeit_detector: Optional[CounterfeitDetector] = None,
        explainability_engine: Optional[ExplainabilityEngine] = None,
        alert_engine: Optional[AlertEngine] = None,
    ):
        self.anomaly_detector = anomaly_detector or AnomalyDetector()
        self.correlation_engine = correlation_engine or CorrelationEngine()
        self.risk_engine = risk_engine or RiskEngine()
        self.counterfeit_detector = counterfeit_detector or CounterfeitDetector()
        self.explainability_engine = explainability_engine or ExplainabilityEngine()
        self.alert_engine = alert_engine or AlertEngine()

    def analyze_readings(
        self,
        shipment_id: str,
        readings: Iterable[IoTReading],
        storage_condition: Optional[StorageCondition] = None,
        expected_rfid_id: Optional[str] = None,
        actual_rfid_id: Optional[str] = None,
        planned_route: Optional[Sequence[RoutePoint]] = None,
        expected_duration_hours: Optional[float] = None,
        delay_tolerance_hours: float = 1.0,
        route_threshold_km: float = 25.0,
        expected_qr_id: Optional[str] = None,
        actual_qr_id: Optional[str] = None,
        expected_product_id: Optional[str] = None,
        actual_product_id: Optional[str] = None,
        expected_batch_id: Optional[str] = None,
        actual_batch_id: Optional[str] = None,
        expected_owner: Optional[str] = None,
        actual_owner: Optional[str] = None,
        expiry_date: Optional[datetime] = None,
        rfid_events: Optional[Iterable[RFIDEvent]] = None,
    ) -> Dict[str, Any]:
        readings_list = list(readings)
        events = list(rfid_events or [])
        observed_times = [
            ensure_utc(item.timestamp)
            for item in [*readings_list, *events]
            if item.timestamp is not None
        ]
        assessment_time = max(observed_times, default=datetime.now(timezone.utc))
        batch_id = expected_batch_id or actual_batch_id
        anomalies = self.anomaly_detector.detect_many(
            readings_list,
            condition=storage_condition,
            planned_route=planned_route,
            route_threshold_km=route_threshold_km,
            expected_duration_hours=expected_duration_hours,
            delay_tolerance_hours=delay_tolerance_hours,
        )

        def add_identity_anomaly(
            anomaly_type: str,
            message: str,
            evidence: dict[str, Any],
            timestamp: datetime | None = None,
            factor: str = "identity",
        ) -> None:
            anomalies.append(
                AnomalyRecord(
                    shipment_id=shipment_id,
                    batch_id=batch_id,
                    sensor_id="identity-gateway",
                    type=anomaly_type,
                    severity="high",
                    message=message,
                    timestamp=timestamp or assessment_time,
                    factor=factor,
                    evidence=evidence,
                )
            )

        observed_rfid = [
            (item.rfid_id, item.timestamp, "iot_reading")
            for item in readings_list
            if item.rfid_id
        ] + [
            (item.rfid_id, item.timestamp, "rfid_event")
            for item in events
            if item.rfid_id
        ]
        observed_qr = [
            (item.qr_id, item.timestamp, "rfid_event")
            for item in events
            if item.qr_id
        ]
        observed_products = [
            (item.product_id, item.timestamp, "rfid_event")
            for item in events
            if item.product_id
        ]
        observed_batches = [
            (item.batch_id, item.timestamp, "rfid_event")
            for item in events
            if item.batch_id
        ]
        observed_owners = [
            (item.owner, item.timestamp, "rfid_event")
            for item in events
            if item.owner
        ]
        resolved_actual_rfid_id = actual_rfid_id if actual_rfid_id is not None else (
            observed_rfid[-1][0] if observed_rfid else None
        )
        resolved_actual_qr_id = actual_qr_id if actual_qr_id is not None else (
            observed_qr[-1][0] if observed_qr else None
        )
        resolved_actual_product_id = actual_product_id if actual_product_id is not None else (
            observed_products[-1][0] if observed_products else None
        )
        resolved_actual_batch_id = actual_batch_id if actual_batch_id is not None else (
            observed_batches[-1][0] if observed_batches else None
        )
        resolved_actual_owner = actual_owner if actual_owner is not None else (
            observed_owners[-1][0] if observed_owners else None
        )

        if events:
            event_keys = [(event.rfid_id, event.location_name, event.timestamp) for event in events]
            if len(event_keys) != len(set(event_keys)):
                duplicate = next(
                    event
                    for event in reversed(events)
                    if (event.rfid_id, event.location_name, event.timestamp) in event_keys[:-1]
                )
                add_identity_anomaly(
                    "rfid_duplicate",
                    "Duplicate RFID activity was observed.",
                    {"observed_rfid_ids": [event.rfid_id for event in events]},
                    duplicate.timestamp,
                )
            if any(event.authorized is False for event in events):
                unauthorized = [event for event in events if event.authorized is False]
                add_identity_anomaly(
                    "ownership_inconsistency",
                    "An RFID transfer was not authorized.",
                    {"unauthorized_events": [event.model_dump(mode="json") for event in unauthorized]},
                    max(ensure_utc(event.timestamp) for event in unauthorized),
                    factor="ownership",
                )

        identity_checks = (
            (
                "rfid_mismatch",
                "RFID identity differs from the expected shipment record.",
                expected_rfid_id,
                resolved_actual_rfid_id,
                observed_rfid,
                "identity",
            ),
            (
                "qr_mismatch",
                "QR identity differs from the expected product record.",
                expected_qr_id,
                resolved_actual_qr_id,
                observed_qr,
                "identity",
            ),
            (
                "product_identity_mismatch",
                "Drug/product identity differs from the expected record.",
                expected_product_id,
                resolved_actual_product_id,
                observed_products,
                "identity",
            ),
            (
                "batch_identity_mismatch",
                "Batch identity differs from the expected record.",
                expected_batch_id,
                resolved_actual_batch_id,
                observed_batches,
                "identity",
            ),
            (
                "ownership_inconsistency",
                "Ownership differs from the expected authorized owner.",
                expected_owner,
                resolved_actual_owner,
                observed_owners,
                "ownership",
            ),
        )
        existing_identity_types = {item.type for item in anomalies}
        for anomaly_type, message, expected, actual, observations, factor in identity_checks:
            mismatches = [
                (value, timestamp, source)
                for value, timestamp, source in observations
                if expected and value != expected
            ]
            explicit_mismatch = bool(expected and actual and expected != actual)
            if (mismatches or explicit_mismatch) and anomaly_type not in existing_identity_types:
                latest_mismatch = max(
                    (ensure_utc(timestamp) for _, timestamp, _ in mismatches if timestamp is not None),
                    default=assessment_time,
                )
                add_identity_anomaly(
                    anomaly_type,
                    message,
                    {
                        "expected": expected,
                        "actual": actual,
                        "mismatched_observations": [
                            {"value": value, "timestamp": timestamp, "source": source}
                            for value, timestamp, source in mismatches
                        ],
                    },
                    latest_mismatch,
                    factor=factor,
                )

        if not all((expected_rfid_id, expected_qr_id, expected_product_id, expected_batch_id)):
            anomalies.append(
                AnomalyRecord(
                    shipment_id=shipment_id,
                    batch_id=batch_id,
                    sensor_id="identity-gateway",
                    type="missing_identity",
                    severity="medium",
                    message="One or more identity fields are unavailable.",
                    timestamp=assessment_time,
                    factor="identity",
                    evidence={
                        "expected_rfid_id": expected_rfid_id,
                        "expected_qr_id": expected_qr_id,
                        "expected_product_id": expected_product_id,
                        "expected_batch_id": expected_batch_id,
                    },
                )
            )
        if expiry_date and ensure_utc(expiry_date).date() < assessment_time.date():
            anomalies.append(
                AnomalyRecord(
                    shipment_id=shipment_id,
                    batch_id=batch_id,
                    sensor_id="identity-gateway",
                    type="expired_product",
                    severity="high",
                    message="Product expiry date has passed.",
                    timestamp=assessment_time,
                    factor="expiry",
                    evidence={"expiry_date": expiry_date},
                )
            )

        for anomaly in anomalies:
            anomaly.batch_id = anomaly.batch_id or batch_id
            anomaly.timestamp = ensure_utc(anomaly.timestamp or assessment_time)
            anomaly.evidence_id = anomaly.evidence_id or evidence_hash(
                {
                    "batch_id": anomaly.batch_id,
                    "shipment_id": anomaly.shipment_id,
                    "sensor_id": anomaly.sensor_id,
                    "type": anomaly.type,
                    "factor": anomaly.factor,
                    "timestamp": anomaly.timestamp,
                    "evidence": anomaly.evidence,
                }
            )

        scored_anomalies = self.correlation_engine.events_for_event(
            anomalies,
            batch_id,
            assessment_time,
        )
        correlations = self.correlation_engine.correlate(anomalies, assessment_time)
        risk = self.risk_engine.assess(shipment_id, scored_anomalies)
        counterfeit = self.counterfeit_detector.assess(
            shipment_id,
            scored_anomalies,
            expected_rfid_id,
            resolved_actual_rfid_id,
            expected_qr_id,
            resolved_actual_qr_id,
            expected_product_id,
            resolved_actual_product_id,
            expected_batch_id,
            resolved_actual_batch_id,
            expected_owner,
            resolved_actual_owner,
            expiry_date,
            assessment_time=assessment_time,
        )
        alerts = self.alert_engine.build_alerts(shipment_id, risk, counterfeit, scored_anomalies)
        explanations = self.explainability_engine.explain(risk, scored_anomalies)
        evidence = {
            "shipment_id": shipment_id,
            "anomalies": [item.model_dump(mode="json") for item in anomalies],
            "scored_evidence_ids": [anomaly_evidence_id(item) for item in scored_anomalies],
            "correlations": [item.model_dump(mode="json") for item in correlations],
        }
        result = AIAnalysisResult(
            shipment_id=shipment_id,
            anomalies=anomalies,
            correlations=correlations,
            risk=risk,
            counterfeit=counterfeit,
            alerts=alerts,
        )
        ml_model = RiskModel()
        ml_prediction = ml_model.predict(ml_model.features_from_analysis({
            "anomalies": [item.model_dump(mode="json") for item in scored_anomalies],
        }))
        return {
            "shipment_id": result.shipment_id,
            "anomalies": [item.model_dump(mode="json") for item in result.anomalies],
            "correlations": [item.model_dump(mode="json") for item in result.correlations],
            "risk": result.risk.model_dump(mode="json"),
            "counterfeit": result.counterfeit.model_dump(mode="json"),
            "alerts": [item.model_dump(mode="json") for item in result.alerts],
            "explanations": explanations,
            "explainability": {
                "what_happened": explanations,
                "why_suspicious": result.risk.drivers,
                "evidence": evidence,
                "assessment_time": assessment_time.isoformat(),
                "correlation_window_minutes": CORRELATION_WINDOW_MINUTES,
                "risk_score": result.risk.score,
                "recommended_action": [item for alert in alerts for item in alert.recommendations],
                "requires_human_review": result.risk.requires_human_review or counterfeit.is_counterfeit_risk,
            },
            "blockchain": {
                "status": "NOT_SUBMITTED",
                "transaction_id": None,
                "evidence_hash": evidence_hash(evidence),
            },
            "ml_assessment": {
                "available": ml_prediction.available,
                "probability": ml_prediction.probability,
                "label": ml_prediction.label,
                "reason": ml_prediction.reason,
                "disclaimer": ML_DISCLAIMER,
            },
        }
