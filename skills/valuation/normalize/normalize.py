from __future__ import annotations

from skills.accountant_artifacts import EdgarFacts, NormalizedFinancials


def normalize_financials(edgar_facts: EdgarFacts) -> NormalizedFinancials:
    return NormalizedFinancials(
        ticker=edgar_facts.ticker,
        cik=edgar_facts.cik,
        years=edgar_facts.years,
        facts=edgar_facts.facts,
        normalization_log=[],
        flags=edgar_facts.flags,
    )

