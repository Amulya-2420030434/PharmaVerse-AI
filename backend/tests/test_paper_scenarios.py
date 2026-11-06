from backend.app.simulation.manager import SimulationManager


def _analysis(scenario: str) -> dict:
    return SimulationManager().run_scenario(scenario)["analysis"]


def _assert_bounded(analysis: dict) -> None:
    assert 0.0 <= analysis["risk"]["score"] <= 100.0


def test_paper_scenario_normal_operation_scores_zero():
    analysis = _analysis("normal")

    assert analysis["risk"]["score"] == 0.0
    assert analysis["risk"]["factor_evidence"] == {}
    _assert_bounded(analysis)


def test_paper_scenario_temperature_excursion_is_evidenced():
    analysis = _analysis("temperature_excursion")

    assert "temperature_excursion" in {item["type"] for item in analysis["anomalies"]}
    assert "environmental" in analysis["risk"]["factor_evidence"]
    _assert_bounded(analysis)


def test_paper_scenario_humidity_excursion_is_evidenced():
    analysis = _analysis("humidity_excursion")

    assert "humidity_excursion" in {item["type"] for item in analysis["anomalies"]}
    assert "environmental" in analysis["risk"]["factor_evidence"]
    _assert_bounded(analysis)


def test_paper_scenario_route_deviation_is_evidenced():
    analysis = _analysis("route_deviation")

    assert "route_deviation" in {item["type"] for item in analysis["anomalies"]}
    assert "route" in analysis["risk"]["factor_evidence"]
    _assert_bounded(analysis)


def test_paper_scenario_delay_is_evidenced():
    analysis = _analysis("delayed_shipment")

    assert "shipment_delay" in {item["type"] for item in analysis["anomalies"]}
    assert "delay" in analysis["risk"]["factor_evidence"]
    _assert_bounded(analysis)


def test_paper_scenario_rfid_mismatch_is_evidenced():
    analysis = _analysis("rfid_mismatch")

    assert "rfid_mismatch" in {item["type"] for item in analysis["anomalies"]}
    assert "identity" in analysis["risk"]["factor_evidence"]
    _assert_bounded(analysis)


def test_paper_scenario_qr_mismatch_is_evidenced():
    analysis = _analysis("qr_mismatch")

    assert "qr_mismatch" in {item["type"] for item in analysis["anomalies"]}
    assert "identity" in analysis["risk"]["factor_evidence"]
    _assert_bounded(analysis)


def test_paper_scenario_unauthorized_transfer_is_evidenced():
    analysis = _analysis("unauthorized_transfer")

    assert "ownership_inconsistency" in {item["type"] for item in analysis["anomalies"]}
    assert "ownership" in analysis["risk"]["factor_evidence"]
    _assert_bounded(analysis)


def test_paper_scenario_combined_high_risk_scores_ninety_five():
    analysis = _analysis("combined_high_risk")

    assert analysis["risk"]["score"] == 95.0
    assert {"environmental", "route", "delay", "identity"} <= set(
        analysis["risk"]["factor_evidence"]
    )
    assert analysis["risk"]["interaction_contributions"] == {
        "environmental+route": 10.0,
        "route+delay": 10.0,
    }
    _assert_bounded(analysis)
