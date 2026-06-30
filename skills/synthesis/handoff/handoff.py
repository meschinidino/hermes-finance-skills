from __future__ import annotations

from datetime import date, datetime, timezone

from skills._primitives import Header, Number
from skills.accountant_artifacts import BareHandoff, Spine


def build_handoff(
    ticker: str,
    cik: str,
    spine: Spine,
    *,
    price: Number | None,
    as_of: date | None,
    schema_version: str,
    flags: list[str],
    source_accessions: list[str] | None = None,
) -> BareHandoff:
    run_date = as_of or date.today()
    return BareHandoff(
        header=Header(schema_version=schema_version, produced_by="D-1", produced_at=datetime.now(timezone.utc)),
        status="m1_walking_skeleton",
        ticker=ticker,
        cik=cik,
        as_of=run_date,
        price=price,
        spine=spine,
        confidence_and_gaps={
            "least_sure_about": "M1 only validates the mechanical spine; Analyst and Senior judgment are deferred.",
            "couldnt_verify": [],
            "would_raise_conviction": "M2-M4 completion: full accounting panels, valuation, analyst evidence, and Senior ratification.",
        },
        data_room={
            "spine_years": spine.years,
            "sources": sorted(set(source_accessions or [])),
            "m1_note": "Bare handoff only; full filing-rules Handoff is deferred to later milestones.",
        },
        flags=sorted(set(flags + spine.flags)),
    )
