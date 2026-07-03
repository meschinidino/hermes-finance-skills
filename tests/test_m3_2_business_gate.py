from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from resolver import GateWiringError, _run_business_early_gate, analyze
from skills.audit import AuditError, audit_analyst_artifact
from skills.bundle_validation import BundleValidationError, validate_skill_bundle
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.analyst_artifacts import AnalystDraft, EvidenceRef
from skills.research.business.business import build_business_artifact
from skills.storage import LocalStorage
from tests.m3_fakes import FakeLLM, FakeSenior


class CountingSenior(FakeSenior):
    def __init__(self, *, decision: str = "GO", senior_handle: str = "senior-family") -> None:
        super().__init__(senior_handle=senior_handle, decided_by="counting-senior")
        self.decision = decision
        self.calls: list[dict[str, Any]] = []

    def gate(self, package: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(package)
        return {
            "decision": self.decision,
            "rationale": f"{self.decision} from test Senior",
            "decided_by": self.decided_by,
            "ticker": package["ticker"],
        }


class UnidentifiedLLM:
    def complete(self, prompt: str, *, context: dict[str, Any]) -> str:
        return prompt


def test_business_bundle_passes_real_analyst_shape_validation() -> None:
    validate_skill_bundle(Path("skills/research/business"), expected_role="analyst")


def test_business_bundle_validation_rejects_bare_assertion_contract(tmp_path) -> None:
    bundle = tmp_path / "business"
    bundle.mkdir()
    (bundle / "SKILL.md").write_text(
        """# SKILL: C-1 Business
type: analyst
outputs: FinalBusinessAssertion
output_contract: FinalBusinessAssertion
implementation: business.py
no_llm: false
llm_dependency: true
""",
        encoding="utf-8",
    )
    (bundle / "business.py").write_text("# fixture\n", encoding="utf-8")
    (bundle / "prompt.md").write_text("prompt\n", encoding="utf-8")
    (bundle / "resolver.entry").write_text("business\n", encoding="utf-8")
    eval_dir = bundle / "eval"
    eval_dir.mkdir()
    (eval_dir / "cases.jsonl").write_text("{}\n", encoding="utf-8")
    (eval_dir / "eval_business.py").write_text("# fixture\n", encoding="utf-8")

    with pytest.raises(BundleValidationError, match="ratifiable"):
        validate_skill_bundle(bundle, expected_role="analyst")


def test_business_artifact_constructs_audits_and_stores(tmp_path) -> None:
    edgar = fetch_edgar_facts("AAPL")
    storage = LocalStorage(tmp_path)
    artifact = build_business_artifact(
        edgar,
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        run_dir="runs/AAPL/2026-06-30",
    )

    audit_analyst_artifact(artifact, storage=storage, path="runs/AAPL/2026-06-30/business.json")

    payload = storage.get_json("runs/AAPL/2026-06-30/business.json")
    assert payload["header"]["produced_by"] == "C-1"
    assert payload["ticker"] == "AAPL"
    assert payload["as_of"] == "2026-06-30"
    assert payload["business_model_summary"]["needs_ratification"] is True
    assert payload["revenue_driver_summary"]["evidence_refs"][0]["filing_reference"]
    assert payload["customer_end_market_summary"]["checklist_area"] == "customers_and_end_markets"
    assert "TODO" not in json.dumps(payload)


def test_business_drafter_fails_closed_when_required_fixture_evidence_missing(tmp_path) -> None:
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    (fixture_dir / "aapl_business_evidence.json").write_text(
        json.dumps({"business_model_summary": {"draft": "partial"}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing_business_evidence_fields"):
        build_business_artifact(
            fetch_edgar_facts("AAPL"),
            as_of=date(2026, 6, 30),
            schema_version="1.0",
            run_dir="runs/AAPL/2026-06-30",
            fixture_dir=fixture_dir,
        )


def test_business_audit_rejects_empty_and_unresolvable_evidence_refs() -> None:
    artifact = build_business_artifact(
        fetch_edgar_facts("AAPL"),
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        run_dir="runs/AAPL/2026-06-30",
    )
    unsupported = artifact.model_copy(
        update={
            "business_model_summary": AnalystDraft.model_construct(
                draft="unsupported",
                evidence_refs=[],
                checklist_area="business_model",
                checklist_rationale="prompt text cannot bypass audit",
            )
        }
    )
    unresolvable = artifact.model_copy(
        update={
            "business_model_summary": artifact.business_model_summary.model_copy(
                update={
                    "evidence_refs": [
                        EvidenceRef(source_label="EDGAR", excerpt_or_summary="summary", artifact_path=" ", filing_reference=None)
                    ]
                }
            )
        }
    )

    with pytest.raises(AuditError, match="evidence"):
        audit_analyst_artifact(unsupported)
    with pytest.raises(AuditError, match="trace target"):
        audit_analyst_artifact(unresolvable)


def test_same_family_gate_wiring_rejects_before_senior_call(tmp_path) -> None:
    artifact = build_business_artifact(
        fetch_edgar_facts("AAPL"),
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        run_dir="runs/AAPL/2026-06-30",
    )
    storage = LocalStorage(tmp_path)
    senior = CountingSenior(senior_handle="same-family")

    with pytest.raises(GateWiringError, match="must differ"):
        _run_business_early_gate(
            artifact,
            business_path="runs/AAPL/2026-06-30/business.json",
            ticker="AAPL",
            as_of=date(2026, 6, 30),
            schema_version="1.0",
            senior=senior,
            analyst_family="same-family",
            storage=storage,
            run_dir="runs/AAPL/2026-06-30",
        )

    assert senior.calls == []


def test_different_family_gate_calls_senior_once_and_files_result(tmp_path) -> None:
    artifact = build_business_artifact(
        fetch_edgar_facts("AAPL"),
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        run_dir="runs/AAPL/2026-06-30",
    )
    storage = LocalStorage(tmp_path)
    senior = CountingSenior(senior_handle="senior-family")

    result = _run_business_early_gate(
        artifact,
        business_path="runs/AAPL/2026-06-30/business.json",
        ticker="AAPL",
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        senior=senior,
        analyst_family="analyst-family",
        storage=storage,
        run_dir="runs/AAPL/2026-06-30",
    )

    assert result.decision == "GO"
    assert len(senior.calls) == 1
    assert senior.calls[0]["business_artifact_path"] == "runs/AAPL/2026-06-30/business.json"
    stored = storage.get_json("runs/AAPL/2026-06-30/business_early_gate.json")
    assert stored["decision"] == "GO"


def test_analyze_go_branch_files_business_and_continues(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    senior = CountingSenior(decision="GO", senior_handle="senior-family")

    payload = analyze(
        "AAPL",
        as_of=date(2026, 6, 30),
        storage=storage,
        llm=FakeLLM(model_handle="analyst-family"),
        senior=senior,
    )

    assert len(senior.calls) == 1
    assert payload["header"]["produced_by"] == "D-3"
    assert storage.get_json("runs/AAPL/2026-06-30/business.json")["ticker"] == "AAPL"
    assert storage.get_json("runs/AAPL/2026-06-30/business_early_gate.json")["decision"] == "GO"
    assert storage.get_json("runs/AAPL/2026-06-30/gate_card.json")["ticker"] == "AAPL"


def test_analyze_no_go_branch_halts_and_files_stop_artifact(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    senior = CountingSenior(decision="NO-GO", senior_handle="senior-family")

    payload = analyze(
        "AAPL",
        as_of=date(2026, 6, 30),
        storage=storage,
        llm=FakeLLM(model_handle="analyst-family"),
        senior=senior,
    )

    assert len(senior.calls) == 1
    assert payload["status"] == "halted"
    assert payload["early_gate"]["decision"] == "NO-GO"
    assert payload["stop_artifact"]["gate_decision"] == "NO-GO"
    assert payload["stop_artifact"]["business_artifact_path"] == "runs/AAPL/2026-06-30/business.json"
    assert "valuation_range" not in payload["stop_artifact"]
    assert storage.get_json("runs/AAPL/2026-06-30/business_stop.json") == payload["stop_artifact"]


def test_analyze_same_family_rejects_before_senior_gate(tmp_path) -> None:
    senior = CountingSenior(senior_handle="shared-family")

    with pytest.raises(GateWiringError):
        analyze(
            "AAPL",
            as_of=date(2026, 6, 30),
            storage=LocalStorage(tmp_path),
            llm=FakeLLM(model_handle="shared-family"),
            senior=senior,
        )

    assert senior.calls == []


def test_analyze_rejects_missing_llm_family_before_senior_gate(tmp_path) -> None:
    senior = CountingSenior(senior_handle="senior-family")

    with pytest.raises(GateWiringError, match="declare model families"):
        analyze(
            "AAPL",
            as_of=date(2026, 6, 30),
            storage=LocalStorage(tmp_path),
            llm=UnidentifiedLLM(),
            senior=senior,
        )

    assert senior.calls == []
