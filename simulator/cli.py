from __future__ import annotations

import argparse
import json

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
for _path in [str(ROOT_DIR), str(BACKEND_DIR)]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

from backend.app.simulation.scenario_engine import ScenarioEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PharmaVerse AI telemetry scenarios.")
    parser.add_argument("--list", action="store_true", help="List available scenarios.")
    parser.add_argument("--scenario", choices=ScenarioEngine().list_scenarios(), help="Scenario to generate.")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of a summary.")
    args = parser.parse_args()

    if args.list:
        print("\n".join(ScenarioEngine().list_scenarios()))
        return

    scenario = ScenarioEngine().build_scenario(args.scenario)
    if args.json:
        print(json.dumps(scenario.model_dump(mode="json"), indent=2))
    else:
        print(f"Scenario: {scenario.name}")
        print(f"Description: {scenario.description}")
        print(f"Shipments: {len(scenario.shipments)}")
        print(f"Sensor readings: {len(scenario.sensor_readings)}")
        print(f"RFID events: {len(scenario.rfid_events)}")


if __name__ == "__main__":
    main()
