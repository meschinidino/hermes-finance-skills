from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from skills._primitives import Header, Number, Provenance
from skills.audit import AuditError, audit_senior_review_package
from skills.bundle_validation import BundleValidationError, validate_skill_bundle
from skills.config import load_config
from skills.data.cost_of_capital.cost_of_capital import build_cost_of_capital_inputs
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.data.price.price import fetch_price
from skills.accountant_artifacts import MethodDirective, MethodIndicator
from skills.analyst_artifacts import ReviewItem, collect_ratifiables
from skills.research.scenarios.scenarios import (
    DIRECT_DRIVER_METRIC_MAP,
    ScenarioSetArtifact,
    audit_scenario_set,
    build_scenario_set_artifact,
)
from skills.serialization import artifact_model_to_payload
from skills.storage import LocalStorage
from skills.valuation.dcf.dcf import build_dcf_artifacts
from skills.valuation.method_router.method_router import route_method
from skills.valuation.normalize.normalize import normalize_financials


RUN_DATE = date(2026, 6, 30)
RUN_DIR = "runs/AAPL/2026-06-30"


def test_scenarios_bundle_passes_real_analyst_shape_validation() -> None:
    validate_skill_bundle(Path("skills/research/scenarios"), expected_role="analyst")


def test_bundle_validation_rejects_missing_eval_and_no_llm_true(tmp_path) -> None:
    bundle = tmp_path / "scenarios"
    (bundle / "eval").mkdir(parents=True)
    (bundle / "SKILL.md").write_text(
        """# SKILL: C-4 Scenarios
type: analyst
outputs: ScenarioSetArtifact containing needs_ratification AnalystDraft fields
output_contract: ScenarioSetArtifact with AnalystDraft needs_ratification drafts
no_llm: true
llm_dependency: true
""",
        encoding="utf-8",
    )
    (bundle / "scenarios.py").write_text("# fixture\n", encoding="utf-8")
    (bundle / "prompt.md").write_text("prompt\n", encoding="utf-8")
    (bundle / "resolver.entry").write_text("scenarios\n", encoding="utf-8")
    (bundle / "eval" / "cases.jsonl").write_text("{}\n", encoding="utf-8")

    with pytest.raises(BundleValidationError, match="no_llm"):
        validate_skill_bundle(bundle, expected_role="analyst")


def test_valid_dcf_scenario_artifact_audits_stores_and_collects_three_probability_items(tmp_path) -> None:
    storage, artifact = _filed_dcf_scenario_set(tmp_path)

    audit_scenario_set(artifact, storage=storage, path=f"{RUN_DIR}/scenarios.json")
    package_a = collect_ratifiables(
        artifact,
        ticker="AAPL",
        as_of=RUN_DATE,
        header=_header("C-4-review"),
        source_artifact=f"{RUN_DIR}/scenarios.json",
    )
    package_b = collect_ratifiables(
        artifact,
        ticker="AAPL",
        as_of=RUN_DATE,
        header=_header("C-4-review"),
        source_artifact=f"{RUN_DIR}/scenarios.json",
    )
    audit_senior_review_package(package_a)

    assert storage.get_json(f"{RUN_DIR}/scenarios.json")["header"]["produced_by"] == "C-4"
    assert [item.source_field_path for item in package_a.review_items] == [
        "ScenarioSetArtifact.scenarios[0].probability",
        "ScenarioSetArtifact.scenarios[1].probability",
        "ScenarioSetArtifact.scenarios[2].probability",
    ]
    assert len({item.id for item in package_a.review_items}) == 3
    assert [item.id for item in package_a.review_items] == [item.id for item in package_b.review_items]
    assert all(item.source_artifact == f"{RUN_DIR}/scenarios.json" for item in package_a.review_items)
    assert all(item.evidence_refs for item in package_a.review_items)
    assert {item.checklist_area for item in package_a.review_items} == {
        "scenario_probability_bear",
        "scenario_probability_base",
        "scenario_probability_bull",
    }
    assert all(item.decision is None for item in package_a.review_items)


