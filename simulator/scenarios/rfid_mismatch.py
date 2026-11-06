from __future__ import annotations


def build_scenario() -> dict:
    return {
        "name": "rfid_mismatch",
        "description": "RFID tag information differs from the expected authenticated identifier.",
        "risk_level": "high",
    }
