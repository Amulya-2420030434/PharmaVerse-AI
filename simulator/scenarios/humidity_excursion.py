from __future__ import annotations


def build_scenario() -> dict:
    return {
        "name": "humidity_excursion",
        "description": "Humidity exceeds expected storage criteria for the product.",
        "risk_level": "medium",
    }
