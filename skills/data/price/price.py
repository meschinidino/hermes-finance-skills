from __future__ import annotations

from datetime import date, datetime, timezone

from skills.interfaces import PriceFeed
from skills.m1_artifacts import PriceResult, make_external_number

DEFAULT_FIXTURE_PRICES = {"AAPL": 200.0}


def fetch_price(
    ticker: str,
    *,
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
            price = DEFAULT_FIXTURE_PRICES[normalized]
            source = "fixture"
    except Exception:
        return PriceResult(ticker=normalized, price=None, source="unavailable", flags=["price_unavailable"])

    return PriceResult(
        ticker=normalized,
        price=make_external_number(
            price,
            tag="external:price",
            unit="USD_per_share",
            period=run_date.isoformat(),
            source_name=source,
            retrieved_at=retrieved_at,
            derivation="Quoted market price from injected PriceFeed or frozen M1 fixture.",
        ),
        source=source,
    )

