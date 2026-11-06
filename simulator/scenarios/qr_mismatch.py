from __future__ import annotations


def build_scenario() -> dict:
    return {
        "name": "qr_mismatch",
        "description": "QR-coded provenance metadata does not align with the traced RFID record.",
        "risk_level": "high",
    }
