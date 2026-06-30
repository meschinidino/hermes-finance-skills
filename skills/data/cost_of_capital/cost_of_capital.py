from __future__ import annotations

from datetime import date, datetime, timezone

from skills.config import Config
from skills.m1_artifacts import CostOfCapitalInputs, make_external_number


def build_cost_of_capital_inputs(
    ticker: str,
    config: Config,
    *,
    as_of: date | None = None,
) -> CostOfCapitalInputs:
    normalized = ticker.upper().strip()
    if normalized not in config.betas:
        raise ValueError(f"missing_beta:{normalized}")

    run_date = as_of or date.today()
    retrieved_at = datetime.now(timezone.utc)
    period = run_date.isoformat()

    return CostOfCapitalInputs(
        risk_free_rate=make_external_number(
            config.cost_of_capital.risk_free_fallback,
            tag="external:risk_free_fallback",
            unit="percent",
            period=period,
            source_name="config",
            retrieved_at=retrieved_at,
            derivation="M1 uses configured risk_free_fallback instead of live FRED.",
        ),
        erp=make_external_number(
            config.cost_of_capital.erp,
            tag="external:erp",
            unit="percent",
            period=period,
            source_name="config",
            retrieved_at=retrieved_at,
            derivation="M1 uses configured ERP.",
        ),
        unlevered_beta=make_external_number(
            config.betas[normalized].unlevered,
            tag="external:unlevered_beta",
            unit="x",
            period=period,
            source_name="config",
            retrieved_at=retrieved_at,
            derivation="M1 uses configured unlevered beta.",
        ),
        credit_spread=make_external_number(
            config.cost_of_capital.credit_spread,
            tag="external:credit_spread",
            unit="percent",
            period=period,
            source_name="config",
            retrieved_at=retrieved_at,
            derivation="M1 uses configured credit spread.",
        ),
        tax_rate=make_external_number(
            config.tax.marginal_rate,
            tag="external:marginal_tax_rate",
            unit="percent",
            period=period,
            source_name="config",
            retrieved_at=retrieved_at,
            derivation="M1 uses configured marginal tax rate.",
        ),
        flags=["risk_free_fallback"],
    )

