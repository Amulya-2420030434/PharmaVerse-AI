from __future__ import annotations

from typing import Iterable

from .models import Alert, RiskScore, CounterfeitAssessment, AnomalyRecord


class AlertEngine:
    def build_alerts(
        self,
        shipment_id: str,
        risk: RiskScore,
        counterfeit: CounterfeitAssessment,
        anomalies: Iterable[AnomalyRecord],
    ) -> list[Alert]:
        anomaly_list = list(anomalies)
        alerts: list[Alert] = []

        if risk.risk_level in {"high", "critical"}:
            alerts.append(
                Alert(
                    shipment_id=shipment_id,
                    alert_type="supply_chain_alert",
                    severity=risk.risk_level,
                    title="High-risk shipment condition",
                    summary="The shipment shows repeated anomalies that suggest potential product integrity or provenance issues.",
                    recommendations=[
                        "Inspect the shipment immediately.",
                        "Verify environmental conditions and chain-of-custody records.",
                        "Escalate to quality control and compliance teams.",
                    ],
                    evidence={"risk_score": risk.score, "anomaly_count": len(anomaly_list)},
                )
            )

        if counterfeit.is_counterfeit_risk:
            alerts.append(
                Alert(
                    shipment_id=shipment_id,
                    alert_type="counterfeit_provenance_alert",
                    severity="high" if counterfeit.risk_level in {"high", "critical"} else "medium",
                    title="Counterfeit or provenance risk",
                    summary="The shipping record indicates a likely discrepancy in provenance or product identity.",
                    recommendations=[
                        "Validate the RFID and product pedigree records.",
                        "Confirm the origin and handoff points for the shipment.",
                        "Hold the package pending verification.",
                    ],
                    evidence={"reasons": counterfeit.reasons},
                )
            )

        return alerts
