from __future__ import annotations

from datetime import date

from skills.data.price.price import fetch_price


class GoodFeed:
    def quote(self, ticker: str) -> dict[str, object]:
        return {"price": 123.45, "source": f"test:{ticker}"}


class BadFeed:
    def quote(self, ticker: str) -> dict[str, object]:
        raise RuntimeError("offline")


def test_fetch_price_from_injected_feed() -> None:
    result = fetch_price("aapl", price_feed=GoodFeed(), as_of=date(2026, 6, 29))

    assert result.price is not None
    assert result.price.value == 123.45
    assert result.price.derivation
    assert result.source == "test:AAPL"


def test_price_failure_flags_unavailable() -> None:
    result = fetch_price("AAPL", price_feed=BadFeed())

    assert result.price is None
    assert "price_unavailable" in result.flags

