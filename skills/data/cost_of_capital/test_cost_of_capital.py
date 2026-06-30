from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from skills.config import load_config
from skills.data.cost_of_capital.cost_of_capital import build_cost_of_capital_inputs
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.data.price.price import fetch_price


class BadFred:
    def dgs10(self) -> float:
        raise RuntimeError("offline")


def _inputs():
    config = load_config("config/conventions.yaml")
    edgar = fetch_edgar_facts("AAPL")
    price = fetch_price("AAPL", edgar=edgar)
    inputs = build_cost_of_capital_inputs("aapl", config, edgar=edgar, price=price)
    return config, edgar, price, inputs


def test_cost_of_capital_inputs_from_fixtures_and_config() -> None:
    config, edgar, price, inputs = _inputs()

    beta = config.beta_for_ticker("AAPL")
    assert inputs.risk_free_rate.value == 0.0418
    assert inputs.risk_free_rate.provenance.source_name == "fixture:FRED:DGS10"
    assert inputs.unlevered_beta.value == beta.unlevered
    assert inputs.unlevered_beta.value != 1.05
    assert inputs.unlevered_beta.provenance.source_name == beta.source_name
    assert inputs.tax_rate.derivation
    assert "risk_free_fixture" in inputs.flags
    assert inputs.debt is not None
    assert inputs.equity_weighting_value == price.weighting_equity
    assert inputs.debt_to_equity is not None
    assert inputs.relevered_beta is not None
    assert inputs.cost_of_equity is not None
    assert inputs.pre_tax_cost_of_debt is not None
    assert inputs.after_tax_cost_of_debt is not None
    assert inputs.wacc is not None
    assert inputs.wacc_low is not None
    assert inputs.wacc_high is not None

    debt = edgar.facts.long_term_debt_noncurrent[-1].value + edgar.facts.long_term_debt_current[-1].value + edgar.facts.short_term_borrowings[-1].value
    equity = price.weighting_equity.value
    d_to_e = debt / equity
    beta_l = beta.unlevered * (1 + (1 - config.tax.marginal_rate) * d_to_e)
    ke = inputs.risk_free_rate.value + beta_l * config.cost_of_capital.erp
    kd = inputs.risk_free_rate.value + config.cost_of_capital.credit_spread
    kd_after_tax = kd * (1 - config.tax.marginal_rate)
    expected_wacc = (equity / (equity + debt)) * ke + (debt / (equity + debt)) * kd_after_tax

    assert inputs.debt_to_equity.value == pytest.approx(d_to_e)
    assert inputs.relevered_beta.value == pytest.approx(beta_l)
    assert inputs.cost_of_equity.value == pytest.approx(ke)
    assert inputs.pre_tax_cost_of_debt.value == pytest.approx(kd)
    assert inputs.after_tax_cost_of_debt.value == pytest.approx(kd_after_tax)
    assert inputs.wacc.value == pytest.approx(expected_wacc)
    assert inputs.wacc_low.value == pytest.approx(expected_wacc - config.cost_of_capital.wacc_band_bps)
    assert inputs.wacc_high.value == pytest.approx(expected_wacc + config.cost_of_capital.wacc_band_bps)


def test_fred_unreachable_uses_config_fallback_and_flags() -> None:
    config = load_config("config/conventions.yaml")
    edgar = fetch_edgar_facts("AAPL")
    price = fetch_price("AAPL", edgar=edgar)
    inputs = build_cost_of_capital_inputs("AAPL", config, edgar=edgar, price=price, fred_client=BadFred())

    assert inputs.risk_free_rate.value == config.cost_of_capital.risk_free_fallback
    assert inputs.risk_free_rate.provenance.source_name == "config:fallback"
    assert "fred_unreachable" in inputs.flags
    assert "risk_free_fallback" in inputs.flags


def test_config_rejects_old_aapl_beta_placeholder() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.yaml"
        path.write_text(
            """
schema_version: "1.0"
cost_of_capital:
  erp: 0.0423
  risk_free_fallback: 0.0418
  credit_spread: 0.010
  synthetic_rating: "AA"
  wacc_band_bps: 0.005
tax:
  marginal_rate: 0.25
invested_capital:
  excess_cash_pct: 0.02
betas:
  AAPL:
    unlevered: 1.05
    source_name: "placeholder"
    source_url: "placeholder"
    source_date: "2026-01"
    tickers: ["AAPL"]
dcf:
  forecast_years: 5
  terminal_growth: 0.025
  reverse_growth_low: -0.05
  reverse_growth_high: 0.20
  scenarios:
    bear: {revenue_growth: 0.02, nopat_margin: 0.24, sales_to_capital: 2.25}
    base: {revenue_growth: 0.04, nopat_margin: 0.28, sales_to_capital: 2.75}
    bull: {revenue_growth: 0.06, nopat_margin: 0.31, sales_to_capital: 3.25}
""",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="placeholder"):
            load_config(path)
