from __future__ import annotations

import inspect
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from skills._primitives import Header, Number, Provenance
from skills.audit import AuditError, audit_analyst_artifact, audit_senior_decision_package, audit_senior_review_package
from skills.bundle_validation import BundleValidationError, validate_skill_bundle
from skills.analyst_artifacts import (
    AnalystDraft,
    EvidenceRef,
    M3Model,
    SeniorDecision,
    SeniorDecisionPackage,
    SeniorReviewPackage,
    collect_ratifiables,
    m3_model_to_payload,
)
from skills.storage import LocalStorage
from tests.m3_fakes import FakeLLM, FakeSenior


class SampleM3Artifact(M3Model):
    header: Header
    ticker: str
    claim: AnalystDraft


class NumericBoundaryArtifact(M3Model):
    header: Header
    threshold: Number


class SyntheticDriver(M3Model):
    name: str
    assumption: AnalystDraft


class SyntheticMultiRatifiableArtifact(M3Model):
    header: Header
    ticker: str
    bear: SyntheticDriver
    base: SyntheticDriver
    bull: SyntheticDriver


def test_valid_m3_artifact_constructs_passes_audit_and_stores(tmp_path) -> None:
    artifact = sample_artifact()
    storage = LocalStorage(tmp_path)

    audit_analyst_artifact(artifact, storage=storage, path="runs/AAPL/2026-06-30/business_test.json")

    payload = storage.get_json("runs/AAPL/2026-06-30/business_test.json")
    assert payload["ticker"] == "AAPL"
    assert payload["claim"]["evidence_refs"][0]["artifact_path"] == "runs/AAPL/source.json"


def test_audit_rejects_unsupported_claim_without_evidence_ref() -> None:
    broken = sample_artifact().model_copy(
        update={"claim": AnalystDraft.model_construct(draft="unsupported", evidence_refs=[], checklist_area="business", checklist_rationale="missing evidence")}
    )

    with pytest.raises(AuditError, match="evidence"):
        audit_analyst_artifact(broken)


def test_audit_rejects_evidence_ref_without_resolvable_trace_target() -> None:
    broken = sample_artifact().model_copy(
        update={
            "claim": sample_draft().model_copy(
                update={
                    "evidence_refs": [
                        EvidenceRef(source_label="EDGAR", excerpt_or_summary="summary", artifact_path=" ", filing_reference=None, external_source_ref=None)
                    ]
                }
            )
        }
    )

    with pytest.raises(AuditError, match="trace target"):
        audit_analyst_artifact(broken)


def test_bare_numeric_boundary_rejected_where_number_required() -> None:
    with pytest.raises(ValidationError):
        NumericBoundaryArtifact(header=header("C-test"), threshold=1.2)


def test_audit_rejects_bare_numeric_analyst_draft_payload() -> None:
    artifact = sample_artifact().model_copy(update={"claim": sample_draft(0.25)})

    with pytest.raises(AuditError, match="bare numeric"):
        audit_analyst_artifact(artifact)


def test_audit_rejects_nested_bare_numeric_analyst_draft_payload() -> None:
    artifact = sample_artifact().model_copy(update={"claim": sample_draft({"bear": 0.2, "base": 0.5})})

    with pytest.raises(AuditError, match="bare numeric"):
        audit_analyst_artifact(artifact)


def test_audit_allows_nested_number_wrapped_analyst_draft_payload() -> None:
    artifact = sample_artifact().model_copy(
        update={
            "claim": sample_draft(
                {
                    "bear": sample_number(0.2),
                    "base": sample_number(0.5),
                    "bull": sample_number(0.8),
                }
            )
        }
    )

    audit_analyst_artifact(artifact)


def test_audit_allows_bool_analyst_draft_payload() -> None:
    artifact = sample_artifact().model_copy(update={"claim": sample_draft({"requires_gate": True})})

    audit_analyst_artifact(artifact)


def test_audit_rejects_bare_numeric_final_payloads() -> None:
    claim = sample_draft("draft").model_copy(update={"decision": "ratified", "decided_by": "senior", "final": {"probability": 0.55}})
    artifact = sample_artifact().model_copy(update={"claim": claim})

    with pytest.raises(AuditError, match="bare numeric"):
        audit_analyst_artifact(artifact)


def test_audit_rejects_bare_numeric_senior_decision_final_payload() -> None:
    package = collect_ratifiables(sample_artifact(), ticker="AAPL", as_of=date(2026, 6, 30), header=header("M3.1"))
    item_id = package.review_items[0].id
    decisions = SeniorDecisionPackage(
        header=header("M3.1"),
        ticker="AAPL",
        as_of=date(2026, 6, 30),
        decided_by="senior",
        required_item_ids=[item_id],
        decisions={item_id: SeniorDecision(decision="ratified", final={"probability": 0.55}, rationale="adjusted")},
    )

    with pytest.raises(AuditError, match="bare numeric"):
        audit_senior_decision_package(decisions)


