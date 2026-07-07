from __future__ import annotations

import pytest

from skills.audit import AuditError, audit_artifact
from skills.config import load_config
from skills.data.cost_of_capital.cost_of_capital import build_cost_of_capital_inputs
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.data.price.price import fetch_price
from skills.serialization import artifact_model_to_payload
from skills.valuation.dcf.dcf import build_dcf_artifacts, build_reverse_expectations
from skills.valuation.method_router.method_router import route_method
from skills.valuation.normalize.normalize import normalize_financials


def _fixture_path():
    config = load_config("config/conventions.yaml")
    edgar = fetch_edgar_facts("AAPL")
    price = fetch_price("AAPL", edgar=edgar)
    coc = build_cost_of_capital_inputs("AAPL", config, edgar=edgar, price=price)
    normalized = normalize_financials(edgar)
    return config, edgar, price, coc, normalized


def _crm_fixture_path():
    config = load_config("config/conventions.yaml")
    edgar = fetch_edgar_facts("CRM")
    price = fetch_price("CRM", edgar=edgar)
    coc = build_cost_of_capital_inputs("CRM", config, edgar=edgar, price=price)
    normalized = normalize_financials(edgar)
    directive = route_method(normalized, edgar, config)
    return config, edgar, price, coc, normalized, directive


def test_forward_dcf_emits_three_schema_valid_scenarios() -> None:
    config, edgar, price, coc, normalized = _fixture_path()
    valuation, expectations = build_dcf_artifacts(normalized, edgar, price, coc, config)

    assert [scenario.name for scenario in valuation.scenarios] == ["bear", "base", "bull"]
    assert valuation.method == "DCF"
    assert all(scenario.value.value > 0 for scenario in valuation.scenarios)
    assert all(scenario.value.derivation for scenario in valuation.scenarios)
    assert all(scenario.probability.decision is None for scenario in valuation.scenarios)
    assert expectations.frame == "DCF"
    base_assumptions = {assumption.driver: assumption for assumption in valuation.scenarios[1].assumptions}
    assert "config.dcf.scenarios.base.revenue_growth" in base_assumptions["revenue_growth"].value.derivation
    assert "config.dcf.scenarios.scenarios" not in base_assumptions["revenue_growth"].value.derivation
    audit_artifact(valuation)


def test_forward_dcf_base_rate_check_uses_current_ticker() -> None:
    config, edgar, price, coc, normalized = _fixture_path()
    normalized = normalized.model_copy(update={"ticker": "MSFT"})
    valuation, _ = build_dcf_artifacts(normalized, edgar, price, coc, config)

    base_assumptions = {assumption.driver: assumption for assumption in valuation.scenarios[1].assumptions}
    expected = "EDGAR fact from normalized MSFT fixture path."
    assert base_assumptions["starting_revenue"].base_rate_check == expected
    assert base_assumptions["diluted_shares"].base_rate_check == expected


def test_reverse_dcf_reports_current_fixture_price_outside_solvable_range() -> None:
    config, edgar, price, coc, normalized = _fixture_path()
    _, expectations = build_dcf_artifacts(normalized, edgar, price, coc, config)

    assert "M2a" not in expectations.frame_justification
    assert "M2b" not in expectations.frame_justification
    assert "DCF is used for routed cash-generating operating companies" in expectations.frame_justification
    low = expectations.reverse_band_results["low"]
    high = expectations.reverse_band_results["high"]
    assert "reverse_dcf_non_convergence" in expectations.flags
    assert not low.converged
    assert not high.converged
    assert low.failure_reason
    assert high.failure_reason
    assert low.implied_revenue_growth is None
    assert high.implied_revenue_growth is None
    assert expectations.implied["revenue_growth"] is None
    assert expectations.implied["revenue_growth_midpoint"] is None
    assert expectations.authoritative_output == "wacc_band_edges"
    assert expectations.wacc_band["low"].value < expectations.wacc_band["high"].value
    audit_artifact(expectations)


def test_reverse_dcf_non_convergence_reports_edges_without_forced_point() -> None:
    config, edgar, price, coc, normalized = _fixture_path()
    expensive_price = price.model_copy(update={"price": price.price.model_copy(update={"value": 1000.0})})
    expectations = build_reverse_expectations(normalized, edgar, expensive_price, coc, config)

    assert "reverse_dcf_non_convergence" in expectations.flags
    assert expectations.implied["revenue_growth"] is None
    assert not expectations.reverse_band_results["low"].converged
    assert not expectations.reverse_band_results["high"].converged
    assert expectations.reverse_band_results["low"].failure_reason
    assert expectations.reverse_band_results["high"].failure_reason
    audit_artifact(expectations)


