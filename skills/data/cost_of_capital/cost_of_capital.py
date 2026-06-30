from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Protocol

from skills.config import Config
from skills._primitives import Number, Provenance
from skills.accountant_artifacts import CostOfCapitalInputs, EdgarFacts, PriceResult, make_external_number

FIXTURE_PATH = Path(__file__).parents[3] / "tests" / "fixtures" / "fred_dgs10.json"


class FredClient(Protocol):
    def dgs10(self) -> float: ...


class UrlFredClient:
    def dgs10(self) -> float:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
        with urllib.request.urlopen(url, timeout=10) as response:
            rows = response.read().decode("utf-8").strip().splitlines()
        for row in reversed(rows[1:]):
            _, value = row.split(",", 1)
            if value != ".":
                return float(value) / 100.0
        raise ValueError("FRED DGS10 had no numeric observations")


def build_cost_of_capital_inputs(
    ticker: str,
    config: Config,
    *,
    edgar: EdgarFacts | None = None,
    price: PriceResult | None = None,
    fred_client: FredClient | None = None,
    use_fixture: bool = True,
    as_of: date | None = None,
) -> CostOfCapitalInputs:
    normalized = ticker.upper().strip()
    beta_config = config.beta_for_ticker(normalized)

    run_date = as_of or date.today()
    retrieved_at = datetime.now(timezone.utc)
    period = run_date.isoformat()
    flags: list[str] = []
    risk_free, risk_free_source = _risk_free_rate(
        config,
        retrieved_at=retrieved_at,
        period=period,
        fred_client=fred_client,
        use_fixture=use_fixture,
        flags=flags,
    )

    erp = make_external_number(
        config.cost_of_capital.erp,
        tag="external:equity_risk_premium",
        unit="percent",
        period=period,
        source_name="Damodaran:ERP",
        retrieved_at=retrieved_at,
        derivation="ERP read from config/conventions.yaml Damodaran convention.",
    )
    unlevered_beta = make_external_number(
        beta_config.unlevered,
        tag="external:unlevered_beta",
        unit="x",
        period=beta_config.source_date,
        source_name=beta_config.source_name,
        retrieved_at=retrieved_at,
        derivation=f"Damodaran sector unlevered beta for ticker {normalized}; source={beta_config.source_url}",
    )
    credit_spread = make_external_number(
        config.cost_of_capital.credit_spread,
        tag=f"external:synthetic_rating_spread:{config.cost_of_capital.synthetic_rating}",
        unit="percent",
        period=period,
        source_name="Damodaran:Synthetic rating spread",
        retrieved_at=retrieved_at,
        derivation="Synthetic-rating spread read from config/conventions.yaml Damodaran convention.",
    )
    tax_rate = make_external_number(
        config.tax.marginal_rate,
        tag="external:marginal_tax_rate",
        unit="percent",
        period=period,
        source_name="config",
        retrieved_at=retrieved_at,
        derivation="Marginal tax rate read from config/conventions.yaml.",
    )

    capital = _capital_structure(edgar, price, tax_rate, unlevered_beta, risk_free, erp, credit_spread, config, retrieved_at)

    return CostOfCapitalInputs(
        risk_free_rate=risk_free,
        erp=erp,
        unlevered_beta=unlevered_beta,
        credit_spread=credit_spread,
        tax_rate=tax_rate,
        flags=flags + [risk_free_source],
        **capital,
    )


def _risk_free_rate(
    config: Config,
    *,
    retrieved_at: datetime,
    period: str,
    fred_client: FredClient | None,
    use_fixture: bool,
    flags: list[str],
) -> tuple[Number, str]:
    try:
        if fred_client is not None:
            value = fred_client.dgs10()
            source = "FRED:DGS10"
            source_flag = "risk_free_fred"
        elif use_fixture:
            raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
            value = float(raw["observations"][-1]["value"]) / 100.0
            source = "fixture:FRED:DGS10"
            period = str(raw["observations"][-1]["date"])
            source_flag = "risk_free_fixture"
        else:
            value = UrlFredClient().dgs10()
            source = "FRED:DGS10"
            source_flag = "risk_free_fred"
        return (
            make_external_number(
                value,
                tag="external:FRED:DGS10",
                unit="percent",
                period=period,
                source_name=source,
                retrieved_at=retrieved_at,
                derivation="Risk-free rate = latest FRED DGS10 observation divided by 100.",
            ),
            source_flag,
        )
    except (OSError, KeyError, RuntimeError, ValueError, urllib.error.URLError):
        flags.append("fred_unreachable")
        return (
            make_external_number(
                config.cost_of_capital.risk_free_fallback,
                tag="external:risk_free_fallback",
                unit="percent",
                period=period,
                source_name="config:fallback",
                retrieved_at=retrieved_at,
                derivation="FRED DGS10 unreachable; used configured risk_free_fallback.",
            ),
            "risk_free_fallback",
        )


