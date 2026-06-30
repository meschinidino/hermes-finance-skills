from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from skills._primitives import Header, Provenance, to_jsonable


class M3Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)


DecisionState = Literal["ratified", "overturned"]


class EvidenceRef(M3Model):
    source_label: str
    excerpt_or_summary: str
    artifact_path: str | None = None
    filing_reference: str | None = None
    external_source_ref: str | None = None
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


class SeniorDecision(M3Model):
    decision: DecisionState
    final: Any | None = None
    rationale: str


class SeniorDecisionPackage(M3Model):
    header: Header
    ticker: str
    as_of: date
    decided_by: str
    required_item_ids: list[str]
    decisions: dict[str, SeniorDecision]

    @property
    def is_complete(self) -> bool:
        return set(self.required_item_ids).issubset(self.decisions)

    @model_validator(mode="after")
    def validate_decisions(self) -> SeniorDecisionPackage:
        if not self.decided_by:
            raise ValueError("senior decision package requires decided_by")
        missing = sorted(set(self.required_item_ids) - set(self.decisions))
        if missing:
            raise ValueError(f"senior decisions missing required item ids: {', '.join(missing)}")
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


def m3_model_to_payload(model: BaseModel) -> dict[str, Any]:
    payload = to_jsonable(model)
    if not isinstance(payload, dict):
        raise TypeError("expected model to serialize to object")
    return payload


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


def _stable_review_id(source_artifact: str, field_path: str) -> str:
    raw = json.dumps({"source_artifact": source_artifact, "field_path": field_path}, sort_keys=True)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"review_{digest}"
