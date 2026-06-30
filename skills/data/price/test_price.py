from __future__ import annotations

from datetime import date

from skills.data.price.price import fetch_price
from skills.data.edgar.edgar import fetch_edgar_facts


class GoodFeed:
    def quote(self, ticker: str) -> dict[str, object]:
        return {"price": 123.45, "source": f"test:{ticker}"}


class BadFeed:
    def quote(self, ticker: str) -> dict[str, object]:
        raise RuntimeError("offline")


def test_fetch_price_from_injected_feed() -> None:
    edgar = fetch_edgar_facts("AAPL")
    result = fetch_price("aapl", edgar=edgar, price_feed=GoodFeed(), as_of=date(2026, 6, 29))

    assert result.price is not None
    assert result.price.value == 123.45
    assert result.price.derivation
    assert result.market_cap is not None
    assert result.market_cap.value == result.price.value * edgar.facts.shares_outstanding[-1].value
    assert result.market_cap.derivation
    assert result.weighting_basis == "market_cap"
    assert result.source == "test:AAPL"


def test_fetch_price_from_frozen_fixture() -> None:
    edgar = fetch_edgar_facts("AAPL")
    result = fetch_price("aapl", edgar=edgar, as_of=date(2026, 6, 29))

    assert result.price is not None
    assert result.price.value == 200.0
    assert result.market_cap is not None
    assert result.market_cap.unit == "USD_millions"
    assert result.weighting_equity == result.market_cap


def test_price_failure_flags_unavailable() -> None:
    edgar = fetch_edgar_facts("AAPL")
    result = fetch_price("AAPL", edgar=edgar, price_feed=BadFeed())

    assert result.price is None
    assert result.market_cap is None
    assert result.weighting_equity is not None
    assert result.weighting_equity.value == edgar.facts.equity[-1].value
    assert result.weighting_basis == "book_equity_fallback"
    assert "price_unavailable" in result.flags
    assert "book_equity_weighting_fallback" in result.flags
