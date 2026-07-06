from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from skills._primitives import Header, Number, Provenance, Ratifiable
from skills.config import Config
from skills.accountant_artifacts import (
    CostOfCapitalInputs,
    DcfAssumption,
    EdgarFacts,
    ExpectationsLine,
    NormalizedFinancials,
    PriceResult,
    ReverseBandResult,
    Scenario,
    Sensitivity,
    ValuationRange,
)


@dataclass(frozen=True)
class DcfDrivers:
    revenue: Number
    revenue_growth: Number
    nopat_margin: Number
    sales_to_capital: Number
    forecast_years: Number
    terminal_growth: Number
    wacc: Number
    net_debt: Number
    shares: Number


def build_dcf_artifacts(
    financials: NormalizedFinancials,
    edgar: EdgarFacts,
    price: PriceResult,
    cost_of_capital: CostOfCapitalInputs,
    config: Config,
) -> tuple[ValuationRange, ExpectationsLine]:
    produced_at = datetime.now(timezone.utc)
    _require_m2a_inputs(price, cost_of_capital)
    valuation_range = build_forward_valuation(financials, edgar, price, cost_of_capital, config, produced_at)
    expectations_line = build_reverse_expectations(financials, edgar, price, cost_of_capital, config, produced_at)
    return valuation_range, expectations_line


def build_forward_valuation(
    financials: NormalizedFinancials,
    edgar: EdgarFacts,
    price: PriceResult,
    cost_of_capital: CostOfCapitalInputs,
    config: Config,
    produced_at: datetime | None = None,
) -> ValuationRange:
    produced = produced_at or datetime.now(timezone.utc)
    scenarios: list[Scenario] = []
    normalized_fixture_check = f"EDGAR fact from normalized {financials.ticker} fixture path."
    for name in ("bear", "base", "bull"):
        scenario_config = config.dcf.scenarios[name]
        wacc = {
            "bear": cost_of_capital.wacc_high,
            "base": cost_of_capital.wacc,
            "bull": cost_of_capital.wacc_low,
        }[name]
        assert wacc is not None
        drivers = _drivers(financials, edgar, config, scenario_config, wacc, produced)
        per_share = _value_per_share(drivers)
        value_derivation = _forward_value_derivation(drivers)
        scenarios.append(
            Scenario(
                name=name,
                assumptions=[
                    DcfAssumption(driver="starting_revenue", value=drivers.revenue, base_rate_check=normalized_fixture_check),
                    DcfAssumption(driver="forecast_years", value=drivers.forecast_years, base_rate_check="M2a deterministic default only; duration judgment is later scope."),
                    DcfAssumption(driver="terminal_growth", value=drivers.terminal_growth, base_rate_check="M2a deterministic default only; terminal economics review is later scope."),
                    DcfAssumption(driver="net_debt", value=drivers.net_debt, base_rate_check="EDGAR-derived mechanical input."),
                    DcfAssumption(driver="diluted_shares", value=drivers.shares, base_rate_check=normalized_fixture_check),
                    DcfAssumption(driver="revenue_growth", value=drivers.revenue_growth, base_rate_check="M2a deterministic default only; base-rate checks are M2b scope."),
                    DcfAssumption(driver="nopat_margin", value=drivers.nopat_margin, base_rate_check="M2a deterministic default only; base-rate checks are M2b scope."),
                    DcfAssumption(driver="sales_to_capital", value=drivers.sales_to_capital, base_rate_check="M2a deterministic default only; base-rate checks are M2b scope."),
                    DcfAssumption(driver="wacc", value=drivers.wacc, base_rate_check="A-3 cost-of-capital band input."),
                ],
                value=_computed(
                    per_share,
                    "computed:dcf_value_per_share",
                    financials.years[-1],
                    "USD_per_share",
                    produced,
                    value_derivation,
                ),
                probability=Ratifiable(
                    draft={"bear": 0.25, "base": 0.50, "bull": 0.25}[name],
                    evidence=["M2a schema placeholder only; Senior probability weighting is explicitly deferred to M3."],
                    needs_ratification=True,
                ),
            )
        )

    low = scenarios[0].value
    high = scenarios[2].value
    return ValuationRange(
        header=Header(schema_version=config.schema_version, produced_by="B-3", produced_at=produced),
        scenarios=scenarios,
        method="DCF",
        sensitivity=[
            Sensitivity(
                variable="WACC band",
                low=cost_of_capital.wacc_low,
                high=cost_of_capital.wacc_high,
                value_impact=_computed(
                    high.value - low.value,
                    "computed:wacc_band_value_impact",
                    financials.years[-1],
                    "USD_per_share",
                    produced,
                    "value_impact = bull per-share DCF value using WACC low - bear per-share DCF value using WACC high; inputs: computed:dcf_value_per_share(bull), computed:dcf_value_per_share(bear)",
                ),
            )
        ],
        flags=sorted(set(price.flags + cost_of_capital.flags + ["m2a_standalone_not_senior_ratified"])),
    )


