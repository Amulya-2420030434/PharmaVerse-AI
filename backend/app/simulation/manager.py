from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

from ..ai.service import AIService
from ..ai.models import IoTReading
from .models import RFIDEvent
from .scenario_engine import ScenarioEngine


class SimulationManager:
    def __init__(self):
        self.scenario_engine = ScenarioEngine()
        self.ai_service = AIService()
        self._lock = threading.RLock()
        self._stop_event: threading.Event | None = None
        self._thread: threading.Thread | None = None
        self._state: Dict[str, Any] = {"status": "stopped", "scenario": None, "last_result": None}

    def available_scenarios(self) -> List[str]:
        return self.scenario_engine.list_scenarios()

    def run_scenario(self, name: str) -> Dict[str, Any]:
        scenario = self.scenario_engine.build_scenario(name)
        readings = [IoTReading(**item) for item in scenario.sensor_readings]
        latest_rfid_event = scenario.rfid_events[-1] if scenario.rfid_events else None
        analysis = self.ai_service.analyze_readings(
            shipment_id=scenario.shipments[0].shipment_id,
            readings=readings,
            storage_condition=scenario.shipments[0].storage_condition,
            expected_rfid_id=scenario.shipments[0].expected_rfid_id,
            actual_rfid_id=latest_rfid_event["rfid_id"] if latest_rfid_event else None,
            planned_route=scenario.shipments[0].route,
            expected_duration_hours=scenario.shipments[0].expected_duration_hours,
            delay_tolerance_hours=scenario.shipments[0].delay_tolerance_hours,
            route_threshold_km=scenario.shipments[0].route_threshold_km,
            expected_qr_id=scenario.shipments[0].expected_qr_id,
            actual_qr_id=latest_rfid_event.get("qr_id") if latest_rfid_event else None,
            expected_product_id=scenario.shipments[0].product_id,
            actual_product_id=latest_rfid_event.get("product_id") if latest_rfid_event else None,
            expected_batch_id=scenario.shipments[0].batch_id,
            actual_batch_id=latest_rfid_event.get("batch_id") if latest_rfid_event else None,
            expected_owner=scenario.shipments[0].expected_owner,
            actual_owner=latest_rfid_event.get("owner") if latest_rfid_event else None,
            rfid_events=[RFIDEvent(**scenario_event) for scenario_event in scenario.rfid_events],
        )
        return {
            "scenario": scenario.name,
            "description": scenario.description,
            "shipments": [shipment.model_dump(mode="json") for shipment in scenario.shipments],
            "rfid_events": scenario.rfid_events,
            "analysis": analysis,
        }

    def start(self, name: str) -> Dict[str, Any]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                raise RuntimeError("Simulation is already running.")
            if name not in self.available_scenarios():
                raise ValueError(f"Unknown scenario '{name}'. Available: {self.available_scenarios()}")
            self._stop_event = threading.Event()
            self._state.update({"status": "running", "scenario": name})
            self._thread = threading.Thread(target=self._run_loop, args=(name, self._stop_event), daemon=True)
            self._thread.start()
            return self.status()

    def _run_loop(self, name: str, stop_event: threading.Event) -> None:
        try:
            while not stop_event.is_set():
                result = self.run_scenario(name)
                with self._lock:
                    self._state["last_result"] = result
                stop_event.wait(1.0)
        finally:
            with self._lock:
                self._state["status"] = "stopped"

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            if self._stop_event:
                self._stop_event.set()
            thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        with self._lock:
            self._state["status"] = "stopped"
            return self.status()

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": self._state["status"],
                "scenario": self._state["scenario"],
                "has_result": self._state["last_result"] is not None,
            }
