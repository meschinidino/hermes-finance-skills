from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from skills.audit import audit_m1_handoff
from skills.config import load_config
from skills.data.cost_of_capital.cost_of_capital import build_cost_of_capital_inputs
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.data.price.price import fetch_price
from skills.interfaces import LLM, PriceFeed, Senior, Storage
from skills.m1_artifacts import EdgarFacts, model_to_payload
from skills.storage import LocalStorage
from skills.synthesis.handoff.handoff import build_handoff
from skills.valuation.normalize.normalize import normalize_financials
from skills.valuation.spine.spine import build_spine


def analyze(
    ticker: str,
    *,
    as_of: date | None = None,
    config_path: Path | str = Path("config/conventions.yaml"),
    storage: Storage | None = None,
    senior: Senior | None = None,
    llm: LLM | None = None,
    price_feed: PriceFeed | None = None,
) -> dict[str, Any]:
    """Run the M1 walking skeleton route for a US-listed ticker."""
    del senior, llm

    normalized_ticker = ticker.upper().strip()
    if not normalized_ticker:
        raise ValueError("ticker is required")

    run_date = as_of or date.today()
    config = load_config(config_path)
    active_storage = storage or LocalStorage()

    edgar = fetch_edgar_facts(normalized_ticker)
    price = fetch_price(normalized_ticker, price_feed=price_feed, as_of=run_date)
    cost_of_capital = build_cost_of_capital_inputs(normalized_ticker, config, as_of=run_date)
    normalized = normalize_financials(edgar)
    spine = build_spine(
        normalized,
        cost_of_capital,
        price,
        excess_cash_pct=config.invested_capital.excess_cash_pct,
        schema_version=config.schema_version,
    )
    handoff = build_handoff(
        normalized_ticker,
        edgar.cik,
        spine,
        price=price.price,
        as_of=run_date,
        schema_version=config.schema_version,
        flags=edgar.flags + price.flags + cost_of_capital.flags,
        source_accessions=_source_accessions(edgar),
    )

    run_dir = f"runs/{normalized_ticker}/{run_date.isoformat()}"
    spine_payload = model_to_payload(spine)
    active_storage.put_json(f"{run_dir}/spine.json", spine_payload)
    if active_storage.get_json(f"{run_dir}/spine.json") != spine_payload:
        raise RuntimeError("spine storage round-trip failed")

    handoff_path = f"{run_dir}/handoff.json"
    audit_m1_handoff(handoff, storage=active_storage, path=handoff_path)
    payload = active_storage.get_json(handoff_path)

    return payload


def _source_accessions(edgar: EdgarFacts) -> list[str]:
    accessions: set[str] = set()
    for values in edgar.facts:
        for number in values[1]:
            accession = number.provenance.accession
            if accession and accession != "explicit-zero":
                accessions.add(accession)
    return sorted(accessions)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the finance skill pack resolver.")
    parser.add_argument("ticker", help="US-listed ticker to analyze")
    args = parser.parse_args()
    print(json.dumps(analyze(args.ticker), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
