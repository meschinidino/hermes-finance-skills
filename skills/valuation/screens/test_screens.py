from __future__ import annotations

from datetime import datetime, timezone

import pytest

from skills.audit import AuditError, audit_artifact
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.data.price.price import fetch_price
from skills.valuation.screens.screens import build_gate_card_from_inputs, inputs_from_edgar, select_altman_variant


def _inputs(industry: str = "manufacturer"):
    produced = datetime(2026, 6, 30, tzinfo=timezone.utc)
    edgar = fetch_edgar_facts("AAPL")
    price = fetch_price("AAPL", edgar=edgar)
    return inputs_from_edgar(edgar, price, industry_classification=industry, produced_at=produced)


def test_altman_variant_selection() -> None:
    assert select_altman_variant("manufacturer") == "manufacturer"
    assert select_altman_variant("software non-manufacturer") == "z_double_prime"
    assert select_altman_variant("emerging market industrial") == "emerging_market_z_double_prime_plus_3_25"


def test_manufacturer_fixture_selects_manufacturer_altman() -> None:
    gate = build_gate_card_from_inputs(_inputs("manufacturer"))

    assert gate.altman.variant == "manufacturer"
    assert gate.altman.z.derivation and "manufacturer Z" in gate.altman.z.derivation
    audit_artifact(gate)


def test_screens_use_sourced_concepts_not_proxies() -> None:
    inputs = _inputs("manufacturer")

    assert inputs.receivables[-1].provenance.tag == "us-gaap:AccountsReceivableNetCurrent"
    assert inputs.operating_cash_flow[-1].provenance.tag == "us-gaap:NetCashProvidedByUsedInOperatingActivities"
    assert inputs.net_income[-1].provenance.tag == "us-gaap:NetIncomeLoss"
    assert "proxy" not in inputs.gross_margin[-1].derivation
    assert "proxy" not in inputs.asset_turnover[-1].derivation


def test_non_manufacturer_fixture_selects_z_double_prime() -> None:
    gate = build_gate_card_from_inputs(_inputs("software non-manufacturer"))

    assert gate.altman.variant == "z_double_prime"
    assert "Z-double-prime" in gate.altman.z.derivation
    audit_artifact(gate)


def test_emerging_market_fixture_selects_plus_3_25_variant() -> None:
    gate = build_gate_card_from_inputs(_inputs("emerging market operator"))

    assert gate.altman.variant == "emerging_market_z_double_prime_plus_3_25"
    assert "+ 3.25" in gate.altman.z.derivation
    audit_artifact(gate)


def test_lit_beneish_flags_scrutiny_without_auto_kill() -> None:
    inputs = _inputs()
    latest_receivable = inputs.receivables[-1].model_copy(update={"value": inputs.sales[-1].value * 0.90})
    lit_inputs = inputs.__class__(
        **{**inputs.__dict__, "receivables": [*inputs.receivables[:-1], latest_receivable]}
    )
    gate = build_gate_card_from_inputs(lit_inputs)

    assert gate.beneish.flag
    assert any("Beneish" in item for item in gate.dig_items)
    assert gate.kill_reason is None
    assert gate.verdict.draft == "DIG"
    assert gate.verdict.decision is None
    audit_artifact(gate)


def test_audit_rejects_lit_beneish_without_dig_item() -> None:
    gate = build_gate_card_from_inputs(_inputs())
    broken_beneish = gate.beneish.model_copy(update={"flag": True})
    broken = gate.model_copy(update={"beneish": broken_beneish, "dig_items": []})

    with pytest.raises(AuditError, match="Beneish"):
        audit_artifact(broken)
