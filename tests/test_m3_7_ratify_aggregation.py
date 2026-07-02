from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from resolver import analyze
from skills._primitives import Header
from skills.analyst_artifacts import (
    ReviewSourceManifest,
    consolidate_review_packages,
    ratify_review_package,
)
from skills.audit import AuditError, audit_senior_decision_package, audit_senior_review_package
from skills.storage import LocalStorage

RUN_DATE = date(2026, 7, 1)
RUN_DIR = "runs/AAPL/2026-07-01"


def test_resolver_builds_consolidated_review_and_decision_package(tmp_path) -> None:
    senior = CountingSenior()
    payload = analyze("AAPL", as_of=RUN_DATE, storage=LocalStorage(tmp_path), senior=senior)

    review = payload["senior_review_package"]
    decisions = payload["senior_decision_package"]
    required_ids = [item["id"] for item in review["review_items"] if item["required"]]

    assert senior.ratify_calls == 1
    assert review["header"]["produced_by"] == "M3-7-review"
    assert decisions["header"]["produced_by"] == "M3-7-ratify"
    assert decisions["required_item_ids"] == required_ids
    assert set(decisions["decisions"]) == set(required_ids)
    assert {
        f"{RUN_DIR}/gate_card.json",
        f"{RUN_DIR}/business.json",
        f"{RUN_DIR}/moat.json",
        f"{RUN_DIR}/capalloc.json",
        f"{RUN_DIR}/scenarios.json",
        f"{RUN_DIR}/edge_cruxes.json",
        f"{RUN_DIR}/risk.json",
    }.issubset(set(review["source_artifact_summary"]))


def test_gate_card_verdict_is_included_as_m2b_ratifiable(tmp_path) -> None:
    payload = analyze("AAPL", as_of=RUN_DATE, storage=LocalStorage(tmp_path))
    review = payload["senior_review_package"]

    gate_items = [
        item
        for item in review["review_items"]
        if item["source_artifact"] == f"{RUN_DIR}/gate_card.json" and item["source_field_path"] == "GateCard.verdict"
    ]

    assert len(gate_items) == 1
    assert gate_items[0]["draft"] in {"PASS", "DIG", "KILL"}
    assert gate_items[0]["evidence_refs"][0]["artifact_path"] == f"{RUN_DIR}/gate_card.json"


def test_business_review_is_included_as_c1_ratifiable(tmp_path) -> None:
    payload = analyze("AAPL", as_of=RUN_DATE, storage=LocalStorage(tmp_path))
    review = payload["senior_review_package"]

    business_items = [
        item
        for item in review["review_items"]
        if item["source_artifact"] == f"{RUN_DIR}/business.json"
    ]

    assert business_items
    assert {item["source_field_path"] for item in business_items} == {
        "BusinessArtifact.business_model_summary",
        "BusinessArtifact.revenue_driver_summary",
        "BusinessArtifact.customer_end_market_summary",
        "BusinessArtifact.business_understanding_risk",
    }


@pytest.mark.parametrize(
    "omitted_source",
    [
        f"{RUN_DIR}/gate_card.json",
        f"{RUN_DIR}/business.json",
        f"{RUN_DIR}/moat.json",
        f"{RUN_DIR}/capalloc.json",
        f"{RUN_DIR}/scenarios.json",
        f"{RUN_DIR}/edge_cruxes.json",
        f"{RUN_DIR}/risk.json",
    ],
)
def test_manifest_rejects_consolidation_when_any_required_source_is_omitted(tmp_path, omitted_source) -> None:
    storage = LocalStorage(tmp_path)
    analyze("AAPL", as_of=RUN_DATE, storage=storage)
    packages = _all_review_packages(storage)
    included = [package for package in packages if omitted_source not in package.source_artifact_summary]

    with pytest.raises(ValueError, match="missing required sources"):
        consolidate_review_packages(
            included,
            ticker="AAPL",
            as_of=RUN_DATE,
            header=_header("M3-7-review"),
            manifest=_manifest(),
        )


