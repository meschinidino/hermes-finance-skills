from __future__ import annotations

from skills.config import load_config
from skills.data.cost_of_capital.cost_of_capital import build_cost_of_capital_inputs


def test_cost_of_capital_inputs_from_config() -> None:
    config = load_config("config/conventions.yaml")
    inputs = build_cost_of_capital_inputs("aapl", config)

    assert inputs.risk_free_rate.value == config.cost_of_capital.risk_free_fallback
    assert inputs.unlevered_beta.value == config.betas["AAPL"].unlevered
    assert inputs.tax_rate.derivation
    assert "risk_free_fallback" in inputs.flags

