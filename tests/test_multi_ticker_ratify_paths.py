from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

import resolver
from skills._primitives import Header
from skills.analyst_artifacts import SeniorReviewPackage, consolidate_review_packages
from skills.storage import LocalStorage

RUN_DATE = date(2026, 7, 1)


def test_mrna_runs_rnpv_route_without_dcf_and_ratifies_once(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    senior = CountingSenior()
    payload = resolver.analyze("MRNA", as_of=RUN_DATE, storage=storage, senior=senior)
    method_directive = storage.get_json("runs/MRNA/2026-07-01/method_directive.json")
    scenarios = storage.get_json("runs/MRNA/2026-07-01/scenarios.json")
    risk = storage.get_json("runs/MRNA/2026-07-01/risk.json")
    senior_decision_package = storage.get_json("runs/MRNA/2026-07-01/senior_decision_package.json")

    assert senior.ratify_calls == 2
    assert method_directive["asset_class"] == "optionality"
    assert method_directive["method"] == "rNPV"
    assert method_directive["routing_reason"] == "Optionality or pre-revenue economics require rNPV/SOTP routing rather than plain DCF."
    assert scenarios["status"] == "drafted"
    assert scenarios["scenarios"][0]["assumptions"][0]["driver"] == "rNPV_program_probability"
    assert payload["valuation_range"]["method"] == "rNPV"
    assert payload["whats_priced_in"]["method"] == "rNPV"
    assert risk["bear_case_value"]["derivation"].startswith("inputs: C-4 scenarios")
    assert payload["route_review_manifest"]["method"] == "rNPV"
    assert payload["route_review_manifest"]["required_context_sources"] == ["runs/MRNA/2026-07-01/method_directive.json"]
    assert senior_decision_package["ratification_summary"]["required_count"] > 0
    assert senior_decision_package["ratification_summary"]["ratified_as_is_rate"] == 1.0


def test_mrna_route_does_not_invoke_dcf(monkeypatch, tmp_path) -> None:
    def fail_dcf(*args, **kwargs):
        raise AssertionError("DCF should not be called for MRNA rNPV route")

    monkeypatch.setattr(resolver, "build_dcf_artifacts", fail_dcf)

    storage = LocalStorage(tmp_path)
    payload = resolver.analyze("MRNA", as_of=RUN_DATE, storage=storage)

    assert storage.get_json("runs/MRNA/2026-07-01/method_directive.json")["method"] == "rNPV"
    assert payload["valuation_range"]["method"] == "rNPV"


def test_non_dcf_same_family_ratify_rejects_before_senior_call(tmp_path) -> None:
    senior = SameRatifyFamilySenior()

    with pytest.raises(ValueError, match="must differ before ratify"):
        resolver.analyze("MRNA", as_of=RUN_DATE, storage=LocalStorage(tmp_path), senior=senior)

    assert senior.ratify_calls == 0


def test_dcf_manifest_fails_for_missing_dcf_context_source(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    packages = _review_packages(storage, "AAPL")
    manifest = resolver.build_review_source_manifest(
        method="DCF",
        run_dir="runs/AAPL/2026-07-01",
        business_path="runs/AAPL/2026-07-01/business.json",
        moat_path="runs/AAPL/2026-07-01/moat.json",
        capalloc_path="runs/AAPL/2026-07-01/capalloc.json",
        scenario_path="runs/AAPL/2026-07-01/scenarios.json",
        edge_cruxes_path="runs/AAPL/2026-07-01/edge_cruxes.json",
        risk_path="runs/AAPL/2026-07-01/risk.json",
        valuation_range_path="runs/AAPL/2026-07-01/valuation_range.json",
        expectations_line_path="runs/AAPL/2026-07-01/expectations_line.json",
    )

    with pytest.raises(ValueError, match="DCF route contract missing required sources: runs/AAPL/2026-07-01/valuation_range.json"):
        consolidate_review_packages(
            packages,
            ticker="AAPL",
            as_of=RUN_DATE,
            header=_header("M3-7-review"),
            manifest=manifest,
            context_sources={
                "runs/AAPL/2026-07-01/method_directive.json": "DCF route context",
                "runs/AAPL/2026-07-01/expectations_line.json": "DCF route context",
            },
        )


def test_non_dcf_manifest_fails_for_missing_risk_but_not_absent_dcf_artifacts(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("MRNA", as_of=RUN_DATE, storage=storage)
    packages = _review_packages(storage, "MRNA")
    without_risk = [package for package in packages if "runs/MRNA/2026-07-01/risk.json" not in package.source_artifact_summary]
    manifest = resolver.build_review_source_manifest(
        method="rNPV",
        run_dir="runs/MRNA/2026-07-01",
        business_path="runs/MRNA/2026-07-01/business.json",
        moat_path="runs/MRNA/2026-07-01/moat.json",
        capalloc_path="runs/MRNA/2026-07-01/capalloc.json",
        scenario_path="runs/MRNA/2026-07-01/scenarios.json",
        edge_cruxes_path="runs/MRNA/2026-07-01/edge_cruxes.json",
        risk_path="runs/MRNA/2026-07-01/risk.json",
        valuation_range_path=None,
        expectations_line_path=None,
    )

    consolidated = consolidate_review_packages(
        packages,
        ticker="MRNA",
        as_of=RUN_DATE,
        header=_header("M3-7-review"),
        manifest=manifest,
        context_sources={"runs/MRNA/2026-07-01/method_directive.json": "rNPV route context"},
    )
    assert "runs/MRNA/2026-07-01/valuation_range.json" not in consolidated.source_artifact_summary

    with pytest.raises(ValueError, match="rNPV route contract missing required sources: runs/MRNA/2026-07-01/risk.json"):
        consolidate_review_packages(
            without_risk,
            ticker="MRNA",
            as_of=RUN_DATE,
            header=_header("M3-7-review"),
            manifest=manifest,
            context_sources={"runs/MRNA/2026-07-01/method_directive.json": "rNPV route context"},
        )


def test_non_dcf_manifest_fails_for_missing_method_directive_context(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("MRNA", as_of=RUN_DATE, storage=storage)
    packages = _review_packages(storage, "MRNA")
    manifest = resolver.build_review_source_manifest(
        method="rNPV",
        run_dir="runs/MRNA/2026-07-01",
        business_path="runs/MRNA/2026-07-01/business.json",
        moat_path="runs/MRNA/2026-07-01/moat.json",
        capalloc_path="runs/MRNA/2026-07-01/capalloc.json",
        scenario_path="runs/MRNA/2026-07-01/scenarios.json",
        edge_cruxes_path="runs/MRNA/2026-07-01/edge_cruxes.json",
        risk_path="runs/MRNA/2026-07-01/risk.json",
        valuation_range_path=None,
        expectations_line_path=None,
    )

    with pytest.raises(ValueError, match="rNPV route contract missing required sources: runs/MRNA/2026-07-01/method_directive.json"):
        consolidate_review_packages(
            packages,
            ticker="MRNA",
            as_of=RUN_DATE,
            header=_header("M3-7-review"),
            manifest=manifest,
        )


class CountingSenior:
    model_family = "offline-senior"

    def __init__(self) -> None:
        self.ratify_calls = 0

    def gate(self, package):
        return {"decision": "GO", "rationale": "test go", "decided_by": "counting-senior"}

    def ratify(self, package):
        self.ratify_calls += 1
        item_ids = list(package["required_item_ids"])
        return {
            "decided_by": "counting-senior",
            "decisions": {
                item_id: {"decision": "ratified", "final": None, "rationale": f"accepted:{item_id}"}
                for item_id in item_ids
            },
        }


class SameRatifyFamilySenior:
    model_family = "offline-analyst-drafters"

    def __init__(self) -> None:
        self.ratify_calls = 0

    def gate(self, package):
        return {"decision": "GO", "rationale": "test go", "decided_by": "same-ratify-family"}

    def ratify(self, package):
        self.ratify_calls += 1
        raise AssertionError("ratify must not be called when families match")


def _review_packages(storage: LocalStorage, ticker: str) -> list[SeniorReviewPackage]:
    run_dir = f"runs/{ticker}/2026-07-01"
    return [
        SeniorReviewPackage.model_validate(storage.get_json(f"{run_dir}/gate_card_review_package.json")),
        SeniorReviewPackage.model_validate(storage.get_json(f"{run_dir}/business_review_package.json")),
        SeniorReviewPackage.model_validate(storage.get_json(f"{run_dir}/moat_review_package.json")),
        SeniorReviewPackage.model_validate(storage.get_json(f"{run_dir}/capalloc_review_package.json")),
        SeniorReviewPackage.model_validate(storage.get_json(f"{run_dir}/scenarios_review_package.json")),
        SeniorReviewPackage.model_validate(storage.get_json(f"{run_dir}/edge_cruxes_review_package.json")),
        SeniorReviewPackage.model_validate(storage.get_json(f"{run_dir}/risk_review_package.json")),
    ]


def _header(produced_by: str) -> Header:
    return Header(schema_version="1.0", produced_by=produced_by, produced_at=datetime(2026, 7, 1, tzinfo=timezone.utc))
