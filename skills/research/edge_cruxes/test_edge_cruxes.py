from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from resolver import analyze
from skills._primitives import Header
from skills.audit import AuditError, audit_analyst_artifact, audit_artifact, audit_m1_handoff, audit_senior_review_package
from skills.bundle_validation import BundleValidationError, validate_skill_bundle
from skills.config import load_config
from skills.data.cost_of_capital.cost_of_capital import build_cost_of_capital_inputs
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.data.price.price import fetch_price
from skills.analyst_artifacts import collect_ratifiables
from skills.research.business.business import build_business_artifact
from skills.research.capalloc.capalloc import build_capalloc_artifact
from skills.research.edge_cruxes.edge_cruxes import (
    EdgeCruxesArtifact,
    audit_edge_cruxes,
    build_edge_cruxes_artifact,
)
from skills.research.moat.moat import build_moat_artifact
from skills.research.scenarios.scenarios import audit_scenario_set, build_scenario_set_artifact
from skills.serialization import artifact_model_to_payload
from skills.storage import LocalStorage
from skills.synthesis.handoff.handoff import build_handoff
from skills.valuation.dcf.dcf import build_dcf_artifacts
from skills.valuation.method_router.method_router import route_method
from skills.valuation.normalize.normalize import normalize_financials
from skills.valuation.screens.screens import build_gate_card
from skills.valuation.spine.spine import build_spine

RUN_DATE = date(2026, 7, 1)
RUN_DIR = "runs/AAPL/2026-07-01"


def test_edge_cruxes_bundle_passes_real_analyst_shape_validation() -> None:
    validate_skill_bundle(Path("skills/research/edge_cruxes"), expected_role="analyst")


def test_bundle_validation_rejects_missing_eval_and_no_llm_true(tmp_path) -> None:
    bundle = tmp_path / "edge_cruxes"
    (bundle / "eval").mkdir(parents=True)
    (bundle / "SKILL.md").write_text(
        """# SKILL: C-5 Edge & Cruxes
type: analyst
outputs: EdgeCruxesArtifact containing needs_ratification AnalystDraft fields
output_contract: EdgeCruxesArtifact with AnalystDraft needs_ratification drafts
implementation: edge_cruxes.py
no_llm: true
llm_dependency: true
""",
        encoding="utf-8",
    )
    (bundle / "edge_cruxes.py").write_text("# fixture\n", encoding="utf-8")
    (bundle / "prompt.md").write_text("prompt\n", encoding="utf-8")
    (bundle / "resolver.entry").write_text("edge_cruxes\n", encoding="utf-8")
    (bundle / "eval" / "cases.jsonl").write_text("{}\n", encoding="utf-8")

    with pytest.raises(BundleValidationError, match="no_llm"):
        validate_skill_bundle(bundle, expected_role="analyst")


def test_valid_edge_cruxes_artifact_audits_stores_and_collects_review_items(tmp_path) -> None:
    storage, artifact = _filed_edge_cruxes(tmp_path)

    audit_edge_cruxes(artifact, storage=storage, path=f"{RUN_DIR}/edge_cruxes.json")
    package_a = collect_ratifiables(
        artifact,
        ticker="AAPL",
        as_of=RUN_DATE,
        header=_header("C-5-review"),
        source_artifact=f"{RUN_DIR}/edge_cruxes.json",
    )
    package_b = collect_ratifiables(
        artifact,
        ticker="AAPL",
        as_of=RUN_DATE,
        header=_header("C-5-review"),
        source_artifact=f"{RUN_DIR}/edge_cruxes.json",
    )
    audit_senior_review_package(package_a)

    assert storage.get_json(f"{RUN_DIR}/edge_cruxes.json")["header"]["produced_by"] == "C-5"
    assert [item.source_field_path for item in package_a.review_items] == [
        "EdgeCruxesArtifact.steelman_no_trade",
        "EdgeCruxesArtifact.counterparty",
        "EdgeCruxesArtifact.structural_mispricing",
        "EdgeCruxesArtifact.variant_view",
        "EdgeCruxesArtifact.catalysts",
        "EdgeCruxesArtifact.cruxes",
    ]
    assert [item.id for item in package_a.review_items] == [item.id for item in package_b.review_items]
    assert all(item.source_artifact == f"{RUN_DIR}/edge_cruxes.json" for item in package_a.review_items)
    assert all(item.evidence_refs for item in package_a.review_items)
    assert all(item.decision is None for item in package_a.review_items)