def _capital_structure(
    edgar: EdgarFacts | None,
    price: PriceResult | None,
    tax_rate: Number,
    unlevered_beta: Number,
    risk_free: Number,
    erp: Number,
    credit_spread: Number,
    config: Config,
    retrieved_at: datetime,
) -> dict[str, Number | None]:
    if edgar is None or price is None or price.weighting_equity is None:
        return {
            "debt": None,
            "equity_weighting_value": None,
            "debt_to_equity": None,
            "relevered_beta": None,
            "cost_of_equity": None,
            "pre_tax_cost_of_debt": None,
            "after_tax_cost_of_debt": None,
            "wacc": None,
            "wacc_low": None,
            "wacc_high": None,
        }

    period = edgar.years[-1]
    debt_value = (
        edgar.facts.long_term_debt_noncurrent[-1].value
        + edgar.facts.long_term_debt_current[-1].value
        + edgar.facts.short_term_borrowings[-1].value
    )
    equity_value = price.weighting_equity.value
    if equity_value <= 0:
        raise ValueError("non_positive_equity_weighting_value")
    debt = _computed(
        debt_value,
        "computed:total_debt",
        period,
        "USD_millions",
        retrieved_at,
        "D = long_term_debt_noncurrent + long_term_debt_current + short_term_borrowings; inputs: EDGAR long_term_debt_noncurrent, EDGAR long_term_debt_current, EDGAR short_term_borrowings",
    )
    d_to_e = _computed(
        debt_value / equity_value,
        "computed:debt_to_equity",
        period,
        "ratio",
        retrieved_at,
        "D_to_E = TotalDebt / A-2 weighting equity value; inputs: computed:total_debt, A-2 weighting_equity",
    )
    relevered_beta = _computed(
        unlevered_beta.value * (1 + (1 - tax_rate.value) * d_to_e.value),
        "computed:relevered_beta",
        period,
        "x",
        retrieved_at,
        "betaL = beta_unlevered * (1 + (1 - tax_rate) * D_to_E); inputs: external:unlevered_beta, external:marginal_tax_rate, computed:debt_to_equity",
    )
    cost_of_equity = _computed(
        risk_free.value + relevered_beta.value * erp.value,
        "computed:cost_of_equity",
        period,
        "percent",
        retrieved_at,
        "Ke = Rf + betaL * ERP; inputs: external:FRED:DGS10 or external:risk_free_fallback, computed:relevered_beta, external:equity_risk_premium",
    )
    pre_tax_debt = _computed(
        risk_free.value + credit_spread.value,
        "computed:pre_tax_cost_of_debt",
        period,
        "percent",
        retrieved_at,
        "Kd = Rf + synthetic_rating_spread; inputs: external:FRED:DGS10 or external:risk_free_fallback, external:synthetic_rating_spread",
    )
    after_tax_debt = _computed(
        pre_tax_debt.value * (1 - tax_rate.value),
        "computed:after_tax_cost_of_debt",
        period,
        "percent",
        retrieved_at,
        "Kd_after_tax = Kd * (1 - tax_rate); inputs: computed:pre_tax_cost_of_debt, external:marginal_tax_rate",
    )
    enterprise_capital = equity_value + debt_value
    wacc_value = (equity_value / enterprise_capital) * cost_of_equity.value + (debt_value / enterprise_capital) * after_tax_debt.value
    wacc = _computed(wacc_value, "computed:wacc", period, "percent", retrieved_at, "WACC = E/(E+D)*Ke + D/(E+D)*Kd_after_tax; inputs: A-2 weighting_equity, computed:total_debt, computed:cost_of_equity, computed:after_tax_cost_of_debt")
    wacc_low = _computed(max(0.0001, wacc_value - config.cost_of_capital.wacc_band_bps), "computed:wacc_low", period, "percent", retrieved_at, "WACC low = WACC - configured wacc_band_bps; inputs: computed:wacc, config.cost_of_capital.wacc_band_bps")
    wacc_high = _computed(wacc_value + config.cost_of_capital.wacc_band_bps, "computed:wacc_high", period, "percent", retrieved_at, "WACC high = WACC + configured wacc_band_bps; inputs: computed:wacc, config.cost_of_capital.wacc_band_bps")

    return {
        "debt": debt,
        "equity_weighting_value": price.weighting_equity,
        "debt_to_equity": d_to_e,
        "relevered_beta": relevered_beta,
        "cost_of_equity": cost_of_equity,
        "pre_tax_cost_of_debt": pre_tax_debt,
        "after_tax_cost_of_debt": after_tax_debt,
        "wacc": wacc,
        "wacc_low": wacc_low,
        "wacc_high": wacc_high,
    }


def _computed(value: float, tag: str, period: str, unit: str, retrieved_at: datetime, derivation: str) -> Number:
    return Number(
        value=value,
        unit=unit,
        kind="estimate",
        provenance=Provenance(
            tag=tag,
            form="computed",
            period=period,
            accession=None,
            source_name="A-3 Cost Of Capital",
            retrieved_at=retrieved_at,
        ),
        derivation=derivation,
    )
