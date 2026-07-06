from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from skills.storage import LocalStorage
from skills.synthesis.calibration import CalibrationCall, CalibrationReview, record_calibration_review

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
    storage.append_calibration_call(
        CalibrationCall(
            id="AAPL:2026-07-05:run-1",
            date=date(2026, 7, 5),
            ticker="AAPL",
            lean="Buy",
            conviction="Med",
            conviction_score=6,
            base_value=200.0,
            bear_value=150.0,
            review_by=date(2027, 7, 5),
            kill_metric="Revenue growth below 2%.",
        )
    )
    return storage
