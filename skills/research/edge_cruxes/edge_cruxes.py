from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError, model_validator

from skills._primitives import Header, Provenance
from skills.accountant_artifacts import ExpectationsLine, GateCard, MethodDirective, Spine, ValuationRange
from skills.analyst_artifacts import AnalystDraft, EvidenceRef, M3Model
from skills.audit import AuditError, audit_analyst_artifact, audit_artifact
from skills.interfaces import Storage
from skills.research.business.business import BusinessArtifact
from skills.research.capalloc.capalloc import CapAllocArtifact
from skills.research.moat.moat import MoatArtifact
from skills.research.scenarios.scenarios import ScenarioSetArtifact
from skills.serialization import artifact_model_to_payload

FIXTURE_DIR = Path(__file__).parent / "fixtures"
TRIVIAL_COUNTERPARTIES = {
    "no one",
    "no-one",
    "nobody",
    "they are dumb",
    "they're dumb",
    "dumb money",
    "the market is dumb",
}
PLACEHOLDERS = {"todo", "stub", "not implemented", "n/a", "none"}
THRESHOLD_DIRECTIONS = {"at_or_above", "at_or_below", "above", "below", "equals", "improves_or_stable", "worsens_or_below"}


class CruxDraft(M3Model):
    kind: Literal["edge_crux", "pass_falsifier"]
    claim: str
    metric: str
    threshold_direction: Literal["at_or_above", "at_or_below", "above", "below", "equals", "improves_or_stable", "worsens_or_below"]
    threshold_value: str
    check_by: date
    evidence_refs: list[EvidenceRef] = []
    missing_data_gap: str | None = None

    @model_validator(mode="after")
    def validate_crux(self) -> CruxDraft:
        for field_name in ("claim", "metric", "threshold_value"):
            if _is_placeholder(getattr(self, field_name)):
                raise ValueError(f"crux {field_name} is required")
        if not self.evidence_refs and _is_placeholder(self.missing_data_gap):
            raise ValueError("crux requires evidence refs or explicit missing-data gap")
        return self


