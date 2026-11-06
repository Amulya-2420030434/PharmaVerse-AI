from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.schemas.fda import FDALiveSummaryResponse
from app.core.security import get_current_user
from app.database.connection import get_db
from app.models.user import User
from app.models.ai_telemetry_event import AIAnalysisRecord
from app.models.shipment import Shipment
from app.schemas.ai import (
    AIAnalysisHistoryItem,
    AIAnalysisRequest,
    AIAnalysisResponse,
    AISimulationRequest,
)
from app.services.ai_adapter import AIAdapter
from app.services.fda_reference import FDAReferenceService


router = APIRouter(
    prefix="/api/ai",
    tags=["AI"],
)

fda_service = FDAReferenceService()


@router.post(
    "/analyze",
    response_model=AIAnalysisResponse,
)
def analyze_shipment(
    request: AIAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AIAdapter().analyze(request, db, current_user.id)


@router.post("/simulate")
def simulate_shipment_events(
    request: AISimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AIAdapter().simulate(request.shipment_id, request.scenario, db)


@router.get(
    "/shipments/{shipment_id}/history",
    response_model=list[AIAnalysisHistoryItem],
)
def shipment_analysis_history(
    shipment_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="limit must be between 1 and 100",
        )
    shipment = db.scalar(
        select(Shipment).where(Shipment.shipment_id == shipment_id.strip())
    )
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    records = db.scalars(
        select(AIAnalysisRecord)
        .where(AIAnalysisRecord.shipment_id == shipment.id)
        .order_by(AIAnalysisRecord.assessed_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "analysis_id": str(record.id),
            "assessed_at": record.assessed_at,
            "risk_score": record.risk_score,
            "risk_level": record.risk_level,
            "evidence_hash": record.evidence_hash,
            "result": record.result,
        }
        for record in records
    ]


@router.get("/fda-reference")
def fda_reference(
    drug_name: str,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
):
    return fda_service.search(drug_name, limit)
@router.get(
    "/fda-live/summary",
    response_model=FDALiveSummaryResponse,
)
def fda_live_summary(
    current_user: User = Depends(get_current_user),
):
    return fda_service.live_summary()