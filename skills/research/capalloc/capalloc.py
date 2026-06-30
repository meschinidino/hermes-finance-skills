from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import model_validator

from skills._primitives import Header, Provenance
from skills.m1_artifacts import EdgarFacts, Spine
from skills.analyst_artifacts import AnalystDraft, EvidenceRef, M3Model

FIXTURE_DIR = Path(__file__).parent / "fixtures"


class CapAllocArtifact(M3Model):
    header: Header
    ticker: str
    as_of: date
    reinvestment_behavior: AnalystDraft
    shareholder_return_behavior: AnalystDraft
    balance_sheet_discipline: AnalystDraft

    @model_validator(mode="after")
    def validate_required_content(self) -> CapAllocArtifact:
        for field_name in ("reinvestment_behavior", "shareholder_return_behavior", "balance_sheet_discipline"):
            draft = getattr(self, field_name).draft
            if not isinstance(draft, str) or not draft.strip():
                raise ValueError(f"{field_name} requires non-empty draft text")
            if draft.strip().lower() in {"todo", "stub", "not implemented"}:
                raise ValueError(f"{field_name} contains placeholder draft text")
        return self


def build_capalloc_artifact(
    edgar: EdgarFacts,
    spine: Spine,
    *,
    as_of: date,
    schema_version: str,
    run_dir: str,
    fixture_dir: Path = FIXTURE_DIR,
) -> CapAllocArtifact:
    evidence = _load_capalloc_evidence(edgar.ticker, fixture_dir=fixture_dir)
    latest_accession = _latest_accession(edgar)
    source_artifact_path = f"{run_dir}/spine.json"
    latest_period = spine.years[-1]
    return CapAllocArtifact(
        header=Header(schema_version=schema_version, produced_by="C-3", produced_at=datetime.now(timezone.utc)),
        ticker=edgar.ticker,
        as_of=as_of,
        reinvestment_behavior=_draft_from_fixture(
            evidence["reinvestment_behavior"],
            artifact_path=source_artifact_path,
            accession=latest_accession,
            checklist_area="capital_allocation_reinvestment",
            checklist_rationale="Senior must judge whether reinvestment behavior supports the thesis quality.",
            fallback_period=latest_period,
        ),
        shareholder_return_behavior=_draft_from_fixture(
            evidence["shareholder_return_behavior"],
            artifact_path=source_artifact_path,
            accession=latest_accession,
            checklist_area="capital_allocation_shareholder_returns",
            checklist_rationale="Senior must judge buyback, dividend, and dilution behavior before synthesis.",
            fallback_period=latest_period,
        ),
        balance_sheet_discipline=_draft_from_fixture(
            evidence["balance_sheet_discipline"],
            artifact_path=source_artifact_path,
            accession=latest_accession,
            checklist_area="capital_allocation_balance_sheet",
            checklist_rationale="Senior must judge balance-sheet and acquisition discipline before synthesis.",
            fallback_period=latest_period,
        ),
    )


def _load_capalloc_evidence(ticker: str, *, fixture_dir: Path) -> dict[str, dict[str, Any]]:
    path = fixture_dir / f"{ticker.lower()}_capalloc_evidence.json"
    if not path.is_file():
        raise ValueError(f"missing_capalloc_evidence:{ticker}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    required = {"reinvestment_behavior", "shareholder_return_behavior", "balance_sheet_discipline"}
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError(f"missing_capalloc_evidence_fields:{','.join(missing)}")
    return raw


def _draft_from_fixture(
    payload: dict[str, Any],
    *,
    artifact_path: str,
    accession: str,
    checklist_area: str,
    checklist_rationale: str,
    fallback_period: str,
) -> AnalystDraft:
    for key in ("draft", "source_label", "excerpt_or_summary", "filing_reference"):
        if not str(payload.get(key, "")).strip():
            raise ValueError(f"capalloc evidence missing {key}")
    period = str(payload.get("period") or fallback_period).strip()
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
