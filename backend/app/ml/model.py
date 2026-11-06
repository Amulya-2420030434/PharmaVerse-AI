from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

FEATURE_NAMES = ("anomaly_count", "high_severity_count", "identity_anomaly_count", "sensor_anomaly_count")


ML_DISCLAIMER = (
    "Statistical risk estimate from a research model. It supplements, and "
    "never replaces, the deterministic rule-based risk engine, and it is not "
    "laboratory confirmation that a product is counterfeit."
)


def _json_safe(value: Any) -> Any:
    """Convert numpy scalars/arrays and other non-JSON values to plain types."""
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "tolist"):  # numpy scalar or ndarray
        return _json_safe(value.tolist())
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


@dataclass(frozen=True)
class ModelStatus:
    available: bool
    reason: str
    artifact: str | None = None
    metrics: dict[str, Any] | None = None
    model_name: str | None = None
    feature_names: list[str] | None = None
    disclaimer: str = ML_DISCLAIMER


@dataclass(frozen=True)
class ModelPrediction:
    available: bool
    probability: float | None
    label: str | None
    reason: str | None = None
    disclaimer: str = ML_DISCLAIMER


class RiskModel:
    """Load an explicitly configured sklearn artifact; never train at import time."""

    def __init__(self, artifact_path: str | os.PathLike[str] | None = None):
        configured = artifact_path or os.getenv("PHARMAVERSE_ML_ARTIFACT")
        if not configured:
            try:
                from app.core.config import settings
                configured = getattr(settings, "pharmaverse_ml_artifact", None)
            except Exception:
                configured = None
        resolved = None
        if configured:
            candidates = [
                Path(configured),
                Path(__file__).resolve().parents[3] / "data" / "models" / "pharmaverse_fraud_model.joblib",
                Path(__file__).resolve().parents[2] / "data" / "models" / "pharmaverse_fraud_model.joblib",
            ]
            for candidate in candidates:
                if candidate.exists():
                    resolved = candidate
                    break
            if resolved is None:
                resolved = Path(configured)
        self.artifact_path = resolved
        self._estimator = None
        self._metrics: dict[str, Any] | None = None
        self._model_name: str | None = None
        self._feature_names: list[str] | None = None
        self._load_error: str | None = None
        if self.artifact_path:
            self._load()

    def _load(self) -> None:
        # The artifact path comes from operator configuration
        # (PHARMAVERSE_ML_ARTIFACT), never from request data: joblib artifacts
        # are pickles and must only ever be loaded from a trusted location.
        if not self.artifact_path or not self.artifact_path.exists():
            return
        try:
            import joblib  # type: ignore
            loaded = joblib.load(self.artifact_path)
        except Exception as exc:  # corrupt/incompatible artifact must not crash the API
            self._estimator = None
            self._load_error = f"model artifact could not be loaded ({type(exc).__name__})"
            return

        estimator = loaded.get("model") if isinstance(loaded, dict) else loaded
        if not hasattr(estimator, "predict"):
            self._load_error = "model artifact does not contain a usable estimator"
            return

        if isinstance(loaded, dict):
            declared = loaded.get("feature_names")
            if declared is not None and list(declared) != list(FEATURE_NAMES):
                # Refuse rather than feed features in the wrong order.
                self._load_error = "model artifact feature names do not match the API"
                return
            metrics = loaded.get("metrics")
            self._metrics = _json_safe(metrics) if isinstance(metrics, Mapping) else None
            name = loaded.get("model_name")
            self._model_name = str(name) if name else None
            self._feature_names = list(declared) if declared is not None else None
        self._estimator = estimator

    @property
    def status(self) -> ModelStatus:
        if self._estimator is None:
            reason = self._load_error or "model artifact unavailable"
            try:
                import sklearn  # noqa: F401
            except ImportError:
                reason = "scikit-learn is not installed"
            return ModelStatus(False, reason, str(self.artifact_path) if self.artifact_path else None)
        return ModelStatus(
            True,
            "loaded",
            str(self.artifact_path),
            self._metrics,
            self._model_name,
            self._feature_names,
        )

    def predict(self, features: Mapping[str, float]) -> ModelPrediction:
        if self._estimator is None:
            return ModelPrediction(False, None, None, self.status.reason)
        vector = [[float(features.get(name, 0.0)) for name in FEATURE_NAMES]]
        try:
            label_value = self._estimator.predict(vector)[0]
            probability = None
            if hasattr(self._estimator, "predict_proba"):
                probability = float(self._estimator.predict_proba(vector)[0][1])
            return ModelPrediction(True, probability, str(label_value))
        except Exception:
            return ModelPrediction(False, None, None, "model prediction failed")

    def metrics(self) -> dict[str, Any]:
        return self._metrics or {}

    @staticmethod
    def features_from_analysis(analysis: Mapping[str, Any]) -> dict[str, float]:
        anomalies = analysis.get("anomalies", [])
        return {
            "anomaly_count": float(len(anomalies)),
            "high_severity_count": float(sum(a.get("severity") == "high" for a in anomalies)),
            "identity_anomaly_count": float(sum(a.get("factor") == "identity" for a in anomalies)),
            "sensor_anomaly_count": float(sum(a.get("factor") == "sensor" for a in anomalies)),
        }
