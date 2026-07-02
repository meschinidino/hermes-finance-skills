from __future__ import annotations

from datetime import datetime, timezone
import re

from skills._primitives import Header, Number, Provenance
from skills.config import Config
from skills.accountant_artifacts import EdgarFacts, MethodDirective, MethodIndicator, NormalizedFinancials


def route_method(
    financials: NormalizedFinancials,
    edgar: EdgarFacts,
    config: Config,
    *,
    industry_classification: str | None = None,
    schema_version: str | None = None,
    produced_at: datetime | None = None,
) -> MethodDirective:
    produced = produced_at or datetime.now(timezone.utc)
    classification = industry_classification or _classification_from_config(edgar.ticker, config)
    revenue = financials.facts.revenue[-1]
    ebit = financials.facts.ebit[-1]
    revenue_growth = _growth(financials.facts.revenue[-2], revenue, produced)
    ebit_margin = _margin(ebit, revenue, produced)
    indicators = [
        MethodIndicator(name="industry_classification", value=classification, source="config.betas"),
        MethodIndicator(name="latest_revenue", value=revenue, source="EDGAR"),
        MethodIndicator(name="latest_ebit", value=ebit, source="EDGAR"),
        MethodIndicator(name="latest_ebit_margin", value=ebit_margin, source="computed"),
        MethodIndicator(name="latest_revenue_growth", value=revenue_growth, source="computed"),
    ]
    asset_class, method, reason = _classify(classification, revenue, ebit, ebit_margin)
    return MethodDirective(
        header=Header(schema_version=schema_version or config.schema_version, produced_by="B-6", produced_at=produced),
        ticker=financials.ticker,
        asset_class=asset_class,
        method=method,
        routing_reason=reason,
        indicators=indicators,
        implemented=method == "DCF",
        fallback_behavior=("invoke B-3 DCF" if method == "DCF" else f"file directive and continue with {method}-specific C-4/C-6 route artifacts; no substitute DCF"),
    )


def _classify(classification: str, revenue: Number, ebit: Number, ebit_margin: Number) -> tuple[str, str, str]:
    normalized = classification.lower()
    tokens = set(re.findall(r"[a-z0-9]+", normalized))
    if any(token in normalized for token in ("bank", "insurance", "financial")):
        return "financial", "financial_model", "Financial institutions require a balance-sheet driven model, not plain DCF."
    if any(token in normalized for token in ("biotech", "pre-revenue", "pipeline", "optionality")) or revenue.value <= 0:
        return "optionality", "rNPV", "Optionality or pre-revenue economics require rNPV/SOTP routing rather than plain DCF."
    if any(token in normalized for token in ("reit", "real estate", "miner", "oil reserves", "asset-nav")):
        return "asset-NAV", "NAV", "Asset-heavy names require NAV routing."
    if tokens & {"cyclical", "airline", "commodity", "steel", "auto", "automotive", "autos"}:
        return "cyclical", "normalized_mid_cycle", "Cyclical earnings require normalized mid-cycle valuation."
    if ebit.value > 0 and ebit_margin.value > 0:
        return "cash-generator", "DCF", "Positive revenue and operating profit support the M2a cash-generator DCF branch."
    return "optionality", "rNPV", "No positive operating-profit base; route away from plain DCF."


def _classification_from_config(ticker: str, config: Config) -> str:
    for sector, beta in config.betas.items():
        if ticker.upper() in {item.upper() for item in beta.tickers}:
            return sector
    raise ValueError(f"missing_industry_classification:{ticker}")


def _growth(prior: Number, latest: Number, produced: datetime) -> Number:
    if prior.value == 0:
        return _computed(0.0, "computed:router_revenue_growth_unavailable", latest.provenance.period, "percent", produced, "revenue growth unavailable when prior revenue is zero; inputs: EDGAR revenue")
    return _computed((latest.value / prior.value) - 1, "computed:router_revenue_growth", latest.provenance.period, "percent", produced, "latest revenue growth = latest revenue / prior revenue - 1; inputs: EDGAR revenue")


def _margin(ebit: Number, revenue: Number, produced: datetime) -> Number:
    if revenue.value == 0:
        return _computed(0.0, "computed:router_ebit_margin_unavailable", revenue.provenance.period, "ratio", produced, "EBIT margin unavailable when revenue is zero; inputs: EDGAR EBIT, EDGAR revenue")
    return _computed(ebit.value / revenue.value, "computed:router_ebit_margin", revenue.provenance.period, "ratio", produced, "EBIT margin = EBIT / revenue; inputs: EDGAR EBIT, EDGAR revenue")


def _computed(value: float, tag: str, period: str, unit: str, produced_at: datetime, derivation: str) -> Number:
    return Number(
        value=float(value),
        unit=unit,
        kind="estimate",
        provenance=Provenance(tag=tag, form="computed", period=period, accession=None, source_name="B-6 Method Router", retrieved_at=produced_at),
        derivation=derivation,
    )
