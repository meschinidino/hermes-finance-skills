from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError, model_validator

from skills._primitives import Header, Number, Provenance
from skills.accountant_artifacts import ExpectationsLine, GateCard, MethodDirective, Spine, ValuationRange
from skills.analyst_artifacts import AnalystDraft, EvidenceRef, M3Model
from skills.audit import AuditError, audit_analyst_artifact, audit_artifact
from skills.interfaces import Storage
from skills.research.business.business import BusinessArtifact
from skills.research.capalloc.capalloc import CapAllocArtifact
from skills.research.edge_cruxes.edge_cruxes import CruxDraft, EdgeCruxesArtifact, audit_edge_cruxes
from skills.research.moat.moat import MoatArtifact
from skills.research.scenarios.scenarios import ScenarioSetArtifact, audit_scenario_set
from skills.serialization import artifact_model_to_payload

FIXTURE_DIR = Path(__file__).parent / "fixtures"
PLACEHOLDERS = {"todo", "stub", "not implemented", "n/a", "none"}
BEAR_VALUE_RECONCILIATION_TOLERANCE = 1e-9


class ModellableRiskDraft(M3Model):
    risk: str
    impact: Literal["low", "med", "high"]
    likelihood: Literal["low", "med", "high"]
    modeled_effect: str
    evidence_refs: list[EvidenceRef]

    @model_validator(mode="after")
    def validate_modellable_risk(self) -> ModellableRiskDraft:
        if _is_placeholder(self.risk):
            raise ValueError("modellable risk description is required")
        if _is_placeholder(self.modeled_effect):
            raise ValueError("modellable risk modeled effect is required")
        if not self.evidence_refs:
            raise ValueError("modellable risk requires evidence refs")
        return self


class TailRiskDraft(M3Model):
    risk: str
    why_not_modelled: str
    monitoring_signal: str | None = None
    missing_data_gap: str | None = None
    evidence_refs: list[EvidenceRef] = []

    @model_validator(mode="after")
    def validate_tail_risk(self) -> TailRiskDraft:
        if _is_placeholder(self.risk):
            raise ValueError("tail risk description is required")
        if _is_placeholder(self.why_not_modelled):
            raise ValueError("tail risk requires why_not_modelled")
        if _is_placeholder(self.monitoring_signal) and _is_placeholder(self.missing_data_gap):
            raise ValueError("tail risk requires monitoring signal or missing-data gap")
        if not self.evidence_refs and _is_placeholder(self.missing_data_gap):
            raise ValueError("tail risk requires evidence refs or explicit missing-data gap")
        return self


class KillMetricDraft(M3Model):
    metric: str
    threshold_direction: Literal["at_or_above", "at_or_below", "above", "below", "equals", "worsens_or_below"]
    threshold_value: Number
    check_by: date
    thesis_action: str
    evidence_refs: list[EvidenceRef]

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_time_bound(cls, data: Any) -> Any:
        if isinstance(data, dict) and "check_by" not in data and "observation_window" in data:
            data = dict(data)
            data["check_by"] = data.pop("observation_window")
        return data

    @model_validator(mode="after")
    def validate_kill_metric(self) -> KillMetricDraft:
        for field_name in ("metric", "thesis_action"):
            if _is_placeholder(getattr(self, field_name)):
                raise ValueError(f"kill metric {field_name} is required")
        if self.threshold_value is None:
            raise ValueError("kill metric threshold_value is required")
        if not self.evidence_refs:
            raise ValueError("kill metric requires evidence refs")
        return self


