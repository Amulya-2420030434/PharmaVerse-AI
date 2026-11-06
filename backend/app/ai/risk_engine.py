from __future__ import annotations

from typing import Iterable, List, Optional

from .models import AnomalyRecord, RiskScore, anomaly_evidence_id


class RiskEngine:
    FACTOR_WEIGHTS = {
        "environmental": 20,
        "route": 20,
        "delay": 15,
        "identity": 20,
        "expiry": 5,
        "ownership": 10,
    }

    INTERACTION_WEIGHTS = {
        ("environmental", "route"): 10,
        ("route", "delay"): 10,
    }

    FACTOR_LABELS = {
        "environmental": "environmental excursion",
        "route": "route deviation",
        "delay": "shipment delay",
        "identity": "identity mismatch",
        "expiry": "expiry violation",
        "ownership": "unauthorized ownership transfer",
    }

    def assess(
        self,
        shipment_id: str,
        anomalies: Iterable[AnomalyRecord],
    ) -> RiskScore:
        anomaly_list = list(anomalies)
        active_factors = {item.factor for item in anomaly_list if item.factor in self.FACTOR_WEIGHTS}
        factor_evidence = {
            factor: sorted(
                {
                    anomaly_evidence_id(item)
                    for item in anomaly_list
                    if item.factor == factor
                }
            )
            for factor in active_factors
        }
        interactions = {
            f"{first}+{second}": float(weight)
            for (first, second), weight in self.INTERACTION_WEIGHTS.items()
            if first in active_factors and second in active_factors
        }
        weighted_score = sum(self.FACTOR_WEIGHTS[factor] for factor in active_factors)
        weighted_score += sum(interactions.values())
        score = min(100.0, max(0.0, float(weighted_score)))

        if score >= 75:
            risk_level = "critical"
        elif score >= 50:
            risk_level = "high"
        elif score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"

        drivers = sorted(self.FACTOR_LABELS[factor] for factor in active_factors)
        if not drivers:
            drivers = ["no anomalies detected"]

        explanation = []
        for factor in sorted(active_factors):
            identifiers = ", ".join(factor_evidence[factor])
            explanation.append(
                f"{self.FACTOR_LABELS[factor]} (weight {self.FACTOR_WEIGHTS[factor]}) "
                f"used evidence IDs: {identifiers}."
            )
        for interaction, contribution in sorted(interactions.items()):
            explanation.append(
                f"Distinct-factor interaction {interaction} contributes {contribution:.1f} points."
            )
        explanation.append(
            f"Bounded heuristic score is {score:.1f}/100, classified as {risk_level}."
        )
        return RiskScore(
            shipment_id=shipment_id,
            score=score,
            risk_level=risk_level,
            drivers=drivers,
            explanation=explanation,
            evidence_count=len(anomaly_list),
            factor_evidence=factor_evidence,
            interaction_contributions=interactions,
            requires_human_review=score >= 50,
        )
