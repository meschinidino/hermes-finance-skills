from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from resolver import analyze
from skills.audit import AuditError, audit_analyst_artifact, audit_senior_review_package
from skills.bundle_validation import validate_skill_bundle
from skills.config import load_config
from skills.data.cost_of_capital.cost_of_capital import build_cost_of_capital_inputs
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.data.price.price import fetch_price
from skills.analyst_artifacts import AnalystDraft, EvidenceRef, collect_ratifiables
from skills.research.capalloc.capalloc import build_capalloc_artifact
from skills.research.moat.moat import build_moat_artifact
from skills.serialization import artifact_model_to_payload
from skills.storage import LocalStorage
from skills.valuation.normalize.normalize import normalize_financials
from skills.valuation.spine.spine import build_spine
from tests.test_m3_2_business_gate import CountingSenior
from tests.m3_fakes import FakeLLM


def test_moat_and_capalloc_bundles_pass_real_analyst_shape_validation() -> None:
    validate_skill_bundle(Path("skills/research/moat"), expected_role="analyst")
    validate_skill_bundle(Path("skills/research/capalloc"), expected_role="analyst")


def test_moat_artifact_constructs_audits_stores_and_collects(tmp_path) -> None:
    edgar, spine = _edgar_and_spine()
    storage = LocalStorage(tmp_path)
    _store_spine(storage, spine)
    artifact = build_moat_artifact(
        edgar,
        spine,
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        run_dir="runs/AAPL/2026-06-30",
    )

    audit_analyst_artifact(artifact, storage=storage, path="runs/AAPL/2026-06-30/moat.json")
    package = collect_ratifiables(
        artifact,
        ticker="AAPL",
        as_of=date(2026, 6, 30),
        header=artifact.header,
        source_artifact="runs/AAPL/2026-06-30/moat.json",
    )
    audit_senior_review_package(package)

    assert storage.get_json("runs/AAPL/2026-06-30/moat.json")["header"]["produced_by"] == "C-2"
    assert artifact.moat_mechanism.needs_ratification is True
    assert artifact.moat_mechanism.draft["mechanism_category"] == "switching_costs"
    assert {item.checklist_area for item in package.review_items} == {
        "moat_strength",
        "moat_economics",
        "moat_evidence_gaps",
    }
    assert all(item.decision is None for item in package.review_items)


def test_capalloc_artifact_constructs_audits_stores_and_collects(tmp_path) -> None:
    edgar, spine = _edgar_and_spine()
    storage = LocalStorage(tmp_path)
    _store_spine(storage, spine)
    artifact = build_capalloc_artifact(
        edgar,
        spine,
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        run_dir="runs/AAPL/2026-06-30",
    )

    audit_analyst_artifact(artifact, storage=storage, path="runs/AAPL/2026-06-30/capalloc.json")
    package = collect_ratifiables(
        artifact,
        ticker="AAPL",
        as_of=date(2026, 6, 30),
        header=artifact.header,
        source_artifact="runs/AAPL/2026-06-30/capalloc.json",
    )
    audit_senior_review_package(package)

    assert storage.get_json("runs/AAPL/2026-06-30/capalloc.json")["header"]["produced_by"] == "C-3"
    assert len(package.review_items) == 3
    assert all(item.source_artifact == "runs/AAPL/2026-06-30/capalloc.json" for item in package.review_items)
    assert all(item.decision is None for item in package.review_items)


def test_period_mismatch_rejects_resolving_evidence_ref(tmp_path) -> None:
    edgar, spine = _edgar_and_spine()
    storage = LocalStorage(tmp_path)
    _store_spine(storage, spine)
    artifact = build_capalloc_artifact(
        edgar,
        spine,
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        run_dir="runs/AAPL/2026-06-30",
    )
    evidence = artifact.reinvestment_behavior.evidence_refs[0]
    mismatched = evidence.model_copy(update={"claimed_period": "FY2025"})
    invalid = artifact.model_copy(
        update={
            "reinvestment_behavior": artifact.reinvestment_behavior.model_copy(
                update={"evidence_refs": [mismatched]}
            )
        }
    )

    with pytest.raises(AuditError, match="claimed FY2025 resolved FY2024"):
        audit_analyst_artifact(invalid, storage=storage)


def test_period_mismatch_rejects_when_ref_provenance_matches_wrong_claim(tmp_path) -> None:
    edgar, spine = _edgar_and_spine()
    storage = LocalStorage(tmp_path)
    _store_spine(storage, spine)
    artifact = build_capalloc_artifact(
        edgar,
        spine,
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        run_dir="runs/AAPL/2026-06-30",
    )
    evidence = artifact.reinvestment_behavior.evidence_refs[0]
    wrong_provenance = evidence.provenance.model_copy(update={"period": "FY2025"})
    bypass_attempt = evidence.model_copy(update={"claimed_period": "FY2025", "provenance": wrong_provenance})
    invalid = artifact.model_copy(
        update={
            "reinvestment_behavior": artifact.reinvestment_behavior.model_copy(
                update={"evidence_refs": [bypass_attempt]}
            )
        }
    )

    with pytest.raises(AuditError, match="claimed FY2025 resolved FY2024"):
        audit_analyst_artifact(invalid, storage=storage)