def test_collect_ratifiables_preserves_paths_ids_evidence_and_checklist() -> None:
    artifact = sample_artifact()

    package_a = collect_ratifiables(artifact, ticker="AAPL", as_of=date(2026, 6, 30), header=header("M3.1"))
    package_b = collect_ratifiables(artifact, ticker="AAPL", as_of=date(2026, 6, 30), header=header("M3.1"))

    assert len(package_a.review_items) == 1
    item = package_a.review_items[0]
    assert item.source_artifact == "SampleM3Artifact"
    assert item.source_field_path == "SampleM3Artifact.claim"
    assert item.id == package_b.review_items[0].id
    assert item.evidence_refs[0].artifact_path == "runs/AAPL/source.json"
    assert item.checklist_area == "business_quality"


def test_synthetic_multi_ratifiable_artifact_collects_distinct_required_items() -> None:
    artifact = synthetic_multi_artifact()
    package = collect_ratifiables(artifact, ticker="AAPL", as_of=date(2026, 6, 30), header=header("M3.1"))

    ids = [item.id for item in package.review_items]
    paths = [item.source_field_path for item in package.review_items]

    assert len(package.review_items) == 3
    assert len(set(ids)) == 3
    assert paths == [
        "SyntheticMultiRatifiableArtifact.bear.assumption",
        "SyntheticMultiRatifiableArtifact.base.assumption",
        "SyntheticMultiRatifiableArtifact.bull.assumption",
    ]
    with pytest.raises(ValidationError, match="missing required"):
        SeniorDecisionPackage(
            header=header("M3.1"),
            ticker="AAPL",
            as_of=date(2026, 6, 30),
            decided_by="senior",
            required_item_ids=ids,
            decisions={ids[0]: SeniorDecision(decision="ratified", rationale="ok")},
        )


def test_empty_senior_review_package_rejected() -> None:
    with pytest.raises(ValidationError, match="requires review items"):
        SeniorReviewPackage(
            header=header("M3.1"),
            ticker="AAPL",
            as_of=date(2026, 6, 30),
            review_items=[],
            source_artifact_summary={},
        )


def test_ratified_state_is_derived_and_not_serialized() -> None:
    package = collect_ratifiables(sample_artifact(), ticker="AAPL", as_of=date(2026, 6, 30), header=header("M3.1"))

    assert "ratified" not in SeniorReviewPackage.model_fields
    assert "ratified" not in SeniorDecisionPackage.model_fields
    assert package.is_ratified is False
    payload = m3_model_to_payload(package)
    assert "ratified" not in payload
    assert "is_ratified" not in payload


def test_complete_senior_decision_package_accepted() -> None:
    package = collect_ratifiables(sample_artifact(), ticker="AAPL", as_of=date(2026, 6, 30), header=header("M3.1"))
    item_id = package.review_items[0].id
    decisions = SeniorDecisionPackage(
        header=header("M3.1"),
        ticker="AAPL",
        as_of=date(2026, 6, 30),
        decided_by="senior",
        required_item_ids=[item_id],
        decisions={item_id: SeniorDecision(decision="ratified", final="accepted", rationale="ok")},
    )

    assert decisions.is_complete is True
    payload = m3_model_to_payload(decisions)
    assert "ratified" not in payload
    assert "is_complete" not in payload


def test_deterministic_fakes_are_distinct_and_senior_has_no_llm_reference() -> None:
    llm = FakeLLM(model_handle="analyst-family")
    senior = FakeSenior(senior_handle="senior-family")

    assert llm is not senior
    assert llm.model_handle != senior.senior_handle
    assert "llm" not in inspect.signature(FakeSenior).parameters
    assert not any("llm" in name.lower() for name in vars(senior))
    assert llm.complete("draft", context={"ticker": "AAPL"}) == llm.complete("draft", context={"ticker": "AAPL"})
    assert senior.gate({"ticker": "AAPL"}) == senior.gate({"ticker": "AAPL"})
    assert senior.ratify({"required_item_ids": ["a", "b"]}) == senior.ratify({"required_item_ids": ["a", "b"]})


