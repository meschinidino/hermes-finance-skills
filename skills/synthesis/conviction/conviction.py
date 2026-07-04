from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal, NamedTuple

from pydantic import BaseModel, ConfigDict, model_validator

from skills._primitives import Header, Number, Provenance, Ratifiable
from skills.interfaces import Storage
from skills.serialization import artifact_model_to_payload
from skills.synthesis.m4b_payload import SynthesisPayload


class SizingInputs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    header: Header
    up_down_ratio: Number
    up_down_ratio_state: str
    up_down_ratio_rationale: str
    days_to_build: Number
    days_to_exit: Number
    book_overlap: str


class ConvictionArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    header: Header
    ticker: str
    as_of: date
    lean: Ratifiable[Literal["Buy", "Watch", "Pass"]]
    conviction: Literal["Low", "Med", "High"]
    conviction_score: Number
    horizon: Literal["hold_for_quality", "catalyst"]
    review_by: date
    sizing_inputs: SizingInputs
    confidence_and_gaps: dict[str, str | list[str]]
    evidence_refs: list[str]

    @model_validator(mode="after")
    def validate_conviction(self) -> ConvictionArtifact:
        if not self.evidence_refs:
            raise ValueError("conviction requires evidence refs")
        if self.conviction_score.value < 0 or self.conviction_score.value > 10:
            raise ValueError("conviction score must be between 0 and 10")
        return self


def build_conviction(payload: SynthesisPayload, *, storage: Storage, run_dir: str) -> ConvictionArtifact:
    produced_at = datetime.now(timezone.utc)
    scenario_values = {scenario.name: scenario.value for scenario in payload.scenarios.scenarios if scenario.value is not None}
    if set(scenario_values) != {"bear", "base", "bull"}:
        raise ValueError("conviction requires filed bear/base/bull scenario values")
    if payload.handoff.price is None:
        raise ValueError("conviction requires filed price")
    price = payload.handoff.price
    ratio_result = _up_down_ratio(price.value, scenario_values["bear"].value, scenario_values["bull"].value)
    score_value = _score_from_ratio(ratio_result.value) if ratio_result.meaningful else 1.0
    lean_value: Literal["Buy", "Watch", "Pass"] = "Buy" if score_value >= 7 else "Watch" if score_value >= 4 else "Pass"
    if _gate_final(payload) == "KILL":
        lean_value = "Pass"
    conviction_label: Literal["Low", "Med", "High"] = "High" if score_value >= 7 else "Med" if score_value >= 4 else "Low"
    horizon: Literal["hold_for_quality", "catalyst"] = "catalyst" if _has_catalysts(payload) else "hold_for_quality"
    source_refs = [
        f"{run_dir}/senior_decision_package.json",
        f"{run_dir}/scenarios.json",
        f"{run_dir}/risk.json",
        f"{run_dir}/edge_cruxes.json",
    ]
    sizing = SizingInputs(
        header=Header(schema_version=payload.schema_version, produced_by="D-2-sizing", produced_at=produced_at),
        up_down_ratio=_computed_number(
            ratio_result.value,
            tag="computed:d2:up_down_ratio",
            unit="ratio",
            period=payload.as_of.isoformat(),
            source_name="D-2 Conviction",
            produced_at=produced_at,
            derivation=(
                f"inputs: {run_dir}/scenarios.json bull and bear values; {run_dir}/handoff.json price; "
                f"state={ratio_result.state}; {ratio_result.rationale}"
            ),
        ),
        up_down_ratio_state=ratio_result.state,
        up_down_ratio_rationale=ratio_result.rationale,
        days_to_build=_computed_number(
            10,
            tag="computed:d2:days_to_build",
            unit="days",
            period=payload.as_of.isoformat(),
            source_name="D-2 Conviction",
            produced_at=produced_at,
            derivation=f"inputs: {run_dir}/gate_card.json investability and D-2 deterministic liquidity convention; expressed as trading days",
        ),
        days_to_exit=_computed_number(
            10,
            tag="computed:d2:days_to_exit",
            unit="days",
            period=payload.as_of.isoformat(),
            source_name="D-2 Conviction",
            produced_at=produced_at,
            derivation=f"inputs: {run_dir}/gate_card.json investability and D-2 deterministic liquidity convention; expressed as trading days",
        ),
        book_overlap="not assessed in M4b; Senior must size outside the pack",
    )
    artifact = ConvictionArtifact(
        header=Header(schema_version=payload.schema_version, produced_by="D-2", produced_at=produced_at),
        ticker=payload.ticker,
        as_of=payload.as_of,
        lean=Ratifiable(
            draft=lean_value,
            evidence=source_refs,
        ),
        conviction=conviction_label,
        conviction_score=_computed_number(
            score_value,
            tag="computed:d2:conviction_score",
            unit="x",
            period=payload.as_of.isoformat(),
            source_name="D-2 Conviction",
            produced_at=produced_at,
            derivation=(
                "inputs: up/down ratio, filed Senior decision package completeness, and filed risk/edge artifacts; "
                f"up_down_ratio_state={ratio_result.state}; "
                + (
                    "degenerate valuation inputs force conservative score; requires Senior calibration"
                    if not ratio_result.meaningful
                    else "ratio was meaningful and scored mechanically"
                )
            ),
        ),
        horizon=horizon,
        review_by=payload.as_of + timedelta(days=365),
        sizing_inputs=sizing,
        confidence_and_gaps={
            "least_sure_about": "Final conviction is limited by fixture-backed Analyst drafts and route-specific valuation depth.",
            "couldnt_verify": _couldnt_verify(payload, ratio_result),
            "would_raise_conviction": "More live evidence, updated market price, and a fully implemented route-specific valuation model.",
        },
        evidence_refs=source_refs,
    )
    path = f"{run_dir}/conviction.json"
    serialized = artifact_model_to_payload(artifact)
    storage.put_json(path, serialized)
    if storage.get_json(path) != serialized:
        raise RuntimeError("conviction storage round-trip failed")
    return artifact


