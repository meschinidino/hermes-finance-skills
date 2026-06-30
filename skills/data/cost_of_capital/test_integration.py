from __future__ import annotations

import os

import pytest

from skills.config import load_config
from skills.data.cost_of_capital.cost_of_capital import build_cost_of_capital_inputs


def test_live_fred_smoke() -> None:
    if os.getenv("RUN_LIVE_M2A") != "1":
        pytest.skip("live M2a FRED smoke is opt-in; offline CI uses tests/fixtures/fred_dgs10.json")

    config = load_config("config/conventions.yaml")
    inputs = build_cost_of_capital_inputs("AAPL", config, use_fixture=False)

    assert inputs.risk_free_rate.value > 0
    assert inputs.risk_free_rate.provenance.source_name in {"FRED:DGS10", "config:fallback"}