def test_partial_scenario_probability_decisions_cannot_ratify_package(tmp_path) -> None:
    _, artifact = _filed_dcf_scenario_set(tmp_path)
    package = collect_ratifiables(artifact, ticker="AAPL", as_of=RUN_DATE, header=_header("C-4-review"))

    base_only = _package_with_decisions(package.review_items, decided_paths={"ScenarioSetArtifact.scenarios[1].probability"})
    bear_and_base = _package_with_decisions(
        package.review_items,
        decided_paths={"ScenarioSetArtifact.scenarios[0].probability", "ScenarioSetArtifact.scenarios[1].probability"},
    )
    all_three = _package_with_decisions(package.review_items, decided_paths={item.source_field_path for item in package.review_items})

    assert base_only.is_ratified is False
    assert bear_and_base.is_ratified is False
    assert all_three.is_ratified is True


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"bear": -0.1}, "negative"),
        ({"base": 1.1}, "exceeds 1"),
        ({"bear": 0.3, "base": 0.6, "bull": 0.5}, "sum"),
    ],
)
def test_probability_coherence_failures_are_rejected(tmp_path, updates, message) -> None:
    storage, artifact = _filed_dcf_scenario_set(tmp_path)
    invalid = _with_probabilities(artifact, updates)

    with pytest.raises(AuditError, match=message):
        audit_scenario_set(invalid, storage=storage)


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"bear": 100.0, "base": 100.0}, "bear must be less"),
        ({"bear": 110.0, "base": 100.0}, "bear must be less"),
        ({"base": 150.0, "bull": 150.0}, "base must be less"),
        ({"base": 160.0, "bull": 150.0}, "base must be less"),
    ],
)
def test_value_ordering_failures_are_rejected(tmp_path, values, message) -> None:
    storage, artifact = _filed_dcf_scenario_set(tmp_path)
    invalid = _with_values(artifact, values)

    with pytest.raises(AuditError, match=message):
        audit_scenario_set(invalid, storage=storage)


def test_driver_binding_reads_filed_valuation_shape_not_copied_allow_list(tmp_path) -> None:
    storage, artifact = _filed_dcf_scenario_set(tmp_path)
    valuation_payload = storage.get_json(f"{RUN_DIR}/valuation_range.json")
    for scenario in valuation_payload["scenarios"]:
        for assumption in scenario["assumptions"]:
            if assumption["driver"] == "revenue_growth":
                assumption["driver"] = "artifact_growth"
    storage.put_json(f"{RUN_DIR}/valuation_range.json", valuation_payload)
    expectations_payload = storage.get_json(f"{RUN_DIR}/expectations_line.json")
    expectations_payload["implied"]["artifact_growth"] = expectations_payload["implied"].pop("revenue_growth")
    storage.put_json(f"{RUN_DIR}/expectations_line.json", expectations_payload)

    with pytest.raises(AuditError, match="unbound driver: revenue_growth"):
        audit_scenario_set(artifact, storage=storage)


def test_driver_binding_accepts_real_expectations_line_driver_when_metric_mapping_exists(tmp_path) -> None:
    storage, artifact = _filed_dcf_scenario_set(tmp_path)
    original_map = dict(DIRECT_DRIVER_METRIC_MAP)
    DIRECT_DRIVER_METRIC_MAP["revenue_growth_midpoint"] = "revenue_growth"
    try:
        updated = _with_assumption_driver(artifact, "revenue_growth_midpoint")
        audit_scenario_set(updated, storage=storage)
    finally:
        DIRECT_DRIVER_METRIC_MAP.clear()
        DIRECT_DRIVER_METRIC_MAP.update(original_map)


def test_unrecognized_decorative_driver_is_rejected(tmp_path) -> None:
    storage, artifact = _filed_dcf_scenario_set(tmp_path)
    invalid = _with_assumption_driver(artifact, "narrative_momentum")

    with pytest.raises(AuditError, match="unbound driver: narrative_momentum"):
        audit_scenario_set(invalid, storage=storage)


def test_driver_with_no_metric_mapping_fails_closed_even_if_filed_driver_exists(tmp_path) -> None:
    storage, artifact = _filed_dcf_scenario_set(tmp_path)
    invalid = _with_assumption_driver(artifact, "sales_to_capital")

    with pytest.raises(AuditError, match="no direct base-rate metric mapping"):
        audit_scenario_set(invalid, storage=storage)


