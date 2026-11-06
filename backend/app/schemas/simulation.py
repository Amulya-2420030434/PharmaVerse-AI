from typing import Any

from pydantic import BaseModel, Field


class SimulationScenarioRequest(BaseModel):
    scenario: str = Field(min_length=1)


class SimulationStatusResponse(BaseModel):
    status: str
    scenario: str | None = None
    has_result: bool


class SimulationResultResponse(BaseModel):
    scenario: str
    description: str
    shipments: list[dict[str, Any]]
    rfid_events: list[dict[str, Any]]
    analysis: dict[str, Any]


class SimulationScenarioResponse(BaseModel):
    scenario: str
    description: str
    shipments: list[dict[str, Any]]
    sensor_readings: list[dict[str, Any]]
    rfid_events: list[dict[str, Any]]
    analysis: dict[str, Any]