@pytest.mark.parametrize(
    ("field_name", "replacement", "message"),
    [
        ("steelman_no_trade", "This is an obvious buy.", "rational Senior could pass|purely bullish"),
        ("counterparty", "no one", "trivial"),
        ("structural_mispricing", {"asserts_edge": True, "persistence_reason": "It takes time."}, "without mechanism"),
        ("variant_view", "Market misunderstands the business.", "generic market misunderstanding"),
        ("catalysts", [{"event": "market realizes value", "timing": "soon"}], "generic catalyst"),
    ],
)
def test_edge_specific_draft_failures_are_rejected(tmp_path, field_name, replacement, message) -> None:
    storage, artifact = _filed_edge_cruxes(tmp_path)
    draft = getattr(artifact, field_name)
    invalid = artifact.model_copy(update={field_name: draft.model_copy(update={"draft": replacement})})

    with pytest.raises(AuditError, match=message):
        audit_edge_cruxes(invalid, storage=storage)


def test_common_analyst_audit_rejects_empty_evidence_before_edge_rules(tmp_path) -> None:
    storage, artifact = _filed_edge_cruxes(tmp_path)
    invalid = artifact.model_copy(
        update={"counterparty": artifact.counterparty.model_copy(update={"evidence_refs": []})}
    )

    with pytest.raises(AuditError, match="missing evidence refs"):
        audit_edge_cruxes(invalid, storage=storage)


def test_exactly_three_cruxes_are_required(tmp_path) -> None:
    storage, artifact = _filed_edge_cruxes(tmp_path)
    two = artifact.cruxes.model_copy(update={"draft": artifact.cruxes.draft[:2]})
    four = artifact.cruxes.model_copy(update={"draft": [*artifact.cruxes.draft, artifact.cruxes.draft[-1]]})
    wrong_kind = artifact.cruxes.draft[0].model_copy(update={"kind": "pass_falsifier"})
    mixed = artifact.cruxes.model_copy(update={"draft": [wrong_kind, *artifact.cruxes.draft[1:]]})

    with pytest.raises(AuditError, match="exactly three cruxes"):
        audit_edge_cruxes(artifact.model_copy(update={"cruxes": two}), storage=storage)
    with pytest.raises(AuditError, match="exactly three cruxes|duplicate crux"):
        audit_edge_cruxes(artifact.model_copy(update={"cruxes": four}), storage=storage)
    with pytest.raises(AuditError, match="invalid for structural framing"):
        audit_edge_cruxes(artifact.model_copy(update={"cruxes": mixed}), storage=storage)


def test_no_edge_pass_framing_allows_zero_cruxes_without_manufacturing_pressure(tmp_path) -> None:
    storage, artifact = _filed_edge_cruxes(tmp_path)
    valid_no_edge = _as_no_edge_artifact(artifact).model_copy(update={"cruxes": None})

    audit_edge_cruxes(valid_no_edge, storage=storage)


def test_no_edge_pass_framing_accepts_well_formed_pass_falsifier(tmp_path) -> None:
    storage, artifact = _filed_edge_cruxes(tmp_path)
    pass_falsifier = artifact.cruxes.draft[0].model_copy(
        update={
            "kind": "pass_falsifier",
            "claim": "The pass view would change if reported services economics materially exceeded what is already priced.",
        }
    )
    no_edge = _as_no_edge_artifact(artifact).model_copy(
        update={"cruxes": artifact.cruxes.model_copy(update={"draft": [pass_falsifier]})}
    )

    audit_edge_cruxes(no_edge, storage=storage)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"threshold_value": ""}, "missing threshold value"),
        ({"check_by": date(1999, 12, 31)}, "missing check-by date"),
    ],
)
def test_no_edge_pass_framing_rejects_malformed_pass_falsifier(tmp_path, updates, message) -> None:
    storage, artifact = _filed_edge_cruxes(tmp_path)
    pass_falsifier = artifact.cruxes.draft[0].model_copy(
        update={
            "kind": "pass_falsifier",
            "claim": "The pass view would change if reported services economics materially exceeded what is already priced.",
            **updates,
        }
    )
    no_edge = _as_no_edge_artifact(artifact).model_copy(
        update={"cruxes": artifact.cruxes.model_copy(update={"draft": [pass_falsifier]})}
    )

    with pytest.raises(AuditError, match=message):
        audit_edge_cruxes(no_edge, storage=storage)


