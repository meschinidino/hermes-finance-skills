"""M4.5 Phase 3: UBER realized-anchor DCF calibration, end to end.

The provisioning-tool guardrail proves algebraic coherence at provision time; this
suite proves the real DCF output is coherent and the miscalibration is fixed:
positive, monotonic scenario values, a bear defensibly below price (so the
price_at_or_below_bear flag clears), and the C-6 risk bear-case value still
reconciling to the filed C-4 bear scenario after the re-base.
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import resolver
from skills.storage import LocalStorage
from skills.synthesis.report_renderer import render_report

RUN_DATE = date(2026, 7, 3)
UBER_PRICE = 74.43  # tests/fixtures/uber_price.json


def _run(tmp_path: Path) -> tuple[LocalStorage, str]:
    storage = LocalStorage(tmp_path)
    resolver.analyze("UBER", as_of=RUN_DATE, storage=storage)
    return storage, f"runs/UBER/{RUN_DATE.isoformat()}"


def _scenarios(storage: LocalStorage, run_dir: str) -> dict[str, float]:
    vr = storage.get_json(f"{run_dir}/valuation_range.json")
    return {s["name"]: s["value"]["value"] for s in vr["scenarios"]}


def test_uber_realized_scenarios_positive_and_monotonic(tmp_path: Path) -> None:
    # The headline proof: the realized anchor produces a coherent range where the
    # dead industry-median anchor produced negative, non-monotonic values.
    storage, run_dir = _run(tmp_path)
    values = _scenarios(storage, run_dir)
    assert values["bear"] > 0
    assert values["bear"] < values["base"] < values["bull"]


def test_uber_bear_scenario_below_price(tmp_path: Path) -> None:
    storage, run_dir = _run(tmp_path)
    assert _scenarios(storage, run_dir)["bear"] < UBER_PRICE


def test_uber_report_no_longer_flags_price_at_or_below_bear(tmp_path: Path) -> None:
    storage, run_dir = _run(tmp_path)
    result = render_report(storage, run_dir)
    report = storage.get_text(result.output_path)
    flags = report.split("Valuation input flags:", 1)[1]
    assert "price_at_or_below_bear" not in flags
    # price_at_or_above_bull is an acceptable, legitimate "priced above realized-economics
    # DCF" signal, not a defect -- the flag we set out to clear is gone.
    assert "price_at_or_above_bull" in flags


def test_uber_c6_bear_case_value_reconciles_after_rebase(tmp_path: Path) -> None:
    # The sector source feeds C-4 scenarios and C-6 risk; after the re-base the C-6
    # bear-case value must still reconcile to the filed C-4 bear scenario.
    storage, run_dir = _run(tmp_path)
    bear_scenario = _scenarios(storage, run_dir)["bear"]
    risk = storage.get_json(f"{run_dir}/risk.json")
    bear_case_value = risk["bear_case_value"]["value"]
    assert math.isclose(bear_case_value, bear_scenario, rel_tol=1e-6, abs_tol=1e-6)


def test_aapl_not_flagged_price_at_or_below_bear(tmp_path: Path) -> None:
    # AAPL is not tagged to any sector and its global-default valuation does not show
    # the bear-above-price anomaly, so no AAPL bracket is needed (and none is added).
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    result = render_report(storage, f"runs/AAPL/{RUN_DATE.isoformat()}")
    report = storage.get_text(result.output_path)
    assert "price_at_or_below_bear" not in report
