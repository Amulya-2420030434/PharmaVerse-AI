from __future__ import annotations


def build_scenario() -> dict:
    return {
        "name": "temperature_excursion",
        "description": "Cold-chain temperature exceeds the maximum threshold during transit.",
        "risk_level": "high",
    }
