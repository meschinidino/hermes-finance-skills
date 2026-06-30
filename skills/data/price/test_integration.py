from __future__ import annotations

import json
import os
import urllib.request

import pytest

from skills.data.edgar.edgar import fetch_edgar_facts
from skills.data.price.price import fetch_price


def test_live_price_smoke() -> None:
    if os.getenv("RUN_LIVE_M2A") != "1":
        pytest.skip("live M2a price smoke is opt-in; offline CI uses tests/fixtures/aapl_price.json")

    def live_yahoo_price(ticker: str) -> float:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        result = payload["chart"]["result"][0]
        price = result["meta"].get("regularMarketPrice")
        if price is None:
            closes = result["indicators"]["quote"][0]["close"]
            price = next((item for item in reversed(closes) if item is not None), None)
        if price is None:
            raise RuntimeError("Yahoo Finance chart returned no price")
        return float(price)

    try:
        live_price = live_yahoo_price("AAPL")
    except Exception as exc:
        pytest.skip(f"live price provider unavailable: {type(exc).__name__}: {exc}")

    class YahooChartFeed:
        def quote(self, ticker: str) -> dict[str, object]:
            return {"price": live_price, "source": "Yahoo Finance chart"}

    edgar = fetch_edgar_facts("AAPL")
    result = fetch_price("AAPL", edgar=edgar, price_feed=YahooChartFeed())

    assert result.price is not None
    assert result.price.value > 0
    assert result.market_cap is not None
    assert result.market_cap.value > 0
