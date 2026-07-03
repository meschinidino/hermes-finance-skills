from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from skills._primitives import Header, Number, Provenance, Ratifiable
from skills.accountant_artifacts import (
    AltmanResult,
    BeneishResult,
    EdgarFacts,
    GateCard,
    Investability,
    PiotroskiResult,
    PriceResult,
    SmokeChecks,
)

AltmanVariant = Literal["manufacturer", "z_double_prime", "emerging_market_z_double_prime_plus_3_25"]
NO_INVENTORY_REPORTED_STATUS = "not_applicable: no inventory reported"
NOT_REPORTED_BY_ISSUER = "not_reported_by_issuer"


@dataclass(frozen=True)
class ScreenInputSet:
    ticker: str
    cik: str
    industry_classification: str
    years: list[str]
    working_capital: list[Number]
    retained_earnings: list[Number]
    ebit: list[Number]
    market_value_equity: list[Number]
    book_value_equity: list[Number]
    total_liabilities: list[Number]
    total_assets: list[Number]
    sales: list[Number]
    receivables: list[Number]
    gross_profit: list[Number]
    current_assets: list[Number]
    depreciation: list[Number]
    sga: list[Number]
    long_term_debt: list[Number]
    current_ratio: list[Number]
    shares: list[Number]
    net_income: list[Number]
    operating_cash_flow: list[Number]
    gross_margin: list[Number]
    asset_turnover: list[Number]
    inventory: list[Number]
    restatement: bool = False
    auditor_change: bool = False
    related_party: str = "not assessed in M2b"
    share_class_risk: str = "not assessed in M2b"


def build_gate_card(
    edgar: EdgarFacts,
    price: PriceResult,
    *,
    industry_classification: str = "manufacturer",
    schema_version: str = "1.0",
    produced_at: datetime | None = None,
) -> GateCard:
    inputs = inputs_from_edgar(edgar, price, industry_classification=industry_classification, produced_at=produced_at)
    return build_gate_card_from_inputs(inputs, schema_version=schema_version, produced_at=produced_at)


def build_gate_card_from_inputs(
    inputs: ScreenInputSet,
    *,
    schema_version: str = "1.0",
    produced_at: datetime | None = None,
) -> GateCard:
    produced = produced_at or datetime.now(timezone.utc)
    _validate_inputs(inputs)
    variant = select_altman_variant(inputs.industry_classification)
    altman = _altman(inputs, variant, produced)
    beneish = _beneish(inputs, produced)
    piotroski = _piotroski(inputs, produced)
    smoke = SmokeChecks(
        restatement=inputs.restatement,
        auditor_change=inputs.auditor_change,
        ni_cfo_gap_widening=_ni_cfo_gap_widening(inputs),
        dso_trend=_trend("DSO", [_ratio(r, s) for r, s in zip(inputs.receivables, inputs.sales, strict=True)]),
        inventory_trend=_inventory_trend(inputs),
    )
    dig_items = _dig_items(altman, beneish, piotroski, smoke)
    latest = inputs.years[-1]
    investability = Investability(
        adv_usd=_computed(0.0, "computed:adv_usd_placeholder", latest, "USD_millions", produced, "M2b schema-compatible placeholder; inputs: no price-volume feed in M2b"),
        float_shares=inputs.shares[-1],
        share_class_risk=inputs.share_class_risk,
        related_party=inputs.related_party,
    )
    return GateCard(
        header=Header(schema_version=schema_version, produced_by="B-4", produced_at=produced),
        ticker=inputs.ticker,
        cik=inputs.cik,
        altman=altman,
        beneish=beneish,
        piotroski=piotroski,
        smoke=smoke,
        investability=investability,
        verdict=Ratifiable(
            draft="DIG" if dig_items else "PASS",
            evidence=["M2b screen placeholder only; screen flags are not Senior-signed verdicts."],
            needs_ratification=True,
        ),
        dig_items=dig_items,
        kill_reason=None,
    )