def test_reverse_dcf_blocks_without_observed_price_but_forward_still_files() -> None:
    config, edgar, price, coc, normalized = _fixture_path()
    no_price = price.model_copy(update={"price": None, "market_cap": None, "flags": [*price.flags, "price_unavailable"]})
    valuation, expectations = build_dcf_artifacts(normalized, edgar, no_price, coc, config)

    assert all(scenario.value.value > 0 for scenario in valuation.scenarios)
    assert "price_unavailable" in valuation.flags
    assert "reverse_dcf_blocked_no_observed_price" in expectations.flags
    assert expectations.implied["revenue_growth"] is None
    assert expectations.reverse_band_results["low"].blocked
    assert expectations.reverse_band_results["high"].blocked
    assert not expectations.reverse_band_results["low"].converged
    audit_artifact(valuation)
    audit_artifact(expectations)


def test_dcf_artifacts_serialize_without_losing_provenance() -> None:
    config, edgar, price, coc, normalized = _fixture_path()
    valuation, expectations = build_dcf_artifacts(normalized, edgar, price, coc, config)
    valuation_payload = artifact_model_to_payload(valuation)
    expectations_payload = artifact_model_to_payload(expectations)

    assert valuation_payload["scenarios"][1]["value"]["provenance"]["tag"] == "computed:dcf_value_per_share"
    assert expectations_payload["wacc_band"]["low"]["provenance"]["tag"] == "computed:wacc_low"


def test_crm_dcf_uses_saas_sector_assumptions_and_differs_from_global_default() -> None:
    config, edgar, price, coc, normalized, directive = _crm_fixture_path()

    global_valuation, global_expectations = build_dcf_artifacts(normalized, edgar, price, coc, config)
    sector_valuation, sector_expectations = build_dcf_artifacts(normalized, edgar, price, coc, config, method_directive=directive)

    assert directive.calibration_sector == "saas"
    assert "dcf_assumption_source:global" in global_valuation.flags
    assert "dcf_assumption_source:sector:saas" in sector_valuation.flags
    assert "dcf_assumption_source:sector:saas" in sector_expectations.flags

    base_assumptions = {assumption.driver: assumption for assumption in sector_valuation.scenarios[1].assumptions}
    assert base_assumptions["revenue_growth"].value.value == pytest.approx(0.123)
    assert base_assumptions["nopat_margin"].value.value == pytest.approx(0.326)
    assert base_assumptions["sales_to_capital"].value.value == pytest.approx(1.54)
    for driver in ("revenue_growth", "nopat_margin", "sales_to_capital"):
        assumption = base_assumptions[driver]
        assert "Aswath Damodaran, NYU Stern" in assumption.base_rate_check
        assert "Software (System & Application)" in assumption.base_rate_check
        assert "January 2026" in assumption.base_rate_check
        assert "config.dcf.sector_scenarios.saas" in assumption.base_rate_check
        assert "config.dcf.sector_scenarios.saas.scenarios.base" in assumption.value.derivation

    global_values = [scenario.value.value for scenario in global_valuation.scenarios]
    sector_values = [scenario.value.value for scenario in sector_valuation.scenarios]
    assert sector_values != global_values
    assert sector_expectations.implied["margin"].value == pytest.approx(0.326)
    assert "config.dcf.sector_scenarios.saas.scenarios.base.nopat_margin" in sector_expectations.implied["margin"].derivation

    audit_artifact(global_valuation)
    audit_artifact(global_expectations)
    audit_artifact(sector_valuation)
    audit_artifact(sector_expectations)


def test_audit_rejects_missing_dcf_derivation() -> None:
    config, edgar, price, coc, normalized = _fixture_path()
    valuation, _ = build_dcf_artifacts(normalized, edgar, price, coc, config)
    broken_value = valuation.scenarios[0].value.model_copy(update={"derivation": None})
    broken_scenario = valuation.scenarios[0].model_copy(update={"value": broken_value})
    broken = valuation.model_copy(update={"scenarios": [broken_scenario, *valuation.scenarios[1:]]})

    with pytest.raises(AuditError, match="estimate missing derivation"):
        audit_artifact(broken)


def test_audit_rejects_computed_derivation_without_input_references() -> None:
    config, edgar, price, coc, normalized = _fixture_path()
    valuation, _ = build_dcf_artifacts(normalized, edgar, price, coc, config)
    broken_value = valuation.scenarios[0].value.model_copy(update={"derivation": "forward DCF per share = formula only"})
    broken_scenario = valuation.scenarios[0].model_copy(update={"value": broken_value})
    broken = valuation.model_copy(update={"scenarios": [broken_scenario, *valuation.scenarios[1:]]})

    with pytest.raises(AuditError, match="input references"):
        audit_artifact(broken)


def test_audit_rejects_invalid_wacc_band() -> None:
    config, edgar, price, coc, normalized = _fixture_path()
    _, expectations = build_dcf_artifacts(normalized, edgar, price, coc, config)
    broken = expectations.model_copy(update={"wacc_band": {"low": expectations.wacc_band["high"], "high": expectations.wacc_band["low"]}})

    with pytest.raises(AuditError, match="WACC band"):
        audit_artifact(broken)
