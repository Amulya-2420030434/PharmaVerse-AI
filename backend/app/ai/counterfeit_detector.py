from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Optional

from .models import AnomalyRecord, CounterfeitAssessment, ensure_utc


class CounterfeitDetector:
    def assess(
        self,
        shipment_id: str,
        anomalies: Iterable[AnomalyRecord],
        expected_rfid_id: str | None = None,
        actual_rfid_id: str | None = None,
        expected_qr_id: str | None = None,
        actual_qr_id: str | None = None,
        expected_product_id: str | None = None,
        actual_product_id: str | None = None,
        expected_batch_id: str | None = None,
        actual_batch_id: str | None = None,
        expected_owner: str | None = None,
        actual_owner: str | None = None,
        expiry_date: Optional[datetime] = None,
        assessment_time: Optional[datetime] = None,
    ) -> CounterfeitAssessment:
        anomaly_list = list(anomalies)
        reasons: List[str] = []
        evaluation_time = ensure_utc(assessment_time) if assessment_time else datetime.now(timezone.utc)
        evidence = {
            "anomaly_count": len(anomaly_list),
            "expected_rfid_id": expected_rfid_id,
            "actual_rfid_id": actual_rfid_id,
            "expected_qr_id": expected_qr_id,
            "actual_qr_id": actual_qr_id,
            "expected_product_id": expected_product_id,
            "actual_product_id": actual_product_id,
            "expected_batch_id": expected_batch_id,
            "actual_batch_id": actual_batch_id,
            "expected_owner": expected_owner,
            "actual_owner": actual_owner,
        }
        mismatches = 0
        if expected_rfid_id and actual_rfid_id and expected_rfid_id != actual_rfid_id:
            mismatches += 1
            reasons.append("RFID does not match the expected authenticated identifier.")
        if expected_qr_id and actual_qr_id and expected_qr_id != actual_qr_id:
            mismatches += 1
            reasons.append("QR identity does not match the expected product record.")
        if expected_product_id and actual_product_id and expected_product_id != actual_product_id:
            mismatches += 1
            reasons.append("Drug/product identity does not match the expected record.")
        if expected_batch_id and actual_batch_id and expected_batch_id != actual_batch_id:
            mismatches += 1
            reasons.append("Batch identity does not match the expected record.")
        if expected_owner and actual_owner and expected_owner != actual_owner:
            mismatches += 1
            reasons.append("Ownership does not match the authorized owner.")
        if expiry_date and ensure_utc(expiry_date).date() < evaluation_time.date():
            mismatches += 1
            reasons.append("Product expiry date has passed.")
        if any(item.type in {"route_deviation", "missing_geolocation"} for item in anomaly_list):
            reasons.append("Route/provenance evidence is incomplete or inconsistent.")
        if any(item.type == "rfid_duplicate" for item in anomaly_list):
            reasons.append("Duplicate RFID activity was observed for the same shipment.")
        if any(item.type == "rfid_mismatch" for item in anomaly_list) and not any(
            "RFID does not match" in reason for reason in reasons
        ):
            mismatches += 1
            reasons.append("RFID event history contains an identity mismatch.")
        if any(item.type == "qr_mismatch" for item in anomaly_list) and not any(
            "QR identity" in reason for reason in reasons
        ):
            mismatches += 1
            reasons.append("QR event history contains an identity mismatch.")
        if any(item.type == "missing_identity" for item in anomaly_list):
            reasons.append("Required drug, batch, or identity fields are missing.")

        identity_checked = any(
            expected and actual
            for expected, actual in (
                (expected_rfid_id, actual_rfid_id),
                (expected_qr_id, actual_qr_id),
                (expected_product_id, actual_product_id),
                (expected_batch_id, actual_batch_id),
                (expected_owner, actual_owner),
            )
        )
        evidence["identity_checked"] = identity_checked
        if not reasons and not identity_checked:
            return CounterfeitAssessment(
                shipment_id=shipment_id,
                is_counterfeit_risk=False,
                risk_level="low",
                status="UNVERIFIED",
                reasons=["No observed QR/RFID or ownership values were supplied for comparison."],
                evidence=evidence,
            )
        if not reasons:
            return CounterfeitAssessment(
                shipment_id=shipment_id,
                is_counterfeit_risk=False,
                risk_level="low",
                status="AUTHENTIC",
                reasons=["Identity and provenance evidence are internally consistent."],
                evidence=evidence,
            )
        status = "POTENTIAL_COUNTERFEIT" if mismatches >= 2 else "SUSPICIOUS"
        if any(item.type == "missing_identity" for item in anomaly_list):
            status = "INVALID"
        risk_level = "critical" if status in {"POTENTIAL_COUNTERFEIT", "INVALID"} else "high"
        return CounterfeitAssessment(
            shipment_id=shipment_id,
            is_counterfeit_risk=True,
            risk_level=risk_level,
            status=status,
            reasons=reasons,
            evidence=evidence,
        )
