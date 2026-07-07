"""Deterministic, offline provisioning of DCF sector base rates.

M4.5 Phase 2. The Damodaran-sourced, staleable numbers live in a committed
source snapshot (config/sources/<name>.json). The house-judgment layer (bear/bull
brackets, tagged tickers, rationale) lives in config/sector_brackets.yaml. This
module assembles the two into config.dcf.sector_scenarios.<sector> blocks so that
refreshing a sector's base rates is "drop in a new snapshot and re-run", not
hand-editing decimals in conventions.yaml.

No network, no LLM, no live data. The runtime (analyze()) is unchanged: it still
reads the committed conventions.yaml. This tool proves the committed sector blocks
are faithfully derived from the pinned source + house brackets, and regenerates
them on demand.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from skills.config import DcfSectorScenarioConfig

DEFAULT_CONVENTIONS = "config/conventions.yaml"
DEFAULT_BRACKETS = "config/sector_brackets.yaml"
DEFAULT_SOURCES_DIR = "config/sources"

_DRIVERS = ("revenue_growth", "nopat_margin", "sales_to_capital")
_SNAPSHOT_DRIVER_KEYS = {
    "revenue_growth": "revenue_growth_next_5y",
    "nopat_margin": "after_tax_operating_margin",
    "sales_to_capital": "sales_to_invested_capital",
}


class ProvisioningError(ValueError):
    """Raised when a sector block cannot be provisioned from its sources."""


def load_snapshot(path: Path | str) -> dict[str, Any]:
    resolved = Path(path)
    if not resolved.exists():
        raise ProvisioningError(f"snapshot_not_found:{resolved}")
    loaded = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ProvisioningError("snapshot root must be a mapping")
    for key in ("source_name", "source_date", "source_urls", "industries"):
        if key not in loaded:
            raise ProvisioningError(f"snapshot_missing_key:{key}")
    if not isinstance(loaded["industries"], dict) or not loaded["industries"]:
        raise ProvisioningError("snapshot industries must be a non-empty mapping")
    return loaded


def load_brackets(path: Path | str) -> dict[str, Any]:
    resolved = Path(path)
    if not resolved.exists():
        raise ProvisioningError(f"brackets_not_found:{resolved}")
    loaded = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ProvisioningError("brackets root must be a mapping")
    if not loaded.get("snapshot"):
        raise ProvisioningError("brackets must name a snapshot")
    sectors = loaded.get("sectors")
    if not isinstance(sectors, dict) or not sectors:
        raise ProvisioningError("brackets must define at least one sector")
    return loaded


def _round_base(value: Any, decimals: int) -> float:
    # round-half-to-even (Python default) on the snapshot's binary floats, so an
    # occasional .xxx5 tie rounds toward even rather than up. Snapshot values are
    # reviewed via `emit` before they land in conventions.yaml, so a surprising
    # tie is caught by a human rather than shipping silently.
    return round(float(value), decimals)


def build_sector_block(sector: str, house: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    """Assemble one config.dcf.sector_scenarios.<sector> block from its sources.

    Base values come from the snapshot (rounded to snapshot.base_value_decimals);
    bear/bull come from the house brackets. Missing sourced drivers fail closed
    rather than being imputed.
    """

    industry = house.get("industry_category")
    if not industry:
        raise ProvisioningError(f"sector_missing_industry_category:{sector}")
    industries = snapshot["industries"]
    if industry not in industries:
        raise ProvisioningError(f"snapshot_missing_industry:{industry}")
    row = industries[industry]
    if not isinstance(row, dict):
        raise ProvisioningError(f"snapshot_industry_not_a_mapping:{industry}")

    decimals = int(snapshot.get("base_value_decimals", 3))
    if row.get("firm_count") is None:
        raise ProvisioningError(f"snapshot_missing_driver:{industry}:firm_count")
    base: dict[str, float] = {}
    for driver in _DRIVERS:
        snapshot_key = _SNAPSHOT_DRIVER_KEYS[driver]
        if row.get(snapshot_key) is None:
            raise ProvisioningError(f"snapshot_missing_driver:{industry}:{snapshot_key}")
        base[driver] = _round_base(row[snapshot_key], decimals)

    brackets = house.get("brackets")
    if not isinstance(brackets, dict):
        raise ProvisioningError(f"sector_missing_brackets:{sector}")

    def _edge(edge: str) -> dict[str, float]:
        values: dict[str, float] = {}
        for driver in _DRIVERS:
            driver_brackets = brackets.get(driver)
            if not isinstance(driver_brackets, dict) or edge not in driver_brackets:
                raise ProvisioningError(f"sector_missing_bracket:{sector}:{driver}:{edge}")
            values[driver] = float(driver_brackets[edge])
        return values

    tickers = house.get("tickers")
    if not tickers:
        raise ProvisioningError(f"sector_missing_tickers:{sector}")
    rationale = house.get("rationale")
    if not rationale:
        raise ProvisioningError(f"sector_missing_rationale:{sector}")

    block = {
        "status": "active",
        "source_name": snapshot["source_name"],
        "source_date": snapshot["source_date"],
        "industry_category": industry,
        "firm_count": int(row["firm_count"]),
        "source_urls": dict(snapshot["source_urls"]),
        "tickers": list(tickers),
        "rationale": rationale,
        "scenarios": {
            "bear": _edge("bear"),
            "base": dict(base),
            "bull": _edge("bull"),
        },
    }
    # Fail closed on any malformed block before it can reach conventions.yaml.
    DcfSectorScenarioConfig.model_validate(block)
    return block


def generate_sector_blocks(
    *,
    brackets_path: Path | str = DEFAULT_BRACKETS,
    sources_dir: Path | str = DEFAULT_SOURCES_DIR,
) -> dict[str, dict[str, Any]]:
    brackets = load_brackets(brackets_path)
    snapshot = load_snapshot(Path(sources_dir) / f"{brackets['snapshot']}.json")
    return {
        sector: build_sector_block(sector, house, snapshot)
        for sector, house in brackets["sectors"].items()
    }


def _committed_sector_scenarios(conventions_path: Path | str) -> dict[str, Any]:
    loaded = yaml.safe_load(Path(conventions_path).read_text(encoding="utf-8"))
    return dict((loaded.get("dcf") or {}).get("sector_scenarios") or {})


def check_config(
    *,
    conventions_path: Path | str = DEFAULT_CONVENTIONS,
    brackets_path: Path | str = DEFAULT_BRACKETS,
    sources_dir: Path | str = DEFAULT_SOURCES_DIR,
) -> list[dict[str, str]]:
    """Return drift issues between generated sector blocks and the committed config.

    Empty list means every committed sector block is faithfully reproduced from
    the snapshot + house brackets, and no committed sector is left unprovisioned.
    """

    generated = generate_sector_blocks(brackets_path=brackets_path, sources_dir=sources_dir)
    committed = _committed_sector_scenarios(conventions_path)

    issues: list[dict[str, str]] = []
    for sector, block in generated.items():
        if sector not in committed:
            issues.append({"sector": sector, "code": "missing_in_config"})
        elif committed[sector] != block:
            issues.append({"sector": sector, "code": "drift"})
    for sector in committed:
        if sector not in generated:
            issues.append({"sector": sector, "code": "unprovisioned_in_config"})
    return issues


def emit_sector_block(
    sector: str,
    *,
    brackets_path: Path | str = DEFAULT_BRACKETS,
    sources_dir: Path | str = DEFAULT_SOURCES_DIR,
) -> str:
    blocks = generate_sector_blocks(brackets_path=brackets_path, sources_dir=sources_dir)
    if sector not in blocks:
        raise ProvisioningError(f"unknown_sector:{sector}")
    return yaml.safe_dump({sector: blocks[sector]}, sort_keys=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Provision DCF sector base rates from a source snapshot.")
    parser.add_argument("--conventions", default=DEFAULT_CONVENTIONS)
    parser.add_argument("--brackets", default=DEFAULT_BRACKETS)
    parser.add_argument("--sources-dir", default=DEFAULT_SOURCES_DIR)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="Verify conventions.yaml sector blocks match the snapshot + brackets.")
    emit_parser = sub.add_parser("emit", help="Print the regenerated block for one sector, ready to review and paste.")
    emit_parser.add_argument("sector")
    args = parser.parse_args(argv)

    try:
        if args.command == "check":
            issues = check_config(
                conventions_path=args.conventions,
                brackets_path=args.brackets,
                sources_dir=args.sources_dir,
            )
            print(json.dumps({"status": "ok" if not issues else "drift", "issues": issues}, indent=2, sort_keys=True))
            return 0 if not issues else 1
        block = emit_sector_block(args.sector, brackets_path=args.brackets, sources_dir=args.sources_dir)
        sys.stdout.write(block)
        return 0
    except ProvisioningError as exc:
        print(json.dumps({"status": "rejected", "error": {"code": "provisioning_error", "message": str(exc)}}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
