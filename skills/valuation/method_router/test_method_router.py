from __future__ import annotations

import pytest

from skills.audit import AuditError, audit_artifact
from skills.config import load_config
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.valuation.method_router.method_router import route_method
from skills.valuation.normalize.normalize import normalize_financials


def _path():
    config = load_config("config/conventions.yaml")
    edgar = fetch_edgar_facts("AAPL")
    normalized = normalize_financials(edgar)
    return config, edgar, normalized


def test_cash_generator_routes_to_dcf() -> None:
    config, edgar, normalized = _path()
    directive = route_method(normalized, edgar, config, industry_classification="Computers/Peripherals")

    assert directive.asset_class == "cash-generator"
    assert directive.method == "DCF"
    assert directive.implemented
    audit_artifact(directive)


def test_optionality_routes_away_from_dcf() -> None:
    config, edgar, normalized = _path()
    pre_revenue = normalized.model_copy(
        update={"facts": normalized.facts.model_copy(update={"revenue": [item.model_copy(update={"value": 0.0}) for item in normalized.facts.revenue]})}
    )
    directive = route_method(pre_revenue, edgar, config, industry_classification="pre-revenue biotech")

    assert directive.asset_class == "optionality"
    assert directive.method == "rNPV"
    assert not directive.implemented
    assert "no substitute DCF" in directive.fallback_behavior
    audit_artifact(directive)


def test_automation_software_does_not_match_automotive_auto_token() -> None:
    config, edgar, normalized = _path()
    directive = route_method(normalized, edgar, config, industry_classification="automation software")

    assert directive.asset_class == "cash-generator"
    assert directive.calibration_sector is None
    assert directive.method == "DCF"
    audit_artifact(directive)


def test_crm_sets_saas_calibration_sector_without_changing_asset_class() -> None:
    config = load_config("config/conventions.yaml")
    edgar = fetch_edgar_facts("CRM")
    normalized = normalize_financials(edgar)
    directive = route_method(normalized, edgar, config)

    assert directive.asset_class == "cash-generator"
    assert directive.calibration_sector == "saas"
    assert directive.method == "DCF"
    assert any(indicator.name == "calibration_sector" and indicator.value == "saas" for indicator in directive.indicators)
    audit_artifact(directive)


def test_audit_rejects_optionality_dcf_directive() -> None:
    config, edgar, normalized = _path()
    directive = route_method(normalized, edgar, config, industry_classification="Computers/Peripherals")
    broken = directive.model_copy(update={"asset_class": "optionality", "method": "DCF"})

    with pytest.raises(AuditError, match="optionality"):
        audit_artifact(broken)
