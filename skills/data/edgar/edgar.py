from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from dataclasses import dataclass

from skills._primitives import Number, Provenance
from skills.accountant_artifacts import EdgarConceptSet, EdgarFacts

FIXTURE_DIR = Path(__file__).parent / "fixtures"

CONCEPT_FALLBACKS = {
    "ebit": ["us-gaap:OperatingIncomeLoss"],
    "revenue": [
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap:Revenues",
        "us-gaap:SalesRevenueNet",
    ],
    "cash": ["us-gaap:CashAndCashEquivalentsAtCarryingValue"],
    "total_assets": ["us-gaap:Assets"],
    "current_assets": ["us-gaap:AssetsCurrent"],
    "total_liabilities": ["us-gaap:Liabilities"],
    "current_liabilities": ["us-gaap:LiabilitiesCurrent"],
    "retained_earnings": ["us-gaap:RetainedEarningsAccumulatedDeficit"],
    "receivables": ["us-gaap:ReceivablesNetCurrent", "us-gaap:AccountsReceivableNetCurrent"],
    "cost_of_revenue": ["us-gaap:CostOfGoodsAndServicesSold", "us-gaap:CostOfRevenue"],
    "operating_cash_flow": ["us-gaap:NetCashProvidedByUsedInOperatingActivities"],
    "net_income": ["us-gaap:NetIncomeLoss"],
    "depreciation_amortization": [
        "us-gaap:DepreciationDepletionAndAmortization",
        "us-gaap:DepreciationDepletionAndAmortizationExpense",
    ],
    "selling_general_admin": ["us-gaap:SellingGeneralAndAdministrativeExpense"],
    "inventory": ["us-gaap:InventoryNet"],
    "long_term_debt_noncurrent": ["us-gaap:LongTermDebtNoncurrent", "us-gaap:LongTermDebt"],
    "long_term_debt_current": ["us-gaap:LongTermDebtCurrent"],
    "short_term_borrowings": ["us-gaap:ShortTermBorrowings", "us-gaap:DebtCurrent"],
    "equity": [
        "us-gaap:StockholdersEquity",
        "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "goodwill": ["us-gaap:Goodwill"],
    "shares_outstanding": ["dei:EntityCommonStockSharesOutstanding"],
    "interest_expense": ["us-gaap:InterestExpense"],
}

OPTIONAL_ZERO_CONCEPTS = {"goodwill", "short_term_borrowings", "interest_expense"}


@dataclass(frozen=True)
class ExtractedConcept:
    values: list[Number]
    tag: str


def fetch_edgar_facts(ticker: str, *, fixture_dir: Path = FIXTURE_DIR) -> EdgarFacts:
    normalized = ticker.upper().strip()
    cik = resolve_cik(normalized, fixture_dir=fixture_dir)
    raw = _load_json(fixture_dir / f"{normalized.lower()}_companyfacts.json")
    retrieved_at = datetime.now(timezone.utc)
    years = _available_years(raw)
    facts: dict[str, list[Number]] = {}
    flags: list[str] = []

    for concept_name, fallback_tags in CONCEPT_FALLBACKS.items():
        extracted = _extract_concept(raw, fallback_tags, years, retrieved_at)
        if extracted is None:
            if concept_name in OPTIONAL_ZERO_CONCEPTS:
                flags.append(f"{concept_name}_explicit_zero")
                values = [_zero_fact(concept_name, year, retrieved_at) for year in years]
            else:
                raise ValueError(f"unresolved_concept:{concept_name}")
        else:
            values = extracted.values
            if extracted.tag != fallback_tags[0]:
                flags.append(f"{concept_name}_fallback:{extracted.tag}")
        facts[concept_name] = values

    return EdgarFacts(
        ticker=normalized,
        cik=cik,
        years=years,
        facts=EdgarConceptSet.model_validate(facts),
        flags=flags,
    )


def resolve_cik(ticker: str, *, fixture_dir: Path = FIXTURE_DIR) -> str:
    raw = _load_json(fixture_dir / "company_tickers.json")
    for record in raw.values():
        if record["ticker"].upper() == ticker.upper():
            return str(record["cik_str"]).zfill(10)
    raise ValueError(f"unknown_ticker:{ticker}")


def _available_years(raw: dict[str, Any]) -> list[str]:
    values = _tag_values(raw, "us-gaap:OperatingIncomeLoss", "USD")
    years = sorted({int(item["fy"]) for item in values if item.get("form") == "10-K" and item.get("fp") == "FY"})
    if len(years) < 5:
        raise ValueError("insufficient_history")
    return [f"FY{year}" for year in years[-5:]]


def _extract_concept(
    raw: dict[str, Any],
    fallback_tags: list[str],
    years: list[str],
    retrieved_at: datetime,
) -> ExtractedConcept | None:
    for tag in fallback_tags:
        unit = "shares" if tag == "dei:EntityCommonStockSharesOutstanding" else "USD"
        rows = _tag_values(raw, tag, unit)
        by_year = {
            f"FY{int(row['fy'])}": row
            for row in rows
            if row.get("form") == "10-K" and row.get("fp") == "FY"
        }
        if all(year in by_year for year in years):
            number_unit = "shares" if unit == "shares" else "USD_millions"
            divisor = 1_000_000 if unit == "shares" else 1
            return ExtractedConcept(
                values=[_fact_number(by_year[year], tag, year, number_unit, divisor, retrieved_at) for year in years],
                tag=tag,
            )
    return None


def _tag_values(raw: dict[str, Any], tag: str, unit: str) -> list[dict[str, Any]]:
    namespace, concept = tag.split(":", 1)
    node = raw.get("facts", {}).get(namespace, {}).get(concept, {})
    values = node.get("units", {}).get(unit, [])
    if not isinstance(values, list):
        return []
    return values


def _fact_number(
    row: dict[str, Any],
    tag: str,
    period: str,
    unit: str,
    divisor: int,
    retrieved_at: datetime,
) -> Number:
    return Number(
        value=float(row["val"]) / divisor,
        unit=unit,
        kind="fact",
        provenance=Provenance(
            tag=tag,
            form="10-K",
            period=period,
            accession=row["accn"],
            source_name="EDGAR",
            retrieved_at=retrieved_at,
        ),
    )


def _zero_fact(concept_name: str, year: str, retrieved_at: datetime) -> Number:
    return Number(
        value=0.0,
        unit="USD_millions",
        kind="fact",
        provenance=Provenance(
            tag=f"us-gaap:{concept_name}:explicit_zero",
            form="10-K",
            period=year,
            accession="explicit-zero",
            source_name="EDGAR",
            retrieved_at=retrieved_at,
        ),
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
