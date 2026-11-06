from __future__ import annotations


def build_scenario() -> dict:
    return {
        "name": "unauthorized_transfer",
        "description": "A product transfer occurs with no valid authorization or provenance record.",
        "risk_level": "critical",
    }
