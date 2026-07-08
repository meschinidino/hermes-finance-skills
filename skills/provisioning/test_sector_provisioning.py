from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from skills.config import DcfSectorScenarioConfig, load_config
from skills.provisioning.sector_provisioning import (
    MIN_FIRMS,
    THIN_MARGIN,
    UPPER_MARGIN,
    ProvisioningError,
    build_sector_block,
    check_config,
    emit_sector_block,
    evaluate_guardrails,
    generate_sector_blocks,
    guardrail_summary,
    load_brackets,
    load_snapshot,
    main,
)

CONVENTIONS = "config/conventions.yaml"
BRACKETS = "config/sector_brackets.yaml"
SOURCES_DIR = "config/sources"


def _committed_saas() -> dict:
    loaded = yaml.safe_load(Path(CONVENTIONS).read_text(encoding="utf-8"))
    return loaded["dcf"]["sector_scenarios"]["saas"]


def test_saas_block_regenerates_from_snapshot_and_brackets() -> None:
    # The headline correctness proof: the committed SaaS block is faithfully
    # reproduced from the Damodaran snapshot + house brackets, field for field.
    generated = generate_sector_blocks()
    assert generated["saas"] == _committed_saas()


def test_check_config_reports_no_drift_on_committed_repo() -> None:
    assert check_config() == []


def test_base_values_are_damodaran_rounded_to_snapshot_decimals() -> None:
    generated = generate_sector_blocks()["saas"]["scenarios"]["base"]
    # Software (System & Application), data as of January 2026:
    # 12.33% growth, 32.62% after-tax operating margin, 1.54 sales/invested capital.
    assert generated == {"revenue_growth": 0.123, "nopat_margin": 0.326, "sales_to_capital": 1.54}


def test_generated_block_is_schema_valid() -> None:
    DcfSectorScenarioConfig.model_validate(generate_sector_blocks()["saas"])


def test_committed_config_still_loads() -> None:
    # analyze() runtime path is unchanged: conventions.yaml stays loadable.
    config = load_config(CONVENTIONS)
    assert config.dcf_sector_for_ticker("CRM") == "saas"


def _write_sources(tmp_path: Path, snapshot: dict, brackets: dict) -> tuple[Path, Path]:
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    (sources_dir / f"{brackets['snapshot']}.json").write_text(json.dumps(snapshot), encoding="utf-8")
    # Copy any per-sector snapshots the brackets reference (e.g. a realized anchor
    # sourced from its own EDGAR snapshot) so the full bracket set can generate.
    for house in brackets.get("sectors", {}).values():
        snap = house.get("snapshot")
        if snap and snap != brackets["snapshot"]:
            src = Path(SOURCES_DIR) / f"{snap}.json"
            (sources_dir / f"{snap}.json").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    brackets_path = tmp_path / "sector_brackets.yaml"
    brackets_path.write_text(yaml.safe_dump(brackets), encoding="utf-8")
    return brackets_path, sources_dir


def _base_snapshot() -> dict:
    return json.loads(Path(SOURCES_DIR).joinpath("damodaran-2026-01.json").read_text(encoding="utf-8"))


def _base_brackets() -> dict:
    return yaml.safe_load(Path(BRACKETS).read_text(encoding="utf-8"))


def test_refreshed_snapshot_flows_into_base_values(tmp_path: Path) -> None:
    snapshot = _base_snapshot()
    snapshot["industries"]["Software (System & Application)"]["revenue_growth_next_5y"] = 0.15
    brackets_path, sources_dir = _write_sources(tmp_path, snapshot, _base_brackets())
    block = generate_sector_blocks(brackets_path=brackets_path, sources_dir=sources_dir)["saas"]
    assert block["scenarios"]["base"]["revenue_growth"] == 0.15


def test_check_detects_drift(tmp_path: Path) -> None:
    snapshot = _base_snapshot()
    # A coherent margin drift (0.30 keeps the saas FCFF proxy monotonic; 0.40 would
    # make base > bull and trip the coherence guardrail before drift is reported).
    snapshot["industries"]["Software (System & Application)"]["after_tax_operating_margin"] = 0.30
    brackets_path, sources_dir = _write_sources(tmp_path, snapshot, _base_brackets())
    issues = check_config(conventions_path=CONVENTIONS, brackets_path=brackets_path, sources_dir=sources_dir)
    assert issues == [{"sector": "saas", "code": "drift"}]


