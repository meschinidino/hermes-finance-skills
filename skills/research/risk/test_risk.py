from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from resolver import analyze
from skills._primitives import Header, Number, Provenance
from skills.analyst_artifacts import AnalystDraft, collect_ratifiables
from skills.audit import AuditError, audit_senior_review_package
from skills.bundle_validation import validate_skill_bundle
from skills.research.risk.risk import (
    KillMetricDraft,
    ModellableRiskDraft,
    RiskArtifact,
    TailRiskDraft,
    audit_risk_artifact,
)
from skills.storage import LocalStorage

RUN_DATE = date(2026, 7, 1)
RUN_DIR = "runs/AAPL/2026-07-01"


def test_risk_bundle_passes_real_analyst_shape_validation() -> None:
    validate_skill_bundle(Path("skills/research/risk"), expected_role="analyst")


def test_valid_risk_artifact_audits_stores_and_collects_review_items(tmp_path) -> None:
    storage, artifact = _filed_risk(tmp_path)

    audit_risk_artifact(artifact, storage=storage, path=f"{RUN_DIR}/risk.json")
    package_a = collect_ratifiables(
        artifact,
        ticker="AAPL",
        as_of=RUN_DATE,
        header=_header("C-6-review"),
        source_artifact=f"{RUN_DIR}/risk.json",
    )
    package_b = collect_ratifiables(
        artifact,
        ticker="AAPL",
        as_of=RUN_DATE,
        header=_header("C-6-review"),
        source_artifact=f"{RUN_DIR}/risk.json",
    )
    audit_senior_review_package(package_a)

    assert storage.get_json(f"{RUN_DIR}/risk.json")["header"]["produced_by"] == "C-6"
    assert [item.source_field_path for item in package_a.review_items] == [
        "RiskArtifact.premortem",
        "RiskArtifact.bear_case_narrative",
        "RiskArtifact.modellable_risks",
        "RiskArtifact.tail_risks",
        "RiskArtifact.kill_metric",
        "RiskArtifact.risk_completeness",
    ]
    assert [item.id for item in package_a.review_items] == [item.id for item in package_b.review_items]
    assert all(item.source_artifact == f"{RUN_DIR}/risk.json" for item in package_a.review_items)
    assert all(item.evidence_refs for item in package_a.review_items)
    assert all(item.decision is None for item in package_a.review_items)


@pytest.mark.parametrize(
    ("field_name", "replacement", "message"),
    [
        ("premortem", "This is a clear buy and cannot lose.", "loses money|purely bullish"),
        ("premortem", "The downside is vague.", "concrete time horizon"),
        ("bear_case_narrative", "competition; regulation; recession", "generic downside list|skeptic frame"),
        (
            "bear_case_narrative",
            "The downside exists because demand weakens.",
            "skeptic frame|persist",
        ),
        ("risk_completeness", "Decision-ready.", "unverifiable|confidence"),
    ],
)
def test_risk_specific_text_failures_are_rejected(tmp_path, field_name, replacement, message) -> None:
    storage, artifact = _filed_risk(tmp_path)
    draft = getattr(artifact, field_name)
    invalid = artifact.model_copy(update={field_name: draft.model_copy(update={"draft": replacement})})

    with pytest.raises(AuditError, match=message):
        audit_risk_artifact(invalid, storage=storage)


def test_common_analyst_audit_rejects_empty_evidence_before_risk_rules(tmp_path) -> None:
    storage, artifact = _filed_risk(tmp_path)
    invalid = artifact.model_copy(update={"premortem": artifact.premortem.model_copy(update={"evidence_refs": []})})

    with pytest.raises(AuditError, match="missing evidence refs"):
        audit_risk_artifact(invalid, storage=storage)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"impact": None}, "missing impact"),
        ({"likelihood": None}, "missing likelihood"),
        ({"modeled_effect": ""}, "missing modeled effect"),
        ({"evidence_refs": []}, "missing evidence"),
    ],
)
def test_modellable_risk_structure_failures_are_rejected(tmp_path, updates, message) -> None:
    storage, artifact = _filed_risk(tmp_path)
    risks = list(artifact.modellable_risks.draft)
    risks[0] = ModellableRiskDraft.model_construct(**{**risks[0].model_dump(), **updates})
    invalid = artifact.model_copy(update={"modellable_risks": artifact.modellable_risks.model_copy(update={"draft": risks})})

    with pytest.raises(AuditError, match=message):
        audit_risk_artifact(invalid, storage=storage)


