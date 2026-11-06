from __future__ import annotations


def build_scenario() -> dict:
    return {
        "name": "route_deviation",
        "description": "Transit route deviates without a documented operational justification.",
        "risk_level": "high",
    }
