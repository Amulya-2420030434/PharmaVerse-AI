from __future__ import annotations

from typing import Iterable, List

from .models import AnomalyRecord, RiskScore


class ExplainabilityEngine:
    def explain(self, risk: RiskScore, anomalies: Iterable[AnomalyRecord]) -> List[str]:
        items = list(anomalies)
        if not items:
            return ["No scored anomaly evidence was recorded for this assessment."]

        descriptions = {
            "environmental": "Environmental excursion",
            "route": "Route deviation",
            "delay": "Shipment delay",
            "identity": "Identity mismatch",
            "expiry": "Expiry violation",
            "ownership": "Unauthorized ownership transfer",
        }
        reasons: List[str] = []
        for factor, evidence_ids in sorted(risk.factor_evidence.items()):
            messages = sorted(
                {
                    item.message
                    for item in items
                    if item.factor == factor and item.message
                }
            )
            message_text = f": {'; '.join(messages)}" if messages else ""
            reasons.append(
                f"{descriptions.get(factor, factor)}{message_text}. "
                f"Evidence IDs: {', '.join(evidence_ids)}."
            )
        for interaction, contribution in sorted(risk.interaction_contributions.items()):
            reasons.append(
                f"Interaction {interaction} adds {contribution:.1f} points."
            )
        return reasons
