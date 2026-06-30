from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skills._primitives import Header, Number, Provenance, Ratifiable, StrictModel, to_jsonable


class M1Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)


class EdgarConceptSet(M1Model):
    ebit: list[Number]
    revenue: list[Number]
    cash: list[Number]
    long_term_debt_noncurrent: list[Number]
    long_term_debt_current: list[Number]
    short_term_borrowings: list[Number]
    equity: list[Number]
    goodwill: list[Number]
    shares_outstanding: list[Number]
    interest_expense: list[Number]


class EdgarFacts(M1Model):
    ticker: str
    cik: str
    years: list[str]
    facts: EdgarConceptSet
    flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_history(self) -> EdgarFacts:
        if len(self.years) < 5:
            raise ValueError("insufficient_history")
        for field_name, values in self.facts:
            if len(values) != len(self.years):
                raise ValueError(f"{field_name} does not match years")
        return self


class NormalizedFinancials(M1Model):
    ticker: str
    cik: str
    years: list[str]
    facts: EdgarConceptSet
    normalization_log: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class PriceResult(M1Model):
    ticker: str
    price: Number | None
    market_cap: Number | None = None
    weighting_equity: Number | None = None
    weighting_basis: Literal["market_cap", "book_equity_fallback"] | None = None
    source: str
    flags: list[str] = Field(default_factory=list)


class CostOfCapitalInputs(M1Model):
    risk_free_rate: Number
    erp: Number
    unlevered_beta: Number
    credit_spread: Number
    tax_rate: Number
    debt: Number | None = None
    equity_weighting_value: Number | None = None
    debt_to_equity: Number | None = None
    relevered_beta: Number | None = None
    cost_of_equity: Number | None = None
    pre_tax_cost_of_debt: Number | None = None
    after_tax_cost_of_debt: Number | None = None
    wacc: Number | None = None
    wacc_low: Number | None = None
    wacc_high: Number | None = None
    flags: list[str] = Field(default_factory=list)


class DcfAssumption(M1Model):
    driver: str
    value: Number
    base_rate_check: str


class Scenario(M1Model):
    name: Literal["bear", "base", "bull"]
    assumptions: list[DcfAssumption]
    value: Number
    probability: Ratifiable[float]


class Sensitivity(M1Model):
    variable: str
    low: Number
    high: Number
    value_impact: Number


class ValuationRange(M1Model):
    header: Header
    scenarios: list[Scenario]
    method: Literal["DCF"]
    sensitivity: list[Sensitivity]
    flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_scenarios(self) -> ValuationRange:
        if [scenario.name for scenario in self.scenarios] != ["bear", "base", "bull"]:
            raise ValueError("valuation range requires bear/base/bull scenarios")
        return self


class ReverseBandResult(M1Model):
    wacc: Number
    converged: bool
    blocked: bool = False
    implied_revenue_growth: Number | None = None
    failure_reason: str | None = None

    @model_validator(mode="after")
    def validate_result(self) -> ReverseBandResult:
        if self.converged and self.blocked:
            raise ValueError("reverse result cannot be both converged and blocked")
        if self.converged and self.implied_revenue_growth is None:
            raise ValueError("converged reverse result requires implied growth")
        if not self.converged and not self.failure_reason:
            raise ValueError("non-converged reverse result requires failure reason")
        return self


class ExpectationsLine(M1Model):
    header: Header
    implied: dict[str, Number | None]
    wacc_band: dict[str, Number]
    reverse_band_results: dict[str, ReverseBandResult]
    frame: Literal["DCF"]
    frame_justification: str
    authoritative_output: str = "wacc_band_edges"
    midpoint_note: str | None = None
    flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_band(self) -> ExpectationsLine:
        if set(self.wacc_band) != {"low", "high"}:
            raise ValueError("wacc band must include low/high")
        if self.wacc_band["low"].value >= self.wacc_band["high"].value:
            raise ValueError("wacc band low must be below high")
        if set(self.reverse_band_results) != {"low", "high"}:
            raise ValueError("reverse band results must include low/high")
        return self


class Spine(M1Model):
    header: Header
    years: list[str]
    wacc: list[Number]
    nopat: list[Number]
    invested_capital_incl_gw: list[Number]
    invested_capital_ex_gw: list[Number]
    roic_incl_gw: list[Number]
    roic_ex_gw: list[Number]
    spread: list[Number]
    nopat_margin: list[Number]
    capital_turnover: list[Number]
    flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_lengths(self) -> Spine:
        for field_name in (
            "wacc",
            "nopat",
            "invested_capital_incl_gw",
            "invested_capital_ex_gw",
            "roic_incl_gw",
            "roic_ex_gw",
            "spread",
            "nopat_margin",
            "capital_turnover",
        ):
            if len(getattr(self, field_name)) != len(self.years):
                raise ValueError(f"{field_name} does not match years")
        return self


class BareHandoff(M1Model):
    header: Header
    status: str
    ticker: str
    cik: str
    as_of: date
    price: Number | None
    spine: Spine
    confidence_and_gaps: dict[str, Any]
    data_room: dict[str, Any]
    flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_status(self) -> BareHandoff:
        if self.status != "m1_walking_skeleton":
            raise ValueError("handoff must be marked as M1 walking skeleton")
        return self


def model_to_payload(model: BaseModel) -> dict[str, Any]:
    payload = to_jsonable(model)
    if not isinstance(payload, dict):
        raise TypeError("expected model to serialize to object")
    return payload


def iter_numbers(value: Any) -> list[Number]:
    numbers: list[Number] = []
    if isinstance(value, Number):
        return [value]
    if isinstance(value, BaseModel):
        for item in value.__dict__.values():
            numbers.extend(iter_numbers(item))
        return numbers
    if isinstance(value, dict):
        for item in value.values():
            numbers.extend(iter_numbers(item))
        return numbers
    if isinstance(value, list | tuple):
        for item in value:
            numbers.extend(iter_numbers(item))
    return numbers


def make_external_number(
    value: float,
    *,
    tag: str,
    unit: str,
    period: str,
    source_name: str,
    retrieved_at,
    derivation: str,
) -> Number:
    return Number(
        value=value,
        unit=unit,
        kind="estimate",
        provenance=Provenance(
            tag=tag,
            form="external",
            period=period,
            accession=None,
            source_name=source_name,
            retrieved_at=retrieved_at,
        ),
        derivation=derivation,
    )
