from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, SerializeAsAny, model_validator

from skills._primitives import Header, Number, Ratifiable
from skills.accountant_artifacts import ExpectationsLine, ValuationRange
from skills.analyst_artifacts import EvidenceRef, ReviewItem, SeniorDecisionPackage, SeniorReviewPackage
from skills.interfaces import Storage
from skills.research.edge_cruxes.edge_cruxes import CruxDraft
from skills.research.risk.risk import KillMetricDraft, ModellableRiskDraft, TailRiskDraft
from skills.serialization import artifact_model_to_payload
from skills.synthesis.conviction.conviction import ConvictionArtifact, SizingInputs
from skills.synthesis.m4b_payload import SynthesisPayload


class RouteValuationDeferred(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    method: str
    reason: str
    scenario_values: dict[str, Number]


class Crux(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    claim: str
    metric: str
    threshold: str


class EdgeStatement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    header: Header
    steelman_no_trade: str
    counterparty: str
    variant_view: str | None
    cruxes: list[Crux]
    catalysts: list[dict[str, str]]

    @model_validator(mode="after")
    def validate_edge(self) -> EdgeStatement:
        if len(self.cruxes) != 3:
            raise ValueError("edge statement requires exactly three cruxes")
        if not self.counterparty.strip():
            raise ValueError("edge statement requires counterparty")
        return self


class RiskKillSheet(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    header: Header
    premortem: str
    bear_case_narrative: str
    modellable: list[ModellableRiskDraft]
    tail_risks: list[TailRiskDraft]
    bear_case_value: Number
    kill_metric: KillMetricDraft

    @model_validator(mode="after")
    def validate_risk(self) -> RiskKillSheet:
        if not self.tail_risks:
            raise ValueError("risk sheet requires tail risks")
        return self


class FinalHandoff(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    header: Header
    ticker: str
    price: Number
    as_of: date
    lean: Ratifiable[Literal["Buy", "Watch", "Pass"]]
    conviction: Literal["Low", "Med", "High"]
    conviction_score: Number
    horizon: Literal["hold_for_quality", "catalyst"]
    review_by: date
    thesis: str
    whats_priced_in: SerializeAsAny[ExpectationsLine | RouteValuationDeferred]
    valuation_range: SerializeAsAny[ValuationRange | RouteValuationDeferred]
    cruxes: list[Crux]
    risk: RiskKillSheet
    edge: EdgeStatement
    sizing_inputs: SizingInputs
    confidence_and_gaps: dict[str, str | list[str]]
    revisit_triggers: list[str]
    revisit_if: list[str]
    final_lean_signed_by: str
    final_lean_signed_by_provider: str
    final_lean_signed_by_deployment: str | None = None
    final_lean_signed_by_model: str
    final_lean_signed_by_model_family: str
    final_lean_signed_by_adapter: str
    final_lean_signed_by_response_model: str | None = None
    final_lean_signed_by_response_id: str | None = None
    data_room: dict[str, str | list[str]]
    senior_review_package: dict
    senior_decision_package: dict
    final_lean_decision_package: dict
    route_review_manifest: dict

    @model_validator(mode="after")
    def validate_final(self) -> FinalHandoff:
        unresolved = _unresolved_ratifiable_paths(self)
        if unresolved:
            raise ValueError(f"unresolved Ratifiable at {unresolved[0]}")
        if self.lean.decision == "overturned" and self.lean.final == self.lean.draft:
            raise ValueError("final handoff lean cannot reuse D-2 draft after Senior overturned it")
        if len(self.cruxes) != 3:
            raise ValueError("final handoff requires exactly three cruxes")
        if not self.revisit_triggers:
            raise ValueError("final handoff requires revisit triggers")
        if self.revisit_if != self.revisit_triggers:
            raise ValueError("final handoff revisit_if must mirror canonical revisit_triggers")
        for field_name in (
            "final_lean_signed_by",
            "final_lean_signed_by_provider",
            "final_lean_signed_by_model",
            "final_lean_signed_by_model_family",
            "final_lean_signed_by_adapter",
        ):
            if not str(getattr(self, field_name) or "").strip():
                raise ValueError(f"final handoff requires {field_name}")
        required_gap_keys = {"least_sure_about", "couldnt_verify", "would_raise_conviction"}
        if set(self.confidence_and_gaps) != required_gap_keys:
            raise ValueError("final handoff confidence_and_gaps is incomplete")
        return self


class FinalLeanReturnedForRevision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    header: Header
    ticker: str
    as_of: date
    status: Literal["halted"]
    halt_reason: Literal["final_lean_overturned_without_replacement"]
    message: str
    final_lean_review_package_path: str
    final_lean_decision_package_path: str
    decided_by: str
    decision: Literal["overturned"]
    replacement_final: None


def build_review_package(
    payload: SynthesisPayload,
    conviction: ConvictionArtifact,
    *,
    storage: Storage,
    run_dir: str,
    lean_decision_package: SeniorDecisionPackage,
) -> FinalHandoff:
    try:
        filed_conviction = ConvictionArtifact.model_validate(storage.get_json(f"{run_dir}/conviction.json"))
    except FileNotFoundError as exc:
        raise ValueError("D-3 requires filed D-2 conviction artifact") from exc
    if filed_conviction != conviction:
        raise ValueError("D-3 conviction input does not match filed D-2 artifact")
    if payload.handoff.price is None:
        raise ValueError("final handoff requires price")

    produced_at = datetime.now(timezone.utc)
    valuation = _hydrated_valuation(payload) if payload.valuation_range is not None else _deferred_valuation(payload)
    expectations = payload.expectations_line or _deferred_valuation(payload)
    cruxes = [_crux(item) for item in _required_cruxes(payload)]
    risk = RiskKillSheet(
        header=Header(schema_version=payload.schema_version, produced_by="D-3-risk", produced_at=produced_at),
        premortem=str(_final_or_draft(payload.risk.premortem)),
        bear_case_narrative=str(_final_or_draft(payload.risk.bear_case_narrative)),
        modellable=list(_final_or_draft(payload.risk.modellable_risks)),
        tail_risks=list(_final_or_draft(payload.risk.tail_risks)),
        bear_case_value=payload.risk.bear_case_value,
        kill_metric=_final_or_draft(payload.risk.kill_metric),
    )
    edge = EdgeStatement(
        header=Header(schema_version=payload.schema_version, produced_by="D-3-edge", produced_at=produced_at),
        steelman_no_trade=str(_final_or_draft(payload.edge_cruxes.steelman_no_trade)),
        counterparty=str(_final_or_draft(payload.edge_cruxes.counterparty)),
        variant_view=str(_final_or_draft(payload.edge_cruxes.variant_view)),
        cruxes=cruxes,
        catalysts=_catalysts(payload),
    )
    revisit_triggers = _revisit_triggers(payload, cruxes)
    handoff = FinalHandoff(
        header=Header(schema_version=payload.schema_version, produced_by="D-3", produced_at=produced_at),
        ticker=payload.ticker,
        price=payload.handoff.price,
        as_of=payload.as_of,
        lean=_ratified_lean(conviction, lean_decision_package),
        conviction=conviction.conviction,
        conviction_score=conviction.conviction_score,
        horizon=conviction.horizon,
        review_by=conviction.review_by,
        thesis=_thesis(payload),
        whats_priced_in=expectations,
        valuation_range=valuation,
        cruxes=cruxes,
        risk=risk,
        edge=edge,
        sizing_inputs=conviction.sizing_inputs,
        confidence_and_gaps=conviction.confidence_and_gaps,
        revisit_triggers=revisit_triggers,
        revisit_if=revisit_triggers,
        final_lean_signed_by=lean_decision_package.decided_by,
        final_lean_signed_by_provider=lean_decision_package.decided_by_provider,
        final_lean_signed_by_deployment=lean_decision_package.decided_by_deployment,
        final_lean_signed_by_model=lean_decision_package.decided_by_model,
        final_lean_signed_by_model_family=lean_decision_package.decided_by_model_family,
        final_lean_signed_by_adapter=lean_decision_package.decided_by_adapter,
        final_lean_signed_by_response_model=lean_decision_package.decided_by_response_model,
        final_lean_signed_by_response_id=lean_decision_package.decided_by_response_id,
        data_room=_data_room(run_dir, payload),
        senior_review_package=artifact_model_to_payload(payload.senior_review_package),
        senior_decision_package=artifact_model_to_payload(payload.senior_decision_package),
        final_lean_decision_package=artifact_model_to_payload(lean_decision_package),
        route_review_manifest=artifact_model_to_payload(payload.route_review_manifest),
    )
    serialized = artifact_model_to_payload(handoff)
    storage.put_json(f"{run_dir}/final_handoff.json", serialized)
    if storage.get_json(f"{run_dir}/final_handoff.json") != serialized:
        raise RuntimeError("final handoff storage round-trip failed")
    return handoff


def build_final_lean_review_package(
    conviction: ConvictionArtifact,
    *,
    source_artifact: str,
    header: Header,
) -> SeniorReviewPackage:
    return SeniorReviewPackage(
        header=header,
        ticker=conviction.ticker,
        as_of=conviction.as_of,
        review_items=[
            ReviewItem(
                id="final_lean",
                source_artifact=source_artifact,
                source_field_path="ConvictionArtifact.lean",
                draft=conviction.lean.draft,
                evidence_refs=[
                    EvidenceRef(
                        source_label="D-2 Conviction",
                        excerpt_or_summary="D-2 derived the final lean from filed scenarios, risk, edge, and prior Senior decisions.",
                        artifact_path=source_artifact,
                    )
                ],
                checklist_area="final_lean",
                checklist_rationale="Senior must sign the final Buy/Watch/Pass lean after synthesis.",
            )
        ],
        source_artifact_summary={source_artifact: "ConvictionArtifact"},
    )


def _final_or_draft(draft):
    return draft.final if draft.final is not None else draft.draft


def _ratified_lean(conviction: ConvictionArtifact, decision_package: SeniorDecisionPackage) -> Ratifiable[Literal["Buy", "Watch", "Pass"]]:
    decision = decision_package.decisions.get("final_lean")
    if decision is None:
        raise ValueError("final lean decision package missing final_lean")
    if decision.decision == "overturned" and decision.final is None:
        raise ValueError("final lean overturned without replacement")
    final_value = decision.final if decision.final is not None else conviction.lean.draft
    if final_value not in {"Buy", "Watch", "Pass"}:
        raise ValueError(f"final lean decision is invalid: {final_value}")
    if decision.decision == "overturned" and final_value == conviction.lean.draft:
        raise ValueError("final lean overturned replacement cannot reuse D-2 draft")
    evidence = list(conviction.lean.evidence)
    if decision.decision == "overturned":
        evidence.append("final_lean_decision_package:overturned-and-replaced")
    return conviction.lean.model_copy(
        update={
            "evidence": evidence,
            "decision": decision.decision,
            "decided_by": decision_package.decided_by,
            "final": final_value,
        }
    )


def _hydrated_valuation(payload: SynthesisPayload) -> ValuationRange:
    if payload.valuation_range is None:
        raise ValueError("DCF handoff requires valuation range")
    scenario_probabilities = _ratified_scenario_probabilities(payload)
    hydrated = []
    for scenario in payload.valuation_range.scenarios:
        probability = scenario_probabilities.get(scenario.name)
        if probability is None:
            raise ValueError(f"missing ratified probability for valuation_range.scenarios.{scenario.name}.probability")
        hydrated.append(scenario.__class__.model_validate({**scenario.model_dump(), "probability": probability.model_dump()}))
    return ValuationRange.model_validate({**payload.valuation_range.model_dump(), "scenarios": [item.model_dump() for item in hydrated]})


def _ratified_scenario_probabilities(payload: SynthesisPayload) -> dict[str, Ratifiable[float]]:
    decisions_by_path = {
        item.source_field_path: payload.senior_decision_package.decisions.get(item.id)
        for item in payload.senior_review_package.review_items
        if item.source_artifact.endswith("/scenarios.json")
    }
    probabilities: dict[str, Ratifiable[float]] = {}
    for index, scenario in enumerate(payload.scenarios.scenarios):
        if scenario.probability is None:
            raise ValueError(f"missing C-4 probability draft for scenario {scenario.name}")
        field_path = f"ScenarioSetArtifact.scenarios[{index}].probability"
        decision = decisions_by_path.get(field_path)
        if decision is None:
            raise ValueError(f"missing Senior decision for {field_path}")
        final_payload = decision.final if decision.final is not None else scenario.probability.draft
        if not isinstance(final_payload, dict):
            raise ValueError(f"Senior decision for {field_path} must preserve structured probability payload")
        if str(final_payload.get("scenario")) != scenario.name:
            raise ValueError(f"Senior decision for {field_path} scenario mismatch")
        probability_number = final_payload.get("probability")
        if isinstance(probability_number, dict):
            probability_number = Number.model_validate(probability_number)
        if not isinstance(probability_number, Number):
            raise ValueError(f"Senior decision for {field_path} missing Number probability")
        probabilities[scenario.name] = Ratifiable(
            draft=float(probability_number.value),
            evidence=[e.artifact_path or e.source_label for e in scenario.probability.evidence_refs],
            decision=decision.decision,
            decided_by=payload.senior_decision_package.decided_by,
            final=float(probability_number.value),
        )
    return probabilities


def _required_cruxes(payload: SynthesisPayload) -> list[CruxDraft]:
    value = _final_or_draft(payload.edge_cruxes.cruxes) if payload.edge_cruxes.cruxes is not None else None
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("final handoff requires exactly three cruxes")
    return value


def _crux(item: CruxDraft) -> Crux:
    return Crux(
        claim=item.claim,
        metric=item.metric,
        threshold=f"{item.threshold_direction} {item.threshold_value}",
    )


def _catalysts(payload: SynthesisPayload) -> list[dict[str, str]]:
    catalysts = _final_or_draft(payload.edge_cruxes.catalysts)
    if not isinstance(catalysts, list):
        return []
    return [{"event": str(item.get("event", "")), "timing": str(item.get("timing", ""))} for item in catalysts if isinstance(item, dict)]


def _deferred_valuation(payload: SynthesisPayload) -> RouteValuationDeferred:
    if not payload.valuation_deferred:
        raise ValueError("non-DCF handoff requires valuation_deferred")
    values = {scenario.name: scenario.value for scenario in payload.scenarios.scenarios if scenario.value is not None}
    if set(values) != {"bear", "base", "bull"}:
        raise ValueError("deferred valuation requires route-compatible scenario values")
    return RouteValuationDeferred(method=payload.method_directive.method, reason=payload.valuation_deferred, scenario_values=values)


def _thesis(payload: SynthesisPayload) -> str:
    business = str(_final_or_draft(payload.business.business_model_summary))
    moat = str(_final_or_draft(payload.moat.moat_mechanism))
    edge = str(_final_or_draft(payload.edge_cruxes.variant_view))
    return f"{business} {moat} {edge}"


def _revisit_triggers(payload: SynthesisPayload, cruxes: list[Crux]) -> list[str]:
    kill_metric = _final_or_draft(payload.risk.kill_metric)
    triggers = _pass_falsifier_triggers(payload)
    triggers.extend(f"{crux.metric} {crux.threshold}" for crux in cruxes)
    if isinstance(kill_metric, KillMetricDraft):
        triggers.append(f"{kill_metric.metric} {kill_metric.threshold_direction} {kill_metric.threshold_value.value:g}")
    return list(dict.fromkeys(triggers))


def _pass_falsifier_triggers(payload: SynthesisPayload) -> list[str]:
    draft = _final_or_draft(payload.edge_cruxes.cruxes) if payload.edge_cruxes.cruxes is not None else []
    if not isinstance(draft, list):
        return []
    triggers = []
    for item in draft:
        if not isinstance(item, CruxDraft) or item.kind != "pass_falsifier":
            continue
        triggers.append(
            f"pass_falsifier:{item.metric} {item.threshold_direction} {item.threshold_value} by {item.check_by.isoformat()}"
        )
    return triggers


def _data_room(run_dir: str, payload: SynthesisPayload) -> dict[str, str | list[str]]:
    sources = [
        f"{run_dir}/gate_card.json",
        f"{run_dir}/spine.json",
        f"{run_dir}/business.json",
        f"{run_dir}/moat.json",
        f"{run_dir}/capalloc.json",
        f"{run_dir}/scenarios.json",
        f"{run_dir}/edge_cruxes.json",
        f"{run_dir}/risk.json",
        f"{run_dir}/senior_review_package.json",
        f"{run_dir}/senior_decision_package.json",
        f"{run_dir}/conviction.json",
    ]
    if payload.valuation_range is not None:
        sources.append(f"{run_dir}/valuation_range.json")
    if payload.expectations_line is not None:
        sources.append(f"{run_dir}/expectations_line.json")
    return {
        "gate_card": f"{run_dir}/gate_card.json",
        "spine": f"{run_dir}/spine.json",
        "panel": "not implemented in M4b; spine and filed analyst artifacts are used instead",
        "sources": sources,
    }


def _unresolved_ratifiable_paths(value: Any, path: str = "handoff") -> list[str]:
    if isinstance(value, Ratifiable):
        if value.decision is None or not value.decided_by:
            return [path]
        return []
    if isinstance(value, BaseModel):
        paths: list[str] = []
        for field_name in value.__class__.model_fields:
            paths.extend(_unresolved_ratifiable_paths(getattr(value, field_name), f"{path}.{field_name}"))
        return paths
    if isinstance(value, dict):
        paths: list[str] = []
        for key, item in value.items():
            paths.extend(_unresolved_ratifiable_paths(item, f"{path}.{key}"))
        return paths
    if isinstance(value, list | tuple):
        paths: list[str] = []
        for index, item in enumerate(value):
            paths.extend(_unresolved_ratifiable_paths(item, f"{path}[{index}]"))
        return paths
    return []
