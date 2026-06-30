from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import model_validator

from skills._primitives import Header
from skills.m1_artifacts import EdgarFacts
from skills.analyst_artifacts import AnalystDraft, EvidenceRef, M3Model

FIXTURE_DIR = Path(__file__).parent / "fixtures"


class BusinessArtifact(M3Model):
    header: Header
    ticker: str
    cik: str
    as_of: date
    source_evidence_summary: dict[str, str]
    business_model_summary: AnalystDraft
    revenue_driver_summary: AnalystDraft
    customer_end_market_summary: AnalystDraft
    business_understanding_risk: AnalystDraft

    @model_validator(mode="after")
    def validate_required_content(self) -> BusinessArtifact:
        for field_name in (
            "business_model_summary",
            "revenue_driver_summary",
            "customer_end_market_summary",
            "business_understanding_risk",
        ):
            draft = getattr(self, field_name).draft
            if not isinstance(draft, str) or not draft.strip():
                raise ValueError(f"{field_name} requires non-empty draft text")
            if draft.strip().lower() in {"todo", "stub", "not implemented"}:
                raise ValueError(f"{field_name} contains placeholder draft text")
        return self


class EarlyGateResult(M3Model):
    header: Header
    ticker: str
    as_of: date
    gate_name: Literal["business_early_gate"]
    decision: Literal["GO", "NO-GO"]
    rationale: str
    decided_by: str
    business_artifact_path: str


class StopArtifact(M3Model):
    header: Header
    ticker: str
    as_of: date
    gate_name: Literal["business_early_gate"]
    gate_decision: Literal["NO-GO"]
    stop_reason: str
    gate_rationale: str
    business_artifact_path: str
    evidence_package: dict[str, str]


def build_business_artifact(
    edgar: EdgarFacts,
    *,
    as_of: date,
    schema_version: str,
    run_dir: str,
    fixture_dir: Path = FIXTURE_DIR,
) -> BusinessArtifact:
    evidence = _load_business_evidence(edgar.ticker, fixture_dir=fixture_dir)
    source_artifact_path = f"{run_dir}/handoff.json"
    latest_revenue = edgar.facts.revenue[-1]
    latest_accession = latest_revenue.provenance.accession or "missing-accession"
    return BusinessArtifact(
        header=Header(schema_version=schema_version, produced_by="C-1", produced_at=datetime.now(timezone.utc)),
        ticker=edgar.ticker,
        cik=edgar.cik,
        as_of=as_of,
        source_evidence_summary={
            "financial_artifact": source_artifact_path,
            "filing_accession": latest_accession,
            "fixture": str((fixture_dir / f"{edgar.ticker.lower()}_business_evidence.json").as_posix()),
        },
        business_model_summary=_draft_from_fixture(
            evidence["business_model_summary"],
            artifact_path=source_artifact_path,
            accession=latest_accession,
            checklist_area="business_model",
            checklist_rationale="Senior must decide whether the described model is understandable enough to continue.",
        ),
        revenue_driver_summary=_draft_from_fixture(
            evidence["revenue_driver_summary"],
            artifact_path=source_artifact_path,
            accession=latest_accession,
            checklist_area="revenue_drivers",
            checklist_rationale="Senior must decide whether the key revenue drivers are identified well enough to proceed.",
        ),
        customer_end_market_summary=_draft_from_fixture(
            evidence["customer_end_market_summary"],
            artifact_path=source_artifact_path,
            accession=latest_accession,
            checklist_area="customers_and_end_markets",
            checklist_rationale="Senior must decide whether the end-market description is sufficient for the early gate.",
        ),
        business_understanding_risk=_draft_from_fixture(
            evidence["business_understanding_risk"],
            artifact_path=source_artifact_path,
            accession=latest_accession,
            checklist_area="early_gate_concern",
            checklist_rationale="Senior must explicitly consider this concern before GO or NO-GO.",
        ),
    )


def _load_business_evidence(ticker: str, *, fixture_dir: Path) -> dict[str, dict[str, str]]:
    path = fixture_dir / f"{ticker.lower()}_business_evidence.json"
    if not path.is_file():
        raise ValueError(f"missing_business_evidence:{ticker}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "business_model_summary",
        "revenue_driver_summary",
        "customer_end_market_summary",
        "business_understanding_risk",
    }
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError(f"missing_business_evidence_fields:{','.join(missing)}")
    return raw


def _draft_from_fixture(
    payload: dict[str, str],
    *,
    artifact_path: str,
    accession: str,
    checklist_area: str,
    checklist_rationale: str,
) -> AnalystDraft:
    for key in ("draft", "source_label", "excerpt_or_summary", "filing_reference"):
        if not str(payload.get(key, "")).strip():
            raise ValueError(f"business evidence missing {key}")
    return AnalystDraft(
        draft=payload["draft"],
        evidence_refs=[
            EvidenceRef(
                source_label=payload["source_label"],
                excerpt_or_summary=payload["excerpt_or_summary"],
                artifact_path=artifact_path,
                filing_reference=f"{payload['filing_reference']}; accession={accession}",
            )
        ],
        checklist_area=checklist_area,
        checklist_rationale=checklist_rationale,
    )