def test_claimed_period_matching_resolved_stored_source_passes(tmp_path) -> None:
    edgar, spine = _edgar_and_spine()
    storage = LocalStorage(tmp_path)
    _store_spine(storage, spine)
    artifact = build_capalloc_artifact(
        edgar,
        spine,
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        run_dir="runs/AAPL/2026-06-30",
    )

    audit_analyst_artifact(artifact, storage=storage)


def test_claimed_period_with_unresolved_storage_target_fails_closed(tmp_path) -> None:
    edgar, spine = _edgar_and_spine()
    storage = LocalStorage(tmp_path)
    artifact = build_capalloc_artifact(
        edgar,
        spine,
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        run_dir="runs/AAPL/2026-06-30",
    )

    with pytest.raises(AuditError, match="unresolvable-source"):
        audit_analyst_artifact(artifact, storage=storage)


def test_period_specific_claim_without_claimed_period_fails_closed() -> None:
    edgar, spine = _edgar_and_spine()
    artifact = build_capalloc_artifact(
        edgar,
        spine,
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        run_dir="runs/AAPL/2026-06-30",
    )
    evidence = EvidenceRef(source_label="EDGAR", excerpt_or_summary="summary", artifact_path="runs/AAPL/2026-06-30/spine.json")
    invalid = artifact.model_copy(
        update={
            "reinvestment_behavior": AnalystDraft(
                draft="FY2024 reinvestment was disciplined.",
                evidence_refs=[evidence],
                checklist_area="capital_allocation_reinvestment",
                checklist_rationale="period-specific claim must carry a period",
            )
        }
    )

    with pytest.raises(AuditError, match="period-specific claim missing claimed period"):
        audit_analyst_artifact(invalid)


def test_metric_only_moat_claim_is_rejected_structurally(tmp_path) -> None:
    edgar, spine = _edgar_and_spine()
    storage = LocalStorage(tmp_path)
    _store_spine(storage, spine)
    artifact = build_moat_artifact(
        edgar,
        spine,
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        run_dir="runs/AAPL/2026-06-30",
    )
    invalid_draft = {
        "claim": "Historical ROIC spread alone proves a moat.",
        "mechanism_category": "",
        "support_categories": ["roic_spread"],
    }
    invalid = artifact.model_copy(
        update={"moat_mechanism": artifact.moat_mechanism.model_copy(update={"draft": invalid_draft})}
    )

    with pytest.raises(AuditError, match="forward-looking mechanism"):
        audit_analyst_artifact(invalid, storage=storage)


def test_metric_only_equivalent_without_roic_string_is_rejected(tmp_path) -> None:
    edgar, spine = _edgar_and_spine()
    storage = LocalStorage(tmp_path)
    _store_spine(storage, spine)
    artifact = build_moat_artifact(
        edgar,
        spine,
        as_of=date(2026, 6, 30),
        schema_version="1.0",
        run_dir="runs/AAPL/2026-06-30",
    )
    invalid_draft = {
        "claim": "Returns above cost of capital alone prove durable protection.",
        "mechanism_category": "",
        "support_categories": ["returns_above_cost_of_capital"],
    }
    invalid = artifact.model_copy(
        update={"moat_mechanism": artifact.moat_mechanism.model_copy(update={"draft": invalid_draft})}
    )

    with pytest.raises(AuditError, match="forward-looking mechanism"):
        audit_analyst_artifact(invalid, storage=storage)


def test_analyze_go_branch_files_moat_and_capalloc_without_second_senior_call(tmp_path) -> None:
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
    assert storage.get_json("runs/AAPL/2026-06-30/moat.json")["header"]["produced_by"] == "C-2"
    assert storage.get_json("runs/AAPL/2026-06-30/capalloc.json")["header"]["produced_by"] == "C-3"
    assert storage.get_json("runs/AAPL/2026-06-30/moat_review_package.json")["review_items"][0]["decision"] is None
    assert storage.get_json("runs/AAPL/2026-06-30/capalloc_review_package.json")["review_items"][0]["decision"] is None


def test_analyze_no_go_branch_does_not_run_moat_or_capalloc(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    senior = CountingSenior(decision="NO-GO", senior_handle="senior-family")

    payload = analyze(
        "AAPL",
        as_of=date(2026, 6, 30),
        storage=storage,
        llm=FakeLLM(model_handle="analyst-family"),
        senior=senior,
    )

    assert payload["status"] == "halted"
    assert "moat" not in payload
    assert "capalloc" not in payload
    with pytest.raises(FileNotFoundError):
        storage.get_json("runs/AAPL/2026-06-30/moat.json")


def _edgar_and_spine():
    run_date = date(2026, 6, 30)
    config = load_config("config/conventions.yaml")
    edgar = fetch_edgar_facts("AAPL")
    price = fetch_price("AAPL", edgar=edgar, as_of=run_date)
    cost_of_capital = build_cost_of_capital_inputs("AAPL", config, edgar=edgar, price=price, as_of=run_date)
    normalized = normalize_financials(edgar)
    spine = build_spine(
        normalized,
        cost_of_capital,
        price,
        excess_cash_pct=config.invested_capital.excess_cash_pct,
        schema_version=config.schema_version,
    )
    return edgar, spine


def _store_spine(storage: LocalStorage, spine) -> None:
    storage.put_json("runs/AAPL/2026-06-30/spine.json", artifact_model_to_payload(spine))
