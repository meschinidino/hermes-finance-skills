from __future__ import annotations

from skills.config import load_config
from skills.data.cost_of_capital.cost_of_capital import build_cost_of_capital_inputs
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.data.price.price import fetch_price
from skills.synthesis.handoff.handoff import build_handoff
from skills.valuation.normalize.normalize import normalize_financials
from skills.valuation.spine.spine import build_spine


def test_builds_m1_handoff() -> None:
    config = load_config("config/conventions.yaml")
    edgar = fetch_edgar_facts("AAPL")
    price = fetch_price("AAPL")
    spine = build_spine(
        normalize_financials(edgar),
        build_cost_of_capital_inputs("AAPL", config),
        price,
        excess_cash_pct=config.invested_capital.excess_cash_pct,
        schema_version=config.schema_version,
    )

    handoff = build_handoff(
        "AAPL",
        edgar.cik,
        spine,
        price=price.price,
        as_of=None,
        schema_version=config.schema_version,
        flags=[],
        source_accessions=["0000320193-24-000123"],
    )

    assert handoff.status == "m1_walking_skeleton"
    assert handoff.spine.years == edgar.years
    assert handoff.data_room["sources"] == ["0000320193-24-000123"]
    assert handoff.confidence_and_gaps["least_sure_about"]
