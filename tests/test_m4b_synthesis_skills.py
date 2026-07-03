from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

import resolver
from skills.analyst_artifacts import ReviewSourceManifest
from skills.analyst_artifacts import SeniorDecisionPackage
from skills.storage import LocalStorage
from skills.synthesis.conviction.conviction import ConvictionArtifact, build_conviction
from skills.synthesis.current_payload import CurrentSynthesisInput, assemble_current_payload
from skills.synthesis.m4b_payload import SynthesisPayload
from skills.synthesis.review_packager.review_packager import FinalHandoff, build_review_package

RUN_DATE = date(2026, 7, 3)


def test_synthesis_payload_accepts_valid_aapl_dcf_boundary_payload(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    payload = _current_payload(storage, ticker="AAPL", method="DCF")

    synthesis = SynthesisPayload.model_validate(payload)

    assert synthesis.ticker == "AAPL"
    assert synthesis.valuation_range is not None
    assert synthesis.expectations_line is not None
    assert synthesis.valuation_deferred is None


def test_synthesis_payload_accepts_valid_mrna_non_dcf_boundary_payload(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("MRNA", as_of=RUN_DATE, storage=storage)
    payload = _current_payload(storage, ticker="MRNA", method="rNPV")

    synthesis = SynthesisPayload.model_validate(payload)

    assert synthesis.ticker == "MRNA"
    assert synthesis.valuation_range is None
    assert synthesis.expectations_line is None
    assert synthesis.valuation_deferred


def test_synthesis_payload_rejects_incomplete_senior_decision_package(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    payload = _current_payload(storage, ticker="AAPL", method="DCF")
    decisions = dict(payload["senior_decision_package"])
    decisions["required_item_ids"] = [*decisions["required_item_ids"], "missing-required-id"]
    payload["senior_decision_package"] = decisions

    with pytest.raises(ValidationError, match="senior decisions missing required item ids"):
        SynthesisPayload.model_validate(payload)


def test_synthesis_payload_rejects_bare_numeric_leakage(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    payload = _current_payload(storage, ticker="AAPL", method="DCF")
    payload["price"] = 200.0

    with pytest.raises(ValidationError):
        SynthesisPayload.model_validate(payload)


def test_synthesis_payload_rejects_dcf_without_valuation_paths(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    payload = _current_payload(storage, ticker="AAPL", method="DCF")
    del payload["valuation_range"]

    with pytest.raises(ValidationError, match="DCF synthesis requires valuation_range and expectations_line"):
        SynthesisPayload.model_validate(payload)


def test_synthesis_payload_rejects_non_dcf_without_deferred_reason(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("MRNA", as_of=RUN_DATE, storage=storage)
    payload = _current_payload(storage, ticker="MRNA", method="rNPV")
    del payload["valuation_deferred"]

    with pytest.raises(ValidationError, match="rNPV synthesis requires valuation_deferred"):
        SynthesisPayload.model_validate(payload)


def test_conviction_files_reloadable_artifact_with_sizing_inputs(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    run_dir = "runs/AAPL/2026-07-03"

    filed = ConvictionArtifact.model_validate(storage.get_json(f"{run_dir}/conviction.json"))

    assert filed.header.produced_by == "D-2"
    assert filed.sizing_inputs.up_down_ratio.value >= 0
    assert filed.lean.decision is None
    assert filed.sizing_inputs.days_to_build.unit == "days"
    assert filed.sizing_inputs.days_to_exit.unit == "days"


def test_review_packager_files_reloadable_final_handoff(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    run_dir = "runs/AAPL/2026-07-03"

    filed = FinalHandoff.model_validate(storage.get_json(f"{run_dir}/final_handoff.json"))

    assert filed.header.produced_by == "D-3"
    assert filed.model_dump(mode="json") == payload
    assert len(filed.cruxes) == 3
    assert filed.sizing_inputs.up_down_ratio.value >= 0
    assert filed.lean.decision == "ratified"
    assert all(scenario.probability.decision == "ratified" for scenario in filed.valuation_range.scenarios)


def test_final_lean_overturned_with_replacement_produces_handoff(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    senior = FinalLeanReplacementSenior()
    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage, senior=senior)
    run_dir = "runs/AAPL/2026-07-03"

    filed = FinalHandoff.model_validate(storage.get_json(f"{run_dir}/final_handoff.json"))

    assert "status" not in payload
    assert senior.replacement is not None
    assert filed.lean.decision == "overturned"
    assert filed.lean.final == senior.replacement
    assert filed.lean.final != filed.lean.draft
    assert "final_lean_decision_package:overturned-and-replaced" in filed.lean.evidence
    assert filed.final_lean_decision_package["outcomes"]["final_lean"] == "modified"


def test_final_lean_overturned_without_replacement_halts_without_handoff(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage, senior=FinalLeanRejectingSenior())
    run_dir = "runs/AAPL/2026-07-03"

    assert payload["status"] == "halted"
    assert payload["returned_for_revision"]["halt_reason"] == "final_lean_overturned_without_replacement"
    assert payload["returned_for_revision"]["decision"] == "overturned"
    assert payload["returned_for_revision"]["replacement_final"] is None
    assert payload["final_lean_decision_package"]["outcomes"]["final_lean"] == "rejected"
    with pytest.raises(FileNotFoundError):
        storage.get_json(f"{run_dir}/final_handoff.json")


def test_review_packager_fails_closed_without_filed_d2_artifact(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    run_dir = "runs/AAPL/2026-07-03"
    synthesis = SynthesisPayload.model_validate(_current_payload(storage, ticker="AAPL", method="DCF"))
    conviction = build_conviction(synthesis, storage=storage, run_dir=run_dir)
    lean_decisions = SeniorDecisionPackage.model_validate(storage.get_json(f"{run_dir}/final_lean_decision_package.json"))
    (tmp_path / run_dir / "conviction.json").unlink()

    with pytest.raises(ValueError, match="D-3 requires filed D-2 conviction artifact"):
        build_review_package(synthesis, conviction, storage=storage, run_dir=run_dir, lean_decision_package=lean_decisions)


def test_final_handoff_rejects_missing_sizing_inputs(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    handoff = storage.get_json("runs/AAPL/2026-07-03/final_handoff.json")
    del handoff["sizing_inputs"]

    with pytest.raises(ValidationError):
        FinalHandoff.model_validate(handoff)


def test_final_handoff_rejects_unresolved_top_level_ratifiable_with_path(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    handoff = storage.get_json("runs/AAPL/2026-07-03/final_handoff.json")
    handoff["lean"]["decision"] = None

    with pytest.raises(ValidationError, match="handoff\\.lean"):
        FinalHandoff.model_validate(handoff)


def test_final_handoff_rejects_nested_unresolved_ratifiable_with_path(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    handoff = storage.get_json("runs/AAPL/2026-07-03/final_handoff.json")
    handoff["valuation_range"]["scenarios"][0]["probability"]["decision"] = None

    with pytest.raises(ValidationError, match="handoff\\.valuation_range\\.scenarios\\[0\\]\\.probability"):
        FinalHandoff.model_validate(handoff)


def test_final_handoff_rejects_overturned_lean_reusing_d2_draft(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    handoff = storage.get_json("runs/AAPL/2026-07-03/final_handoff.json")
    handoff["lean"]["decision"] = "overturned"
    handoff["lean"]["final"] = handoff["lean"]["draft"]

    with pytest.raises(ValidationError, match="cannot reuse D-2 draft"):
        FinalHandoff.model_validate(handoff)


class FinalLeanReplacementSenior:
    model_family = "offline-senior"

    def __init__(self) -> None:
        self.replacement: str | None = None

    def gate(self, package):
        return {"decision": "GO", "rationale": "test go", "decided_by": "replacement-senior"}

    def ratify(self, package):
        item_ids = list(package["required_item_ids"])
        if item_ids == ["final_lean"]:
            draft = package["review_package"]["review_items"][0]["draft"]
            self.replacement = "Buy" if draft != "Buy" else "Pass"
            return {
                "decided_by": "replacement-senior",
                "decisions": {
                    "final_lean": {"decision": "overturned", "final": self.replacement, "rationale": "replace final lean"}
                },
            }
        return {
            "decided_by": "replacement-senior",
            "decisions": {
                item_id: {"decision": "ratified", "final": None, "rationale": f"accepted:{item_id}"}
                for item_id in item_ids
            },
        }


class FinalLeanRejectingSenior:
    model_family = "offline-senior"

    def gate(self, package):
        return {"decision": "GO", "rationale": "test go", "decided_by": "rejecting-senior"}

    def ratify(self, package):
        item_ids = list(package["required_item_ids"])
        if item_ids == ["final_lean"]:
            return {
                "decided_by": "rejecting-senior",
                "decisions": {"final_lean": {"decision": "overturned", "final": None, "rationale": "reject final lean"}},
            }
        return {
            "decided_by": "rejecting-senior",
            "decisions": {
                item_id: {"decision": "ratified", "final": None, "rationale": f"accepted:{item_id}"}
                for item_id in item_ids
            },
        }


def _current_payload(storage: LocalStorage, *, ticker: str, method: str) -> dict:
    run_dir = f"runs/{ticker}/2026-07-03"
    method_directive = storage.get_json(f"{run_dir}/method_directive.json")
    return assemble_current_payload(
        storage,
        CurrentSynthesisInput(
            ticker=ticker,
            as_of=RUN_DATE,
            run_dir=run_dir,
            method=method,
            route_manifest=ReviewSourceManifest.model_validate(storage.get_json(f"{run_dir}/final_handoff.json")["route_review_manifest"]),
            handoff_path=f"{run_dir}/handoff.json",
            business_path=f"{run_dir}/business.json",
            moat_path=f"{run_dir}/moat.json",
            capalloc_path=f"{run_dir}/capalloc.json",
            scenario_path=f"{run_dir}/scenarios.json",
            edge_cruxes_path=f"{run_dir}/edge_cruxes.json",
            risk_path=f"{run_dir}/risk.json",
            valuation_range_path=f"{run_dir}/valuation_range.json" if method == "DCF" else None,
            expectations_line_path=f"{run_dir}/expectations_line.json" if method == "DCF" else None,
            valuation_deferred=None if method == "DCF" else method_directive["fallback_behavior"],
        ),
    )
