from __future__ import annotations

import math
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from skills._primitives import Number
from skills.accountant_artifacts import BaseRateResult, ExpectationsLine, GateCard, MethodDirective, Spine, ValuationRange, iter_numbers
from skills.analyst_artifacts import AnalystDraft, EvidenceRef, ReviewItem, SeniorDecisionPackage, SeniorReviewPackage
from skills.interfaces import Storage
from skills.serialization import artifact_model_to_payload


class AuditError(ValueError):
    pass


def audit_m1_handoff(handoff: BaseModel, *, storage: Storage | None = None, path: str | None = None) -> None:
    numbers = iter_numbers(handoff)
    if not numbers:
        raise AuditError("no numbers found")

    for number in numbers:
        _audit_number(number)

    spine = _find_spine(handoff)
    _audit_spine(spine)

    if storage and path:
        payload = artifact_model_to_payload(handoff)
        storage.put_json(path, payload)
        reloaded = storage.get_json(path)
        if reloaded != payload:
            raise AuditError("storage round-trip failed")


def audit_artifact(artifact: BaseModel, *, storage: Storage | None = None, path: str | None = None) -> None:
    numbers = iter_numbers(artifact)
    if not numbers:
        raise AuditError("artifact has no numbers")
    for number in numbers:
        _audit_number(number, require_input_refs=True)
    if isinstance(artifact, ValuationRange):
        _audit_valuation_range(artifact)
    if isinstance(artifact, ExpectationsLine):
        _audit_expectations_line(artifact)
    if isinstance(artifact, GateCard):
        _audit_gate_card(artifact)
    if isinstance(artifact, BaseRateResult):
        _audit_base_rate(artifact)
    if isinstance(artifact, MethodDirective):
        _audit_method_directive(artifact)
    if storage and path:
        payload = artifact_model_to_payload(artifact)
        storage.put_json(path, payload)
        if storage.get_json(path) != payload:
            raise AuditError("storage round-trip failed")


def audit_analyst_artifact(artifact: BaseModel, *, storage: Storage | None = None, path: str | None = None) -> None:
    drafts = _iter_m3_values(artifact, AnalystDraft)
    if not drafts:
        raise AuditError("analyst artifact has no ratifiable drafts")
    for draft in drafts:
        _audit_analyst_draft(draft)
    _audit_m3_3_period_consistency(drafts, storage=storage)
    if artifact.__class__.__name__ == "MoatArtifact":
        _audit_metric_only_moat(artifact)
    for number in iter_numbers(artifact):
        _audit_number(number, require_input_refs=True)
    if storage and path:
        payload = artifact_model_to_payload(artifact)
        storage.put_json(path, payload)
        if storage.get_json(path) != payload:
            raise AuditError("storage round-trip failed")


def audit_senior_review_package(package: SeniorReviewPackage, *, storage: Storage | None = None, path: str | None = None) -> None:
    if not package.review_items:
        raise AuditError("senior review package requires review items")
    for item in package.review_items:
        _audit_review_item(item)
    if storage and path:
        payload = artifact_model_to_payload(package)
        storage.put_json(path, payload)
        if storage.get_json(path) != payload:
            raise AuditError("storage round-trip failed")


def audit_senior_decision_package(package: SeniorDecisionPackage, *, storage: Storage | None = None, path: str | None = None) -> None:
    if not package.is_complete:
        raise AuditError("senior decision package missing required decisions")
    for item_id, decision in package.decisions.items():
        _audit_no_bare_numeric_payload(decision.final, f"decisions.{item_id}.final")
    if storage and path:
        payload = artifact_model_to_payload(package)
        storage.put_json(path, payload)
        if storage.get_json(path) != payload:
            raise AuditError("storage round-trip failed")


def _audit_number(number: Number, *, require_input_refs: bool = False) -> None:
    if number.provenance is None:
        raise AuditError("number missing provenance")
    if number.kind == "fact" and number.provenance.form not in {"10-K", "10-Q", "DEF 14A", "Form 4"}:
        raise AuditError("fact must trace to accepted filing form")
    if number.kind != "fact" and not number.derivation:
        raise AuditError("estimate missing derivation")
    if require_input_refs and number.provenance.form == "computed" and "inputs:" not in (number.derivation or ""):
        raise AuditError("computed estimate derivation missing input references")
    if not math.isfinite(number.value):
        raise AuditError("number must be finite")


def _audit_analyst_draft(draft: AnalystDraft) -> None:
    if not draft.needs_ratification:
        raise AuditError("analyst drafts must need ratification")
    if not draft.evidence_refs:
        raise AuditError("analyst draft missing evidence refs")
    for evidence in draft.evidence_refs:
        _audit_evidence_ref(evidence)
    _audit_no_bare_numeric_payload(draft.draft, "AnalystDraft.draft")
    _audit_no_bare_numeric_payload(draft.final, "AnalystDraft.final")
    if draft.final is not None and (draft.decision is None or not draft.decided_by):
        raise AuditError("analyst draft asserts a final value without Senior decision")


