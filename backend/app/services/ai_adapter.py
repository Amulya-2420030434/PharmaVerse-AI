from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.service import AIService
from app.ai.models import IoTReading, StorageCondition
from app.models.ai_telemetry_event import AIAnalysisRecord, AITelemetryEvent
from app.models.batch import Batch
from app.models.qr_record import QRRecord
from app.models.rfid_record import RFIDRecord
from app.models.shipment import Shipment
from app.schemas.ai import AIAnalysisRequest
from app.simulation.models import RFIDEvent, RoutePoint
from app.simulation.scenario_engine import ScenarioEngine


class AIAdapter:
    """Maps operational PostgreSQL data and request telemetry to AI inputs."""

    def __init__(self, ai_service: AIService | None = None):
        self.ai_service = ai_service or AIService()

    def analyze(
        self,
        request: AIAnalysisRequest,
        db: Session,
        assessed_by: UUID | None = None,
    ) -> dict:
        shipment, batch, qr, rfid = self._load_context(request.shipment_id, db)

        condition = self._storage_condition(batch.drug)
        expected_duration = request.expected_duration_hours
        if expected_duration is None and shipment.expected_departure and shipment.expected_arrival:
            expected_duration = (
                shipment.expected_arrival - shipment.expected_departure
            ).total_seconds() / 3600

        result = self.ai_service.analyze_readings(
            shipment_id=shipment.shipment_id,
            readings=[
                IoTReading(
                    shipment_id=shipment.shipment_id,
                    **reading.model_dump(),
                )
                for reading in request.readings
            ],
            storage_condition=condition,
            expected_rfid_id=rfid.rfid_id if rfid else None,
            actual_rfid_id=request.actual_rfid_id,
            planned_route=[
                RoutePoint(**point.model_dump())
                for point in request.planned_route
            ],
            expected_duration_hours=expected_duration,
            delay_tolerance_hours=request.delay_tolerance_hours,
            route_threshold_km=request.route_threshold_km,
            expected_qr_id=qr.qr_id if qr else None,
            actual_qr_id=request.actual_qr_id,
            expected_product_id=batch.drug.drug_id,
            actual_product_id=request.actual_product_id,
            expected_batch_id=batch.batch_id,
            actual_batch_id=request.actual_batch_id,
            expected_owner=shipment.current_owner,
            actual_owner=request.actual_owner,
            expiry_date=datetime.combine(
                request.actual_expiry_date or batch.expiry_date,
                time.min,
                tzinfo=timezone.utc,
            ),
            rfid_events=[
                RFIDEvent(
                    shipment_id=shipment.shipment_id,
                    **event.model_dump(),
                )
                for event in request.rfid_events
            ],
        )

        submitted_events = self._submitted_events(request)
        fingerprints = [item["fingerprint"] for item in submitted_events]
        try:
            existing_fingerprints = set()
            if fingerprints:
                existing_fingerprints = set(
                    db.scalars(
                        select(AITelemetryEvent.event_fingerprint).where(
                            AITelemetryEvent.event_fingerprint.in_(fingerprints)
                        )
                    ).all()
                )
            new_events = []
            seen_fingerprints = set(existing_fingerprints)
            for item in submitted_events:
                fingerprint = item["fingerprint"]
                if fingerprint in seen_fingerprints:
                    continue
                seen_fingerprints.add(fingerprint)
                new_events.append(item)
            duplicate_count = len(submitted_events) - len(new_events)
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI telemetry persistence is unavailable",
            ) from exc

        analysis_id = uuid4()
        persistence_payload = {
            "analysis_id": str(analysis_id),
            "persisted_event_count": len(new_events),
            "duplicate_event_count": duplicate_count,
        }
        result["persistence"] = persistence_payload
        analysis_time = datetime.fromisoformat(
            result["explainability"]["assessment_time"]
        )
        analysis_record = AIAnalysisRecord(
            id=analysis_id,
            shipment_id=shipment.id,
            assessed_by=assessed_by,
            assessed_at=analysis_time,
            risk_score=result["risk"]["score"],
            risk_level=result["risk"]["risk_level"],
            evidence_hash=result["blockchain"]["evidence_hash"],
            result=result,
        )

        try:
            for item in new_events:
                db.add(
                    AITelemetryEvent(
                        shipment_id=shipment.id,
                        batch_id=batch.id,
                        event_type=item["event_type"],
                        event_time=item["event_time"],
                        event_fingerprint=item["fingerprint"],
                        payload=item["payload"],
                    )
                )
            db.add(analysis_record)
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI telemetry or analysis could not be persisted",
            ) from exc

        return result

    def simulate(self, shipment_id: str, scenario_name: str, db: Session) -> dict:
        shipment, batch, qr, rfid = self._load_context(shipment_id, db)
        simulated_expiry_date = None
        try:
            if scenario_name == "expiry_violation":
                scenario = ScenarioEngine().build_scenario("normal")
                simulated_expiry_date = date.today() - timedelta(days=1)
            else:
                scenario = ScenarioEngine().build_scenario(scenario_name)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        generated = scenario.sensor_readings
        generated_events = scenario.rfid_events
        expected_rfid_id = rfid.rfid_id if rfid else None
        expected_qr_id = qr.qr_id if qr else None
        expected_owner = shipment.current_owner
        expected_batch_id = batch.batch_id
        expected_product_id = batch.drug.drug_id

        simulated_readings = []
        for reading in generated:
            observed = dict(reading)
            observed["shipment_id"] = shipment.shipment_id
            observed["rfid_id"] = expected_rfid_id
            simulated_readings.append(observed)

        condition = self._storage_condition(batch.drug)
        if condition is not None:
            normal_temperature = (
                condition.minimum_temperature + condition.maximum_temperature
            ) / 2
            normal_humidity = (
                condition.minimum_humidity + condition.maximum_humidity
            ) / 2
            temperature_excursion = scenario_name in {
                "temperature_excursion",
                "combined_high_risk",
            }
            humidity_excursion = scenario_name in {
                "humidity_excursion",
                "combined_high_risk",
                "unauthorized_transfer",
            }
            for reading in simulated_readings:
                reading["temperature"] = (
                    condition.maximum_temperature + 7.0
                    if temperature_excursion
                    else normal_temperature
                )
                reading["humidity"] = (
                    condition.maximum_humidity + 18.0
                    if humidity_excursion
                    else normal_humidity
                )

        simulated_events = []
        for source in generated_events:
            event = dict(source)
            event["shipment_id"] = shipment.shipment_id
            is_rfid_mismatch = scenario_name in {"rfid_mismatch", "combined_high_risk"}
            is_qr_mismatch = scenario_name == "qr_mismatch"
            is_unauthorized = scenario_name == "unauthorized_transfer"
            event["rfid_id"] = (
                f"{expected_rfid_id or 'RFID'}-SIMULATED-MISMATCH"
                if is_rfid_mismatch
                else expected_rfid_id
            )
            event["qr_id"] = (
                f"{expected_qr_id or 'QR'}-SIMULATED-MISMATCH"
                if is_qr_mismatch
                else expected_qr_id
            )
            event["product_id"] = expected_product_id
            event["batch_id"] = expected_batch_id
            event["owner"] = "simulated-unauthorized-owner" if is_unauthorized else expected_owner
            event["authorized"] = not is_unauthorized
            simulated_events.append(event)

        route_points = []
        for point in scenario.shipments[0].route:
            route_points.append(
                {
                    "latitude": point.latitude,
                    "longitude": point.longitude,
                    "location_name": point.location_name,
                    "timestamp": point.timestamp,
                }
            )
        actuals = simulated_events[-1] if simulated_events else {}
        return AIAnalysisRequest(
            shipment_id=shipment.shipment_id,
            readings=simulated_readings,
            rfid_events=simulated_events,
            planned_route=route_points,
            actual_rfid_id=actuals.get("rfid_id"),
            actual_qr_id=actuals.get("qr_id"),
            actual_product_id=actuals.get("product_id"),
            actual_batch_id=actuals.get("batch_id"),
            actual_owner=actuals.get("owner"),
            expected_duration_hours=scenario.shipments[0].expected_duration_hours,
            delay_tolerance_hours=scenario.shipments[0].delay_tolerance_hours,
            route_threshold_km=scenario.shipments[0].route_threshold_km,
            actual_expiry_date=simulated_expiry_date,
        ).model_dump(mode="json")

    @staticmethod
    def _submitted_events(request: AIAnalysisRequest) -> list[dict]:
        events = []
        for event_type, items in (
            ("READING", request.readings),
            ("RFID_SCAN", request.rfid_events),
        ):
            for item in items:
                payload = item.model_dump(mode="json")
                event_time = item.timestamp
                canonical = json.dumps(
                    {
                        "shipment_id": request.shipment_id,
                        "event_type": event_type,
                        "event_time": event_time.isoformat(),
                        "payload": payload,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                events.append(
                    {
                        "event_type": event_type,
                        "event_time": event_time,
                        "payload": payload,
                        "fingerprint": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
                    }
                )
        return events

    @staticmethod
    def _load_context(shipment_id: str, db: Session):
        shipment = (
            db.query(Shipment)
            .filter(Shipment.shipment_id == shipment_id)
            .first()
        )
        if shipment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shipment not found",
            )

        batch = db.query(Batch).filter(Batch.id == shipment.batch_id).first()
        if batch is None or batch.drug is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shipment batch or drug not found",
            )

        qr = (
            db.query(QRRecord)
            .filter(QRRecord.batch_id == batch.id, QRRecord.status == "ACTIVE")
            .order_by(QRRecord.created_at.desc())
            .first()
        )
        rfid = (
            db.query(RFIDRecord)
            .filter(RFIDRecord.batch_id == batch.id, RFIDRecord.status == "ACTIVE")
            .order_by(RFIDRecord.created_at.desc())
            .first()
        )

        return shipment, batch, qr, rfid

    @staticmethod
    def _storage_condition(drug) -> StorageCondition | None:
        values = (
            drug.storage_min_temp,
            drug.storage_max_temp,
            drug.storage_min_humidity,
            drug.storage_max_humidity,
        )
        if any(value is None for value in values):
            return None
        return StorageCondition(
            minimum_temperature=drug.storage_min_temp,
            maximum_temperature=drug.storage_max_temp,
            minimum_humidity=drug.storage_min_humidity,
            maximum_humidity=drug.storage_max_humidity,
        )
