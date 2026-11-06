from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, List, Optional

from ..ai.models import IoTReading, StorageCondition
from .models import Shipment


class SensorSimulator:
    def __init__(self, default_condition: Optional[StorageCondition] = None):
        self.default_condition = default_condition or StorageCondition(
            minimum_temperature=2.0,
            maximum_temperature=8.0,
            minimum_humidity=35.0,
            maximum_humidity=65.0,
        )

    def generate_readings(
        self,
        shipment: Shipment,
        hours: int = 6,
        interval_minutes: int = 30,
        anomaly: Optional[str] = None,
    ) -> List[IoTReading]:
        readings: List[IoTReading] = []
        current = datetime.utcnow()
        condition = shipment.storage_condition or self.default_condition
        if not shipment.route:
            return readings
        for index in range(0, hours * 60, interval_minutes):
            point = shipment.route[min(index // interval_minutes, len(shipment.route) - 1)]
            latitude, longitude, location_name = point.latitude, point.longitude, point.location_name
            temperature = 5.0 + (index % 90) / 20.0
            humidity = 45.0 + ((index * 3) % 25)

            if anomaly == "temperature_excursion":
                temperature = condition.maximum_temperature + 7.0 + (index % 5)
            elif anomaly == "humidity_excursion":
                humidity = condition.maximum_humidity + 18.0
            elif anomaly == "delayed_shipment":
                temperature = 5.0
                humidity = 45.0
            elif anomaly == "route_deviation":
                latitude += 1.0
                longitude += 1.0
                location_name = "off-corridor"

            readings.append(
                IoTReading(
                    shipment_id=shipment.shipment_id,
                    timestamp=current + timedelta(minutes=index),
                    temperature=round(temperature, 2),
                    humidity=round(humidity, 2),
                    latitude=latitude,
                    longitude=longitude,
                    location_name=location_name,
                    speed=45.0 + ((index // 15) % 20),
                    sensor_id=f"sensor-{shipment.shipment_id}",
                    rfid_id=shipment.rfid_id,
                    metadata={"route_index": index // interval_minutes},
                )
            )
        return readings