def inputs_from_edgar(
    edgar: EdgarFacts,
    price: PriceResult,
    *,
    industry_classification: str,
    produced_at: datetime | None = None,
) -> ScreenInputSet:
    produced = produced_at or datetime.now(timezone.utc)
    working_capital = [
        _computed(
            current_assets.value - current_liabilities.value,
            "computed:screen_working_capital",
            year,
            "USD_millions",
            produced,
            "working_capital = current_assets - current_liabilities; inputs: EDGAR current_assets, EDGAR current_liabilities",
        )
        for year, current_assets, current_liabilities in zip(edgar.years, edgar.facts.current_assets, edgar.facts.current_liabilities, strict=True)
    ]
    market_equity = []
    for year, shares in zip(edgar.years, edgar.facts.shares_outstanding, strict=True):
        if price.price is not None:
            market_equity.append(_computed(shares.value * price.price.value, "computed:screen_market_value_equity", year, "USD_millions", produced, "market value equity = shares outstanding * observed price; inputs: shares_outstanding, observed price"))
        else:
            market_equity.append(edgar.facts.equity[edgar.years.index(year)])
    gross_profit = [
        _computed(
            revenue.value - cost.value,
            "computed:screen_gross_profit",
            year,
            "USD_millions",
            produced,
            "gross_profit = revenue - cost_of_revenue; inputs: EDGAR revenue, EDGAR cost_of_revenue",
        )
        for year, revenue, cost in zip(edgar.years, edgar.facts.revenue, edgar.facts.cost_of_revenue, strict=True)
    ]
    current_ratio = [
        _computed(
            current_assets.value / current_liabilities.value,
            "computed:screen_current_ratio",
            year,
            "ratio",
            produced,
            "current_ratio = current_assets / current_liabilities; inputs: EDGAR current_assets, EDGAR current_liabilities",
        )
        for year, current_assets, current_liabilities in zip(edgar.years, edgar.facts.current_assets, edgar.facts.current_liabilities, strict=True)
    ]
    gross_margin = [
        _computed(gp.value / revenue.value, "computed:screen_gross_margin", year, "ratio", produced, "gross_margin = gross_profit / revenue; inputs: computed:screen_gross_profit, EDGAR revenue")
        for year, gp, revenue in zip(edgar.years, gross_profit, edgar.facts.revenue, strict=True)
    ]
    asset_turnover = [
        _computed(revenue.value / asset.value, "computed:screen_asset_turnover", year, "x", produced, "asset_turnover = revenue / total_assets; inputs: EDGAR revenue, EDGAR total_assets")
        for year, revenue, asset in zip(edgar.years, edgar.facts.revenue, edgar.facts.total_assets, strict=True)
    ]
    return ScreenInputSet(
        ticker=edgar.ticker,
        cik=edgar.cik,
        industry_classification=industry_classification,
        years=edgar.years,
        working_capital=working_capital,
        retained_earnings=edgar.facts.retained_earnings,
        ebit=edgar.facts.ebit,
        market_value_equity=market_equity,
        book_value_equity=edgar.facts.equity,
        total_liabilities=edgar.facts.total_liabilities,
        total_assets=edgar.facts.total_assets,
        sales=edgar.facts.revenue,
        receivables=edgar.facts.receivables,
        gross_profit=gross_profit,
        current_assets=edgar.facts.current_assets,
        depreciation=edgar.facts.depreciation_amortization,
        sga=edgar.facts.selling_general_admin,
        long_term_debt=edgar.facts.long_term_debt_noncurrent,
        current_ratio=current_ratio,
        shares=edgar.facts.shares_outstanding,
        net_income=edgar.facts.net_income,
        operating_cash_flow=edgar.facts.operating_cash_flow,
        gross_margin=gross_margin,
        asset_turnover=asset_turnover,
        inventory=edgar.facts.inventory,
    )


def select_altman_variant(industry_classification: str) -> AltmanVariant:
    normalized = industry_classification.lower()
    if "emerging" in normalized:
        return "emerging_market_z_double_prime_plus_3_25"
    if "non-manufacturer" in normalized or "non manufacturer" in normalized:
        return "z_double_prime"
    if "manufacturer" in normalized or "industrial" in normalized:
        return "manufacturer"
    return "z_double_prime"


