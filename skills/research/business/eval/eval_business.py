from __future__ import annotations

from datetime import date

from skills.audit import audit_analyst_artifact
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.research.business.business import build_business_artifact


def test_eval_business_fixture_audits() -> None:
    artifact = build_business_artifact(
        fetch_edgar_facts("AAPL"),
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        run_dir="runs/AAPL/2026-06-30",
    )
    audit_analyst_artifact(artifact)
