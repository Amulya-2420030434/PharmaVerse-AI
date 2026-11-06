from __future__ import annotations

from typing import Any, Callable, Dict, List

from ..ai.models import StorageCondition
from .models import ScenarioResult, Shipment
from .rfid_simulator import RFIDSimulator
from .sensor_simulator import SensorSimulator
from .shipment_simulator import ShipmentSimulator


class ScenarioEngine:
    def __init__(self):
        self.shipment_simulator = ShipmentSimulator()
        self.sensor_simulator = SensorSimulator()
        self.rfid_simulator = RFIDSimulator()

    def list_scenarios(self) -> List[str]:
        return [
            "normal",
            "temperature_excursion",
            "humidity_excursion",
            "route_deviation",
            "delayed_shipment",
            "rfid_mismatch",
            "qr_mismatch",
            "unauthorized_transfer",
            "combined_high_risk",
        ]

    def build_scenario(self, name: str) -> ScenarioResult:
        scenario_map: Dict[str, Callable[[], ScenarioResult]] = {
            "normal": self._normal,
            "temperature_excursion": self._temperature_excursion,
            "humidity_excursion": self._humidity_excursion,
            "route_deviation": self._route_deviation,
            "delayed_shipment": self._delayed_shipment,
            "rfid_mismatch": self._rfid_mismatch,
            "qr_mismatch": self._qr_mismatch,
            "unauthorized_transfer": self._unauthorized_transfer,
            "combined_high_risk": self._combined_high_risk,
        }
        if name not in scenario_map:
            raise ValueError(f"Unknown scenario '{name}'. Available: {self.list_scenarios()}")
        scenario = scenario_map[name]()
        if scenario.sensor_readings and scenario.rfid_events:
            scenario.rfid_events[-1]["timestamp"] = scenario.sensor_readings[-1]["timestamp"]
        return scenario

    def _base_shipment(self, shipment_id: str, expected_rfid_id: str | None = None) -> Shipment:
        return self.shipment_simulator.create_shipment(
            shipment_id=shipment_id,
            source="Bengaluru",
            destination="Chennai",
            product_name="Aspirin 250mg",
            rfid_id="RFID-1001",
            expected_rfid_id=expected_rfid_id or "RFID-1001",
            expected_qr_id="QR-1001",
            product_id="DRUG-1001",
            batch_id="BATCH-1001",
            expected_owner="manufacturer",
            owner="manufacturer",
            expected_duration_hours=6.0,
            product_type="pharmaceutical",
            storage_condition=StorageCondition(
                minimum_temperature=2.0,
                maximum_temperature=8.0,
                minimum_humidity=35.0,
                maximum_humidity=65.0,
            ),
        )

    def _normal(self) -> ScenarioResult:
        shipment = self._base_shipment("SHP-001")
        readings = self.sensor_simulator.generate_readings(shipment, hours=6, interval_minutes=30)
        rfid_events = self.rfid_simulator.generate_events(shipment)
        return ScenarioResult(
            name="normal",
            description="Baseline shipment with stable environmental and transport conditions.",
            shipments=[shipment],
            sensor_readings=[item.model_dump(mode="json") for item in readings],
            rfid_events=[item.model_dump(mode="json") for item in rfid_events],
        )

    def _temperature_excursion(self) -> ScenarioResult:
        shipment = self._base_shipment("SHP-002")
        readings = self.sensor_simulator.generate_readings(shipment, anomaly="temperature_excursion")
        rfid_events = self.rfid_simulator.generate_events(shipment)
        return ScenarioResult(
            name="temperature_excursion",
            description="Temperature rises above the safe cold-chain threshold during transit.",
            shipments=[shipment],
            sensor_readings=[item.model_dump(mode="json") for item in readings],
            rfid_events=[item.model_dump(mode="json") for item in rfid_events],
        )

    def _humidity_excursion(self) -> ScenarioResult:
        shipment = self._base_shipment("SHP-003")
        readings = self.sensor_simulator.generate_readings(shipment, anomaly="humidity_excursion")
        rfid_events = self.rfid_simulator.generate_events(shipment)
        return ScenarioResult(
            name="humidity_excursion",
            description="Humidity exceeds the acceptable storage range for the product.",
            shipments=[shipment],
            sensor_readings=[item.model_dump(mode="json") for item in readings],
            rfid_events=[item.model_dump(mode="json") for item in rfid_events],
        )

    def _route_deviation(self) -> ScenarioResult:
        shipment = self._base_shipment("SHP-004")
        readings = self.sensor_simulator.generate_readings(shipment, hours=6, interval_minutes=30, anomaly="route_deviation")
        rfid_events = self.rfid_simulator.generate_events(shipment)
        return ScenarioResult(
            name="route_deviation",
            description="Shipment experiences abnormal route conditions and elevated transit speed.",
            shipments=[shipment],
            sensor_readings=[item.model_dump(mode="json") for item in readings],
            rfid_events=[item.model_dump(mode="json") for item in rfid_events],
        )

    def _delayed_shipment(self) -> ScenarioResult:
        shipment = self._base_shipment("SHP-005")
        readings = self.sensor_simulator.generate_readings(shipment, hours=12, interval_minutes=30, anomaly="delayed_shipment")
        rfid_events = self.rfid_simulator.generate_events(shipment)
        return ScenarioResult(
            name="delayed_shipment",
            description="Shipment has delayed delivery with suboptimal environmental guarantees.",
            shipments=[shipment],
            sensor_readings=[item.model_dump(mode="json") for item in readings],
            rfid_events=[item.model_dump(mode="json") for item in rfid_events],
        )

    def _rfid_mismatch(self) -> ScenarioResult:
        shipment = self._base_shipment("SHP-006", expected_rfid_id="RFID-1001")
        readings = self.sensor_simulator.generate_readings(shipment, hours=6, interval_minutes=30)
        rfid_events = self.rfid_simulator.generate_events(shipment, anomaly="rfid_mismatch")
        return ScenarioResult(
            name="rfid_mismatch",
            description="RFID reads do not match the expected value, suggesting tampering or substitution.",
            shipments=[shipment],
            sensor_readings=[item.model_dump(mode="json") for item in readings],
            rfid_events=[item.model_dump(mode="json") for item in rfid_events],
        )

    def _qr_mismatch(self) -> ScenarioResult:
        shipment = self._base_shipment("SHP-007")
        readings = self.sensor_simulator.generate_readings(shipment, hours=6, interval_minutes=30)
        rfid_events = self.rfid_simulator.generate_events(shipment, anomaly="qr_mismatch")
        return ScenarioResult(
            name="qr_mismatch",
            description="QR-associated product identity is inconsistent with the RFID trace.",
            shipments=[shipment],
            sensor_readings=[item.model_dump(mode="json") for item in readings],
            rfid_events=[item.model_dump(mode="json") for item in rfid_events],
        )

    def _unauthorized_transfer(self) -> ScenarioResult:
        shipment = self._base_shipment("SHP-008")
        readings = self.sensor_simulator.generate_readings(shipment, hours=6, interval_minutes=30, anomaly="humidity_excursion")
        rfid_events = self.rfid_simulator.generate_events(shipment, anomaly="unauthorized_transfer")
        return ScenarioResult(
            name="unauthorized_transfer",
            description="The shipment changes custody without a verifiable authorized transfer record.",
            shipments=[shipment],
            sensor_readings=[item.model_dump(mode="json") for item in readings],
            rfid_events=[item.model_dump(mode="json") for item in rfid_events],
        )

    def _combined_high_risk(self) -> ScenarioResult:
        shipment = self._base_shipment("SHP-009", expected_rfid_id="RFID-1001")
        readings = self.sensor_simulator.generate_readings(shipment, hours=12, interval_minutes=30, anomaly="temperature_excursion")
        for reading in readings:
            reading.latitude += 1.0
            reading.longitude += 1.0
            reading.location_name = "off-corridor"
        rfid_events = self.rfid_simulator.generate_events(shipment, anomaly="rfid_mismatch")
        return ScenarioResult(
            name="combined_high_risk",
            description="Multiple anomalies co-occur, indicating an elevated counterfeit and integrity risk.",
            shipments=[shipment],
            sensor_readings=[item.model_dump(mode="json") for item in readings],
            rfid_events=[item.model_dump(mode="json") for item in rfid_events],
        )
