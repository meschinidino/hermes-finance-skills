from __future__ import annotations

from datetime import date

import resolver
from skills.config import load_config
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.accountant_artifacts import model_to_payload
from skills.storage import LocalStorage
from skills.valuation.method_router.method_router import route_method
from skills.valuation.normalize.normalize import normalize_financials


def test_analyze_files_gate_card_and_uses_dcf_directive(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    payload = resolver.analyze("AAPL", as_of=date(2026, 6, 30), storage=storage)

    assert payload["gate_card"]["header"]["produced_by"] == "B-4"
    assert payload["method_directive"]["header"]["produced_by"] == "B-6"
    assert payload["method_directive"]["method"] == "DCF"
    assert payload["valuation_range"]["method"] == "DCF"
    assert storage.get_json("runs/AAPL/2026-06-30/gate_card.json")["ticker"] == "AAPL"
    assert storage.get_json("runs/AAPL/2026-06-30/method_directive.json")["implemented"]


def test_resolver_does_not_call_dcf_for_deferred_optionality(monkeypatch, tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    config = load_config("config/conventions.yaml")

    def optionality_route(financials, edgar, active_config, **kwargs):
        zero_revenue = [item.model_copy(update={"value": 0.0}) for item in financials.facts.revenue]
        pre_revenue = financials.model_copy(update={"facts": financials.facts.model_copy(update={"revenue": zero_revenue})})
        return route_method(pre_revenue, edgar, active_config, industry_classification="pre-revenue biotech", schema_version=config.schema_version)

    def fail_dcf(*args, **kwargs):
        raise AssertionError("DCF should not be called for deferred optionality route")

    monkeypatch.setattr(resolver, "route_method", optionality_route)
    monkeypatch.setattr(resolver, "build_dcf_artifacts", fail_dcf)

    payload = resolver.analyze("AAPL", as_of=date(2026, 6, 30), storage=storage)

    assert payload["method_directive"]["asset_class"] == "optionality"
    assert payload["method_directive"]["method"] == "rNPV"
    assert "valuation_deferred" in payload
    assert "valuation_range" not in payload
    assert storage.get_json("runs/AAPL/2026-06-30/method_directive.json")["method"] == "rNPV"
