from __future__ import annotations

from skills.data.edgar.edgar import fetch_edgar_facts
from skills.valuation.normalize.normalize import normalize_financials


def test_normalize_preserves_facts_and_provenance() -> None:
    edgar = fetch_edgar_facts("AAPL")
    normalized = normalize_financials(edgar)

    assert normalized.years == edgar.years
    assert normalized.facts.revenue[-1].provenance == edgar.facts.revenue[-1].provenance
    assert normalized.normalization_log == []