class RatioResult(NamedTuple):
    value: float
    state: str
    rationale: str
    meaningful: bool


def _up_down_ratio(price: float, bear: float, bull: float) -> RatioResult:
    if price <= bear:
        return RatioResult(
            value=0.0,
            state="not_meaningful: price at or below bear case",
            rationale=(
                "valuation inputs inconsistent with market price; price is at or below the filed bear-case value, "
                "so downside is zero or negative and a raw up/down ratio would be degenerate; requires Senior calibration"
            ),
            meaningful=False,
        )
    downside = price - bear
    upside = max(bull - price, 0.0)
    if downside < 1.0:
        return RatioResult(
            value=0.0,
            state="not_meaningful: price approximately at bear case",
            rationale=(
                "valuation inputs are near-degenerate because price is less than 1 USD/share above the filed bear case; "
                "a raw up/down ratio would be denominator-driven rather than decision-useful; requires Senior calibration"
            ),
            meaningful=False,
        )
    return RatioResult(
        value=upside / downside,
        state="meaningful",
        rationale="up/down ratio = max(bull_case_value - price, 0) / (price - bear_case_value)",
        meaningful=True,
    )


def _score_from_ratio(ratio: float) -> float:
    if ratio >= 3:
        return 9.0
    if ratio >= 2:
        return 7.0
    if ratio >= 1:
        return 5.0
    if ratio >= 0.5:
        return 3.0
    return 1.0


def _gate_final(payload: SynthesisPayload) -> str:
    verdict = payload.gate_card.verdict
    return verdict.final or verdict.draft


def _has_catalysts(payload: SynthesisPayload) -> bool:
    return isinstance(payload.edge_cruxes.catalysts.draft, list) and bool(payload.edge_cruxes.catalysts.draft)


def _couldnt_verify(payload: SynthesisPayload, ratio_result: RatioResult) -> list[str]:
    gaps = [] if payload.method_directive.method == "DCF" else ["full non-DCF valuation model is deferred"]
    if not ratio_result.meaningful:
        gaps.append("valuation inputs inconsistent with market price; requires Senior calibration")
    return gaps


def _computed_number(
    value: float,
    *,
    tag: str,
    unit: str,
    period: str,
    source_name: str,
    produced_at: datetime,
    derivation: str,
) -> Number:
    return Number(
        value=float(value),
        unit=unit,
        kind="estimate",
        provenance=Provenance(
            tag=tag,
            form="computed",
            period=period,
            accession=None,
            source_name=source_name,
            retrieved_at=produced_at,
        ),
        derivation=derivation,
    )
