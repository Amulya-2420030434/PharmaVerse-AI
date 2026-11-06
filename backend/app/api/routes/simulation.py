from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import require_roles
from app.models.user import User
from app.schemas.simulation import (
    SimulationResultResponse,
    SimulationScenarioRequest,
    SimulationStatusResponse,
)
from app.simulation.manager import SimulationManager


router = APIRouter(
    prefix="/api/simulation",
    tags=["Simulation"],
)

simulation_manager = SimulationManager()


@router.post("/start", response_model=SimulationStatusResponse)
def start_simulation(
    request: SimulationScenarioRequest,
    current_user: User = Depends(require_roles("ADMIN", "REGULATOR")),
):
    try:
        return simulation_manager.start(request.scenario)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/stop", response_model=SimulationStatusResponse)
def stop_simulation(
    current_user: User = Depends(require_roles("ADMIN", "REGULATOR")),
):
    return simulation_manager.stop()


@router.post(
    "/scenario",
    response_model=SimulationResultResponse,
)
def run_simulation_scenario(
    request: SimulationScenarioRequest,
    current_user: User = Depends(require_roles("ADMIN", "REGULATOR")),
):
    try:
        return simulation_manager.run_scenario(request.scenario)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/status", response_model=SimulationStatusResponse)
def simulation_status(
    current_user: User = Depends(require_roles("ADMIN", "REGULATOR")),
):
    return simulation_manager.status()
