from __future__ import annotations

from datetime import datetime, timezone

import pytest

from skills._primitives import Number, Provenance
from skills.audit import audit_artifact
from skills.accountant_artifacts import BaseRateForecast
from skills.valuation.base_rate.base_rate import lookup_base_rate


def _number(value: float, tag: str, unit: str = "percent") -> Number:
    return Number(
        value=value,
        unit=unit,
        kind="estimate",
        provenance=Provenance(tag=tag, form="external", period="M2b", accession=None, source_name="fixture", retrieved_at=datetime(2026, 6, 30, tzinfo=timezone.utc)),
        derivation=f"fixture input; inputs: {tag}",
    )


def test_base_rate_lookup_returns_known_bucket() -> None:
    forecast = BaseRateForecast(
        metric="revenue_growth",
        rate=_number(0.04, "forecast:revenue_growth"),
        horizon=_number(5, "forecast:horizon", "years"),
        company_size_decile=_number(8, "forecast:size_decile", "x"),
    )
    result = lookup_base_rate(forecast)

    assert result.reference_class == "large-company modest revenue growth, 3-5y"
    assert result.probability.value == 0.62
    assert not result.low_probability_bucket
    assert result.citation
    audit_artifact(result)


def test_base_rate_low_probability_bucket() -> None:
    forecast = BaseRateForecast(
        metric="revenue_growth",
        rate=_number(0.20, "forecast:revenue_growth"),
        horizon=_number(5, "forecast:horizon", "years"),
        company_size_decile=_number(8, "forecast:size_decile", "x"),
    )
    result = lookup_base_rate(forecast)

    assert result.probability.value == 0.11
    assert result.low_probability_bucket
    audit_artifact(result)


def test_base_rate_no_match_fails_closed() -> None:
    forecast = BaseRateForecast(
        metric="eps_growth",
        rate=_number(0.10, "forecast:eps_growth"),
        horizon=_number(10, "forecast:horizon", "years"),
        company_size_decile=_number(8, "forecast:size_decile", "x"),
    )

    with pytest.raises(ValueError, match="no_base_rate_match"):
        lookup_base_rate(forecast)
