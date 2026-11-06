import json
from pathlib import Path

import pytest

from app.ml.model import RiskModel
from app.services.fda_reference import FDAReferenceService
from scripts.inspect_dataset import inspect


FIXTURE = Path(__file__).parents[2] / "data" / "fixtures" / "risk_fixture.jsonl"


@pytest.mark.skipif(
    not FIXTURE.exists(),
    reason="data/fixtures lives in the project root, outside backend/",
)
def test_fixture_is_small_and_inspectable():
    summary = inspect(FIXTURE)
    assert summary["rows"] == 4
    assert summary["labels"]["0"] == 2
    assert summary["labels"]["1"] == 2


def test_model_is_explicitly_unavailable_without_artifact(monkeypatch):
    monkeypatch.delenv("PHARMAVERSE_ML_ARTIFACT", raising=False)
    monkeypatch.setattr("app.core.config.settings.pharmaverse_ml_artifact", None)
    prediction = RiskModel().predict({"anomaly_count": 1})
    assert prediction.available is False
    assert prediction.reason


def test_configured_research_artifact_is_available_through_authenticated_api(
    client, make_user, monkeypatch
):
    artifact = Path(__file__).parents[2] / "data" / "models" / "pharmaverse_fraud_model.joblib"
    if not artifact.is_file():
        pytest.skip("optional trained-model artifact is not present")

    monkeypatch.setenv("PHARMAVERSE_ML_ARTIFACT", str(artifact))
    _, headers = make_user("ADMIN")

    status = client.get("/api/ml/status", headers=headers)
    prediction = client.post(
        "/api/ml/predict",
        headers=headers,
        json={
            "anomaly_count": 0,
            "high_severity_count": 0,
            "identity_anomaly_count": 0,
            "sensor_anomaly_count": 0,
        },
    )

    assert status.status_code == 200
    assert status.json()["available"] is True
    assert status.json()["model_name"] == "RandomForestClassifier"
    assert prediction.status_code == 200
    assert prediction.json()["available"] is True
    assert prediction.json()["probability"] is not None


def test_fda_reference_uses_injected_offline_transport():
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps({"results": [{"safetyreportid": "fixture"}]}).encode()

    service = FDAReferenceService(opener=lambda url, timeout: Response())
    result = service.search("acetaminophen")
    assert result["results"][0]["safetyreportid"] == "fixture"