def _altman(inputs: ScreenInputSet, variant: AltmanVariant, produced: datetime) -> AltmanResult:
    latest = -1
    a = inputs.total_assets[latest].value
    tl = inputs.total_liabilities[latest].value
    if variant == "manufacturer":
        z = (
            1.2 * inputs.working_capital[latest].value / a
            + 1.4 * inputs.retained_earnings[latest].value / a
            + 3.3 * inputs.ebit[latest].value / a
            + 0.6 * inputs.market_value_equity[latest].value / tl
            + inputs.sales[latest].value / a
        )
        zone = "safe" if z > 2.99 else "grey" if z >= 1.81 else "distress"
        formula = "Altman manufacturer Z = 1.2 WC/TA + 1.4 RE/TA + 3.3 EBIT/TA + 0.6 MVE/TL + Sales/TA"
    else:
        z = (
            6.56 * inputs.working_capital[latest].value / a
            + 3.26 * inputs.retained_earnings[latest].value / a
            + 6.72 * inputs.ebit[latest].value / a
            + 1.05 * inputs.book_value_equity[latest].value / tl
        )
        if variant == "emerging_market_z_double_prime_plus_3_25":
            z += 3.25
        zone = "safe" if z > 2.60 else "grey" if z >= 1.10 else "distress"
        formula = "Altman Z-double-prime = 6.56 WC/TA + 3.26 RE/TA + 6.72 EBIT/TA + 1.05 BVE/TL"
        if variant == "emerging_market_z_double_prime_plus_3_25":
            formula += " + 3.25 emerging-market constant"
    return AltmanResult(
        variant=variant,
        z=_computed(z, "computed:altman_z", inputs.years[latest], "x", produced, f"{formula}; inputs: working_capital, retained_earnings, EBIT, market/book equity, total_liabilities, sales, total_assets"),
        zone=zone,
    )


def _beneish(inputs: ScreenInputSet, produced: datetime) -> BeneishResult:
    i = -1
    p = -2
    dsri = _ratio(inputs.receivables[i], inputs.sales[i]) / _ratio(inputs.receivables[p], inputs.sales[p])
    gmi = inputs.gross_margin[p].value / inputs.gross_margin[i].value
    aqi = (1 - _ratio(inputs.current_assets[i], inputs.total_assets[i])) / (1 - _ratio(inputs.current_assets[p], inputs.total_assets[p]))
    sgi = inputs.sales[i].value / inputs.sales[p].value
    depi = 1.0
    sgai = 1.0
    lvgi = _ratio(inputs.long_term_debt[i], inputs.total_assets[i]) / _ratio(inputs.long_term_debt[p], inputs.total_assets[p])
    tata = (inputs.net_income[i].value - inputs.operating_cash_flow[i].value) / inputs.total_assets[i].value
    score = -4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi
    return BeneishResult(
        m=_computed(score, "computed:beneish_m_score", inputs.years[i], "x", produced, "Beneish M = -4.84 + 0.92 DSRI + 0.528 GMI + 0.404 AQI + 0.892 SGI + 0.115 DEPI - 0.172 SGAI + 4.679 TATA - 0.327 LVGI; inputs: receivables, sales, gross_profit, current_assets, total_assets, long_term_debt, net_income, operating_cash_flow"),
        flag=score > -1.78,
    )