def build_reverse_expectations(
    financials: NormalizedFinancials,
    edgar: EdgarFacts,
    price: PriceResult,
    cost_of_capital: CostOfCapitalInputs,
    config: Config,
    produced_at: datetime | None = None,
) -> ExpectationsLine:
    produced = produced_at or datetime.now(timezone.utc)
    assert cost_of_capital.wacc_low is not None
    assert cost_of_capital.wacc_high is not None
    base = config.dcf.scenarios["base"]
    flags = sorted(set(price.flags + cost_of_capital.flags))
    if price.price is None:
        low = _blocked_reverse_result(cost_of_capital.wacc_low, "observed price unavailable; reverse DCF requires market price", produced)
        high = _blocked_reverse_result(cost_of_capital.wacc_high, "observed price unavailable; reverse DCF requires market price", produced)
        flags.append("reverse_dcf_blocked_no_observed_price")
    else:
        low = _solve_growth_at_wacc(financials, edgar, config, price.price, base.nopat_margin, base.sales_to_capital, cost_of_capital.wacc_low, produced)
        high = _solve_growth_at_wacc(financials, edgar, config, price.price, base.nopat_margin, base.sales_to_capital, cost_of_capital.wacc_high, produced)
    implied_growth: Number | None = None
    if low.converged and high.converged and low.implied_revenue_growth is not None and high.implied_revenue_growth is not None:
        implied_growth = _computed(
            (low.implied_revenue_growth.value + high.implied_revenue_growth.value) / 2,
            "computed:reverse_dcf_implied_growth_midpoint",
            financials.years[-1],
            "percent",
            produced,
            "convenience midpoint only, not the headline implied value; authoritative reverse DCF outputs are the low/high WACC band edges; inputs: computed:reverse_dcf_implied_revenue_growth(low), computed:reverse_dcf_implied_revenue_growth(high)",
        )
    else:
        flags.append("reverse_dcf_non_convergence")

    margin = _assumption_number(base.nopat_margin, "computed:reverse_dcf_margin_assumption", financials.years[-1], "ratio", produced, "Reverse DCF holds config base NOPAT margin constant while solving revenue growth; inputs: config.dcf.scenarios.base.nopat_margin")
    duration = _assumption_number(float(config.dcf.forecast_years), "computed:reverse_dcf_duration_assumption", financials.years[-1], "years", produced, "Reverse DCF uses configured explicit forecast duration; inputs: config.dcf.forecast_years")
    terminal = _assumption_number(config.dcf.terminal_growth, "computed:reverse_dcf_terminal_growth_assumption", financials.years[-1], "percent", produced, "Reverse DCF uses configured terminal growth as terminal economics proxy for M2a; inputs: config.dcf.terminal_growth")

    return ExpectationsLine(
        header=Header(schema_version=config.schema_version, produced_by="B-3", produced_at=produced),
        implied={
            "revenue_growth": None,
            "revenue_growth_midpoint": implied_growth,
            "margin": margin,
            "years": duration,
            "terminal_roic": terminal,
        },
        wacc_band={"low": cost_of_capital.wacc_low, "high": cost_of_capital.wacc_high},
        reverse_band_results={"low": low, "high": high},
        frame="DCF",
        frame_justification="DCF is used for routed cash-generating operating companies when the required price, cost-of-capital, and normalized filing inputs are available.",
        authoritative_output="wacc_band_edges",
        midpoint_note="The low/high WACC edge results are authoritative. Any midpoint is a convenience summary only and must not be treated as the headline implied expectation.",
        flags=flags,
    )