def _audit_review_item(item: ReviewItem) -> None:
    if not item.evidence_refs:
        raise AuditError("review item missing evidence refs")
    for evidence in item.evidence_refs:
        _audit_evidence_ref(evidence)
    _audit_no_bare_numeric_payload(item.draft, f"{item.source_field_path}.draft")
    _audit_no_bare_numeric_payload(item.final, f"{item.source_field_path}.final")
    if item.final is not None and (item.decision is None or not item.decided_by):
        raise AuditError("review item asserts a final value without Senior decision")


def _audit_evidence_ref(evidence: EvidenceRef) -> None:
    if not evidence.source_label.strip():
        raise AuditError("evidence ref missing source label")
    if not evidence.excerpt_or_summary.strip():
        raise AuditError("evidence ref missing excerpt or summary")
    if not evidence.has_resolvable_trace_target:
        raise AuditError("evidence ref missing resolvable trace target")


def _audit_m3_3_period_consistency(drafts: list[AnalystDraft], *, storage: Storage | None) -> None:
    for draft in drafts:
        period_specific = _contains_period_specific_claim(draft.draft)
        for evidence in draft.evidence_refs:
            claimed_period = evidence.claimed_period.strip() if evidence.claimed_period else None
            if period_specific and not claimed_period:
                raise AuditError("period-specific claim missing claimed period")
            if not claimed_period:
                continue
            resolved_period = _resolve_evidence_period(evidence, storage=storage)
            if claimed_period and resolved_period and claimed_period != resolved_period:
                raise AuditError(f"period mismatch: claimed {claimed_period} resolved {resolved_period}")


def _resolve_evidence_period(evidence: EvidenceRef, *, storage: Storage | None) -> str:
    if storage is None:
        raise AuditError("unresolvable-source: storage required for period consistency")
    if not evidence.artifact_path or not evidence.artifact_path.strip():
        raise AuditError("unresolvable-source: evidence ref missing artifact path")
    try:
        payload = storage.get_json(evidence.artifact_path.strip())
    except Exception as exc:
        raise AuditError(f"unresolvable-source: {evidence.artifact_path}") from exc
    resolved_period = _period_from_stored_artifact(payload)
    if not resolved_period:
        raise AuditError(f"unresolvable-source: stored artifact missing period: {evidence.artifact_path}")
    return resolved_period


def _period_from_stored_artifact(payload: dict[str, Any]) -> str | None:
    direct_period = payload.get("period")
    if isinstance(direct_period, str) and direct_period.strip():
        return direct_period.strip()
    header = payload.get("header")
    if isinstance(header, dict):
        header_period = header.get("period")
        if isinstance(header_period, str) and header_period.strip():
            return header_period.strip()
    years = payload.get("years")
    if isinstance(years, list) and years and isinstance(years[-1], str) and years[-1].strip():
        return years[-1].strip()
    return None


def _contains_period_specific_claim(value: Any) -> bool:
    text = _flatten_text(value)
    return bool(re.search(r"\b(?:FY20\d{2}|Q[1-4][ -]?20\d{2})\b", text))


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list | tuple):
        return " ".join(_flatten_text(item) for item in value)
    return ""


def _audit_metric_only_moat(artifact: BaseModel) -> None:
    mechanism = getattr(artifact, "moat_mechanism", None)
    if not isinstance(mechanism, AnalystDraft):
        raise AuditError("moat artifact missing moat mechanism draft")
    draft = mechanism.draft
    if not isinstance(draft, dict):
        raise AuditError("moat mechanism draft must expose support categories")
    support_categories = {str(item).strip() for item in draft.get("support_categories", [])}
    mechanism_category = str(draft.get("mechanism_category", "")).strip()
    claim = _flatten_text(draft).lower()
    forward_categories = {
        "switching_costs",
        "network_effects",
        "scale_advantage",
        "cost_advantage",
        "intangible_assets",
        "regulatory_position",
        "distribution_advantage",
        "forward_mechanism",
    }
    historical_categories = {
        "historical_economics",
        "roic_spread",
        "wacc_spread",
        "margin_history",
        "returns_above_cost_of_capital",
    }
    has_forward_support = bool(support_categories & forward_categories) and bool(mechanism_category)
    if not has_forward_support:
        raise AuditError("moat durability claim requires evidenced forward-looking mechanism")
    if support_categories and support_categories <= historical_categories:
        raise AuditError("metric-only moat durability claim rejected")
    asserts_durability = any(term in claim for term in ("durable", "durability", "moat", "protect", "proves"))
    if asserts_durability and not has_forward_support:
        raise AuditError("metric-only moat durability claim rejected")


