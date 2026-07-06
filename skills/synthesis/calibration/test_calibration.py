from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from skills.storage import LocalStorage
from skills.synthesis.calibration import CalibrationAnalytics, CalibrationCall, CalibrationReview, record_calibration_review
from skills.synthesis.calibration.calibration import (
    EscalationCorrectnessReview,
    RoutingCorrectnessReview,
    build_calibration_analytics,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_record_calibration_review_appends_typed_review(tmp_path) -> None:
    storage = _storage_with_call(tmp_path)

    review = record_calibration_review(
        storage,
        {
            "call_id": "AAPL:2026-07-05:run-1",
            "reviewed_at": "2027-07-05",
            "what_happened": "Revenue durability matched the thesis.",
            "cruxes_held": ["services growth held"],
            "cruxes_broke": [],
            "right_for_the_reasons": True,
        },
    )

    assert review.call_id == "AAPL:2026-07-05:run-1"
    assert storage.list_calibration_reviews() == [review]


def test_record_calibration_review_rejects_unknown_call_id(tmp_path) -> None:
    storage = LocalStorage(tmp_path)

    with pytest.raises(ValueError, match="unknown calibration call id"):
        record_calibration_review(
            storage,
            {
                "call_id": "missing",
                "reviewed_at": "2027-07-05",
                "what_happened": "No call exists.",
                "right_for_the_reasons": True,
            },
        )


def test_calibration_analytics_empty_report_is_typed(tmp_path) -> None:
    report = build_calibration_analytics(LocalStorage(tmp_path))

    assert isinstance(report, CalibrationAnalytics)
    assert report.calls_count == 0
    assert report.reviews_count == 0
    assert report.open_reviews_count == 0
    assert report.hit_rate_by_conviction_band["Low"].hit_rate == 0.0
    assert report.routing_correctness_rate.rate == 0.0
    assert report.escalation_correctness_rate.rate == 0.0


def test_calibration_analytics_uses_latest_non_superseded_review_per_call(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    storage.append_calibration_call(_call("AAA:2026-07-05:run-1", ticker="AAA", conviction="Med", lean="Buy"))
    storage.append_calibration_call(_call("BBB:2026-07-05:run-1", ticker="BBB", conviction="High", lean="Watch"))
    storage.append_calibration_call(_call("CCC:2026-07-05:run-1", ticker="CCC", conviction="Low", lean="Pass"))
    storage.append_calibration_review(
        CalibrationReview(
            id="old-miss",
            call_id="AAA:2026-07-05:run-1",
            reviewed_at=date(2027, 7, 5),
            outcome_direction="down",
            what_happened="Initial correction was too harsh.",
            cruxes_held=[],
            cruxes_broke=["services growth"],
            right_for_the_reasons=False,
            primary_leak_phase="P4",
        )
    )
    storage.append_calibration_review(
        CalibrationReview(
            id="new-hit",
            call_id="AAA:2026-07-05:run-1",
            reviewed_at=date(2027, 7, 6),
            outcome_direction="up",
            what_happened="Correction superseded prior review.",
            cruxes_held=["services growth"],
            cruxes_broke=[],
            right_for_the_reasons=True,
            supersedes_review_id="old-miss",
        )
    )
    storage.append_calibration_review(
        CalibrationReview(
            id="latest-miss",
            call_id="BBB:2026-07-05:run-1",
            reviewed_at=date(2027, 7, 7),
            outcome_direction="down",
            what_happened="Base case broke.",
            cruxes_held=[],
            cruxes_broke=["gross margin"],
            right_for_the_reasons=False,
            primary_leak_phase="P5",
        )
    )
    storage.append_routing_correctness_review(
        RoutingCorrectnessReview(
            id="route-ok",
            date=date(2026, 7, 5),
            ticker="AAA",
            expected_route="A-1 > D-3",
            actual_route="A-1 > D-3",
            correct=True,
            rationale="route matched",
        )
    )
    storage.append_routing_correctness_review(
        RoutingCorrectnessReview(
            id="route-bad",
            date=date(2026, 7, 5),
            ticker="BBB",
            expected_route="A-1 > D-3",
            actual_route="A-1",
            correct=False,
            rationale="missing D-3",
        )
    )
    storage.append_escalation_correctness_review(
        EscalationCorrectnessReview(
            id="esc-ok",
            date=date(2026, 7, 5),
            ticker="AAA",
            touchpoint="early_gate",
            expected_escalation="Senior",
            actual_escalation="Senior",
            correct=True,
            rationale="matched",
        )
    )
    storage.append_escalation_correctness_review(
        EscalationCorrectnessReview(
            id="esc-bad",
            date=date(2026, 7, 5),
            ticker="BBB",
            touchpoint="final_lean_ratification",
            expected_escalation="Senior",
            actual_escalation="none",
            correct=False,
            rationale="missing final lean ratification",
        )
    )

    report = build_calibration_analytics(storage)

    assert report.calls_count == 3
    assert report.reviews_count == 3
    assert report.reviewed_calls_count == 2
    assert report.open_reviews_count == 1
    assert report.hit_rate_by_conviction_band["Med"].hits == 1
    assert report.hit_rate_by_conviction_band["High"].misses == 1
    assert report.leak_by_phase == {"P5": 1}
    assert report.directional_bias == {"Buy": {"up": 1}, "Watch": {"down": 1}}
    assert report.routing_correctness_rate.rate == 0.5
    assert report.escalation_correctness_rate.rate == 0.5
    assert report.routing_findings[0].findings == ["missing D-3"]


def test_calibration_analytics_as_of_filters_future_rows(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    storage.append_calibration_call(_call("AAA:2026-07-05:run-1", ticker="AAA"))
    storage.append_calibration_call(_call("BBB:2026-08-05:run-1", ticker="BBB", call_date=date(2026, 8, 5)))
    storage.append_calibration_review(
        CalibrationReview(
            id="review-a",
            call_id="AAA:2026-07-05:run-1",
            reviewed_at=date(2027, 7, 5),
            what_happened="Done.",
            cruxes_held=[],
            cruxes_broke=[],
            right_for_the_reasons=True,
        )
    )
    storage.append_routing_correctness_review(
        RoutingCorrectnessReview(
            id="route-a",
            date=date(2026, 7, 5),
            ticker="AAA",
            expected_route="A-1",
            actual_route="A-1",
            correct=True,
            rationale="matched",
        )
    )
    storage.append_routing_correctness_review(
        RoutingCorrectnessReview(
            id="route-b",
            date=date(2026, 8, 5),
            ticker="BBB",
            expected_route="A-1",
            actual_route="none",
            correct=False,
            rationale="future route",
        )
    )

    report = build_calibration_analytics(storage, as_of="2026-07-31")

    assert report.calls_count == 1
    assert report.reviews_count == 0
    assert report.routing_correctness_rate.observations_count == 1
    assert report.routing_correctness_rate.rate == 1.0


def test_calibration_report_cli_prints_model_json(tmp_path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "resolver", "calibration-report", "--data-root", str(tmp_path)],
        check=False,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["calls_count"] == 0
    assert payload["hit_rate_by_conviction_band"]["Low"]["hit_rate"] == 0.0


def test_calibration_review_cli_prints_review_json(tmp_path) -> None:
    _storage_with_call(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "resolver",
            "calibration-review",
            "--data-root",
            str(tmp_path),
            "--call-id",
            "AAPL:2026-07-05:run-1",
            "--reviewed-at",
            "2027-07-05",
            "--what-happened",
            "Cruxes held.",
            "--right-for-the-reasons",
            "true",
            "--primary-leak-phase",
            "none",
        ],
        check=False,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["call_id"] == "AAPL:2026-07-05:run-1"
    assert payload["right_for_the_reasons"] is True


def test_calibration_review_cli_accepts_json_file(tmp_path) -> None:
    _storage_with_call(tmp_path)
    review_path = tmp_path / "review.json"
    review_path.write_text(
        json.dumps(
            {
                "call_id": "AAPL:2026-07-05:run-1",
                "reviewed_at": "2027-07-05",
                "what_happened": "Filed from JSON.",
                "right_for_the_reasons": True,
                "primary_leak_phase": "none",
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "resolver",
            "calibration-review",
            "--data-root",
            str(tmp_path),
            "--json-file",
            str(review_path),
        ],
        check=False,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["what_happened"] == "Filed from JSON."


def test_calibration_review_cli_retry_is_idempotent(tmp_path) -> None:
    storage = _storage_with_call(tmp_path)
    command = [
        sys.executable,
        "-m",
        "resolver",
        "calibration-review",
        "--data-root",
        str(tmp_path),
        "--call-id",
        "AAPL:2026-07-05:run-1",
        "--reviewed-at",
        "2027-07-05",
        "--what-happened",
        "Same payload.",
        "--right-for-the-reasons",
        "true",
        "--primary-leak-phase",
        "none",
    ]

    first = subprocess.run(command, check=False, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    second = subprocess.run(command, check=False, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    assert first.returncode == 0
    assert second.returncode == 0
    assert first.stderr == ""
    assert second.stderr == ""
    assert storage.list_calibration_reviews(call_id="AAPL:2026-07-05:run-1") == [
        CalibrationReview(
            call_id="AAPL:2026-07-05:run-1",
            reviewed_at=date(2027, 7, 5),
            what_happened="Same payload.",
            cruxes_held=[],
            cruxes_broke=[],
            right_for_the_reasons=True,
        )
    ]


@pytest.mark.parametrize(
    "args",
    [
        ["--call-id", "missing", "--reviewed-at", "2027-07-05", "--what-happened", "No call.", "--right-for-the-reasons", "true", "--primary-leak-phase", "none"],
        [
            "--call-id",
            "AAPL:2026-07-05:run-1",
            "--reviewed-at",
            "2027-07-05",
            "--what-happened",
            "Bad phase.",
            "--right-for-the-reasons",
            "true",
            "--primary-leak-phase",
            "P8",
        ],
        [
            "--call-id",
            "AAPL:2026-07-05:run-1",
            "--reviewed-at",
            "2027-99-05",
            "--what-happened",
            "Bad date.",
            "--right-for-the-reasons",
            "true",
            "--primary-leak-phase",
            "none",
        ],
    ],
)
def test_calibration_review_cli_rejects_without_traceback(tmp_path, args: list[str]) -> None:
    _storage_with_call(tmp_path)

    result = subprocess.run(
        [sys.executable, "-m", "resolver", "calibration-review", "--data-root", str(tmp_path), *args],
        check=False,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "Traceback" not in combined
    payload = json.loads(result.stdout)
    assert payload["status"] == "rejected"


def _storage_with_call(tmp_path) -> LocalStorage:
    storage = LocalStorage(tmp_path)
    storage.append_calibration_call(_call("AAPL:2026-07-05:run-1"))
    return storage


def _call(
    call_id: str,
    *,
    ticker: str = "AAPL",
    call_date: date = date(2026, 7, 5),
    lean: str = "Buy",
    conviction: str = "Med",
    conviction_score: int = 6,
) -> CalibrationCall:
    return CalibrationCall(
        id=call_id,
        date=call_date,
        ticker=ticker,
        lean=lean,
        conviction=conviction,
        conviction_score=conviction_score,
        base_value=200.0,
        bear_value=150.0,
        review_by=date(2027, 7, 5),
        kill_metric="Revenue growth below 2%.",
    )