def _piotroski(inputs: ScreenInputSet, produced: datetime) -> PiotroskiResult:
    i = -1
    p = -2
    score = 0
    score += inputs.net_income[i].value > 0
    score += inputs.operating_cash_flow[i].value > 0
    score += _ratio(inputs.net_income[i], inputs.total_assets[i]) > _ratio(inputs.net_income[p], inputs.total_assets[p])
    score += inputs.operating_cash_flow[i].value > inputs.net_income[i].value
    score += _ratio(inputs.long_term_debt[i], inputs.total_assets[i]) < _ratio(inputs.long_term_debt[p], inputs.total_assets[p])
    score += inputs.current_ratio[i].value > inputs.current_ratio[p].value
    score += inputs.shares[i].value <= inputs.shares[p].value
    score += inputs.gross_margin[i].value > inputs.gross_margin[p].value
    score += inputs.asset_turnover[i].value > inputs.asset_turnover[p].value
    return PiotroskiResult(
        f=_computed(float(score), "computed:piotroski_f_score", inputs.years[i], "x", produced, "Piotroski F-score sum of nine profitability, leverage/liquidity, dilution, margin, and turnover signals; inputs: net_income, operating_cash_flow, total_assets, long_term_debt, current_ratio, shares, gross_margin, asset_turnover")
    )


def _dig_items(altman: AltmanResult, beneish: BeneishResult, piotroski: PiotroskiResult, smoke: SmokeChecks) -> list[str]:
    items: list[str] = []
    if altman.zone != "safe":
        items.append(f"Altman {altman.variant} zone is {altman.zone}; solvency scrutiny required.")
    if beneish.flag:
        items.append("Beneish M-Score above -1.78; earnings-manipulation scrutiny required.")
    if piotroski.f.value <= 4:
        items.append("Piotroski F-Score is low; quality scrutiny required.")
    if smoke.restatement or smoke.auditor_change or smoke.ni_cfo_gap_widening:
        items.append("Smoke checks lit; filing-quality scrutiny required.")
    return items


def _validate_inputs(inputs: ScreenInputSet) -> None:
    fields = (
        "working_capital",
        "retained_earnings",
        "ebit",
        "market_value_equity",
        "book_value_equity",
        "total_liabilities",
        "total_assets",
        "sales",
        "receivables",
        "gross_profit",
        "current_assets",
        "depreciation",
        "sga",
        "long_term_debt",
        "current_ratio",
        "shares",
        "net_income",
        "operating_cash_flow",
        "gross_margin",
        "asset_turnover",
        "inventory",
    )
    for field in fields:
        values = getattr(inputs, field)
        if len(values) != len(inputs.years):
            raise ValueError(f"{field} does not match years")
        if any(number.provenance is None for number in values):
            raise ValueError(f"{field} missing provenance")
    if len(inputs.years) < 2:
        raise ValueError("screens require at least two years")


def _ni_cfo_gap_widening(inputs: ScreenInputSet) -> bool:
    latest_gap = abs(inputs.net_income[-1].value - inputs.operating_cash_flow[-1].value)
    prior_gap = abs(inputs.net_income[-2].value - inputs.operating_cash_flow[-2].value)
    return latest_gap > prior_gap


def _inventory_trend(inputs: ScreenInputSet) -> str:
    if _inventory_not_reported(inputs.inventory):
        return NO_INVENTORY_REPORTED_STATUS
    return _trend("Inventory", [_ratio(inv, sales) for inv, sales in zip(inputs.inventory, inputs.sales, strict=True)])


def _inventory_not_reported(inventory: list[Number]) -> bool:
    return all(
        number.provenance.accession == NOT_REPORTED_BY_ISSUER
        or number.provenance.tag.endswith(f":{NOT_REPORTED_BY_ISSUER}")
        for number in inventory
    )


def _trend(name: str, values: list[float]) -> str:
    if values[-1] > values[-2] * 1.05:
        return f"{name.lower()}_widening"
    if values[-1] < values[-2] * 0.95:
        return f"{name.lower()}_improving"
    return "stable"


def _ratio(left: Number, right: Number) -> float:
    if right.value == 0:
        raise ValueError("screen ratio denominator is zero")
    return left.value / right.value


def _computed(value: float, tag: str, period: str, unit: str, produced_at: datetime, derivation: str) -> Number:
    return Number(
        value=float(value),
        unit=unit,
        kind="estimate",
        provenance=Provenance(tag=tag, form="computed", period=period, accession=None, source_name="B-4 Screens", retrieved_at=produced_at),
        derivation=derivation,
    )