def _audit_no_bare_numeric_payload(value: Any, path: str) -> None:
    if isinstance(value, Number):
        return
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, int | float):
        raise AuditError(f"{path} contains bare numeric value")
    if isinstance(value, dict):
        if _is_serialized_number(value):
            return
        for key, item in value.items():
            _audit_no_bare_numeric_payload(item, f"{path}.{key}")
        return
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _audit_no_bare_numeric_payload(item, f"{path}[{index}]")


def _is_serialized_number(value: dict[str, Any]) -> bool:
    try:
        Number.model_validate(value)
    except ValidationError:
        return False
    return True


def _iter_m3_values(value: Any, target_type: type) -> list[Any]:
    matches: list[Any] = []
    if isinstance(value, target_type):
        return [value]
    if isinstance(value, BaseModel):
        for field_name in value.__class__.model_fields:
            matches.extend(_iter_m3_values(getattr(value, field_name), target_type))
        return matches
    if isinstance(value, dict):
        for item in value.values():
            matches.extend(_iter_m3_values(item, target_type))
        return matches
    if isinstance(value, list | tuple):
        for item in value:
            matches.extend(_iter_m3_values(item, target_type))
    return matches


def _find_spine(value: Any) -> Spine:
    if isinstance(value, Spine):
        return value
    if isinstance(value, BaseModel):
        for item in value.__dict__.values():
            try:
                return _find_spine(item)
            except AuditError:
                pass
    if isinstance(value, dict):
        for item in value.values():
            try:
                return _find_spine(item)
            except AuditError:
                pass
    raise AuditError("handoff missing spine")


def _audit_spine(spine: Spine) -> None:
    for year, ic, roic, wacc, margin, turnover in zip(
        spine.years,
        spine.invested_capital_incl_gw,
        spine.roic_incl_gw,
        spine.wacc,
        spine.nopat_margin,
        spine.capital_turnover,
        strict=True,
    ):
        if ic.value <= 0:
            raise AuditError(f"{year} invested capital must be positive")
        if not 0 < wacc.value < 0.30:
            raise AuditError(f"{year} WACC out of bounds")
        if abs(roic.value) >= 2.0:
            raise AuditError(f"{year} ROIC out of bounds")
        if abs((margin.value * turnover.value) - roic.value) > 0.000001:
            raise AuditError(f"{year} margin-turnover reconciliation failed")


def _audit_valuation_range(valuation: ValuationRange) -> None:
    if len(valuation.scenarios) != 3:
        raise AuditError("valuation range requires exactly three scenarios")
    if [scenario.name for scenario in valuation.scenarios] != ["bear", "base", "bull"]:
        raise AuditError("valuation range requires bear/base/bull scenarios")
    for scenario in valuation.scenarios:
        if scenario.probability.decision is not None:
            raise AuditError("M2a probabilities must remain unratified")


def _audit_expectations_line(expectations: ExpectationsLine) -> None:
    low = expectations.wacc_band["low"].value
    high = expectations.wacc_band["high"].value
    if low >= high:
        raise AuditError("WACC band low must be below high")
    if not 0 < low < 0.30 or not 0 < high < 0.30:
        raise AuditError("WACC band out of bounds")
    for edge, result in expectations.reverse_band_results.items():
        if edge not in {"low", "high"}:
            raise AuditError("unexpected reverse DCF edge")
        if not result.converged and result.implied_revenue_growth is not None:
            raise AuditError("non-converged reverse DCF must not force an implied point")


def _audit_gate_card(gate: GateCard) -> None:
    if gate.header.produced_by != "B-4":
        raise AuditError("gate card must be produced by B-4")
    if not gate.altman.variant:
        raise AuditError("gate card missing Altman variant")
    if gate.beneish.flag and not any("Beneish" in item for item in gate.dig_items):
        raise AuditError("lit Beneish screen must add scrutiny dig item")
    if gate.verdict.decision is not None:
        raise AuditError("M2b screen verdict placeholder must remain unratified")
    if gate.kill_reason is not None:
        raise AuditError("M2b screens must not auto-kill")


def _audit_base_rate(result: BaseRateResult) -> None:
    if result.header.produced_by != "B-5":
        raise AuditError("base-rate result must be produced by B-5")
    if not result.reference_class or not result.citation:
        raise AuditError("base-rate result requires reference class citation")
    if not 0 <= result.probability.value <= 1:
        raise AuditError("base-rate probability out of bounds")


def _audit_method_directive(directive: MethodDirective) -> None:
    if directive.header.produced_by != "B-6":
        raise AuditError("method directive must be produced by B-6")
    if not directive.indicators:
        raise AuditError("method directive requires sourced indicators")
    if directive.asset_class == "optionality" and directive.method == "DCF":
        raise AuditError("optionality/pre-revenue names must route away from DCF")
    if directive.implemented != (directive.method == "DCF"):
        raise AuditError("M2b implements only DCF valuation")
