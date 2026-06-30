from __future__ import annotations

from datetime import datetime, timezone

from skills._primitives import Header, Number, Provenance
from skills.accountant_artifacts import CostOfCapitalInputs, NormalizedFinancials, PriceResult, Spine


def build_spine(
    financials: NormalizedFinancials,
    cost_of_capital: CostOfCapitalInputs,
    price: PriceResult,
    *,
    excess_cash_pct: float,
    schema_version: str,
) -> Spine:
    produced_at = datetime.now(timezone.utc)
    flags = sorted(set(financials.flags + cost_of_capital.flags + price.flags))
    rows = [_row(financials, cost_of_capital, price, index, excess_cash_pct, produced_at) for index in range(len(financials.years))]

    return Spine(
        header=Header(schema_version=schema_version, produced_by="B-2", produced_at=produced_at),
        years=financials.years,
        wacc=[row["wacc"] for row in rows],
        nopat=[row["nopat"] for row in rows],
        invested_capital_incl_gw=[row["ic_incl"] for row in rows],
        invested_capital_ex_gw=[row["ic_ex"] for row in rows],
        roic_incl_gw=[row["roic_incl"] for row in rows],
        roic_ex_gw=[row["roic_ex"] for row in rows],
        spread=[row["spread"] for row in rows],
        nopat_margin=[row["margin"] for row in rows],
        capital_turnover=[row["turnover"] for row in rows],
        flags=flags,
    )


def _row(
    financials: NormalizedFinancials,
    cost: CostOfCapitalInputs,
    price: PriceResult,
    index: int,
    excess_cash_pct: float,
    produced_at: datetime,
) -> dict[str, Number]:
    facts = financials.facts
    year = financials.years[index]
    ebit = facts.ebit[index]
    revenue = facts.revenue[index]
    cash = facts.cash[index]
    debt = facts.long_term_debt_noncurrent[index].value + facts.long_term_debt_current[index].value + facts.short_term_borrowings[index].value
    equity = facts.equity[index].value
    goodwill = facts.goodwill[index].value
    shares = facts.shares_outstanding[index].value
    tax_rate = cost.tax_rate.value

    nopat_value = ebit.value * (1 - tax_rate)
    excess_cash = max(0.0, cash.value - excess_cash_pct * revenue.value)
    ic_incl_value = debt + equity - excess_cash
    ic_ex_value = ic_incl_value - goodwill
    if ic_incl_value <= 0 or ic_ex_value <= 0:
        raise ValueError(f"{year}:non_positive_invested_capital")

    roic_incl_value = nopat_value / ic_incl_value
    roic_ex_value = nopat_value / ic_ex_value
    margin_value = nopat_value / revenue.value
    turnover_value = revenue.value / ic_incl_value

    if price.price is None:
        market_equity = equity
        weight_derivation = "price unavailable; book equity used for WACC weights"
    else:
        market_equity = price.price.value * shares
        weight_derivation = "market equity = price per share * shares outstanding"

    enterprise_capital = market_equity + debt
    debt_to_equity = debt / market_equity
    beta_l = cost.unlevered_beta.value * (1 + (1 - tax_rate) * debt_to_equity)
    ke = cost.risk_free_rate.value + beta_l * cost.erp.value
    kd = cost.risk_free_rate.value + cost.credit_spread.value
    kd_after_tax = kd * (1 - tax_rate)
    wacc_value = (market_equity / enterprise_capital) * ke + (debt / enterprise_capital) * kd_after_tax
    spread_value = roic_incl_value - wacc_value

    return {
        "nopat": _computed(nopat_value, year, "USD_millions", produced_at, f"NOPAT = EBIT({ebit.provenance.tag}) * (1 - tax_rate)"),
        "ic_incl": _computed(
            ic_incl_value,
            year,
            "USD_millions",
            produced_at,
            "IC_incl_gw = total debt + equity - max(0, cash - excess_cash_pct * revenue)",
        ),
        "ic_ex": _computed(ic_ex_value, year, "USD_millions", produced_at, "IC_ex_gw = IC_incl_gw - goodwill"),
        "roic_incl": _computed(roic_incl_value, year, "ratio", produced_at, "ROIC_incl = NOPAT / IC_incl_gw"),
        "roic_ex": _computed(roic_ex_value, year, "ratio", produced_at, "ROIC_ex = NOPAT / IC_ex_gw"),
        "wacc": _computed(
            wacc_value,
            year,
            "percent",
            produced_at,
            f"WACC = E/(E+D)*Ke + D/(E+D)*Kd_after_tax; {weight_derivation}",
        ),
        "spread": _computed(spread_value, year, "percent", produced_at, "spread = ROIC_incl - WACC"),
        "margin": _computed(margin_value, year, "ratio", produced_at, "NOPAT margin = NOPAT / revenue"),
        "turnover": _computed(turnover_value, year, "x", produced_at, "capital turnover = revenue / IC_incl_gw"),
    }


def _computed(value: float, period: str, unit: str, produced_at: datetime, derivation: str) -> Number:
    return Number(
        value=value,
        unit=unit,
        kind="estimate",
        provenance=Provenance(
            tag="computed",
            form="computed",
            period=period,
            accession=None,
            source_name="M1",
            retrieved_at=produced_at,
        ),
        derivation=derivation,
    )

