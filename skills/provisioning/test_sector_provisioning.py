from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from skills.config import DcfSectorScenarioConfig, load_config
from skills.provisioning.sector_provisioning import (
    ProvisioningError,
    build_sector_block,
    check_config,
    emit_sector_block,
    generate_sector_blocks,
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
    snapshot["industries"]["Software (System & Application)"]["after_tax_operating_margin"] = 0.40
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
    assert out == {"status": "ok", "issues": []}


def test_cli_emit_prints_block(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["emit", "saas"]) == 0
    printed = yaml.safe_load(capsys.readouterr().out)
    assert printed["saas"] == _committed_saas()