def test_base_rate_anchor_must_resolve_to_b5_with_matching_metric(tmp_path) -> None:
    storage, artifact = _filed_dcf_scenario_set(tmp_path)
    missing_anchor = _with_anchor_path(artifact, None)
    with pytest.raises(AuditError, match="missing base-rate anchor"):
        audit_scenario_set(missing_anchor, storage=storage)

    unresolvable = _with_anchor_path(artifact, "runs/AAPL/2026-06-30/missing_base_rate.json")
    with pytest.raises(FileNotFoundError):
        audit_scenario_set(unresolvable, storage=storage)

    storage.put_json("runs/AAPL/2026-06-30/not_b5.json", storage.get_json(f"{RUN_DIR}/method_directive.json"))
    wrong_producer = _with_anchor_path(artifact, "runs/AAPL/2026-06-30/not_b5.json")
    with pytest.raises(AuditError, match="BaseRateResult"):
        audit_scenario_set(wrong_producer, storage=storage)

    anchor_path = artifact.scenarios[0].assumptions[0].base_rate_anchor.artifact_path
    base_rate_payload = storage.get_json(anchor_path)
    base_rate_payload["forecast"]["metric"] = "margin_expansion"
    storage.put_json(anchor_path, base_rate_payload)
    with pytest.raises(AuditError, match="metric mismatch"):
        audit_scenario_set(artifact, storage=storage)


def test_method_directive_must_resolve_to_b6(tmp_path) -> None:
    storage, artifact = _filed_dcf_scenario_set(tmp_path)
    invalid = artifact.model_copy(update={"method_directive_path": ""})
    with pytest.raises(AuditError, match="method directive reference"):
        audit_scenario_set(invalid, storage=storage)

    storage.put_json("runs/AAPL/2026-06-30/not_b6.json", storage.get_json(f"{RUN_DIR}/valuation_range.json"))
    invalid = artifact.model_copy(update={"method_directive_path": "runs/AAPL/2026-06-30/not_b6.json"})
    with pytest.raises(AuditError):
        audit_scenario_set(invalid, storage=storage)