def _solve_growth_at_wacc(
    financials: NormalizedFinancials,
    edgar: EdgarFacts,
    config: Config,
    target_price: Number,
    margin: float,
    sales_to_capital: float,
    wacc: Number,
    produced_at: datetime,
) -> ReverseBandResult:
    low = config.dcf.reverse_growth_low
    high = config.dcf.reverse_growth_high
    low_drivers = _drivers_from_values(financials, edgar, config, low, margin, sales_to_capital, wacc, produced_at)
    high_drivers = _drivers_from_values(financials, edgar, config, high, margin, sales_to_capital, wacc, produced_at)
    low_value = _value_per_share(low_drivers)
    high_value = _value_per_share(high_drivers)
    if not min(low_value, high_value) <= target_price.value <= max(low_value, high_value):
        return ReverseBandResult(
            wacc=wacc,
            converged=False,
            failure_reason=(
                f"target price {target_price.value:.4f} outside solvable value range "
                f"[{min(low_value, high_value):.4f}, {max(low_value, high_value):.4f}] for growth bounds [{low:.4f}, {high:.4f}]"
            ),
        )

    lo, hi = low, high
    mid = lo
    for _ in range(80):
        mid = (lo + hi) / 2
        mid_value = _value_per_share(_drivers_from_values(financials, edgar, config, mid, margin, sales_to_capital, wacc, produced_at))
        if abs(mid_value - target_price.value) < 0.0001:
            break
        if (low_value <= target_price.value <= mid_value) or (mid_value <= target_price.value <= low_value):
            hi = mid
            high_value = mid_value
        else:
            lo = mid
            low_value = mid_value

    return ReverseBandResult(
        wacc=wacc,
        converged=True,
        implied_revenue_growth=_computed(
            mid,
            "computed:reverse_dcf_implied_revenue_growth",
            financials.years[-1],
            "percent",
            produced_at,
            f"Bisection solve for revenue growth where DCF per-share value equals observed market price at this WACC band edge; inputs: {target_price.provenance.tag}, {wacc.provenance.tag}, EDGAR revenue, EDGAR shares, computed:net_debt, config.dcf.scenarios.base.nopat_margin, config.dcf.scenarios.base.sales_to_capital, config.dcf.forecast_years, config.dcf.terminal_growth",
        ),
    )


def _drivers(financials, edgar, config, scenario_config, wacc: Number, produced_at: datetime) -> DcfDrivers:
    return _drivers_from_values(
        financials,
        edgar,
        config,
        scenario_config.revenue_growth,
        scenario_config.nopat_margin,
        scenario_config.sales_to_capital,
        wacc,
        produced_at,
    )


def _drivers_from_values(financials: NormalizedFinancials, edgar: EdgarFacts, config: Config, growth: float, margin: float, sales_to_capital: float, wacc: Number, produced_at: datetime) -> DcfDrivers:
    return DcfDrivers(
        revenue=financials.facts.revenue[-1],
        revenue_growth=_assumption_number(growth, "computed:dcf_assumption:revenue_growth", "M2a", "percent", produced_at, "Config-backed M2a default; Analyst scenarios are out of scope; inputs: config.dcf.scenarios.revenue_growth"),
        nopat_margin=_assumption_number(margin, "computed:dcf_assumption:nopat_margin", "M2a", "ratio", produced_at, "Config-backed M2a default from AAPL fixture economics; inputs: config.dcf.scenarios.nopat_margin"),
        sales_to_capital=_assumption_number(sales_to_capital, "computed:dcf_assumption:sales_to_capital", "M2a", "x", produced_at, "Config-backed M2a reinvestment driver; inputs: config.dcf.scenarios.sales_to_capital"),
        forecast_years=_assumption_number(float(config.dcf.forecast_years), "computed:dcf_assumption:forecast_years", "M2a", "years", produced_at, "Configured explicit DCF duration; inputs: config.dcf.forecast_years"),
        terminal_growth=_assumption_number(config.dcf.terminal_growth, "computed:dcf_assumption:terminal_growth", "M2a", "percent", produced_at, "Configured DCF terminal growth; inputs: config.dcf.terminal_growth"),
        wacc=wacc,
        net_debt=_net_debt(edgar, produced_at),
        shares=edgar.facts.shares_outstanding[-1],
    )


