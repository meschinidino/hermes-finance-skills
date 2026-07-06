from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

import resolver
from skills.bundle_validation import validate_skill_bundle
from skills.storage import LocalStorage
from skills.synthesis.report_renderer import normalize_cli_run_dir, render_report

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_DATE = date(2026, 7, 3)


def test_report_renderer_bundle_is_deterministic_accountant() -> None:
    bundle = Path(__file__).parent

    validate_skill_bundle(bundle, expected_role="accountant")

    assert not (bundle / "prompt.md").exists()
    assert not (bundle / "eval").exists()


def test_render_report_rejects_missing_terminal_artifact(tmp_path) -> None:
    storage = LocalStorage(tmp_path)

    with pytest.raises(ValueError, match="neither final_handoff"):
        render_report(storage, "runs/AAPL/2026-07-03")


def test_render_report_rejects_conflicting_terminal_artifacts(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    storage.put_json(
        "runs/AAPL/2026-07-03/kill_memo.json",
        {"ticker": "AAPL", "gate": "P0", "reason": "test conflict"},
    )

    with pytest.raises(ValueError, match="both final_handoff"):
        render_report(storage, "runs/AAPL/2026-07-03")


def test_render_dcf_final_handoff_writes_markdown_report(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)

    result = render_report(storage, "runs/AAPL/2026-07-03")
    report = storage.get_text(result.output_path)

    assert result.output_path == "runs/AAPL/2026-07-03/report.md"
    assert "AAPL Fundamental Analysis Report" in report
    assert "Final lean:" in report
    assert "Conviction:" in report
    assert "Current price:" in report
    assert "Bear value:" in report
    assert "Base value:" in report
    assert "Bull value:" in report
    assert "Kill metric:" in report
    assert report.count("| Metric:") == 3
    assert "Revisit Triggers" in report
    assert "Provenance Summary" in report
    assert "Displayed estimate Numbers:" in report


def test_rendered_thesis_formats_moat_dict_as_sentences(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("UBER", as_of=RUN_DATE, storage=storage)

    result = render_report(storage, "runs/UBER/2026-07-03")
    report = storage.get_text(result.output_path)
    thesis = report.split("## Thesis", 1)[1].split("### Whats Priced In", 1)[0]

    assert "Mechanism category: network effects." in thesis
    assert "Mechanism evidence:" in thesis
    assert "Supporting categories:" in thesis
    assert "{'claim':" not in thesis
    assert "mechanism_category" not in thesis
    assert "support_categories" not in thesis
    assert "{" not in thesis
    assert "}" not in thesis


def test_rendered_report_omits_internal_milestones_and_unavailable_placeholders(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)

    result = render_report(storage, "runs/AAPL/2026-07-03")
    report = storage.get_text(result.output_path)

    assert "M2a" not in report
    assert "M2b" not in report
    assert "Frame justification" not in report
    assert "Implied revenue_growth: unavailable" not in report
    assert "Implied revenue_growth_midpoint: unavailable" not in report
    assert "unavailable" not in report.lower()


def test_render_method_deferred_handoff_does_not_fabricate_dcf_values(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("MRNA", as_of=RUN_DATE, storage=storage)

    result = render_report(storage, "runs/MRNA/2026-07-03")
    report = storage.get_text(result.output_path)

    assert "MRNA Fundamental Analysis Report" in report
    assert "Method: rNPV" in report
    assert "Route-deferred valuation:" in report
    assert "method_deferred" in report
    assert "Bear value:" not in report
    assert [warning.code for warning in result.warnings] == ["method_deferred"]


def test_render_kill_memo_writes_short_kill_report(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    storage.put_json(
        "runs/ZZZ/2026-07-03/kill_memo.json",
        {"ticker": "ZZZ", "gate": "P0", "reason": "Liquidity gate failed."},
    )

    result = render_report(storage, "runs/ZZZ/2026-07-03")
    report = storage.get_text(result.output_path)

    assert "ZZZ Kill Report" in report
    assert "Gate: P0" in report
    assert "Liquidity gate failed." in report
    assert "Valuation" not in report
    assert "Falsifiable Cruxes" not in report


def test_valuation_flags_include_degenerate_inputs(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    handoff = storage.get_json("runs/AAPL/2026-07-03/final_handoff.json")
    price_value = handoff["price"]["value"]
    handoff["valuation_range"]["scenarios"][0]["value"]["value"] = price_value
    handoff["valuation_range"]["scenarios"][1]["value"]["value"] = price_value - 1
    handoff["valuation_range"]["scenarios"][2]["value"]["value"] = price_value + 10
    storage.put_json("runs/AAPL/2026-07-03/final_handoff.json", handoff)
    scenarios = storage.get_json("runs/AAPL/2026-07-03/scenarios.json")
    scenarios["scenarios"][0]["value"]["value"] = price_value
    scenarios["scenarios"][1]["value"]["value"] = price_value - 1
    scenarios["scenarios"][2]["value"]["value"] = price_value + 10
    storage.put_json("runs/AAPL/2026-07-03/scenarios.json", scenarios)

    result = render_report(storage, "runs/AAPL/2026-07-03")
    report = storage.get_text(result.output_path)

    assert "price_at_or_below_bear" in report
    assert "non_monotonic_scenarios" in report
    assert {warning.code for warning in result.warnings} == {"price_at_or_below_bear", "non_monotonic_scenarios"}


def test_invalid_final_handoff_is_rejected(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    handoff = storage.get_json("runs/AAPL/2026-07-03/final_handoff.json")
    handoff["lean"]["decision"] = None
    storage.put_json("runs/AAPL/2026-07-03/final_handoff.json", handoff)

    with pytest.raises(ValidationError):
        render_report(storage, "runs/AAPL/2026-07-03")


def test_auxiliary_conflict_fails_closed(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    risk = storage.get_json("runs/AAPL/2026-07-03/risk.json")
    risk["kill_metric"]["draft"]["metric"] = "conflicting metric"
    storage.put_json("runs/AAPL/2026-07-03/risk.json", risk)

    with pytest.raises(ValueError, match="risk.json conflicts"):
        render_report(storage, "runs/AAPL/2026-07-03")


def test_scenario_auxiliary_conflict_fails_closed(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    scenarios = storage.get_json("runs/AAPL/2026-07-03/scenarios.json")
    scenarios["scenarios"][0]["value"]["value"] += 1
    storage.put_json("runs/AAPL/2026-07-03/scenarios.json", scenarios)

    with pytest.raises(ValueError, match="scenarios.json conflicts"):
        render_report(storage, "runs/AAPL/2026-07-03")


def test_custom_output_path_and_cli_run_dir_normalization(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)

    assert normalize_cli_run_dir("data/runs/AAPL/2026-07-03") == "runs/AAPL/2026-07-03"
    result = render_report(storage, "runs/AAPL/2026-07-03", output_path="runs/AAPL/2026-07-03/custom.md")

    assert result.output_path == "runs/AAPL/2026-07-03/custom.md"
    assert storage.get_text("runs/AAPL/2026-07-03/custom.md").startswith("# AAPL")


def test_resolver_render_report_cli_prints_result_json(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "resolver",
            "render-report",
            "--data-root",
            str(tmp_path),
            "--run-dir",
            str(tmp_path / "runs" / "AAPL" / "2026-07-03"),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["output_path"] == "runs/AAPL/2026-07-03/report.md"
    assert payload["format"] == "markdown"


def test_resolver_render_report_cli_rejects_invalid_input_without_traceback(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "resolver",
            "render-report",
            "--data-root",
            str(tmp_path),
            "--run-dir",
            "runs/AAPL/2026-07-03",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "Traceback" not in completed.stderr
    assert json.loads(completed.stdout)["status"] == "rejected"
