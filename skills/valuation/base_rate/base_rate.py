from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from skills._primitives import Header, Number, Provenance
from skills.accountant_artifacts import BaseRateForecast, BaseRateResult


@dataclass(frozen=True)
class ReferenceClass:
    metric: str
    min_rate: float
    max_rate: float
    min_horizon: float
    max_horizon: float
    min_size_decile: float
    max_size_decile: float
    name: str
    probability: float
    citation: str


REFERENCE_CLASSES = [
    ReferenceClass("revenue_growth", 0.00, 0.05, 3, 5, 1, 10, "large-company modest revenue growth, 3-5y", 0.62, "Mauboussin-style base-rate fixture v1"),
    ReferenceClass("revenue_growth", 0.05, 0.15, 3, 5, 1, 5, "large-company high revenue growth, 3-5y", 0.28, "Mauboussin-style base-rate fixture v1"),
    ReferenceClass("revenue_growth", 0.15, 1.00, 3, 5, 1, 10, "sustained exceptional revenue growth, 3-5y", 0.11, "Mauboussin-style base-rate fixture v1"),
    ReferenceClass("margin_expansion", 0.00, 0.05, 3, 5, 1, 10, "operating margin expansion, 3-5y", 0.39, "Mauboussin-style base-rate fixture v1"),
    ReferenceClass("roic_improvement", 0.00, 0.05, 3, 5, 1, 10, "ROIC improvement, 3-5y", 0.34, "Mauboussin-style base-rate fixture v1"),
]

LOW_PROBABILITY_THRESHOLD = 0.30


def lookup_base_rate(
    forecast: BaseRateForecast,
    *,
    schema_version: str = "1.0",
    produced_at: datetime | None = None,
) -> BaseRateResult:
    produced = produced_at or datetime.now(timezone.utc)
    matched = _match(forecast)
    probability = Number(
        value=matched.probability,
        unit="ratio",
        kind="estimate",
        provenance=Provenance(
            tag="external:mauboussin_base_rate_fixture",
            form="external",
            period="M2b",
            accession=None,
            source_name=matched.citation,
            retrieved_at=produced,
        ),
        derivation=(
            f"probability selected from offline reference class '{matched.name}' "
            f"for metric/rate/horizon/size bucket; inputs: {forecast.rate.provenance.tag}, "
            f"{forecast.horizon.provenance.tag}, {forecast.company_size_decile.provenance.tag}"
        ),
    )
    return BaseRateResult(
        header=Header(schema_version=schema_version, produced_by="B-5", produced_at=produced),
        forecast=forecast,
        reference_class=matched.name,
        probability=probability,
        low_probability_bucket=matched.probability < LOW_PROBABILITY_THRESHOLD,
        citation=matched.citation,
    )


def _match(forecast: BaseRateForecast) -> ReferenceClass:
    for reference in REFERENCE_CLASSES:
        if (
            forecast.metric == reference.metric
            and reference.min_rate <= forecast.rate.value < reference.max_rate
            and reference.min_horizon <= forecast.horizon.value <= reference.max_horizon
            and reference.min_size_decile <= forecast.company_size_decile.value <= reference.max_size_decile
        ):
            return reference
    raise ValueError(f"no_base_rate_match:{forecast.metric}")
