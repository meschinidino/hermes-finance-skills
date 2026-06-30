from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import model_validator

from skills._primitives import Header, Provenance
from skills.m1_artifacts import EdgarFacts, Spine
from skills.m3_artifacts import AnalystDraft, EvidenceRef, M3Model

FIXTURE_DIR = Path(__file__).parent / "fixtures"


class MoatArtifact(M3Model):
    header: Header
    ticker: str
    as_of: date
    moat_mechanism: AnalystDraft
    historical_economics: AnalystDraft
    durability_risk: AnalystDraft

    @model_validator(mode="after")
    def validate_required_content(self) -> MoatArtifact:
        for field_name in ("moat_mechanism", "historical_economics", "durability_risk"):
            draft = getattr(self, field_name).draft
            if not _has_substantive_text(draft):
                raise ValueError(f"{field_name} requires non-empty draft content")
        mechanism = self.moat_mechanism.draft
        if not isinstance(mechanism, dict):
            raise ValueError("moat_mechanism draft must include mechanism metadata")
        if not str(mechanism.get("mechanism_category", "")).strip():
            raise ValueError("moat_mechanism requires mechanism_category")
        if not mechanism.get("support_categories"):
            raise ValueError("moat_mechanism requires support_categories")
        return self


def build_moat_artifact(
    edgar: EdgarFacts,
    spine: Spine,
    *,
    as_of: date,
    schema_version: str,
    run_dir: str,
    fixture_dir: Path = FIXTURE_DIR,
) -> MoatArtifact:
    evidence = _load_moat_evidence(edgar.ticker, fixture_dir=fixture_dir)
    latest_accession = _latest_accession(edgar)
    source_artifact_path = f"{run_dir}/spine.json"
    return MoatArtifact(
        header=Header(schema_version=schema_version, produced_by="C-2", produced_at=datetime.now(timezone.utc)),
        ticker=edgar.ticker,
        as_of=as_of,
        moat_mechanism=_draft_from_fixture(
            evidence["moat_mechanism"],
            artifact_path=source_artifact_path,
            accession=latest_accession,
            checklist_area="moat_strength",
            checklist_rationale="Senior must judge whether the mechanism plausibly supports durable excess returns.",
        ),
        historical_economics=_draft_from_fixture(
            evidence["historical_economics"],
            artifact_path=source_artifact_path,
            accession=latest_accession,
            checklist_area="moat_economics",
            checklist_rationale="Senior must decide how much weight to place on historical spread and margins.",
            fallback_period=spine.years[-1],
        ),
        durability_risk=_draft_from_fixture(
            evidence["durability_risk"],
            artifact_path=source_artifact_path,
            accession=latest_accession,
            checklist_area="moat_evidence_gaps",
            checklist_rationale="Senior must explicitly consider durability risks and disconfirming evidence.",
        ),
    )


def _load_moat_evidence(ticker: str, *, fixture_dir: Path) -> dict[str, dict[str, Any]]:
    path = fixture_dir / f"{ticker.lower()}_moat_evidence.json"
    if not path.is_file():
        raise ValueError(f"missing_moat_evidence:{ticker}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    required = {"moat_mechanism", "historical_economics", "durability_risk"}
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError(f"missing_moat_evidence_fields:{','.join(missing)}")
    return raw


def _draft_from_fixture(
    payload: dict[str, Any],
    *,
    artifact_path: str,
    accession: str,
    checklist_area: str,
    checklist_rationale: str,
    fallback_period: str | None = None,
) -> AnalystDraft:
    for key in ("draft", "source_label", "excerpt_or_summary", "filing_reference", "period"):
        if not str(payload.get(key, "")).strip():
            raise ValueError(f"moat evidence missing {key}")
    period = str(payload.get("period") or fallback_period or "").strip()
    return AnalystDraft(
        draft=payload["draft"],
        evidence_refs=[
            EvidenceRef(
                source_label=payload["source_label"],
                excerpt_or_summary=payload["excerpt_or_summary"],
                artifact_path=artifact_path,
                filing_reference=f"{payload['filing_reference']}; accession={accession}",
                external_source_ref=str(payload.get("fixture_ref", "")).strip() or None,
                claimed_period=period,
                provenance=Provenance(
                    tag=str(payload.get("tag") or "fixture"),
                    form=str(payload.get("form") or "10-K"),
                    period=period,
                    accession=accession,
                    source_name="EDGAR fixture",
                    retrieved_at=datetime.now(timezone.utc),
                ),
            )
        ],
        checklist_area=checklist_area,
        checklist_rationale=checklist_rationale,
    )


def _latest_accession(edgar: EdgarFacts) -> str:
    latest_revenue = edgar.facts.revenue[-1]
    return latest_revenue.provenance.accession or "missing-accession"


def _has_substantive_text(value: Any) -> bool:
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, dict):
        text = " ".join(str(item).strip() for item in value.values())
    else:
        text = str(value).strip()
    return bool(text) and text.lower() not in {"todo", "stub", "not implemented"}