def test_no_edge_pass_framing_rejects_edge_crux_kind(tmp_path) -> None:
    storage, artifact = _filed_edge_cruxes(tmp_path)
    no_edge = _as_no_edge_artifact(artifact)

    with pytest.raises(AuditError, match="invalid for structural framing"):
        audit_edge_cruxes(no_edge, storage=storage)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"metric": ""}, "missing metric"),
        ({"threshold_value": ""}, "missing threshold value"),
        ({"evidence_refs": [], "missing_data_gap": None}, "missing evidence"),
    ],
)
def test_crux_falsifiability_fields_are_structural_not_keyword_based(tmp_path, updates, message) -> None:
    storage, artifact = _filed_edge_cruxes(tmp_path)
    cruxes = list(artifact.cruxes.draft)
    cruxes[0] = cruxes[0].model_copy(update=updates)
    invalid = artifact.model_copy(update={"cruxes": artifact.cruxes.model_copy(update={"draft": cruxes})})

    with pytest.raises(AuditError, match=message):
        audit_edge_cruxes(invalid, storage=storage)


def test_nested_crux_evidence_refs_must_resolve_even_when_aggregate_evidence_is_valid(tmp_path) -> None:
    storage, artifact = _filed_edge_cruxes(tmp_path)
    cruxes = list(artifact.cruxes.draft)
    bad_evidence = cruxes[0].evidence_refs[0].model_copy(update={"artifact_path": f"{RUN_DIR}/missing_source.json"})
    cruxes[0] = cruxes[0].model_copy(update={"evidence_refs": [bad_evidence]})
    invalid = artifact.model_copy(update={"cruxes": artifact.cruxes.model_copy(update={"draft": cruxes})})

    with pytest.raises(AuditError, match="crux 0 evidence ref unresolvable"):
        audit_edge_cruxes(invalid, storage=storage)


def test_duplicate_cruxes_are_rejected(tmp_path) -> None:
    storage, artifact = _filed_edge_cruxes(tmp_path)
    cruxes = list(artifact.cruxes.draft)
    cruxes[2] = cruxes[0]

    with pytest.raises(AuditError, match="duplicate crux"):
        audit_edge_cruxes(artifact.model_copy(update={"cruxes": artifact.cruxes.model_copy(update={"draft": cruxes})}), storage=storage)


def test_resolver_reaches_edge_cruxes_on_go_path_and_does_not_ratify(tmp_path) -> None:
    payload = analyze("AAPL", as_of=RUN_DATE, storage=LocalStorage(tmp_path))

    assert payload["edge_cruxes"]["header"]["produced_by"] == "C-5"
    assert len(payload["edge_cruxes"]["cruxes"]["draft"]) == 3
    assert all(item["decision"] is None for item in payload["edge_cruxes_review_package"]["review_items"])


def test_resolver_no_go_stops_before_edge_cruxes(tmp_path) -> None:
    class NoGoSenior:
        model_family = "offline-senior"

        def gate(self, package):
            return {"decision": "NO-GO", "rationale": "test halt", "decided_by": "test-senior"}

        def ratify(self, package):
            raise AssertionError("ratify must not be called")

    payload = analyze("AAPL", as_of=RUN_DATE, storage=LocalStorage(tmp_path), senior=NoGoSenior())

    assert payload["status"] == "halted"
    assert "edge_cruxes" not in payload


