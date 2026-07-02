from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from skills._primitives import Header, Provenance, Ratifiable
from skills.interfaces import Senior
from skills.serialization import artifact_model_to_payload


class M3Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)


DecisionState = Literal["ratified", "overturned"]
RatificationOutcome = Literal["ratified_as_is", "modified", "rejected"]


class EvidenceRef(M3Model):
    source_label: str
    excerpt_or_summary: str
    artifact_path: str | None = None
    filing_reference: str | None = None
    external_source_ref: str | None = None
    claimed_period: str | None = None
    provenance: Provenance | None = None

    @property
    def trace_targets(self) -> tuple[str | None, str | None, str | None]:
        return (self.artifact_path, self.filing_reference, self.external_source_ref)

    @property
    def has_resolvable_trace_target(self) -> bool:
        return any(isinstance(target, str) and bool(target.strip()) for target in self.trace_targets)


class AnalystDraft(M3Model):
    draft: Any
    evidence_refs: list[EvidenceRef]
    checklist_area: str
    checklist_rationale: str
    required: bool = True
    needs_ratification: bool = True
    decision: DecisionState | None = None
    decided_by: str | None = None
    final: Any | None = None

    @model_validator(mode="after")
    def validate_draft(self) -> AnalystDraft:
        if not self.needs_ratification:
            raise ValueError("analyst drafts must need ratification")
        if not self.evidence_refs:
            raise ValueError("analyst drafts require evidence refs")
        if self.final is not None and (self.decision is None or not self.decided_by):
            raise ValueError("final analyst values require Senior decision metadata")
        return self


class ReviewItem(M3Model):
    id: str
    source_artifact: str
    source_field_path: str
    draft: Any
    evidence_refs: list[EvidenceRef]
    checklist_area: str
    checklist_rationale: str
    required: bool = True
    decision: DecisionState | None = None
    decided_by: str | None = None
    final: Any | None = None

    @property
    def is_ratified(self) -> bool:
        return (not self.required) or self.decision is not None

    @model_validator(mode="after")
    def validate_item(self) -> ReviewItem:
        if not self.id:
            raise ValueError("review item requires stable id")
        if not self.source_artifact or not self.source_field_path:
            raise ValueError("review item requires source artifact and field path")
        if not self.evidence_refs:
            raise ValueError("review item requires evidence refs")
        if self.final is not None and (self.decision is None or not self.decided_by):
            raise ValueError("final review values require Senior decision metadata")
        return self


class SeniorReviewPackage(M3Model):
    header: Header
    ticker: str
    as_of: date
    review_items: list[ReviewItem]
    source_artifact_summary: dict[str, str]

    @property
    def is_ratified(self) -> bool:
        return all(item.is_ratified for item in self.review_items if item.required)

    @model_validator(mode="after")
    def validate_package(self) -> SeniorReviewPackage:
        if not self.review_items:
            raise ValueError("senior review package requires review items")
        return self


class ReviewSourceManifest(M3Model):
    method: str = "unspecified"
    required_sources: tuple[str, ...]
    required_context_sources: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_manifest(self) -> ReviewSourceManifest:
        if not self.required_sources:
            raise ValueError("review source manifest requires sources")
        if any(not source.strip() for source in (*self.required_sources, *self.required_context_sources)):
            raise ValueError("review source manifest sources must be non-empty")
        all_sources = (*self.required_sources, *self.required_context_sources)
        if len(set(all_sources)) != len(all_sources):
            raise ValueError("review source manifest sources must be unique")
        return self


class SeniorDecision(M3Model):
    decision: DecisionState
    final: Any | None = None
    rationale: str


class RatificationSummary(M3Model):
    required_count: int
    ratified_as_is_count: int
    modified_count: int
    rejected_count: int
    ratified_as_is_rate: float

    @model_validator(mode="after")
    def validate_summary(self) -> RatificationSummary:
        if self.required_count < 0:
            raise ValueError("ratification summary required_count cannot be negative")
        counts_total = self.ratified_as_is_count + self.modified_count + self.rejected_count
        if counts_total != self.required_count:
            raise ValueError("ratification summary counts must equal required_count")
        expected_rate = 0.0 if self.required_count == 0 else self.ratified_as_is_count / self.required_count
        if abs(self.ratified_as_is_rate - expected_rate) > 0.000001:
            raise ValueError("ratification summary rate does not match counts")
        return self