def _value_per_share(drivers: DcfDrivers) -> float:
    if drivers.wacc.value <= drivers.terminal_growth.value:
        raise ValueError("WACC must exceed terminal growth")
    previous_revenue = drivers.revenue.value
    pv = 0.0
    final_fcff = 0.0
    for year in range(1, int(drivers.forecast_years.value) + 1):
        revenue = previous_revenue * (1 + drivers.revenue_growth.value)
        nopat = revenue * drivers.nopat_margin.value
        reinvestment = max(0.0, revenue - previous_revenue) / drivers.sales_to_capital.value
        fcff = nopat - reinvestment
        pv += fcff / ((1 + drivers.wacc.value) ** year)
        previous_revenue = revenue
        final_fcff = fcff
    terminal_value = final_fcff * (1 + drivers.terminal_growth.value) / (drivers.wacc.value - drivers.terminal_growth.value)
    enterprise_value = pv + terminal_value / ((1 + drivers.wacc.value) ** int(drivers.forecast_years.value))
    equity_value = enterprise_value - drivers.net_debt.value
    return equity_value / drivers.shares.value


def _net_debt(edgar: EdgarFacts, produced_at: datetime) -> Number:
    debt = edgar.facts.long_term_debt_noncurrent[-1].value + edgar.facts.long_term_debt_current[-1].value + edgar.facts.short_term_borrowings[-1].value
    return _computed(
        debt - edgar.facts.cash[-1].value,
        "computed:net_debt",
        edgar.years[-1],
        "USD_millions",
        produced_at,
        "net_debt = long_term_debt_noncurrent + long_term_debt_current + short_term_borrowings - cash; inputs: EDGAR long_term_debt_noncurrent, EDGAR long_term_debt_current, EDGAR short_term_borrowings, EDGAR cash",
    )


def _blocked_reverse_result(wacc: Number, reason: str, produced_at: datetime) -> ReverseBandResult:
    return ReverseBandResult(wacc=wacc, converged=False, blocked=True, failure_reason=f"{reason}; inputs: {wacc.provenance.tag}")


def _assumption_number(value: float, tag: str, period: str, unit: Literal["percent", "ratio", "years", "x"], produced_at: datetime, derivation: str) -> Number:
    return _computed(value, tag, period, unit, produced_at, derivation)


def _forward_value_derivation(drivers: DcfDrivers) -> str:
    refs = [
        _ref(drivers.revenue),
        _ref(drivers.revenue_growth),
        _ref(drivers.nopat_margin),
        _ref(drivers.sales_to_capital),
        _ref(drivers.forecast_years),
        _ref(drivers.terminal_growth),
        _ref(drivers.wacc),
        _ref(drivers.net_debt),
        _ref(drivers.shares),
    ]
    return "forward DCF per share = (PV explicit FCFF + PV terminal value - net debt) / diluted shares; inputs: " + ", ".join(refs)


def _ref(number: Number) -> str:
    return f"{number.provenance.tag}@{number.provenance.period}"


def _computed(value: float, tag: str, period: str, unit: str, produced_at: datetime, derivation: str) -> Number:
    return Number(
        value=value,
        unit=unit,
        kind="estimate",
        provenance=Provenance(tag=tag, form="computed", period=period, accession=None, source_name="B-3 DCF", retrieved_at=produced_at),
        derivation=derivation,
    )


def _require_m2a_inputs(price: PriceResult, cost_of_capital: CostOfCapitalInputs) -> None:
    required = [cost_of_capital.wacc, cost_of_capital.wacc_low, cost_of_capital.wacc_high]
    if any(item is None for item in required):
        raise ValueError("DCF requires M2a cost-of-capital WACC inputs")
