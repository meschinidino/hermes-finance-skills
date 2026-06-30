from __future__ import annotations

from datetime import date
from pathlib import Path

from skills.audit import audit_analyst_artifact
from skills.bundle_validation import validate_skill_bundle
from skills.config import load_config
from skills.data.cost_of_capital.cost_of_capital import build_cost_of_capital_inputs
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.data.price.price import fetch_price
from skills.m1_artifacts import model_to_payload
from skills.research.moat.moat import build_moat_artifact
from skills.storage import LocalStorage
from skills.valuation.normalize.normalize import normalize_financials
from skills.valuation.spine.spine import build_spine


def test_moat_bundle_validates_and_audits_fixture(tmp_path) -> None:
    validate_skill_bundle(Path("skills/research/moat"), expected_role="analyst")
    edgar = fetch_edgar_facts("AAPL")
    run_date = date(2026, 6, 30)
    config = load_config("config/conventions.yaml")
    price = fetch_price("AAPL", edgar=edgar, as_of=run_date)
    cost_of_capital = build_cost_of_capital_inputs("AAPL", config, edgar=edgar, price=price, as_of=run_date)
    spine = build_spine(
        normalize_financials(edgar),
        cost_of_capital,
        price,
        excess_cash_pct=config.invested_capital.excess_cash_pct,
        schema_version=config.schema_version,
    )

    artifact = build_moat_artifact(
        edgar,
        spine,
        as_of=run_date,
        schema_version=config.schema_version,
        run_dir="runs/AAPL/2026-06-30",
    )

    storage = LocalStorage(tmp_path)
    storage.put_json("runs/AAPL/2026-06-30/spine.json", model_to_payload(spine))
    audit_analyst_artifact(artifact, storage=storage)