def test_tail_risks_are_required_and_separate_from_modellable_matrix(tmp_path) -> None:
    storage, artifact = _filed_risk(tmp_path)
    empty_tail = artifact.model_copy(update={"tail_risks": artifact.tail_risks.model_copy(update={"draft": []})})
    duplicate_tail = TailRiskDraft(
        risk=artifact.modellable_risks.draft[0].risk,
        why_not_modelled="Discontinuous legal remedy makes modelling inappropriate.",
        monitoring_signal="New ruling",
        evidence_refs=artifact.tail_risks.draft[0].evidence_refs,
    )
    duplicate = artifact.model_copy(update={"tail_risks": artifact.tail_risks.model_copy(update={"draft": [duplicate_tail]})})
    scored_tail = TailRiskDraft.model_construct(
        risk="Unmodelled shock",
        why_not_modelled="Discontinuous shock.",
        monitoring_signal="New disclosure",
        evidence_refs=artifact.tail_risks.draft[0].evidence_refs,
    )
    object.__setattr__(scored_tail, "likelihood", "low")
    scored = artifact.model_copy(update={"tail_risks": artifact.tail_risks.model_copy(update={"draft": [scored_tail]})})

    with pytest.raises(AuditError, match="tail-risk bucket is empty"):
        audit_risk_artifact(empty_tail, storage=storage)
    with pytest.raises(AuditError, match="duplicate risk across modellable and tail"):
        audit_risk_artifact(duplicate, storage=storage)
    with pytest.raises(AuditError, match="must not carry likelihood"):
        audit_risk_artifact(scored, storage=storage)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"metric": ""}, "missing metric name"),
        ({"threshold_direction": None}, "missing threshold direction"),
        ({"threshold_value": None}, "missing threshold value"),
        ({"check_by": None}, "missing check_by"),
        ({"thesis_action": ""}, "missing thesis action"),
        ({"evidence_refs": []}, "missing evidence"),
    ],
)
def test_kill_metric_falsifiability_is_field_based(tmp_path, updates, message) -> None:
    storage, artifact = _filed_risk(tmp_path)
    metric = artifact.kill_metric.draft.model_copy(update=updates)
    invalid = artifact.model_copy(update={"kill_metric": artifact.kill_metric.model_copy(update={"draft": metric})})

    with pytest.raises(AuditError, match=message):
        audit_risk_artifact(invalid, storage=storage)


def test_bear_case_value_must_be_provenance_complete_and_source_bound(tmp_path) -> None:
    storage, artifact = _filed_risk(tmp_path)
    missing_derivation = artifact.bear_case_value.model_copy(update={"derivation": "computed without source"})
    bad_unit = artifact.bear_case_value.model_copy(update={"unit": "ratio"})

    with pytest.raises(AuditError, match="derivation missing input references"):
        audit_risk_artifact(artifact.model_copy(update={"bear_case_value": missing_derivation}), storage=storage)
    with pytest.raises(AuditError, match="incompatible unit"):
        audit_risk_artifact(artifact.model_copy(update={"bear_case_value": bad_unit}), storage=storage)


def test_bear_case_value_must_reconcile_to_filed_c4_bear_value(tmp_path) -> None:
    storage, artifact = _filed_risk(tmp_path)
    scenarios = storage.get_json(artifact.source_artifact_paths["scenarios"])
    bear_value = next(scenario["value"]["value"] for scenario in scenarios["scenarios"] if scenario["name"] == "bear")
    base_value = next(scenario["value"]["value"] for scenario in scenarios["scenarios"] if scenario["name"] == "base")

    audit_risk_artifact(artifact, storage=storage)
    divergent = artifact.bear_case_value.model_copy(update={"value": (bear_value + base_value) / 2.0})

    with pytest.raises(AuditError, match="does not reconcile to filed C-4 bear scenario"):
        audit_risk_artifact(artifact.model_copy(update={"bear_case_value": divergent}), storage=storage)