def test_non_dcf_deferred_artifact_is_substantive_and_does_not_force_dcf_drivers(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    directive = _non_dcf_directive()
    storage.put_json(f"{RUN_DIR}/method_directive.json", artifact_model_to_payload(directive))
    artifact = build_scenario_set_artifact(
        ticker="AAPL",
        as_of=RUN_DATE,
        schema_version="1.0",
        storage=storage,
        run_dir=RUN_DIR,
        method_directive_path=f"{RUN_DIR}/method_directive.json",
    )

    audit_scenario_set(artifact, storage=storage)

    assert artifact.status == "method_deferred"
    assert artifact.source_evidence_summary["deferred_method"] == "rNPV"
    assert all(scenario.probability is not None for scenario in artifact.scenarios)
    assert all(scenario.assumptions[0].driver == "rNPV_scenario_frame" for scenario in artifact.scenarios)
    assert all(scenario.assumptions[0].evidence_refs for scenario in artifact.scenarios)

    forced_dcf = _with_assumption_driver(artifact, "revenue_growth")
    with pytest.raises(AuditError, match="DCF-only driver revenue_growth"):
        audit_scenario_set(forced_dcf, storage=storage)


def _filed_dcf_scenario_set(tmp_path) -> tuple[LocalStorage, ScenarioSetArtifact]:
    storage = LocalStorage(tmp_path)
    config = load_config("config/conventions.yaml")
    edgar = fetch_edgar_facts("AAPL")
    price = fetch_price("AAPL", edgar=edgar, as_of=RUN_DATE)
    cost_of_capital = build_cost_of_capital_inputs("AAPL", config, edgar=edgar, price=price, as_of=RUN_DATE)
    normalized = normalize_financials(edgar)
    directive = route_method(
        normalized,
        edgar,
        config,
        industry_classification="Technology",
        schema_version=config.schema_version,
        produced_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
    )
    valuation, expectations = build_dcf_artifacts(normalized, edgar, price, cost_of_capital, config)
    storage.put_json(f"{RUN_DIR}/method_directive.json", artifact_model_to_payload(directive))
    storage.put_json(f"{RUN_DIR}/valuation_range.json", artifact_model_to_payload(valuation))
    storage.put_json(f"{RUN_DIR}/expectations_line.json", artifact_model_to_payload(expectations))
    artifact = build_scenario_set_artifact(
        ticker="AAPL",
        as_of=RUN_DATE,
        schema_version=config.schema_version,
        storage=storage,
        run_dir=RUN_DIR,
        method_directive_path=f"{RUN_DIR}/method_directive.json",
        valuation_range_path=f"{RUN_DIR}/valuation_range.json",
        expectations_line_path=f"{RUN_DIR}/expectations_line.json",
    )
    return storage, artifact


def _package_with_decisions(items: list[ReviewItem], *, decided_paths: set[str]):
    decided = []
    for item in items:
        if item.source_field_path in decided_paths:
            decided.append(item.model_copy(update={"decision": "ratified", "decided_by": "senior"}))
        else:
            decided.append(item)
    from skills.analyst_artifacts import SeniorReviewPackage

    return SeniorReviewPackage(
        header=_header("C-4-review"),
        ticker="AAPL",
        as_of=RUN_DATE,
        review_items=decided,
        source_artifact_summary={"scenarios": "ScenarioSetArtifact"},
    )


def _with_probabilities(artifact: ScenarioSetArtifact, updates: dict[str, float]) -> ScenarioSetArtifact:
    scenarios = []
    for scenario in artifact.scenarios:
        if scenario.name not in updates:
            scenarios.append(scenario)
            continue
        probability = scenario.probability.draft["probability"].model_copy(update={"value": updates[scenario.name]})
        draft = dict(scenario.probability.draft)
        draft["probability"] = probability
        scenarios.append(scenario.model_copy(update={"probability": scenario.probability.model_copy(update={"draft": draft})}))
    return artifact.model_copy(update={"scenarios": scenarios})


def _with_values(artifact: ScenarioSetArtifact, updates: dict[str, float]) -> ScenarioSetArtifact:
    scenarios = []
    for scenario in artifact.scenarios:
        if scenario.name not in updates:
            scenarios.append(scenario)
            continue
        scenarios.append(scenario.model_copy(update={"value": scenario.value.model_copy(update={"value": updates[scenario.name]})}))
    return artifact.model_copy(update={"scenarios": scenarios})


def _with_assumption_driver(artifact: ScenarioSetArtifact, driver: str) -> ScenarioSetArtifact:
    scenarios = []
    for scenario in artifact.scenarios:
        assumptions = [assumption.model_copy(update={"driver": driver}) for assumption in scenario.assumptions]
        scenarios.append(scenario.model_copy(update={"assumptions": assumptions}))
    return artifact.model_copy(update={"scenarios": scenarios})


def _with_anchor_path(artifact: ScenarioSetArtifact, path: str | None) -> ScenarioSetArtifact:
    scenarios = []
    for index, scenario in enumerate(artifact.scenarios):
        if index != 0:
            scenarios.append(scenario)
            continue
        assumption = scenario.assumptions[0]
        anchor = None if path is None else assumption.base_rate_anchor.model_copy(update={"artifact_path": path})
        scenarios.append(scenario.model_copy(update={"assumptions": [assumption.model_copy(update={"base_rate_anchor": anchor})]}))
    return artifact.model_copy(update={"scenarios": scenarios})


def _non_dcf_directive() -> MethodDirective:
    produced = datetime(2026, 6, 30, tzinfo=timezone.utc)
    return MethodDirective(
        header=_header("B-6"),
        ticker="AAPL",
        asset_class="optionality",
        method="rNPV",
        routing_reason="Optionality fixture lacks operating-profit base and must not be forced into plain DCF.",
        indicators=[
            MethodIndicator(
                name="pre_revenue_fixture",
                value=True,
                source="test fixture",
            ),
            MethodIndicator(
                name="latest_revenue",
                value=_number(0.0, "computed:non_dcf_revenue", "USD_millions", produced),
                source="test fixture",
            ),
        ],
        implemented=False,
        fallback_behavior="file directive and defer rNPV; no substitute DCF",
    )


def _number(value: float, tag: str, unit: str, produced: datetime) -> Number:
    return Number(
        value=value,
        unit=unit,
        kind="estimate",
        provenance=Provenance(tag=tag, form="computed", period="M3.4", accession=None, source_name="test", retrieved_at=produced),
        derivation=f"test fixture; inputs: {tag}",
    )


def _header(produced_by: str) -> Header:
    return Header(schema_version="1.0", produced_by=produced_by, produced_at=datetime(2026, 6, 30, tzinfo=timezone.utc))
