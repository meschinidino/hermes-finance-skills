from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from skills.config import Config, load_config
from skills.interfaces import LLM, PriceFeed, Senior, Storage
from skills.storage import LocalStorage


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
    """M0 entry point.

    The injected role arguments are accepted now so Hermes or tests can wire the
    same call shape before the M1 skills exist.
    """
    del senior, llm, price_feed

    normalized_ticker = ticker.upper().strip()
    if not normalized_ticker:
        raise ValueError("ticker is required")

    run_date = as_of or date.today()
    config = load_config(config_path)
    active_storage = storage or LocalStorage()

    payload = _stub_payload(normalized_ticker, run_date, config)
    artifact_path = f"runs/{normalized_ticker}/{run_date.isoformat()}/m0_stub.json"
    active_storage.put_json(artifact_path, payload)
    reloaded = active_storage.get_json(artifact_path)
    if reloaded["ticker"] != normalized_ticker:
        raise RuntimeError("storage round-trip failed")

    return payload


def _stub_payload(ticker: str, as_of: date, config: Config) -> dict[str, Any]:
    return {
        "schema_version": config.schema_version,
        "status": "m0_stub",
        "ticker": ticker,
        "as_of": as_of.isoformat(),
        "produced_at": datetime.now(timezone.utc).isoformat(),
        "message": "M0 scaffold only; no financial analysis has been computed.",
        "loaded_conventions": {
            "tax_rate": config.tax.marginal_rate,
            "erp": config.cost_of_capital.erp,
            "risk_free_fallback": config.cost_of_capital.risk_free_fallback,
            "credit_spread": config.cost_of_capital.credit_spread,
            "excess_cash_pct": config.invested_capital.excess_cash_pct,
            "has_beta": ticker in config.betas,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the finance skill pack resolver.")
    parser.add_argument("ticker", help="US-listed ticker to analyze")
    args = parser.parse_args()
    print(json.dumps(analyze(args.ticker), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
