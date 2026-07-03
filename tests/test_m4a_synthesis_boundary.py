from __future__ import annotations

from datetime import date

import pytest

import resolver
from skills.analyst_artifacts import ReviewSourceManifest
from skills.storage import LocalStorage
from skills.synthesis.current_payload import CurrentSynthesisInput, assemble_current_payload

RUN_DATE = date(2026, 7, 2)


def test_synthesis_boundary_assembles_current_aapl_dcf_payload(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    run_dir = "runs/AAPL/2026-07-02"

    assembled = assemble_current_payload(
        storage,
        _synthesis_input(
            run_dir=run_dir,
            ticker="AAPL",
            method="DCF",
            route_manifest=ReviewSourceManifest.model_validate(payload["route_review_manifest"]),
            valuation_range_path=f"{run_dir}/valuation_range.json",
            expectations_line_path=f"{run_dir}/expectations_line.json",
        ),
    )

    assert payload["header"]["produced_by"] == "D-3"
    assert storage.get_json(f"{run_dir}/final_handoff.json") == payload
    assert assembled["valuation_range"]["method"] == "DCF"
    assert assembled["expectations_line"]["frame"] == "DCF"
    assert assembled["senior_review_package"]["header"]["produced_by"] == "M3-7-review"
    assert assembled["senior_decision_package"]["header"]["produced_by"] == "M3-7-ratify"


def test_synthesis_boundary_assembles_current_mrna_non_dcf_payload(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    payload = resolver.analyze("MRNA", as_of=RUN_DATE, storage=storage)
    run_dir = "runs/MRNA/2026-07-02"
    method_directive = storage.get_json(f"{run_dir}/method_directive.json")

    assembled = assemble_current_payload(
        storage,
        _synthesis_input(
            run_dir=run_dir,
            ticker="MRNA",
            method="rNPV",
            route_manifest=ReviewSourceManifest.model_validate(payload["route_review_manifest"]),
            valuation_deferred=method_directive["fallback_behavior"],
        ),
    )

    assert payload["header"]["produced_by"] == "D-3"
    assert storage.get_json(f"{run_dir}/final_handoff.json") == payload
    assert assembled["method_directive"]["method"] == "rNPV"
    assert assembled["valuation_deferred"]
    assert "valuation_range" not in assembled
    assert "expectations_line" not in assembled


def test_synthesis_boundary_fails_closed_for_missing_required_artifact(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    run_dir = "runs/AAPL/2026-07-02"

    synthesis_input = _synthesis_input(
        run_dir=run_dir,
        ticker="AAPL",
        method="DCF",
        route_manifest=ReviewSourceManifest.model_validate(payload["route_review_manifest"]),
        business_path=f"{run_dir}/missing_business.json",
        valuation_range_path=f"{run_dir}/valuation_range.json",
        expectations_line_path=f"{run_dir}/expectations_line.json",
    )

    with pytest.raises(ValueError, match=f"missing required synthesis artifact: {run_dir}/missing_business.json"):
        assemble_current_payload(storage, synthesis_input)


def test_synthesis_boundary_fails_closed_for_incomplete_dcf_paths(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    run_dir = "runs/AAPL/2026-07-02"

    synthesis_input = _synthesis_input(
        run_dir=run_dir,
        ticker="AAPL",
        method="DCF",
        route_manifest=ReviewSourceManifest.model_validate(payload["route_review_manifest"]),
        valuation_range_path=f"{run_dir}/valuation_range.json",
        expectations_line_path=None,
    )

    with pytest.raises(ValueError, match="DCF synthesis requires valuation_range_path and expectations_line_path"):
        assemble_current_payload(storage, synthesis_input)


def test_synthesis_boundary_non_dcf_does_not_require_dcf_artifacts(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    payload = resolver.analyze("MRNA", as_of=RUN_DATE, storage=storage)
    run_dir = "runs/MRNA/2026-07-02"
    method_directive = storage.get_json(f"{run_dir}/method_directive.json")

    assembled = assemble_current_payload(
        storage,
        _synthesis_input(
            run_dir=run_dir,
            ticker="MRNA",
            method="rNPV",
            route_manifest=ReviewSourceManifest.model_validate(payload["route_review_manifest"]),
            valuation_range_path=f"{run_dir}/does_not_exist_valuation_range.json",
            expectations_line_path=f"{run_dir}/does_not_exist_expectations_line.json",
            valuation_deferred=method_directive["fallback_behavior"],
        ),
    )

    assert assembled["valuation_deferred"] == method_directive["fallback_behavior"]
    assert "valuation_range" not in assembled
    assert "expectations_line" not in assembled


def _synthesis_input(
    *,
    run_dir: str,
    ticker: str,
    method: str,
    route_manifest: ReviewSourceManifest,
    business_path: str | None = None,
    valuation_range_path: str | None = None,
    expectations_line_path: str | None = None,
    valuation_deferred: str | None = None,
) -> CurrentSynthesisInput:
    return CurrentSynthesisInput(
        ticker=ticker,
        as_of=RUN_DATE,
        run_dir=run_dir,
        method=method,
        route_manifest=route_manifest,
        handoff_path=f"{run_dir}/handoff.json",
        business_path=business_path or f"{run_dir}/business.json",
        moat_path=f"{run_dir}/moat.json",
        capalloc_path=f"{run_dir}/capalloc.json",
        scenario_path=f"{run_dir}/scenarios.json",
        edge_cruxes_path=f"{run_dir}/edge_cruxes.json",
        risk_path=f"{run_dir}/risk.json",
        valuation_range_path=valuation_range_path,
        expectations_line_path=expectations_line_path,
        valuation_deferred=valuation_deferred,
    )