def test_bear_case_value_requires_resolvable_filed_c4_scenarios(tmp_path) -> None:
    storage, artifact = _filed_risk(tmp_path)
    invalid = artifact.model_copy(
        update={
            "source_artifact_paths": {
                **artifact.source_artifact_paths,
                "scenarios": f"{RUN_DIR}/missing_scenarios.json",
            }
        }
    )

    with pytest.raises(AuditError, match="risk scenarios reference did not resolve|missing_scenarios"):
        audit_risk_artifact(invalid, storage=storage)


def test_bear_case_value_must_be_below_filed_c4_base_value(tmp_path) -> None:
    storage, artifact = _filed_risk(tmp_path)
    scenarios = storage.get_json(artifact.source_artifact_paths["scenarios"])
    base_value = next(scenario["value"]["value"] for scenario in scenarios["scenarios"] if scenario["name"] == "base")
    too_high = artifact.bear_case_value.model_copy(update={"value": base_value + 1.0})

    with pytest.raises(AuditError, match="must be below filed C-4 base scenario"):
        audit_risk_artifact(artifact.model_copy(update={"bear_case_value": too_high}), storage=storage)


def test_bare_numeric_bear_case_value_is_rejected_by_schema(tmp_path) -> None:
    _, artifact = _filed_risk(tmp_path)

    with pytest.raises(Exception):
        RiskArtifact.model_validate({**artifact.model_dump(), "bear_case_value": 1.0})


def test_nested_risk_evidence_refs_must_resolve_even_when_aggregate_evidence_is_valid(tmp_path) -> None:
    storage, artifact = _filed_risk(tmp_path)
    risks = list(artifact.modellable_risks.draft)
    bad_evidence = risks[0].evidence_refs[0].model_copy(update={"artifact_path": f"{RUN_DIR}/missing_source.json"})
    risks[0] = risks[0].model_copy(update={"evidence_refs": [bad_evidence]})
    invalid = artifact.model_copy(update={"modellable_risks": artifact.modellable_risks.model_copy(update={"draft": risks})})

    with pytest.raises(AuditError, match="evidence ref unresolvable"):
        audit_risk_artifact(invalid, storage=storage)


def test_resolver_reaches_risk_on_go_path_and_does_not_ratify(tmp_path) -> None:
    payload = analyze("AAPL", as_of=RUN_DATE, storage=LocalStorage(tmp_path))

    assert payload["risk"]["header"]["produced_by"] == "C-6"
    assert payload["risk"]["tail_risks"]["draft"]
    assert payload["risk"]["bear_case_value"]["provenance"]["form"] == "computed"
    assert all(item["decision"] is None for item in payload["risk_review_package"]["review_items"])


def test_resolver_no_go_stops_before_risk(tmp_path) -> None:
    class NoGoSenior:
        model_family = "offline-senior"

        def gate(self, package):
            return {"decision": "NO-GO", "rationale": "test halt", "decided_by": "test-senior"}

        def ratify(self, package):
            raise AssertionError("ratify must not be called")

    payload = analyze("AAPL", as_of=RUN_DATE, storage=LocalStorage(tmp_path), senior=NoGoSenior())

    assert payload["status"] == "halted"
    assert "risk" not in payload


def _filed_risk(tmp_path) -> tuple[LocalStorage, RiskArtifact]:
    storage = LocalStorage(tmp_path)
    analyze("AAPL", as_of=RUN_DATE, storage=storage)
    artifact = RiskArtifact.model_validate(storage.get_json(f"{RUN_DIR}/risk.json"))
    return storage, artifact


def _header(produced_by: str):
    return Header(schema_version="1.0", produced_by=produced_by, produced_at=datetime(2026, 7, 1, tzinfo=timezone.utc))