def _filed_edge_cruxes(tmp_path) -> tuple[LocalStorage, EdgeCruxesArtifact]:
    storage = LocalStorage(tmp_path)
    config = load_config("config/conventions.yaml")
    edgar = fetch_edgar_facts("AAPL")
    price = fetch_price("AAPL", edgar=edgar, as_of=RUN_DATE)
    cost_of_capital = build_cost_of_capital_inputs("AAPL", config, edgar=edgar, price=price, as_of=RUN_DATE)
    normalized = normalize_financials(edgar)
    spine = build_spine(
        normalized,
        cost_of_capital,
        price,
        excess_cash_pct=config.invested_capital.excess_cash_pct,
        schema_version=config.schema_version,
    )
    handoff = build_handoff(
        "AAPL",
        edgar.cik,
        spine,
        price=price.price,
        as_of=RUN_DATE,
        schema_version=config.schema_version,
        flags=edgar.flags + price.flags + cost_of_capital.flags,
        source_accessions=sorted({n.provenance.accession for _, values in edgar.facts for n in values if n.provenance.accession}),
    )
    storage.put_json(f"{RUN_DIR}/spine.json", artifact_model_to_payload(spine))
    audit_m1_handoff(handoff, storage=storage, path=f"{RUN_DIR}/handoff.json")

    business = build_business_artifact(edgar, as_of=RUN_DATE, schema_version=config.schema_version, run_dir=RUN_DIR)
    audit_analyst_artifact(business, storage=storage, path=f"{RUN_DIR}/business.json")
    moat = build_moat_artifact(edgar, spine, as_of=RUN_DATE, schema_version=config.schema_version, run_dir=RUN_DIR)
    audit_analyst_artifact(moat, storage=storage, path=f"{RUN_DIR}/moat.json")
    capalloc = build_capalloc_artifact(edgar, spine, as_of=RUN_DATE, schema_version=config.schema_version, run_dir=RUN_DIR)
    audit_analyst_artifact(capalloc, storage=storage, path=f"{RUN_DIR}/capalloc.json")

    gate_card = build_gate_card(edgar, price, industry_classification="Technology", schema_version=config.schema_version)
    audit_artifact(gate_card, storage=storage, path=f"{RUN_DIR}/gate_card.json")
    method_directive = route_method(
        normalized,
        edgar,
        config,
        industry_classification="Technology",
        schema_version=config.schema_version,
        produced_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    audit_artifact(method_directive, storage=storage, path=f"{RUN_DIR}/method_directive.json")
    valuation, expectations = build_dcf_artifacts(normalized, edgar, price, cost_of_capital, config)
    audit_artifact(valuation, storage=storage, path=f"{RUN_DIR}/valuation_range.json")
    audit_artifact(expectations, storage=storage, path=f"{RUN_DIR}/expectations_line.json")
    scenarios = build_scenario_set_artifact(
        ticker="AAPL",
        as_of=RUN_DATE,
        schema_version=config.schema_version,
        storage=storage,
        run_dir=RUN_DIR,
        method_directive_path=f"{RUN_DIR}/method_directive.json",
        valuation_range_path=f"{RUN_DIR}/valuation_range.json",
        expectations_line_path=f"{RUN_DIR}/expectations_line.json",
    )
    audit_scenario_set(scenarios, storage=storage, path=f"{RUN_DIR}/scenarios.json")

    artifact = build_edge_cruxes_artifact(
        ticker="AAPL",
        as_of=RUN_DATE,
        schema_version=config.schema_version,
        storage=storage,
        run_dir=RUN_DIR,
        business_path=f"{RUN_DIR}/business.json",
        moat_path=f"{RUN_DIR}/moat.json",
        capalloc_path=f"{RUN_DIR}/capalloc.json",
        scenarios_path=f"{RUN_DIR}/scenarios.json",
        gate_card_path=f"{RUN_DIR}/gate_card.json",
        method_directive_path=f"{RUN_DIR}/method_directive.json",
        spine_path=f"{RUN_DIR}/spine.json",
        valuation_range_path=f"{RUN_DIR}/valuation_range.json",
        expectations_line_path=f"{RUN_DIR}/expectations_line.json",
    )
    return storage, artifact


def _as_no_edge_artifact(artifact: EdgeCruxesArtifact) -> EdgeCruxesArtifact:
    no_edge = artifact.structural_mispricing.model_copy(
        update={
            "draft": {
                "no_structural_edge": True,
                "pass_framing": "No durable structural edge because the filed scenarios already price the observable business quality.",
            }
        }
    )
    fairly_priced = artifact.variant_view.model_copy(
        update={
            "draft": "Fairly priced pass because the filed valuation already captures the business quality and no edge is evident."
        }
    )
    return artifact.model_copy(update={"structural_mispricing": no_edge, "variant_view": fairly_priced})


def _header(produced_by: str):
    return Header(schema_version="1.0", produced_by=produced_by, produced_at=datetime(2026, 7, 1, tzinfo=timezone.utc))