def test_check_detects_unprovisioned_committed_sector(tmp_path: Path) -> None:
    # A sector hand-edited into conventions.yaml but not backed by the
    # provisioning layer must be flagged, not silently trusted.
    conventions = yaml.safe_load(Path(CONVENTIONS).read_text(encoding="utf-8"))
    conventions["dcf"]["sector_scenarios"]["mystery"] = dict(conventions["dcf"]["sector_scenarios"]["saas"])
    conventions_path = tmp_path / "conventions.yaml"
    conventions_path.write_text(yaml.safe_dump(conventions), encoding="utf-8")
    issues = check_config(conventions_path=conventions_path, brackets_path=BRACKETS, sources_dir=SOURCES_DIR)
    assert {"sector": "mystery", "code": "unprovisioned_in_config"} in issues


def test_missing_sourced_driver_fails_closed(tmp_path: Path) -> None:
    snapshot = _base_snapshot()
    del snapshot["industries"]["Software (System & Application)"]["sales_to_invested_capital"]
    brackets_path, sources_dir = _write_sources(tmp_path, snapshot, _base_brackets())
    with pytest.raises(ProvisioningError, match="snapshot_missing_driver"):
        generate_sector_blocks(brackets_path=brackets_path, sources_dir=sources_dir)


def test_industry_not_in_snapshot_fails_closed(tmp_path: Path) -> None:
    brackets = _base_brackets()
    brackets["sectors"]["saas"]["industry_category"] = "Nonexistent Industry"
    brackets_path, sources_dir = _write_sources(tmp_path, _base_snapshot(), brackets)
    with pytest.raises(ProvisioningError, match="snapshot_missing_industry"):
        generate_sector_blocks(brackets_path=brackets_path, sources_dir=sources_dir)


def test_missing_bracket_edge_fails_closed(tmp_path: Path) -> None:
    brackets = _base_brackets()
    del brackets["sectors"]["saas"]["brackets"]["nopat_margin"]["bull"]
    brackets_path, sources_dir = _write_sources(tmp_path, _base_snapshot(), brackets)
    with pytest.raises(ProvisioningError, match="sector_missing_bracket"):
        generate_sector_blocks(brackets_path=brackets_path, sources_dir=sources_dir)


def test_malformed_industry_row_fails_closed(tmp_path: Path) -> None:
    snapshot = _base_snapshot()
    snapshot["industries"]["Software (System & Application)"] = "not-a-mapping"
    brackets_path, sources_dir = _write_sources(tmp_path, snapshot, _base_brackets())
    with pytest.raises(ProvisioningError, match="snapshot_industry_not_a_mapping"):
        generate_sector_blocks(brackets_path=brackets_path, sources_dir=sources_dir)


def test_emit_unknown_sector_fails_closed() -> None:
    with pytest.raises(ProvisioningError, match="unknown_sector"):
        emit_sector_block("nope")