class SeniorDecisionPackage(M3Model):
    header: Header
    ticker: str
    as_of: date
    decided_by: str
    required_item_ids: list[str]
    decisions: dict[str, SeniorDecision]
    outcomes: dict[str, RatificationOutcome]
    ratification_summary: RatificationSummary

    @property
    def is_complete(self) -> bool:
        return set(self.required_item_ids).issubset(self.decisions)

    @model_validator(mode="before")
    @classmethod
    def fill_ratification_outcomes(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "decisions" not in data:
            return data
        required_item_ids = [str(item_id) for item_id in data.get("required_item_ids", [])]
        decisions_payload = data.get("decisions") or {}
        if not isinstance(decisions_payload, dict):
            return data
        outcomes = data.get("outcomes")
        if not isinstance(outcomes, dict):
            outcomes = {
                str(item_id): _outcome_for_decision_payload(decision_payload)
                for item_id, decision_payload in decisions_payload.items()
            }
            data = {**data, "outcomes": outcomes}
        if "ratification_summary" not in data:
            summary_item_ids = [item_id for item_id in required_item_ids if item_id in outcomes]
            data = {
                **data,
                "ratification_summary": _ratification_summary_payload(
                    required_item_ids=summary_item_ids,
                    outcomes={str(key): value for key, value in outcomes.items()},
                ),
            }
        return data

    @model_validator(mode="after")
    def validate_decisions(self) -> SeniorDecisionPackage:
        if not self.decided_by:
            raise ValueError("senior decision package requires decided_by")
        missing = sorted(set(self.required_item_ids) - set(self.decisions))
        if missing:
            raise ValueError(f"senior decisions missing required item ids: {', '.join(missing)}")
        missing_outcomes = sorted(set(self.required_item_ids) - set(self.outcomes))
        if missing_outcomes:
            raise ValueError(f"senior outcomes missing required item ids: {', '.join(missing_outcomes)}")
        expected_summary = RatificationSummary.model_validate(
            _ratification_summary_payload(
                required_item_ids=self.required_item_ids,
                outcomes=self.outcomes,
            )
        )
        if self.ratification_summary != expected_summary:
            raise ValueError("senior ratification summary does not match outcomes")
        return self


def collect_ratifiables(
    artifact: BaseModel,
    *,
    ticker: str,
    as_of: date,
    header: Header,
    source_artifact: str | None = None,
) -> SeniorReviewPackage:
    artifact_name = source_artifact or artifact.__class__.__name__
    items = [
        _review_item_for_draft(artifact_name, field_path, draft)
        for field_path, draft in _iter_analyst_drafts(artifact, artifact.__class__.__name__)
    ]
    return SeniorReviewPackage(
        header=header,
        ticker=ticker,
        as_of=as_of,
        review_items=items,
        source_artifact_summary={artifact_name: artifact.__class__.__name__},
    )


def collect_accountant_ratifiables(
    artifact: BaseModel,
    *,
    ticker: str,
    as_of: date,
    header: Header,
    source_artifact: str | None = None,
) -> SeniorReviewPackage:
    artifact_name = source_artifact or artifact.__class__.__name__
    items = [
        _review_item_for_ratifiable(artifact_name, field_path, ratifiable)
        for field_path, ratifiable in _iter_primitive_ratifiables(artifact, artifact.__class__.__name__)
    ]
    return SeniorReviewPackage(
        header=header,
        ticker=ticker,
        as_of=as_of,
        review_items=items,
        source_artifact_summary={artifact_name: artifact.__class__.__name__},
    )


def consolidate_review_packages(
    packages: list[SeniorReviewPackage],
    *,
    ticker: str,
    as_of: date,
    header: Header,
    manifest: ReviewSourceManifest | Sequence[str] | None = None,
    context_sources: dict[str, str] | None = None,
) -> SeniorReviewPackage:
    if not packages:
        raise ValueError("consolidated review package requires source packages")
    review_items: list[ReviewItem] = []
    source_summary: dict[str, str] = {}
    seen: set[str] = set()
    for package in packages:
        if package.ticker != ticker or package.as_of != as_of:
            raise ValueError("cannot consolidate review packages across ticker or as_of")
        for item in package.review_items:
            if item.id in seen:
                raise ValueError(f"duplicate review item id: {item.id}")
            seen.add(item.id)
            review_items.append(item)
        source_summary.update(package.source_artifact_summary)
    source_summary.update(context_sources or {})
    package = SeniorReviewPackage(
        header=header,
        ticker=ticker,
        as_of=as_of,
        review_items=review_items,
        source_artifact_summary=source_summary,
    )
    if manifest is not None:
        review_manifest = manifest if isinstance(manifest, ReviewSourceManifest) else ReviewSourceManifest(required_sources=tuple(manifest))
        _validate_review_source_manifest(package, review_manifest)
    return package


def _validate_review_source_manifest(package: SeniorReviewPackage, manifest: ReviewSourceManifest) -> None:
    route_contract = f"{manifest.method} route contract"
    required_summary_sources = (*manifest.required_sources, *manifest.required_context_sources)
    missing_summary = sorted(source for source in required_summary_sources if source not in package.source_artifact_summary)
    if missing_summary:
        raise ValueError(f"{route_contract} missing required sources: {', '.join(missing_summary)}")
    item_sources = {item.source_artifact for item in package.review_items}
    missing_items = sorted(source for source in manifest.required_sources if source not in item_sources)
    if missing_items:
        raise ValueError(f"{route_contract} missing required review items: {', '.join(missing_items)}")


def _outcome_for_decision_payload(payload: Any) -> RatificationOutcome:
    decision = SeniorDecision.model_validate(payload)
    return _outcome_for_decision(decision)


def _outcome_for_decision(decision: SeniorDecision) -> RatificationOutcome:
    if decision.decision == "ratified":
        return "modified" if decision.final is not None else "ratified_as_is"
    return "modified" if decision.final is not None else "rejected"


def _ratification_summary_payload(
    *,
    required_item_ids: list[str],
    outcomes: dict[str, RatificationOutcome],
) -> dict[str, int | float]:
    required_outcomes = [outcomes[item_id] for item_id in required_item_ids if item_id in outcomes]
    required_count = len(required_item_ids)
    ratified_as_is_count = required_outcomes.count("ratified_as_is")
    modified_count = required_outcomes.count("modified")
    rejected_count = required_outcomes.count("rejected")
    return {
        "required_count": required_count,
        "ratified_as_is_count": ratified_as_is_count,
        "modified_count": modified_count,
        "rejected_count": rejected_count,
        "ratified_as_is_rate": 0.0 if required_count == 0 else ratified_as_is_count / required_count,
    }


def ratify_review_package(
    package: SeniorReviewPackage,
    *,
    senior: Senior,
    analyst_family: str,
    header: Header,
) -> SeniorDecisionPackage:
    senior_family = _declared_family(senior)
    if not analyst_family or not senior_family:
        raise ValueError("analyst and senior adapters must declare model families before ratify")
    if analyst_family == senior_family:
        raise ValueError(f"analyst and senior model families must differ before ratify: {analyst_family}")
    required_item_ids = [item.id for item in package.review_items if item.required]
    response = senior.ratify(
        {
            "ticker": package.ticker,
            "as_of": package.as_of.isoformat(),
            "required_item_ids": required_item_ids,
            "review_package": artifact_model_to_payload(package),
        }
    )
    decisions_payload = response.get("decisions")
    if not isinstance(decisions_payload, dict):
        raise ValueError("senior ratify response requires decisions")
    decided_by = str(
        response.get("decided_by")
        or getattr(senior, "decided_by", None)
        or getattr(senior, "senior_handle", None)
        or "unknown-senior"
    )
    decisions = {
        str(item_id): SeniorDecision.model_validate(decision_payload)
        for item_id, decision_payload in decisions_payload.items()
    }
    outcomes = {item_id: _outcome_for_decision(decision) for item_id, decision in decisions.items()}
    summary_item_ids = [item_id for item_id in required_item_ids if item_id in outcomes]
    return SeniorDecisionPackage(
        header=header,
        ticker=package.ticker,
        as_of=package.as_of,
        decided_by=decided_by,
        required_item_ids=required_item_ids,
        decisions=decisions,
        outcomes=outcomes,
        ratification_summary=RatificationSummary.model_validate(
            _ratification_summary_payload(required_item_ids=summary_item_ids, outcomes=outcomes)
        ),
    )


def _declared_family(adapter: Any) -> str | None:
    if adapter is None:
        return None
    for attr in ("model_family", "model_handle", "senior_handle"):
        value = getattr(adapter, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _iter_analyst_drafts(value: Any, path: str) -> list[tuple[str, AnalystDraft]]:
    if isinstance(value, AnalystDraft):
        return [(path, value)]
    drafts: list[tuple[str, AnalystDraft]] = []
    if isinstance(value, BaseModel):
        for field_name in value.__class__.model_fields:
            drafts.extend(_iter_analyst_drafts(getattr(value, field_name), f"{path}.{field_name}"))
        return drafts
    if isinstance(value, dict):
        for key, item in value.items():
            drafts.extend(_iter_analyst_drafts(item, f"{path}.{key}"))
        return drafts
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            drafts.extend(_iter_analyst_drafts(item, f"{path}[{index}]"))
    return drafts


def _iter_primitive_ratifiables(value: Any, path: str) -> list[tuple[str, Ratifiable]]:
    if isinstance(value, AnalystDraft):
        return []
    if isinstance(value, Ratifiable):
        return [(path, value)]
    ratifiables: list[tuple[str, Ratifiable]] = []
    if isinstance(value, BaseModel):
        for field_name in value.__class__.model_fields:
            ratifiables.extend(_iter_primitive_ratifiables(getattr(value, field_name), f"{path}.{field_name}"))
        return ratifiables
    if isinstance(value, dict):
        for key, item in value.items():
            ratifiables.extend(_iter_primitive_ratifiables(item, f"{path}.{key}"))
        return ratifiables
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            ratifiables.extend(_iter_primitive_ratifiables(item, f"{path}[{index}]"))
    return ratifiables


def _review_item_for_draft(source_artifact: str, field_path: str, draft: AnalystDraft) -> ReviewItem:
    return ReviewItem(
        id=_stable_review_id(source_artifact, field_path),
        source_artifact=source_artifact,
        source_field_path=field_path,
        draft=draft.draft,
        evidence_refs=draft.evidence_refs,
        checklist_area=draft.checklist_area,
        checklist_rationale=draft.checklist_rationale,
        required=draft.required,
        decision=draft.decision,
        decided_by=draft.decided_by,
        final=draft.final,
    )


def _review_item_for_ratifiable(source_artifact: str, field_path: str, ratifiable: Ratifiable) -> ReviewItem:
    return ReviewItem(
        id=_stable_review_id(source_artifact, field_path),
        source_artifact=source_artifact,
        source_field_path=field_path,
        draft=ratifiable.draft,
        evidence_refs=[
            EvidenceRef(
                source_label=field_path,
                excerpt_or_summary=evidence,
                artifact_path=source_artifact,
            )
            for evidence in ratifiable.evidence
        ],
        checklist_area=field_path,
        checklist_rationale=f"Senior must ratify {field_path}.",
        required=ratifiable.needs_ratification,
        decision=ratifiable.decision,
        decided_by=ratifiable.decided_by,
        final=ratifiable.final,
    )


def _stable_review_id(source_artifact: str, field_path: str) -> str:
    raw = json.dumps({"source_artifact": source_artifact, "field_path": field_path}, sort_keys=True)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"review_{digest}"