class RiskArtifact(M3Model):
    header: Header
    ticker: str
    as_of: date
    source_artifact_paths: dict[str, str]
    premortem: AnalystDraft
    bear_case_narrative: AnalystDraft
    modellable_risks: AnalystDraft
    tail_risks: AnalystDraft
    bear_case_value: Number
    kill_metric: AnalystDraft
    risk_completeness: AnalystDraft
    source_evidence_summary: dict[str, str]

    @model_validator(mode="before")
    @classmethod
    def rehydrate_nested_drafts(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if isinstance(data.get("modellable_risks"), dict):
            draft = data["modellable_risks"].get("draft")
            if isinstance(draft, list):
                data["modellable_risks"] = {
                    **data["modellable_risks"],
                    "draft": [
                        item if isinstance(item, ModellableRiskDraft) else ModellableRiskDraft.model_validate(item)
                        for item in draft
                    ],
                }
        if isinstance(data.get("tail_risks"), dict):
            draft = data["tail_risks"].get("draft")
            if isinstance(draft, list):
                data["tail_risks"] = {
                    **data["tail_risks"],
                    "draft": [
                        item if isinstance(item, TailRiskDraft) else TailRiskDraft.model_validate(item)
                        for item in draft
                    ],
                }
        if isinstance(data.get("kill_metric"), dict):
            draft = data["kill_metric"].get("draft")
            if isinstance(draft, dict):
                data["kill_metric"] = {
                    **data["kill_metric"],
                    "draft": KillMetricDraft.model_validate(draft),
                }
        return data

    @model_validator(mode="after")
    def validate_required_content(self) -> RiskArtifact:
        required_paths = {
            "business",
            "moat",
            "capalloc",
            "scenarios",
            "edge_cruxes",
            "gate_card",
            "method_directive",
            "spine",
        }
        missing = sorted(required_paths - set(self.source_artifact_paths))
        if missing:
            raise ValueError(f"risk artifact missing source paths: {', '.join(missing)}")
        for key, value in self.source_evidence_summary.items():
            if _is_placeholder(key) or _is_placeholder(value):
                raise ValueError("risk source evidence summary must be substantive")
        return self


def build_risk_artifact(
    *,
    ticker: str,
    as_of: date,
    schema_version: str,
    storage: Storage,
    run_dir: str,
    business_path: str,
    moat_path: str,
    capalloc_path: str,
    scenarios_path: str,
    edge_cruxes_path: str,
    gate_card_path: str,
    method_directive_path: str,
    spine_path: str,
    valuation_range_path: str | None = None,
    expectations_line_path: str | None = None,
    fixture_dir: Path = FIXTURE_DIR,
) -> RiskArtifact:
    source_paths = {
        "business": business_path,
        "moat": moat_path,
        "capalloc": capalloc_path,
        "scenarios": scenarios_path,
        "edge_cruxes": edge_cruxes_path,
        "gate_card": gate_card_path,
        "method_directive": method_directive_path,
        "spine": spine_path,
    }
    if valuation_range_path:
        source_paths["valuation_range"] = valuation_range_path
    if expectations_line_path:
        source_paths["expectations_line"] = expectations_line_path
    sources = _load_and_audit_sources(storage, source_paths)

    fixture = _load_risk_fixture(ticker, fixture_dir=fixture_dir)
    produced_at = datetime.now(timezone.utc)
    modellable = [
        _modellable_risk_from_fixture(item, source_paths=source_paths, produced_at=produced_at)
        for item in fixture["modellable_risks"]
    ]
    tail = [_tail_risk_from_fixture(item, source_paths=source_paths, produced_at=produced_at) for item in fixture["tail_risks"]]
    kill_metric = _kill_metric_from_fixture(fixture["kill_metric"], source_paths=source_paths, produced_at=produced_at)
    bear_value = _bear_case_value_from_sources(sources["scenarios"], sources.get("valuation_range"), produced_at=produced_at)

    return RiskArtifact(
        header=Header(schema_version=schema_version, produced_by="C-6", produced_at=produced_at),
        ticker=ticker,
        as_of=as_of,
        source_artifact_paths=source_paths,
        premortem=_draft_from_fixture(
            fixture["premortem"],
            source_paths=source_paths,
            produced_at=produced_at,
            checklist_area="risk_premortem",
            checklist_rationale="Senior must ratify whether the pre-mortem captures the real path to permanent loss.",
        ),
        bear_case_narrative=_draft_from_fixture(
            fixture["bear_case_narrative"],
            source_paths=source_paths,
            produced_at=produced_at,
            checklist_area="risk_bear_case_narrative",
            checklist_rationale="Senior must judge whether the short-seller narrative is credible and evidence-backed.",
        ),
        modellable_risks=AnalystDraft(
            draft=modellable,
            evidence_refs=[evidence for risk in modellable for evidence in risk.evidence_refs],
            checklist_area="risk_modellable_register",
            checklist_rationale="Senior must ratify impact and likelihood for risks that can be scenario-modelled.",
        ),
        tail_risks=AnalystDraft(
            draft=tail,
            evidence_refs=[evidence for risk in tail for evidence in risk.evidence_refs]
            or [
                EvidenceRef(
                    source_label="explicit missing-data gaps",
                    excerpt_or_summary="Tail risks include explicit missing-data gaps where no resolvable source can prove absence.",
                    external_source_ref="missing-data-gap:risk-tail",
                    provenance=Provenance(
                        tag="computed:risk:tail_missing_data_gap",
                        form="computed",
                        period="M3.6",
                        accession=None,
                        source_name="C-6 Risk",
                        retrieved_at=produced_at,
                    ),
                )
            ],
            checklist_area="risk_tail_bucket",
            checklist_rationale="Senior must ratify that non-modelled tail risks are surfaced separately from the matrix.",
        ),
        bear_case_value=bear_value,
        kill_metric=AnalystDraft(
            draft=kill_metric,
            evidence_refs=kill_metric.evidence_refs,
            checklist_area="risk_kill_metric",
            checklist_rationale="Senior must ratify whether this metric would actually kill or materially change the thesis.",
        ),
        risk_completeness=_draft_from_fixture(
            fixture["risk_completeness"],
            source_paths=source_paths,
            produced_at=produced_at,
            checklist_area="risk_completeness",
            checklist_rationale="Senior must decide whether the risk sheet is decision-ready despite stated gaps.",
        ),
        source_evidence_summary=fixture["source_evidence_summary"],
    )


def audit_risk_artifact(artifact: RiskArtifact, *, storage: Storage, path: str | None = None) -> None:
    audit_analyst_artifact(artifact, storage=storage)
    sources = _load_and_audit_sources(storage, artifact.source_artifact_paths)
    _audit_premortem(artifact.premortem)
    _audit_bear_case(artifact.bear_case_narrative)
    _audit_modellable_risks(artifact.modellable_risks, storage=storage)
    _audit_tail_risks(artifact.tail_risks, artifact.modellable_risks, storage=storage)
    _audit_bear_case_value(artifact.bear_case_value, artifact.source_artifact_paths, scenarios=sources["scenarios"])
    _audit_kill_metric(artifact.kill_metric, storage=storage)
    _audit_risk_completeness(artifact.risk_completeness)
    if path:
        payload = artifact_model_to_payload(artifact)
        storage.put_json(path, payload)
        if storage.get_json(path) != payload:
            raise AuditError("storage round-trip failed")


def _load_and_audit_sources(storage: Storage, source_paths: dict[str, str]) -> dict[str, Any]:
    business = _load_model(storage, source_paths.get("business"), BusinessArtifact, "business")
    moat = _load_model(storage, source_paths.get("moat"), MoatArtifact, "moat")
    capalloc = _load_model(storage, source_paths.get("capalloc"), CapAllocArtifact, "capalloc")
    scenarios = _load_scenarios(storage, source_paths.get("scenarios"))
    edge_cruxes = _load_edge_cruxes(storage, source_paths.get("edge_cruxes"))
    gate_card = _load_model(storage, source_paths.get("gate_card"), GateCard, "gate card")
    method_directive = _load_model(storage, source_paths.get("method_directive"), MethodDirective, "method directive")
    spine = _load_model(storage, source_paths.get("spine"), Spine, "spine")
    audit_analyst_artifact(business, storage=storage)
    audit_analyst_artifact(moat, storage=storage)
    audit_analyst_artifact(capalloc, storage=storage)
    audit_scenario_set(scenarios, storage=storage)
    audit_edge_cruxes(edge_cruxes, storage=storage)
    audit_artifact(gate_card)
    audit_artifact(method_directive)
    if spine.header.produced_by != "B-2":
        raise AuditError("risk spine reference must resolve to B-2")
    if not spine.years:
        raise AuditError("risk spine reference missing years")
    sources: dict[str, Any] = {"scenarios": scenarios}
    if "valuation_range" in source_paths:
        valuation = _load_model(storage, source_paths.get("valuation_range"), ValuationRange, "valuation range")
        audit_artifact(valuation)
        sources["valuation_range"] = valuation
    if "expectations_line" in source_paths:
        expectations = _load_model(storage, source_paths.get("expectations_line"), ExpectationsLine, "expectations line")
        audit_artifact(expectations)
        sources["expectations_line"] = expectations
    return sources


def _audit_premortem(draft: AnalystDraft) -> None:
    text = _normalize_text(_flatten_text(draft.draft))
    if _is_placeholder(text):
        raise AuditError("premortem is empty or placeholder")
    if any(term in text for term in ("obvious buy", "clear buy", "cannot lose")):
        raise AuditError("premortem cannot be purely bullish")
    if not any(term in text for term in ("lose", "loss", "downside", "drawdown", "impair", "breaks")):
        raise AuditError("premortem must explain how the investment loses money")
    if not any(term in text for term in ("over", "within", "by", "through", "next", "year", "month")):
        raise AuditError("premortem requires a concrete time horizon")


def _audit_bear_case(draft: AnalystDraft) -> None:
    text = _normalize_text(_flatten_text(draft.draft))
    if _is_placeholder(text):
        raise AuditError("bear case narrative is empty or placeholder")
    if text.count(";") >= 2 or text.count(",") >= 5 and "because" not in text:
        raise AuditError("bear case narrative cannot be a generic downside list")
    if not any(term in text for term in ("bear case", "short seller", "skeptic", "downside")):
        raise AuditError("bear case narrative must be written from a skeptic frame")
    if not any(term in text for term in ("because", "mechanism", "pressure", "compress", "persist", "compound")):
        raise AuditError("bear case narrative requires a central downside mechanism")
    if not any(term in text for term in ("persist", "compound", "multi-year", "several periods", "keeps")):
        raise AuditError("bear case narrative must explain why downside can persist")


def _audit_modellable_risks(draft: AnalystDraft, *, storage: Storage) -> None:
    risks = draft.draft
    if not isinstance(risks, list) or not risks:
        raise AuditError("modellable risk register is empty")
    for index, risk in enumerate(risks):
        if not isinstance(risk, ModellableRiskDraft):
            raise AuditError(f"modellable risk {index} must be ModellableRiskDraft")
        if _is_placeholder(risk.risk):
            raise AuditError(f"modellable risk {index} missing risk")
        if risk.impact not in {"low", "med", "high"}:
            raise AuditError(f"modellable risk {index} missing impact")
        if risk.likelihood not in {"low", "med", "high"}:
            raise AuditError(f"modellable risk {index} missing likelihood")
        if _is_placeholder(risk.modeled_effect):
            raise AuditError(f"modellable risk {index} missing modeled effect")
        if not risk.evidence_refs:
            raise AuditError(f"modellable risk {index} missing evidence")
        for evidence in risk.evidence_refs:
            _audit_nested_evidence_ref(evidence, storage=storage, label=f"modellable risk {index}")


def _audit_tail_risks(tail_draft: AnalystDraft, modellable_draft: AnalystDraft, *, storage: Storage) -> None:
    tail_risks = tail_draft.draft
    modellable_risks = modellable_draft.draft
    if not isinstance(tail_risks, list) or not tail_risks:
        raise AuditError("tail-risk bucket is empty")
    modellable_keys = {_risk_key(risk.risk) for risk in modellable_risks if isinstance(risk, ModellableRiskDraft)}
    seen: set[str] = set()
    for index, risk in enumerate(tail_risks):
        if not isinstance(risk, TailRiskDraft):
            raise AuditError(f"tail risk {index} must be TailRiskDraft")
        if hasattr(risk, "likelihood"):
            raise AuditError(f"tail risk {index} must not carry likelihood")
        key = _risk_key(risk.risk)
        if key in modellable_keys:
            raise AuditError("duplicate risk across modellable and tail buckets")
        if key in seen:
            raise AuditError("duplicate tail risk rejected")
        seen.add(key)
        if _is_placeholder(risk.why_not_modelled):
            raise AuditError(f"tail risk {index} missing why_not_modelled")
        if _is_placeholder(risk.monitoring_signal) and _is_placeholder(risk.missing_data_gap):
            raise AuditError(f"tail risk {index} missing monitoring signal or missing-data gap")
        for evidence in risk.evidence_refs:
            _audit_nested_evidence_ref(evidence, storage=storage, label=f"tail risk {index}")


def _audit_bear_case_value(value: Number, source_paths: dict[str, str], *, scenarios: ScenarioSetArtifact) -> None:
    if not math.isfinite(value.value):
        raise AuditError("bear-case value must be finite")
    if value.unit not in {"USD_per_share", "USD_millions"}:
        raise AuditError("bear-case value uses incompatible unit")
    if value.provenance.form != "computed":
        raise AuditError("bear-case value must be computed from filed valuation inputs")
    derivation = value.derivation or ""
    if "inputs:" not in derivation:
        raise AuditError("bear-case value derivation missing input references")
    if not any(source_paths.get(key, "") in derivation for key in ("scenarios", "valuation_range")):
        raise AuditError("bear-case value disconnected from scenario or valuation evidence")
    scenario_values = _filed_scenario_values(scenarios)
    filed_bear = scenario_values["bear"]
    filed_base = scenario_values["base"]
    if value.unit != filed_bear.unit:
        raise AuditError("bear-case value unit does not match filed C-4 bear scenario")
    if value.unit != filed_base.unit:
        raise AuditError("bear-case value unit does not match filed C-4 base scenario")
    if not value.value < filed_base.value:
        raise AuditError("bear-case value must be below filed C-4 base scenario")
    if not math.isclose(
        value.value,
        filed_bear.value,
        rel_tol=0.0,
        abs_tol=BEAR_VALUE_RECONCILIATION_TOLERANCE,
    ):
        raise AuditError("bear-case value does not reconcile to filed C-4 bear scenario")


def _audit_kill_metric(draft: AnalystDraft, *, storage: Storage) -> None:
    metric = draft.draft
    if not isinstance(metric, KillMetricDraft):
        raise AuditError("kill metric must be KillMetricDraft")
    if _is_placeholder(metric.metric):
        raise AuditError("kill metric missing metric name")
    if metric.threshold_direction not in {"at_or_above", "at_or_below", "above", "below", "equals", "worsens_or_below"}:
        raise AuditError("kill metric missing threshold direction")
    threshold = getattr(metric, "threshold_value", None)
    if not isinstance(threshold, Number):
        raise AuditError("kill metric missing threshold value")
    if not math.isfinite(threshold.value):
        raise AuditError("kill metric threshold value must be finite")
    if getattr(metric, "check_by", None) is None:
        raise AuditError("kill metric missing check_by")
    if _is_placeholder(metric.thesis_action):
        raise AuditError("kill metric missing thesis action")
    if not metric.evidence_refs:
        raise AuditError("kill metric missing evidence")
    for evidence in metric.evidence_refs:
        _audit_nested_evidence_ref(evidence, storage=storage, label="kill metric")


def _audit_risk_completeness(draft: AnalystDraft) -> None:
    text = _normalize_text(_flatten_text(draft.draft))
    if _is_placeholder(text):
        raise AuditError("risk completeness is empty")
    if not any(term in text for term in ("decision-ready", "decision ready", "not decision-ready")):
        raise AuditError("risk completeness must state decision readiness")
    if not any(term in text for term in ("could not verify", "unverified", "missing data", "gap")):
        raise AuditError("risk completeness must identify unverifiable items or gaps")
    if not any(term in text for term in ("raise confidence", "lower confidence", "would raise", "would lower")):
        raise AuditError("risk completeness must state what would change confidence")
    if draft.final is not None or draft.decision is not None or draft.decided_by is not None:
        raise AuditError("risk completeness must remain undecided before M3.7")


def _draft_from_fixture(
    payload: dict[str, Any],
    *,
    source_paths: dict[str, str],
    produced_at: datetime,
    checklist_area: str,
    checklist_rationale: str,
) -> AnalystDraft:
    if "draft" not in payload:
        raise ValueError("risk fixture missing draft")
    evidence = _evidence_ref_from_fixture(payload, source_paths=source_paths, produced_at=produced_at)
    return AnalystDraft(
        draft=payload["draft"],
        evidence_refs=[evidence],
        checklist_area=checklist_area,
        checklist_rationale=checklist_rationale,
    )


def _modellable_risk_from_fixture(payload: dict[str, Any], *, source_paths: dict[str, str], produced_at: datetime) -> ModellableRiskDraft:
    return ModellableRiskDraft(
        risk=str(payload.get("risk", "")).strip(),
        impact=payload.get("impact"),
        likelihood=payload.get("likelihood"),
        modeled_effect=str(payload.get("modeled_effect", "")).strip(),
        evidence_refs=[_evidence_ref_from_fixture(payload, source_paths=source_paths, produced_at=produced_at)],
    )


def _tail_risk_from_fixture(payload: dict[str, Any], *, source_paths: dict[str, str], produced_at: datetime) -> TailRiskDraft:
    evidence_refs: list[EvidenceRef] = []
    if str(payload.get("source_key", "")).strip():
        evidence_refs.append(_evidence_ref_from_fixture(payload, source_paths=source_paths, produced_at=produced_at))
    return TailRiskDraft(
        risk=str(payload.get("risk", "")).strip(),
        why_not_modelled=str(payload.get("why_not_modelled", "")).strip(),
        monitoring_signal=str(payload.get("monitoring_signal", "")).strip() or None,
        missing_data_gap=str(payload.get("missing_data_gap", "")).strip() or None,
        evidence_refs=evidence_refs,
    )


def _kill_metric_from_fixture(payload: dict[str, Any], *, source_paths: dict[str, str], produced_at: datetime) -> KillMetricDraft:
    return KillMetricDraft(
        metric=str(payload.get("metric", "")).strip(),
        threshold_direction=payload.get("threshold_direction"),
        threshold_value=Number(
            value=float(payload["threshold_value"]),
            unit=payload["threshold_unit"],
            kind="estimate",
            provenance=Provenance(
                tag="computed:risk:kill_metric_threshold",
                form="computed",
                period=str(payload.get("threshold_period", "M3.6")),
                accession=None,
                source_name="C-6 Risk fixture",
                retrieved_at=produced_at,
            ),
            derivation=f"inputs: {source_paths[payload['source_key']]}; threshold set from filed thesis-risk evidence.",
        ),
        check_by=date.fromisoformat(str(payload.get("check_by", "")).strip()),
        thesis_action=str(payload.get("thesis_action", "")).strip(),
        evidence_refs=[_evidence_ref_from_fixture(payload, source_paths=source_paths, produced_at=produced_at)],
    )


def _bear_case_value_from_sources(
    scenarios: ScenarioSetArtifact,
    valuation: ValuationRange | None,
    *,
    produced_at: datetime,
) -> Number:
    bear = next((scenario for scenario in scenarios.scenarios if scenario.name == "bear"), None)
    if bear is None or bear.value is None:
        raise AuditError("risk requires a bear scenario value")
    inputs = [scenarios.valuation_range_path or "C-4 scenarios"]
    if valuation is not None:
        inputs.append("B-3 valuation_range")
    return Number(
        value=bear.value.value,
        unit=bear.value.unit,
        kind="estimate",
        provenance=Provenance(
            tag="computed:risk:bear_case_value",
            form="computed",
            period=bear.value.provenance.period,
            accession=None,
            source_name="C-4 Scenario Set",
            retrieved_at=produced_at,
        ),
        derivation=f"inputs: {', '.join(inputs)}; C-6 bear-case value adopts the filed C-4 bear scenario value.",
    )


def _filed_scenario_values(scenarios: ScenarioSetArtifact) -> dict[str, Number]:
    values: dict[str, Number] = {}
    for scenario in scenarios.scenarios:
        if scenario.value is not None:
            values[scenario.name] = scenario.value
    missing = sorted({"bear", "base"} - set(values))
    if missing:
        raise AuditError(f"risk scenarios source missing required values: {', '.join(missing)}")
    return values


def _evidence_ref_from_fixture(payload: dict[str, Any], *, source_paths: dict[str, str], produced_at: datetime) -> EvidenceRef:
    source_key = str(payload.get("source_key") or "").strip()
    artifact_path = source_paths.get(source_key)
    if not artifact_path:
        raise ValueError(f"risk fixture references unknown source key: {source_key}")
    source_label = str(payload.get("source_label") or f"{source_key} artifact").strip()
    summary = str(payload.get("excerpt_or_summary") or payload.get("risk") or payload.get("draft") or "").strip()
    return EvidenceRef(
        source_label=source_label,
        excerpt_or_summary=summary,
        artifact_path=artifact_path,
        external_source_ref=str(payload.get("fixture_ref", "")).strip() or None,
        claimed_period=None,
        provenance=Provenance(
            tag=f"computed:risk:{source_key}",
            form="computed",
            period="M3.6",
            accession=None,
            source_name=source_label,
            retrieved_at=produced_at,
        ),
    )


def _audit_nested_evidence_ref(evidence: EvidenceRef, *, storage: Storage, label: str) -> None:
    if _is_placeholder(evidence.source_label):
        raise AuditError(f"{label} evidence ref missing source label")
    if _is_placeholder(evidence.excerpt_or_summary):
        raise AuditError(f"{label} evidence ref missing excerpt or summary")
    if not evidence.has_resolvable_trace_target:
        raise AuditError(f"{label} evidence ref missing resolvable trace target")
    if evidence.artifact_path and evidence.artifact_path.strip():
        try:
            storage.get_json(evidence.artifact_path.strip())
        except Exception as exc:
            raise AuditError(f"{label} evidence ref unresolvable: {evidence.artifact_path}") from exc


def _load_risk_fixture(ticker: str, *, fixture_dir: Path) -> dict[str, Any]:
    path = fixture_dir / f"{ticker.lower()}_risk_evidence.json"
    if not path.is_file():
        raise ValueError(f"missing_risk_evidence:{ticker}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "premortem",
        "bear_case_narrative",
        "modellable_risks",
        "tail_risks",
        "kill_metric",
        "risk_completeness",
        "source_evidence_summary",
    }
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError(f"missing_risk_evidence_fields:{','.join(missing)}")
    return raw


def _load_model(storage: Storage, path: str | None, model_type: type[M3Model] | type, label: str):
    if not isinstance(path, str) or not path.strip():
        raise AuditError(f"risk artifact missing {label} reference")
    try:
        return model_type.model_validate(storage.get_json(path.strip()))
    except ValidationError as exc:
        raise AuditError(f"risk {label} reference did not resolve to {model_type.__name__}") from exc


def _load_edge_cruxes(storage: Storage, path: str | None) -> EdgeCruxesArtifact:
    if not isinstance(path, str) or not path.strip():
        raise AuditError("risk artifact missing edge cruxes reference")
    try:
        payload = storage.get_json(path.strip())
        if isinstance(payload.get("cruxes"), dict) and isinstance(payload["cruxes"].get("draft"), list):
            payload = {
                **payload,
                "cruxes": {
                    **payload["cruxes"],
                    "draft": [
                        item if isinstance(item, CruxDraft) else CruxDraft.model_validate(item)
                        for item in payload["cruxes"]["draft"]
                    ],
                },
            }
        return EdgeCruxesArtifact.model_validate(payload)
    except ValidationError as exc:
        raise AuditError("risk edge cruxes reference did not resolve to EdgeCruxesArtifact") from exc


def _load_scenarios(storage: Storage, path: str | None) -> ScenarioSetArtifact:
    if not isinstance(path, str) or not path.strip():
        raise AuditError("risk artifact missing scenarios reference")
    try:
        payload = storage.get_json(path.strip())
        if isinstance(payload.get("scenarios"), list):
            scenarios = []
            for scenario in payload["scenarios"]:
                if (
                    isinstance(scenario, dict)
                    and isinstance(scenario.get("probability"), dict)
                    and isinstance(scenario["probability"].get("draft"), dict)
                    and isinstance(scenario["probability"]["draft"].get("probability"), dict)
                ):
                    probability = scenario["probability"]
                    draft = probability["draft"]
                    scenario = {
                        **scenario,
                        "probability": {
                            **probability,
                            "draft": {
                                **draft,
                                "probability": Number.model_validate(draft["probability"]),
                            },
                        },
                    }
                scenarios.append(scenario)
            payload = {**payload, "scenarios": scenarios}
        return ScenarioSetArtifact.model_validate(payload)
    except ValidationError as exc:
        raise AuditError("risk scenarios reference did not resolve to ScenarioSetArtifact") from exc
    except Exception as exc:
        raise AuditError("risk scenarios reference did not resolve to ScenarioSetArtifact") from exc


def _risk_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


def _is_placeholder(value: Any) -> bool:
    text = _normalize_text(_flatten_text(value))
    return not text or text in PLACEHOLDERS


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list | tuple):
        return " ".join(_flatten_text(item) for item in value)
    return str(value or "")


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())