def test_cli_check_returns_zero_on_committed_repo(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["issues"] == []
    # Guardrail surfacing: saas passes clean, uber_realized carries its documented overrides.
    by_sector = {g["sector"]: g for g in out["guardrails"]}
    assert by_sector["saas"]["applied_overrides"] == []
    assert {o["guardrail"] for o in by_sector["uber_realized"]["applied_overrides"]} == {"firm_count", "nopat_margin"}
    assert all(g["coherence"] == "ok" for g in out["guardrails"])


def test_cli_emit_prints_block(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["emit", "saas"]) == 0
    printed = yaml.safe_load(capsys.readouterr().out)
    assert printed["saas"] == _committed_saas()


# --- M4.5 Phase 3: UBER realized anchor + guardrails ---


def _committed_sector(name: str) -> dict:
    loaded = yaml.safe_load(Path(CONVENTIONS).read_text(encoding="utf-8"))
    return loaded["dcf"]["sector_scenarios"][name]


def _block(firm_count: int, scenarios: dict) -> dict:
    # Minimal block shape evaluate_guardrails reads (firm_count + scenarios only) --
    # deliberately no EDGAR/ticker/price, proving the guardrail is pure and offline.
    return {"firm_count": firm_count, "scenarios": scenarios}


_COHERENT = {
    "bear": {"revenue_growth": 0.10, "nopat_margin": 0.06, "sales_to_capital": 2.00},
    "base": {"revenue_growth": 0.13, "nopat_margin": 0.08, "sales_to_capital": 2.30},
    "bull": {"revenue_growth": 0.16, "nopat_margin": 0.11, "sales_to_capital": 2.50},
}


def test_uber_realized_block_regenerates_from_snapshot_and_brackets() -> None:
    # The realized block is faithfully reproduced from its own snapshot + house layer.
    assert generate_sector_blocks()["uber_realized"] == _committed_sector("uber_realized")


def test_uber_realized_maps_and_saas_unchanged() -> None:
    config = load_config(CONVENTIONS)
    assert config.dcf_sector_for_ticker("UBER") == "uber_realized"
    assert config.dcf_sector_for_ticker("CRM") == "saas"


def test_untagged_ticker_uses_global_scenario_source() -> None:
    # A ticker in no sector resolves to the global dcf.scenarios source (None sector).
    assert load_config(CONVENTIONS).dcf_sector_for_ticker("AAPL") is None


def test_realized_base_overrides_growth_and_s2c_from_house_layer() -> None:
    # base nopat_margin comes from the snapshot (0.0802 -> 0.08); growth and s2c are
    # the house-owned faded/ex-goodwill judgments, not the raw snapshot facts (0.1812, 1.651).
    base = generate_sector_blocks()["uber_realized"]["scenarios"]["base"]
    assert base == {"revenue_growth": 0.13, "nopat_margin": 0.08, "sales_to_capital": 2.30}


def test_base_override_only_growth_and_s2c(tmp_path: Path) -> None:
    snapshot = _base_snapshot()
    brackets = _base_brackets()
    brackets["sectors"]["saas"]["base_overrides"] = {"nopat_margin": 0.5}
    brackets_path, sources_dir = _write_sources(tmp_path, snapshot, brackets)
    with pytest.raises(ProvisioningError, match="base_override_not_allowed"):
        generate_sector_blocks(brackets_path=brackets_path, sources_dir=sources_dir)


def test_non_numeric_base_override_fails_closed(tmp_path: Path) -> None:
    # A malformed override value fails closed as a ProvisioningError (clean rejected
    # JSON), not a raw ValueError traceback out of float().
    snapshot = _base_snapshot()
    brackets = _base_brackets()
    brackets["sectors"]["saas"]["base_overrides"] = {"revenue_growth": "not-a-number"}
    brackets_path, sources_dir = _write_sources(tmp_path, snapshot, brackets)
    with pytest.raises(ProvisioningError, match="base_override_not_numeric"):
        generate_sector_blocks(brackets_path=brackets_path, sources_dir=sources_dir)


def test_snapshot_holds_raw_realized_facts_not_the_used_values() -> None:
    # D3-A: the snapshot is a faithful record of raw facts; the used base growth/s2c
    # (0.13 / 2.30) live in the house layer, not the snapshot.
    snap = load_snapshot("config/sources/uber-realized-2026-01.json")
    row = snap["industries"]["UBER realized (FY2025 companyfacts)"]
    assert row["revenue_growth_next_5y"] == 0.1812   # raw trailing CAGR, not the faded 0.13
    assert row["sales_to_invested_capital"] == 1.651  # incl-goodwill raw, not the ex-gw 2.30
    assert row["sales_to_invested_capital_ex_goodwill"] == 2.305
    assert "trailing 3-year revenue CAGR" in snap["captured_by"]


def test_guardrail_thresholds_declared_in_one_place() -> None:
    assert (MIN_FIRMS, THIN_MARGIN, UPPER_MARGIN) == (50, 0.10, 0.60)


def test_uber_realized_block_passes_coherence() -> None:
    result = evaluate_guardrails("uber_realized", generate_sector_blocks()["uber_realized"],
                                 _base_brackets_overrides("uber_realized"))
    assert result["coherence"] == "ok"


def test_saas_emits_without_guardrail_override() -> None:
    # The passing sector (309 firms, 0.326 margin) clears every guardrail with no override.
    result = evaluate_guardrails("saas", generate_sector_blocks()["saas"], None)
    assert result["applied_overrides"] == []
    assert result["coherence"] == "ok"


def test_provisioning_stays_offline() -> None:
    # evaluate_guardrails runs on a hand-built block dict with no EDGAR, price, or ticker
    # analysis -- proving the coherence check adds no coupling to analyze().
    result = evaluate_guardrails("x", _block(1, _COHERENT),
                                 {"firm_count": "n=1 realized", "nopat_margin": "thin but real"})
    assert result["coherence"] == "ok"
    assert {o["guardrail"] for o in result["applied_overrides"]} == {"firm_count", "nopat_margin"}


def test_coherence_guardrail_rejects_negative_fcff_scenario() -> None:
    scenarios = {
        "bear": {"revenue_growth": 0.10, "nopat_margin": 0.06, "sales_to_capital": 2.00},
        "base": {"revenue_growth": 0.30, "nopat_margin": 0.05, "sales_to_capital": 1.00},  # 0.05 < 0.30
        "bull": {"revenue_growth": 0.16, "nopat_margin": 0.11, "sales_to_capital": 2.50},
    }
    with pytest.raises(ProvisioningError, match="guardrail_incoherent_negative_fcff"):
        evaluate_guardrails("x", _block(100, scenarios), None)


def test_coherence_guardrail_rejects_internet_platform_median() -> None:
    # The exact dead industry-median block: growth at that margin destroys value.
    # Pins the past failure so the incoherent-median class can never ship again.
    scenarios = {
        "bear": {"revenue_growth": 0.08, "nopat_margin": 0.02, "sales_to_capital": 1.00},
        "base": {"revenue_growth": 0.177, "nopat_margin": 0.046, "sales_to_capital": 1.35},
        "bull": {"revenue_growth": 0.25, "nopat_margin": 0.12, "sales_to_capital": 1.35},
    }
    with pytest.raises(ProvisioningError, match="guardrail_incoherent"):
        evaluate_guardrails("internet_platform", _block(29, scenarios),
                            {"firm_count": "thin", "nopat_margin": "low"})


def test_coherence_guardrail_rejects_non_monotonic_proxy() -> None:
    # All scenarios positive FCFF proxy, but base proxy < bear proxy (non-monotonic).
    scenarios = {
        "bear": {"revenue_growth": 0.05, "nopat_margin": 0.15, "sales_to_capital": 3.00},  # proxy 0.133
        "base": {"revenue_growth": 0.20, "nopat_margin": 0.10, "sales_to_capital": 3.00},  # proxy 0.033
        "bull": {"revenue_growth": 0.10, "nopat_margin": 0.20, "sales_to_capital": 3.00},  # proxy 0.167
    }
    with pytest.raises(ProvisioningError, match="guardrail_incoherent_non_monotonic"):
        evaluate_guardrails("x", _block(100, scenarios), None)


def test_coherence_guardrail_is_not_overridable() -> None:
    scenarios = {
        "bear": {"revenue_growth": 0.30, "nopat_margin": 0.05, "sales_to_capital": 1.00},
        "base": {"revenue_growth": 0.13, "nopat_margin": 0.08, "sales_to_capital": 2.30},
        "bull": {"revenue_growth": 0.16, "nopat_margin": 0.11, "sales_to_capital": 2.50},
    }
    with pytest.raises(ProvisioningError, match="guardrail_override_not_allowed:x:coherence"):
        evaluate_guardrails("x", _block(100, scenarios), {"coherence": "please ignore"})


def test_firm_count_override_required_and_surfaced() -> None:
    with pytest.raises(ProvisioningError, match="guardrail_violation_requires_override:x:firm_count"):
        evaluate_guardrails("x", _block(1, _COHERENT), {"nopat_margin": "thin but real"})
    ok = evaluate_guardrails("x", _block(1, _COHERENT), {"firm_count": "n=1 realized", "nopat_margin": "thin"})
    assert {o["guardrail"] for o in ok["applied_overrides"]} == {"firm_count", "nopat_margin"}


def test_thin_margin_override_required_and_surfaced() -> None:
    # firm_count high (no firm-count violation), but base margin 0.08 < THIN_MARGIN.
    with pytest.raises(ProvisioningError, match="guardrail_violation_requires_override:x:nopat_margin"):
        evaluate_guardrails("x", _block(100, _COHERENT), None)


def test_unused_override_declaration_fails_closed() -> None:
    # saas-like block: 309 firms, healthy margin -> no violation; declaring an override is stale.
    healthy = {
        "bear": {"revenue_growth": 0.06, "nopat_margin": 0.22, "sales_to_capital": 1.20},
        "base": {"revenue_growth": 0.12, "nopat_margin": 0.30, "sales_to_capital": 1.54},
        "bull": {"revenue_growth": 0.20, "nopat_margin": 0.38, "sales_to_capital": 2.00},
    }
    with pytest.raises(ProvisioningError, match="guardrail_unused_override:x:firm_count"):
        evaluate_guardrails("x", _block(309, healthy), {"firm_count": "not actually thin"})


def test_hard_margin_implausible_not_overridable() -> None:
    scenarios = {
        "bear": {"revenue_growth": 0.10, "nopat_margin": 0.06, "sales_to_capital": 2.00},
        "base": {"revenue_growth": 0.13, "nopat_margin": 0.90, "sales_to_capital": 2.30},  # > UPPER_MARGIN
        "bull": {"revenue_growth": 0.16, "nopat_margin": 0.95, "sales_to_capital": 2.50},
    }
    with pytest.raises(ProvisioningError, match="guardrail_margin_implausible"):
        evaluate_guardrails("x", _block(100, scenarios), {"nopat_margin": "trust me"})


def _base_brackets_overrides(sector: str) -> dict:
    return _base_brackets()["sectors"][sector].get("guardrail_overrides")
