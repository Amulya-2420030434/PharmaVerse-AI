from __future__ import annotations

from datetime import timedelta
from math import atan2, cos, radians, sin, sqrt
from typing import Iterable, List, Optional, Sequence

from .models import AnomalyRecord, IoTReading, StorageCondition, ensure_utc
from ..simulation.models import RoutePoint


class AnomalyDetector:
    def __init__(self, default_condition: Optional[StorageCondition] = None):
        self.default_condition = default_condition or StorageCondition(
            minimum_temperature=2.0,
            maximum_temperature=8.0,
            minimum_humidity=35.0,
            maximum_humidity=65.0,
        )

    def detect(self, reading: IoTReading, condition: Optional[StorageCondition] = None) -> List[AnomalyRecord]:
        condition = condition or self.default_condition
        anomalies: List[AnomalyRecord] = []
        timestamp = reading.timestamp

        if reading.temperature is not None and not condition.minimum_temperature <= reading.temperature <= condition.maximum_temperature:
            distance = min(
                abs(reading.temperature - condition.minimum_temperature),
                abs(reading.temperature - condition.maximum_temperature),
            )
            anomalies.append(
                AnomalyRecord(
                    shipment_id=reading.shipment_id,
                    sensor_id=reading.sensor_id,
                    type="temperature_excursion",
                    severity="high" if distance >= 5 else "medium",
                    message="Temperature is outside the configured storage range.",
                    timestamp=timestamp,
                    factor="environmental",
                    evidence={
                        "temperature": reading.temperature,
                        "minimum": condition.minimum_temperature,
                        "maximum": condition.maximum_temperature,
                        "magnitude": round(distance, 2),
                    },
                )
            )

        if reading.humidity is not None and not condition.minimum_humidity <= reading.humidity <= condition.maximum_humidity:
            distance = min(
                abs(reading.humidity - condition.minimum_humidity),
                abs(reading.humidity - condition.maximum_humidity),
            )
            anomalies.append(
                AnomalyRecord(
                    shipment_id=reading.shipment_id,
                    sensor_id=reading.sensor_id,
                    type="humidity_excursion",
                    severity="high" if distance >= 25 else "medium",
                    message="Humidity is outside the configured storage range.",
                    timestamp=timestamp,
                    factor="environmental",
                    evidence={
                        "humidity": reading.humidity,
                        "minimum": condition.minimum_humidity,
                        "maximum": condition.maximum_humidity,
                        "magnitude": round(distance, 2),
                    },
                )
            )

        if reading.speed is not None and reading.speed > 80.0:
            anomalies.append(
                AnomalyRecord(
                    shipment_id=reading.shipment_id,
                    sensor_id=reading.sensor_id,
                    type="route_deviation",
                    severity="medium",
                    message="Vehicle speed exceeds the configured transit threshold.",
                    timestamp=timestamp,
                    factor="route",
                    evidence={"speed": reading.speed, "threshold": 80.0},
                )
            )

        if reading.latitude is None or reading.longitude is None:
            anomalies.append(
                AnomalyRecord(
                    shipment_id=reading.shipment_id,
                    sensor_id=reading.sensor_id,
                    type="missing_geolocation",
                    severity="low",
                    message="Reading is missing coordinates, reducing provenance confidence.",
                    timestamp=timestamp,
                    factor="route",
                    evidence={"latitude": reading.latitude, "longitude": reading.longitude},
                )
            )

        if reading.rfid_id is None:
            anomalies.append(
                AnomalyRecord(
                    shipment_id=reading.shipment_id,
                    sensor_id=reading.sensor_id,
                    type="rfid_missing",
                    severity="medium",
                    message="RFID identifier is missing for the shipment event.",
                    timestamp=timestamp,
                    factor="identity",
                    evidence={"rfid_id": None},
                )
            )
        return anomalies

    @staticmethod
    def _distance_km(first: tuple[float, float], second: tuple[float, float]) -> float:
        lat1, lon1, lat2, lon2 = map(radians, (*first, *second))
        dlat, dlon = lat2 - lat1, lon2 - lon1
        value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        return 6371.0 * 2 * atan2(sqrt(value), sqrt(1 - value))

    @classmethod
    def _nearest_route_distance(cls, reading: IoTReading, route: Sequence[RoutePoint]) -> float:
        if reading.latitude is None or reading.longitude is None:
            return 0.0
        return min(
            cls._distance_km((reading.latitude, reading.longitude), (point.latitude, point.longitude))
            for point in route
        )

    def detect_many(
        self,
        readings: Iterable[IoTReading],
        condition: Optional[StorageCondition] = None,
        planned_route: Optional[Sequence[RoutePoint]] = None,
        route_threshold_km: float = 25.0,
        expected_duration_hours: Optional[float] = None,
        delay_tolerance_hours: float = 1.0,
    ) -> List[AnomalyRecord]:
        reading_list = sorted(readings, key=lambda item: ensure_utc(item.timestamp))
        records: List[AnomalyRecord] = []
        for reading in reading_list:
            records.extend(self.detect(reading, condition=condition))
            if planned_route and reading.latitude is not None and reading.longitude is not None:
                distance = self._nearest_route_distance(reading, planned_route)
                if distance > route_threshold_km:
                    records.append(
                        AnomalyRecord(
                            shipment_id=reading.shipment_id,
                            sensor_id=reading.sensor_id,
                            type="route_deviation",
                            severity="high" if distance > route_threshold_km * 2 else "medium",
                            message="Actual coordinates are outside the planned route corridor.",
                            timestamp=reading.timestamp,
                            factor="route",
                            evidence={
                                "expected_route": [point.location_name for point in planned_route],
                                "actual_location": reading.location_name,
                                "actual_coordinates": [reading.latitude, reading.longitude],
                                "nearest_route_distance_km": round(distance, 2),
                                "threshold_km": route_threshold_km,
                            },
                        )
                    )

        if expected_duration_hours is not None and len(reading_list) >= 2:
            actual_duration = (
                ensure_utc(reading_list[-1].timestamp) - ensure_utc(reading_list[0].timestamp)
            ).total_seconds() / 3600
            delay_hours = actual_duration - expected_duration_hours
            if delay_hours > delay_tolerance_hours:
                records.append(
                    AnomalyRecord(
                        shipment_id=reading_list[-1].shipment_id,
                        sensor_id=reading_list[-1].sensor_id,
                        type="shipment_delay",
                        severity="high" if delay_hours > expected_duration_hours else "medium",
                        message="Projected shipment duration exceeds the expected arrival duration.",
                        timestamp=reading_list[-1].timestamp,
                        factor="delay",
                        evidence={
                            "expected_duration_hours": expected_duration_hours,
                            "actual_duration_hours": round(actual_duration, 2),
                            "delay_hours": round(delay_hours, 2),
                            "tolerance_hours": delay_tolerance_hours,
                        },
                    )
                )
        return records