def test_manifest_rejects_when_required_source_has_summary_but_no_review_items(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    analyze("AAPL", as_of=RUN_DATE, storage=storage)
    packages = _all_review_packages(storage)
    package = consolidate_review_packages(
        packages,
        ticker="AAPL",
        as_of=RUN_DATE,
        header=_header("M3-7-review"),
        manifest=_manifest(),
    )
    without_business_items = package.model_copy(
        update={
            "review_items": [
                item
                for item in package.review_items
                if item.source_artifact != f"{RUN_DIR}/business.json"
            ]
        }
    )

    with pytest.raises(ValueError, match="missing required review items"):
        consolidate_review_packages(
            [
                without_business_items,
            ],
            ticker="AAPL",
            as_of=RUN_DATE,
            header=_header("M3-7-review"),
            manifest=_manifest(),
        )


def test_consolidation_rejects_duplicate_review_item_ids(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    analyze("AAPL", as_of=RUN_DATE, storage=storage)
    package = storage.get_json(f"{RUN_DIR}/moat_review_package.json")
    review_package = _review_package_from_payload(package)

    with pytest.raises(ValueError, match="duplicate review item id"):
        consolidate_review_packages(
            [review_package, review_package],
            ticker="AAPL",
            as_of=RUN_DATE,
            header=_header("M3-7-review"),
            manifest=ReviewSourceManifest(required_sources=(f"{RUN_DIR}/moat.json",)),
        )


def test_incomplete_senior_ratification_fails_closed(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    analyze("AAPL", as_of=RUN_DATE, storage=storage)
    review_package = _review_package_from_payload(storage.get_json(f"{RUN_DIR}/senior_review_package.json"))

    with pytest.raises(ValueError, match="missing required item ids"):
        ratify_review_package(
            review_package,
            senior=IncompleteSenior(),
            analyst_family="offline-analyst-drafters",
            header=_header("M3-7-ratify"),
        )


def test_same_family_ratify_wiring_rejects_before_senior_call(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    analyze("AAPL", as_of=RUN_DATE, storage=storage)
    review_package = _review_package_from_payload(storage.get_json(f"{RUN_DIR}/senior_review_package.json"))
    senior = SameFamilySenior()

    with pytest.raises(ValueError, match="must differ before ratify"):
        ratify_review_package(
            review_package,
            senior=senior,
            analyst_family="same-family",
            header=_header("M3-7-ratify"),
        )

    assert senior.ratify_calls == 0


def test_no_go_path_does_not_call_ratify(tmp_path) -> None:
    senior = NoGoSenior()
    payload = analyze("AAPL", as_of=RUN_DATE, storage=LocalStorage(tmp_path), senior=senior)

    assert payload["status"] == "halted"
    assert senior.ratify_calls == 0
    assert "senior_decision_package" not in payload


def test_persisted_packages_audit_from_storage(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    analyze("AAPL", as_of=RUN_DATE, storage=storage)

    review = _review_package_from_payload(storage.get_json(f"{RUN_DIR}/senior_review_package.json"))
    decisions = _decision_package_from_payload(storage.get_json(f"{RUN_DIR}/senior_decision_package.json"))

    audit_senior_review_package(review)
    audit_senior_decision_package(decisions)


def test_full_consolidated_package_with_one_missing_required_decision_is_not_ratified(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    analyze("AAPL", as_of=RUN_DATE, storage=storage)
    package = _review_package_from_payload(storage.get_json(f"{RUN_DIR}/senior_review_package.json"))
    decided_items = [
        item.model_copy(update={"decision": "ratified", "decided_by": "test-senior"})
        for item in package.review_items
    ]
    partial_package = package.model_copy(update={"review_items": decided_items[:-1] + [package.review_items[-1]]})
    complete_package = package.model_copy(update={"review_items": decided_items})

    assert partial_package.is_ratified is False
    assert complete_package.is_ratified is True


def test_filed_decision_package_captures_per_item_outcomes_and_aggregate_rate(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    payload = analyze("AAPL", as_of=RUN_DATE, storage=storage, senior=MixedOutcomeSenior())
    filed = storage.get_json(f"{RUN_DIR}/senior_decision_package.json")
    decisions = payload["senior_decision_package"]

    assert filed == decisions
    assert set(decisions["outcomes"]) == set(decisions["required_item_ids"])
    assert "ratified_as_is" in set(decisions["outcomes"].values())
    assert "modified" in set(decisions["outcomes"].values())
    assert "rejected" in set(decisions["outcomes"].values())
    assert decisions["ratification_summary"] == {
        "required_count": len(decisions["required_item_ids"]),
        "ratified_as_is_count": len(decisions["required_item_ids"]) - 2,
        "modified_count": 1,
        "rejected_count": 1,
        "ratified_as_is_rate": (len(decisions["required_item_ids"]) - 2) / len(decisions["required_item_ids"]),
    }
    audit_senior_decision_package(_decision_package_from_payload(filed))


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


class IncompleteSenior:
    model_family = "offline-senior"

    def ratify(self, package):
        return {"decided_by": "incomplete-senior", "decisions": {}}


class SameFamilySenior:
    model_family = "same-family"

    def __init__(self) -> None:
        self.ratify_calls = 0

    def ratify(self, package):
        self.ratify_calls += 1
        return {"decided_by": "same-family-senior", "decisions": {}}


class MixedOutcomeSenior:
    model_family = "offline-senior"

    def gate(self, package):
        return {"decision": "GO", "rationale": "test go", "decided_by": "mixed-senior"}

    def ratify(self, package):
        item_ids = list(package["required_item_ids"])
        decisions = {
            item_id: {"decision": "ratified", "final": None, "rationale": f"accepted:{item_id}"}
            for item_id in item_ids
        }
        decisions[item_ids[0]] = {"decision": "overturned", "final": "senior modified value", "rationale": "modified"}
        decisions[item_ids[1]] = {"decision": "overturned", "final": None, "rationale": "rejected"}
        return {"decided_by": "mixed-senior", "decisions": decisions}


class NoGoSenior:
    model_family = "offline-senior"

    def __init__(self) -> None:
        self.ratify_calls = 0

    def gate(self, package):
        return {"decision": "NO-GO", "rationale": "test halt", "decided_by": "no-go-senior"}

    def ratify(self, package):
        self.ratify_calls += 1
        raise AssertionError("ratify must not be called on NO-GO")


def _header(produced_by: str) -> Header:
    return Header(schema_version="1.0", produced_by=produced_by, produced_at=datetime(2026, 7, 1, tzinfo=timezone.utc))


def _review_package_from_payload(payload):
    from skills.analyst_artifacts import SeniorReviewPackage

    return SeniorReviewPackage.model_validate(payload)


def _decision_package_from_payload(payload):
    from skills.analyst_artifacts import SeniorDecisionPackage

    return SeniorDecisionPackage.model_validate(payload)


def _all_review_packages(storage):
    return [
        _review_package_from_payload(storage.get_json(f"{RUN_DIR}/gate_card_review_package.json")),
        _review_package_from_payload(storage.get_json(f"{RUN_DIR}/business_review_package.json")),
        _review_package_from_payload(storage.get_json(f"{RUN_DIR}/moat_review_package.json")),
        _review_package_from_payload(storage.get_json(f"{RUN_DIR}/capalloc_review_package.json")),
        _review_package_from_payload(storage.get_json(f"{RUN_DIR}/scenarios_review_package.json")),
        _review_package_from_payload(storage.get_json(f"{RUN_DIR}/edge_cruxes_review_package.json")),
        _review_package_from_payload(storage.get_json(f"{RUN_DIR}/risk_review_package.json")),
    ]


def _manifest() -> ReviewSourceManifest:
    return ReviewSourceManifest(
        required_sources=(
            f"{RUN_DIR}/gate_card.json",
            f"{RUN_DIR}/business.json",
            f"{RUN_DIR}/moat.json",
            f"{RUN_DIR}/capalloc.json",
            f"{RUN_DIR}/scenarios.json",
            f"{RUN_DIR}/edge_cruxes.json",
            f"{RUN_DIR}/risk.json",
        )
    )