def test_full_offline_construct_audit_store_collect_path_is_deterministic(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    llm = FakeLLM()
    senior = FakeSenior()
    artifact = sample_artifact()

    audit_analyst_artifact(artifact)
    storage.put_json("runs/AAPL/2026-06-30/m3_sample.json", m3_model_to_payload(artifact))
    assert storage.get_json("runs/AAPL/2026-06-30/m3_sample.json") == m3_model_to_payload(artifact)

    package_a = collect_ratifiables(artifact, ticker="AAPL", as_of=date(2026, 6, 30), header=header("M3.1"))
    package_b = collect_ratifiables(artifact, ticker="AAPL", as_of=date(2026, 6, 30), header=header("M3.1"))
    audit_senior_review_package(package_a)

    assert llm is not senior
    assert not any("llm" in name.lower() for name in vars(senior))
    assert m3_model_to_payload(package_a) == m3_model_to_payload(package_b)
    assert llm.complete("draft", context={"ticker": "AAPL"}) == llm.complete("draft", context={"ticker": "AAPL"})
    assert senior.ratify({"required_item_ids": [item.id for item in package_a.review_items]}) == senior.ratify(
        {"required_item_ids": [item.id for item in package_a.review_items]}
    )


def test_accountant_bundle_shape_validation(tmp_path) -> None:
    bundle = make_bundle(
        tmp_path,
        "spine",
        skill_text="""# SKILL: B-2 Spine
type: accountant
outputs: Spine
no_llm: true
llm_dependency: false
""",
    )
    validate_skill_bundle(bundle, expected_role="accountant")

    bad = make_bundle(
        tmp_path,
        "bad_accountant",
        skill_text="""# SKILL: bad
type: accountant
outputs: Spine
no_llm: true
llm_dependency: true
""",
    )
    with pytest.raises(BundleValidationError, match="LLM dependency"):
        validate_skill_bundle(bad, expected_role="accountant")


def test_analyst_bundle_shape_validation(tmp_path) -> None:
    bundle = make_bundle(
        tmp_path,
        "business",
        analyst=True,
        skill_text="""# SKILL: C-1 Business
type: analyst
outputs: AnalystDraft
output_contract: AnalystDraft
no_llm: false
llm_dependency: true
""",
    )
    validate_skill_bundle(bundle, expected_role="analyst")

    assertion_bundle = make_bundle(
        tmp_path,
        "assertion_business",
        analyst=True,
        skill_text="""# SKILL: C-1 Business
type: analyst
outputs: FinalBusinessAssertion
output_contract: FinalBusinessAssertion
no_llm: false
llm_dependency: true
""",
    )
    with pytest.raises(BundleValidationError, match="ratifiable"):
        validate_skill_bundle(assertion_bundle, expected_role="analyst")


def test_analyst_bundle_validation_rejects_missing_prompt_and_eval(tmp_path) -> None:
    missing_prompt = make_bundle(
        tmp_path,
        "missing_prompt",
        analyst=True,
        include_prompt=False,
        skill_text="""# SKILL: C-1 Business
type: analyst
outputs: AnalystDraft
output_contract: AnalystDraft
no_llm: false
llm_dependency: true
""",
    )
    with pytest.raises(BundleValidationError, match="prompt.md"):
        validate_skill_bundle(missing_prompt, expected_role="analyst")

    missing_eval = make_bundle(
        tmp_path,
        "missing_eval",
        analyst=True,
        include_eval=False,
        skill_text="""# SKILL: C-1 Business
type: analyst
outputs: AnalystDraft
output_contract: AnalystDraft
no_llm: false
llm_dependency: true
""",
    )
    with pytest.raises(BundleValidationError, match="cases.jsonl|eval runner"):
        validate_skill_bundle(missing_eval, expected_role="analyst")


def sample_artifact() -> SampleM3Artifact:
    return SampleM3Artifact(header=header("C-test"), ticker="AAPL", claim=sample_draft())


def synthetic_multi_artifact() -> SyntheticMultiRatifiableArtifact:
    return SyntheticMultiRatifiableArtifact(
        header=header("C-test"),
        ticker="AAPL",
        bear=SyntheticDriver(name="bear", assumption=sample_draft("bear margin compresses")),
        base=SyntheticDriver(name="base", assumption=sample_draft("base growth continues")),
        bull=SyntheticDriver(name="bull", assumption=sample_draft("bull services mix expands")),
    )


def sample_draft(draft: Any = "durable business model") -> AnalystDraft:
    return AnalystDraft(
        draft=draft,
        evidence_refs=[
            EvidenceRef(
                source_label="EDGAR",
                artifact_path="runs/AAPL/source.json",
                excerpt_or_summary="Segment disclosure supports the claim.",
            )
        ],
        checklist_area="business_quality",
        checklist_rationale="Senior must ratify business-quality judgment.",
    )


def sample_number(value: float) -> Number:
    return Number(
        value=value,
        unit="percent",
        kind="estimate",
        provenance=Provenance(
            tag="computed:test_probability",
            form="computed",
            period="M3.1",
            accession=None,
            source_name="test",
            retrieved_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
        ),
        derivation="test fixture estimate; inputs: synthetic wrapped Number",
    )


def header(produced_by: str) -> Header:
    return Header(schema_version="1.0", produced_by=produced_by, produced_at=datetime(2026, 6, 30, tzinfo=timezone.utc))


def make_bundle(
    tmp_path: Path,
    name: str,
    *,
    skill_text: str,
    analyst: bool = False,
    include_prompt: bool = True,
    include_eval: bool = True,
) -> Path:
    bundle = tmp_path / name
    bundle.mkdir()
    (bundle / "SKILL.md").write_text(skill_text, encoding="utf-8")
    (bundle / f"{name}.py").write_text("# fixture\n", encoding="utf-8")
    (bundle / "resolver.entry").write_text(name, encoding="utf-8")
    if analyst and include_prompt:
        (bundle / "prompt.md").write_text("prompt", encoding="utf-8")
    if analyst and include_eval:
        eval_dir = bundle / "eval"
        eval_dir.mkdir()
        (eval_dir / "cases.jsonl").write_text("{}\n", encoding="utf-8")
        (eval_dir / f"eval_{name}.py").write_text("# fixture\n", encoding="utf-8")
    return bundle
