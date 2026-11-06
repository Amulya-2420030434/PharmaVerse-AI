"""Optional, reproducible machine-learning components.

The deterministic rule engine remains the source of truth.  ML is an additive
assessment and is deliberately unavailable when its optional dependencies or
artifacts are not installed.
"""

from .model import ML_DISCLAIMER, ModelPrediction, ModelStatus, RiskModel

__all__ = ["ML_DISCLAIMER", "ModelPrediction", "ModelStatus", "RiskModel"]
