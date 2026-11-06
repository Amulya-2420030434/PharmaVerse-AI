from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models.user import User
from app.ml.model import RiskModel

router = APIRouter(prefix="/api/ml", tags=["ML"])


@router.get("/status")
def status(current_user: User = Depends(get_current_user)):
    return RiskModel().status.__dict__


@router.get("/metrics")
def metrics(current_user: User = Depends(get_current_user)):
    model = RiskModel()
    return {"available": model.status.available, "metrics": model.metrics()}


@router.post("/predict")
def predict(features: dict[str, float], current_user: User = Depends(get_current_user)):
    model = RiskModel()
    return model.predict(features).__dict__
