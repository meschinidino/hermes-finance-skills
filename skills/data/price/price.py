from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from skills.interfaces import PriceFeed
from skills._primitives import Number, Provenance
from skills.accountant_artifacts import EdgarFacts, PriceResult, make_external_number

FIXTURE_DIR = Path(__file__).parents[3] / "tests" / "fixtures"
TICKER_FIXTURE_PATHS = {
    "AAPL": FIXTURE_DIR / "aapl_price.json",
    "MRNA": FIXTURE_DIR / "mrna_price.json",
    "UBER": FIXTURE_DIR / "uber_price.json",
}
DEFAULT_FIXTURE_PRICES = {"AAPL": 200.0}


def fetch_price(
    ticker: str,
    *,
    edgar: EdgarFacts | None = None,
    price_feed: PriceFeed | None = None,
    as_of: date | None = None,
) -> PriceResult:
    normalized = ticker.upper().strip()
    run_date = as_of or date.today()
    retrieved_at = datetime.now(timezone.utc)

    try:
        if price_feed is not None:
            quote = price_feed.quote(normalized)
            price = float(quote["price"])
            source = str(quote.get("source", "InjectedPriceFeed"))
        else:
            fixture_path = _fixture_path(normalized)
            fixture = _load_fixture(fixture_path)
            price = float(fixture[normalized] if normalized in fixture else DEFAULT_FIXTURE_PRICES[normalized])
            source = f"fixture:tests/fixtures/{fixture_path.name}"
    except Exception:
        if edgar is None:
            return PriceResult(ticker=normalized, price=None, source="unavailable", flags=["price_unavailable"])
        fallback = _book_equity_fallback(edgar, retrieved_at)
        return PriceResult(
            ticker=normalized,
            price=None,
            market_cap=None,
            weighting_equity=fallback,
            weighting_basis="book_equity_fallback",
            source="unavailable",
            flags=["price_unavailable", "book_equity_weighting_fallback"],
        )

    price_number = make_external_number(
        price,
        tag="external:price",
        unit="USD_per_share",
        period=run_date.isoformat(),
        source_name=source,
        retrieved_at=retrieved_at,
        derivation="Quoted market price from injected PriceFeed or frozen M2a fixture.",
    )
    market_cap = _market_cap(price_number, edgar, retrieved_at) if edgar is not None else None
    return PriceResult(
        ticker=normalized,
        price=price_number,
        market_cap=market_cap,
        weighting_equity=market_cap,
        weighting_basis="market_cap" if market_cap is not None else None,
        source=source,
    )


def _fixture_path(ticker: str) -> Path:
    if ticker not in TICKER_FIXTURE_PATHS:
        raise KeyError(ticker)
    return TICKER_FIXTURE_PATHS[ticker]


def _load_fixture(path: Path) -> dict[str, float]:
    if not path.exists():
        return DEFAULT_FIXTURE_PRICES
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("price fixture must be an object")
    return {str(key).upper(): float(value) for key, value in raw.items()}


def _market_cap(price: Number, edgar: EdgarFacts, retrieved_at: datetime) -> Number:
    shares = edgar.facts.shares_outstanding[-1]
    value = price.value * shares.value
    return Number(
        value=value,
        unit="USD_millions",
        kind="estimate",
        provenance=Provenance(
            tag="computed:market_cap",
            form="computed",
            period=shares.provenance.period,
            accession=None,
            source_name="A-2 Price",
            retrieved_at=retrieved_at,
        ),
        derivation=(
            "market_cap = current_price(USD/share) * EDGAR shares_outstanding(shares already stored "
            f"in millions); price_tag={price.provenance.tag}; shares_tag={shares.provenance.tag}"
        ),
    )


def _book_equity_fallback(edgar: EdgarFacts, retrieved_at: datetime) -> Number:
    equity = edgar.facts.equity[-1]
    return Number(
        value=equity.value,
        unit="USD_millions",
        kind="estimate",
        provenance=Provenance(
            tag="computed:book_equity_weighting_fallback",
            form="computed",
            period=equity.provenance.period,
            accession=None,
            source_name="A-2 Price",
            retrieved_at=retrieved_at,
        ),
        derivation=(
            "price feed unavailable; non-fatal WACC weighting fallback uses EDGAR book equity "
            f"from {equity.provenance.tag}"
        ),
    )