class EdgeCruxesArtifact(M3Model):
    header: Header
    ticker: str
    as_of: date
    source_artifact_paths: dict[str, str]
    steelman_no_trade: AnalystDraft
    counterparty: AnalystDraft
    structural_mispricing: AnalystDraft
    variant_view: AnalystDraft
    catalysts: AnalystDraft
    cruxes: AnalystDraft | None = None
    source_evidence_summary: dict[str, str]

    @model_validator(mode="before")
    @classmethod
    def rehydrate_nested_drafts(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if isinstance(data.get("cruxes"), dict):
            draft = data["cruxes"].get("draft")
            if isinstance(draft, list):
                data["cruxes"] = {
                    **data["cruxes"],
                    "draft": [
                        item if isinstance(item, CruxDraft) else CruxDraft.model_validate(item)
                        for item in draft
                    ],
                }
        return data

    @model_validator(mode="after")
    def validate_required_content(self) -> EdgeCruxesArtifact:
        required_paths = {
            "business",
            "moat",
            "capalloc",
            "scenarios",
            "gate_card",
            "method_directive",
            "spine",
        }
        missing = sorted(required_paths - set(self.source_artifact_paths))
        if missing:
            raise ValueError(f"edge artifact missing source paths: {', '.join(missing)}")
        for key, value in self.source_evidence_summary.items():
            if _is_placeholder(key) or _is_placeholder(value):
                raise ValueError("edge source evidence summary must be substantive")
        frame = _structural_mispricing_frame(self.structural_mispricing)
        cruxes = [] if self.cruxes is None else self.cruxes.draft
        if not isinstance(cruxes, list):
            raise ValueError("edge cruxes draft must contain a list")
        if frame == "edge" and len(cruxes) != 3:
            raise ValueError("edge artifact requires exactly three edge crux drafts")
        if frame == "no_edge" and self.cruxes is None:
            return self
        for crux in cruxes:
            if not isinstance(crux, CruxDraft):
                raise ValueError("edge cruxes draft must contain CruxDraft records")
            if frame == "edge" and crux.kind != "edge_crux":
                raise ValueError("edge-asserted artifacts require edge_crux records")
            if frame == "no_edge" and crux.kind != "pass_falsifier":
                raise ValueError("no-edge artifacts may only file pass_falsifier records")
        return self


def build_edge_cruxes_artifact(
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
    gate_card_path: str,
    method_directive_path: str,
    spine_path: str,
    valuation_range_path: str | None = None,
    expectations_line_path: str | None = None,
    fixture_dir: Path = FIXTURE_DIR,
) -> EdgeCruxesArtifact:
    source_paths = {
        "business": business_path,
        "moat": moat_path,
        "capalloc": capalloc_path,
        "scenarios": scenarios_path,
        "gate_card": gate_card_path,
        "method_directive": method_directive_path,
        "spine": spine_path,
    }
    if valuation_range_path:
        source_paths["valuation_range"] = valuation_range_path
    if expectations_line_path:
        source_paths["expectations_line"] = expectations_line_path
    _load_and_audit_sources(storage, source_paths)

    fixture = _load_edge_fixture(ticker, fixture_dir=fixture_dir)
    produced_at = datetime.now(timezone.utc)
    crux_records = [_crux_from_fixture(item, source_paths=source_paths, produced_at=produced_at) for item in fixture["cruxes"]]
    crux_evidence = [evidence for crux in crux_records for evidence in crux.evidence_refs]
    if not crux_evidence:
        raise AuditError("edge cruxes require evidence refs")
    return EdgeCruxesArtifact(
        header=Header(schema_version=schema_version, produced_by="C-5", produced_at=produced_at),
        ticker=ticker,
        as_of=as_of,
        source_artifact_paths=source_paths,
        steelman_no_trade=_draft_from_fixture(
            fixture["steelman_no_trade"],
            source_paths=source_paths,
            produced_at=produced_at,
            checklist_area="edge_no_trade_steelman",
            checklist_rationale="Senior must weigh the best no-trade case before accepting any variant view.",
        ),
        counterparty=_draft_from_fixture(
            fixture["counterparty"],
            source_paths=source_paths,
            produced_at=produced_at,
            checklist_area="edge_counterparty",
            checklist_rationale="Senior must judge whether the counterparty explanation is plausible and non-trivial.",
        ),
        structural_mispricing=_draft_from_fixture(
            fixture["structural_mispricing"],
            source_paths=source_paths,
            produced_at=produced_at,
            checklist_area="edge_structural_mispricing",
            checklist_rationale="Senior must decide whether the mispricing mechanism and persistence reason are credible.",
        ),
        variant_view=_draft_from_fixture(
            fixture["variant_view"],
            source_paths=source_paths,
            produced_at=produced_at,
            checklist_area="edge_variant_view",
            checklist_rationale="Senior must decide whether the variant view is differentiated enough to matter.",
        ),
        catalysts=_draft_from_fixture(
            fixture["catalysts"],
            source_paths=source_paths,
            produced_at=produced_at,
            checklist_area="edge_catalysts",
            checklist_rationale="Senior must judge whether the catalysts are observable updates rather than predictions.",
        ),
        cruxes=AnalystDraft(
            draft=crux_records,
            evidence_refs=crux_evidence,
            checklist_area="edge_falsifiable_cruxes",
            checklist_rationale="Senior must ratify that these are the three measurable cruxes that would update the thesis.",
        ),
        source_evidence_summary=fixture["source_evidence_summary"],
    )


def audit_edge_cruxes(artifact: EdgeCruxesArtifact, *, storage: Storage, path: str | None = None) -> None:
    audit_analyst_artifact(artifact, storage=storage)
    _load_and_audit_sources(storage, artifact.source_artifact_paths)
    _audit_steelman(artifact.steelman_no_trade)
    _audit_counterparty(artifact.counterparty)
    _audit_structural_mispricing(artifact.structural_mispricing)
    _audit_variant_view(artifact.variant_view)
    _audit_catalysts(artifact.catalysts)
    frame = _structural_mispricing_frame(artifact.structural_mispricing)
    if frame == "edge":
        if artifact.cruxes is None:
            raise AuditError("edge requires exactly three cruxes")
        _audit_cruxes(artifact.cruxes, storage=storage, expected_kind="edge_crux", exact_count=3)
    else:
        if artifact.cruxes is not None:
            _audit_cruxes(artifact.cruxes, storage=storage, expected_kind="pass_falsifier", exact_count=None)
    if path:
        payload = artifact_model_to_payload(artifact)
        storage.put_json(path, payload)
        if storage.get_json(path) != payload:
            raise AuditError("storage round-trip failed")


def _load_and_audit_sources(storage: Storage, source_paths: dict[str, str]) -> None:
    business = _load_model(storage, source_paths.get("business"), BusinessArtifact, "business")
    moat = _load_model(storage, source_paths.get("moat"), MoatArtifact, "moat")
    capalloc = _load_model(storage, source_paths.get("capalloc"), CapAllocArtifact, "capalloc")
    scenarios = _load_model(storage, source_paths.get("scenarios"), ScenarioSetArtifact, "scenarios")
    gate_card = _load_model(storage, source_paths.get("gate_card"), GateCard, "gate card")
    method_directive = _load_model(storage, source_paths.get("method_directive"), MethodDirective, "method directive")
    spine = _load_model(storage, source_paths.get("spine"), Spine, "spine")
    audit_analyst_artifact(business, storage=storage)
    audit_analyst_artifact(moat, storage=storage)
    audit_analyst_artifact(capalloc, storage=storage)
    if scenarios.header.produced_by != "C-4":
        raise AuditError("edge scenarios reference must resolve to C-4")
    if len(scenarios.scenarios) != 3:
        raise AuditError("edge scenarios reference must contain three scenarios")
    audit_artifact(gate_card)
    audit_artifact(method_directive)
    if spine.header.produced_by != "B-2":
        raise AuditError("edge spine reference must resolve to B-2")
    if not spine.years:
        raise AuditError("edge spine reference missing years")
    if "valuation_range" in source_paths:
        audit_artifact(_load_model(storage, source_paths.get("valuation_range"), ValuationRange, "valuation range"))
    if "expectations_line" in source_paths:
        audit_artifact(_load_model(storage, source_paths.get("expectations_line"), ExpectationsLine, "expectations line"))


def _audit_steelman(draft: AnalystDraft) -> None:
    text = _flatten_text(draft.draft).lower()
    if _is_placeholder(text):
        raise AuditError("steelman_no_trade is empty or placeholder")
    if not any(term in text for term in ("pass", "no-trade", "no trade", "limited room", "risk", "uncertain", "downside", "opportunity", "already assumes")):
        raise AuditError("steelman_no_trade must explain why a rational Senior could pass")
    if any(term in text for term in ("clear buy", "obvious buy", "must buy")):
        raise AuditError("steelman_no_trade cannot be purely bullish")


def _audit_counterparty(draft: AnalystDraft) -> None:
    text = _normalize_text(_flatten_text(draft.draft))
    if _is_placeholder(text) or text in TRIVIAL_COUNTERPARTIES:
        raise AuditError("counterparty is empty or trivial")
    if any(term in text for term in TRIVIAL_COUNTERPARTIES):
        raise AuditError("counterparty is contemptuous or trivial")
    if text in {"the market", "market"} or (text.startswith("the market") and not any(term in text for term in ("because", "holder", "seller", "short", "constraint", "benchmark", "mechanism"))):
        raise AuditError("counterparty cannot be circular market language without mechanism")
    if not any(term in text for term in ("holder", "seller", "short", "constraint", "benchmark", "index", "participant", "buyer", "fund")):
        raise AuditError("counterparty must identify a plausible market participant")
    if "because" not in text and "due to" not in text:
        raise AuditError("counterparty must explain why they may disagree")


def _audit_structural_mispricing(draft: AnalystDraft) -> None:
    value = draft.draft
    if _is_placeholder(value):
        raise AuditError("structural_mispricing is empty or placeholder")
    if isinstance(value, dict):
        asserts_edge = bool(value.get("asserts_edge"))
        no_edge = bool(value.get("no_structural_edge"))
        mechanism = str(value.get("mechanism", "")).strip()
        persistence = str(value.get("persistence_reason", "")).strip()
        if asserts_edge:
            if _is_placeholder(mechanism):
                raise AuditError("structural_mispricing asserts edge without mechanism")
            if _is_placeholder(persistence):
                raise AuditError("structural_mispricing asserts edge without persistence reason")
            return
        if no_edge and not _is_placeholder(value.get("pass_framing")):
            return
        raise AuditError("structural_mispricing must assert evidenced edge or explicit no-edge/pass framing")
    text = _normalize_text(_flatten_text(value))
    if "no structural edge" in text or "fairly priced" in text:
        return
    if "market misunderstands" in text:
        raise AuditError("structural_mispricing generic market misunderstanding lacks mechanism and persistence")
    raise AuditError("structural_mispricing must be structured with mechanism and persistence")


def _audit_variant_view(draft: AnalystDraft) -> None:
    text = _normalize_text(_flatten_text(draft.draft))
    if _is_placeholder(text):
        raise AuditError("variant_view is empty or placeholder")
    if "fairly priced" in text or "pass" in text:
        if not any(term in text for term in ("because", "no edge", "already")):
            raise AuditError("variant_view pass framing must explain why no edge exists")
        return
    if "market misunderstands" in text and not any(term in text for term in ("underweight", "over-index", "misweight", "missing")):
        raise AuditError("variant_view generic market misunderstanding lacks support")
    if not any(term in text for term in ("underweight", "over-index", "misweight", "missing", "variant view")):
        raise AuditError("variant_view must identify what the market may be missing or misweighting")


def _audit_catalysts(draft: AnalystDraft) -> None:
    catalysts = draft.draft
    if not isinstance(catalysts, list) or not catalysts:
        raise AuditError("catalysts require a non-empty list")
    for index, catalyst in enumerate(catalysts):
        if not isinstance(catalyst, dict):
            raise AuditError(f"catalyst {index} must be structured")
        event = str(catalyst.get("event", "")).strip()
        timing = str(catalyst.get("timing", "")).strip()
        text = _normalize_text(" ".join(str(value) for value in catalyst.values()))
        if _is_placeholder(event):
            raise AuditError(f"catalyst {index} missing event")
        if _is_placeholder(timing):
            raise AuditError(f"catalyst {index} missing timing")
        if "market realizes value" in text or text == "market realizes":
            raise AuditError("generic catalyst rejected")


def _audit_cruxes(
    draft: AnalystDraft,
    *,
    storage: Storage,
    expected_kind: Literal["edge_crux", "pass_falsifier"],
    exact_count: int | None,
) -> None:
    cruxes = draft.draft
    if not isinstance(cruxes, list):
        raise AuditError("cruxes draft must be a list")
    if exact_count is not None and len(cruxes) != exact_count:
        raise AuditError("edge requires exactly three cruxes")
    seen: set[tuple[str, str]] = set()
    for index, crux in enumerate(cruxes):
        if not isinstance(crux, CruxDraft):
            raise AuditError(f"crux {index} must be CruxDraft")
        if crux.kind != expected_kind:
            raise AuditError(f"crux {index} kind {crux.kind} invalid for structural framing {expected_kind}")
        if _is_placeholder(crux.claim):
            raise AuditError(f"crux {index} missing claim")
        if _is_placeholder(crux.metric):
            raise AuditError(f"crux {index} missing metric")
        if crux.threshold_direction not in THRESHOLD_DIRECTIONS:
            raise AuditError(f"crux {index} missing threshold direction")
        if _is_placeholder(crux.threshold_value):
            raise AuditError(f"crux {index} missing threshold value")
        if crux.check_by <= date(2000, 1, 1):
            raise AuditError(f"crux {index} missing check-by date")
        if not crux.evidence_refs and _is_placeholder(crux.missing_data_gap):
            raise AuditError(f"crux {index} missing evidence or explicit missing-data gap")
        for evidence in crux.evidence_refs:
            _audit_crux_evidence_ref(evidence, storage=storage, index=index)
        key = (_normalize_text(crux.claim), _normalize_text(crux.metric))
        if key in seen:
            raise AuditError("duplicate crux rejected")
        seen.add(key)


def _audit_crux_evidence_ref(evidence: EvidenceRef, *, storage: Storage, index: int) -> None:
    if _is_placeholder(evidence.source_label):
        raise AuditError(f"crux {index} evidence ref missing source label")
    if _is_placeholder(evidence.excerpt_or_summary):
        raise AuditError(f"crux {index} evidence ref missing excerpt or summary")
    if not evidence.has_resolvable_trace_target:
        raise AuditError(f"crux {index} evidence ref missing resolvable trace target")
    if evidence.artifact_path and evidence.artifact_path.strip():
        try:
            storage.get_json(evidence.artifact_path.strip())
        except Exception as exc:
            raise AuditError(f"crux {index} evidence ref unresolvable: {evidence.artifact_path}") from exc


def _draft_from_fixture(
    payload: dict[str, Any],
    *,
    source_paths: dict[str, str],
    produced_at: datetime,
    checklist_area: str,
    checklist_rationale: str,
) -> AnalystDraft:
    if "draft" not in payload:
        raise ValueError("edge fixture missing draft")
    evidence = _evidence_ref_from_fixture(payload, source_paths=source_paths, produced_at=produced_at)
    return AnalystDraft(
        draft=payload["draft"],
        evidence_refs=[evidence],
        checklist_area=checklist_area,
        checklist_rationale=checklist_rationale,
    )


def _crux_from_fixture(payload: dict[str, Any], *, source_paths: dict[str, str], produced_at: datetime) -> CruxDraft:
    evidence_refs: list[EvidenceRef] = []
    if str(payload.get("evidence_source_key", "")).strip():
        evidence_refs.append(_evidence_ref_from_fixture(payload, source_paths=source_paths, produced_at=produced_at))
    gap = str(payload.get("missing_data_gap", "")).strip() or None
    return CruxDraft(
        kind=payload.get("kind"),
        claim=str(payload.get("claim", "")).strip(),
        metric=str(payload.get("metric", "")).strip(),
        threshold_direction=payload.get("threshold_direction"),
        threshold_value=str(payload.get("threshold_value", "")).strip(),
        check_by=date.fromisoformat(str(payload.get("check_by", "")).strip()),
        evidence_refs=evidence_refs,
        missing_data_gap=gap,
    )


def _evidence_ref_from_fixture(payload: dict[str, Any], *, source_paths: dict[str, str], produced_at: datetime) -> EvidenceRef:
    source_key = str(payload.get("source_key") or payload.get("evidence_source_key") or "").strip()
    artifact_path = source_paths.get(source_key)
    if not artifact_path:
        raise ValueError(f"edge fixture references unknown source key: {source_key}")
    source_label = str(payload.get("source_label") or f"{source_key} artifact").strip()
    summary = str(payload.get("excerpt_or_summary") or payload.get("claim") or "").strip()
    return EvidenceRef(
        source_label=source_label,
        excerpt_or_summary=summary,
        artifact_path=artifact_path,
        external_source_ref=str(payload.get("fixture_ref", "")).strip() or None,
        claimed_period=None,
        provenance=Provenance(
            tag=f"computed:edge_cruxes:{source_key}",
            form="computed",
            period="M3.5",
            accession=None,
            source_name=source_label,
            retrieved_at=produced_at,
        ),
    )


def _load_edge_fixture(ticker: str, *, fixture_dir: Path) -> dict[str, Any]:
    path = fixture_dir / f"{ticker.lower()}_edge_cruxes_evidence.json"
    if not path.is_file():
        raise ValueError(f"missing_edge_cruxes_evidence:{ticker}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "steelman_no_trade",
        "counterparty",
        "structural_mispricing",
        "variant_view",
        "catalysts",
        "cruxes",
        "source_evidence_summary",
    }
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError(f"missing_edge_cruxes_evidence_fields:{','.join(missing)}")
    return raw


def _load_model(storage: Storage, path: str | None, model_type: type[M3Model] | type, label: str):
    if not isinstance(path, str) or not path.strip():
        raise AuditError(f"edge artifact missing {label} reference")
    try:
        return model_type.model_validate(storage.get_json(path.strip()))
    except ValidationError as exc:
        raise AuditError(f"edge {label} reference did not resolve to {model_type.__name__}") from exc


def _structural_mispricing_frame(draft: AnalystDraft) -> Literal["edge", "no_edge"]:
    value = draft.draft
    if isinstance(value, dict):
        if bool(value.get("asserts_edge")):
            return "edge"
        if bool(value.get("no_structural_edge")) and not _is_placeholder(value.get("pass_framing")):
            return "no_edge"
    text = _normalize_text(_flatten_text(value))
    if "no structural edge" in text or "fairly priced" in text:
        return "no_edge"
    return "edge"


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
