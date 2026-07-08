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
# For a realized anchor the base growth and reinvestment are house judgments
# layered on the raw sourced facts; base margin always comes from the snapshot.
_BASE_OVERRIDABLE = ("revenue_growth", "sales_to_capital")

# Economic guardrails (house policy, judged identically for every sector). These
# are NOT sourced data and NOT per-sector judgment, so they live here as module
# constants rather than in the snapshot or the house bracket layer.
MIN_FIRMS = 50            # firm-count reliability floor for a cross-sectional sample
THIN_MARGIN = 0.10        # base NOPAT margin below this is flagged (override-able)
UPPER_MARGIN = 0.60       # base NOPAT margin above this (or <= 0) is a data error (hard)
# Guardrails a sector may knowingly waive with a written rationale.
_OVERRIDABLE_GUARDRAILS = ("firm_count", "nopat_margin")


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
        # The snapshot must carry the raw sourced fact for every driver even when
        # the base is house-overridden, so it stays a faithful, refreshable record.
        if row.get(snapshot_key) is None:
            raise ProvisioningError(f"snapshot_missing_driver:{industry}:{snapshot_key}")
        base[driver] = _round_base(row[snapshot_key], decimals)

    # Realized anchors layer a house judgment (faded growth, ex-goodwill turnover)
    # on top of the raw sourced facts. Only revenue_growth and sales_to_capital may
    # be overridden; base nopat_margin always comes from the snapshot.
    base_overrides = house.get("base_overrides") or {}
    if not isinstance(base_overrides, dict):
        raise ProvisioningError(f"sector_base_overrides_not_a_mapping:{sector}")
    for driver, value in base_overrides.items():
        if driver not in _BASE_OVERRIDABLE:
            raise ProvisioningError(f"base_override_not_allowed:{sector}:{driver}")
        try:
            base[driver] = float(value)
        except (TypeError, ValueError):
            raise ProvisioningError(f"base_override_not_numeric:{sector}:{driver}:{value!r}") from None

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


def evaluate_guardrails(sector: str, block: dict[str, Any], overrides: Any = None) -> dict[str, Any]:
    """Apply the economic guardrails to an assembled block.

    Two guardrail families:

    - Coherence (NOT override-able): every scenario must have a positive free-cash-
      flow proxy (nopat_margin > revenue_growth / sales_to_capital) and the proxy
      must be ordered bear < base < bull. This is the algebraic proxy only -- no DCF,
      no EDGAR -- so provisioning stays pure and offline. It catches the incoherent
      industry-median class (0.046 < 0.177/1.35) at `check`/`emit`, before a bad
      block can reach conventions.yaml and halt analyze() on the C-4 ordering audit.
      The full positive-value + monotonicity check on the real DCF output lives in
      the UBER validation test, which already runs analyze().
    - Override-able economic guardrails: firm_count >= MIN_FIRMS and base
      nopat_margin >= THIN_MARGIN. A violation fails closed unless the house layer
      declares a matching `guardrail_overrides` entry with a non-empty rationale. A
      base margin of <= 0 or > UPPER_MARGIN is a data error with no override.

    Returns a surfacing record ({sector, applied_overrides, coherence}). Raises
    ProvisioningError on any un-overridden violation, unused override, or incoherence.
    """

    overrides = overrides or {}
    if not isinstance(overrides, dict):
        raise ProvisioningError(f"guardrail_overrides_not_a_mapping:{sector}")

    scenarios = block["scenarios"]
    base_margin = float(scenarios["base"]["nopat_margin"])

    # Hard margin plausibility (never override-able): catch data errors.
    if base_margin <= 0 or base_margin > UPPER_MARGIN:
        raise ProvisioningError(f"guardrail_margin_implausible:{sector}:{base_margin}")

    # Coherence proxy (never override-able).
    if "coherence" in overrides:
        raise ProvisioningError(f"guardrail_override_not_allowed:{sector}:coherence")
    proxies: dict[str, float] = {}
    for name in ("bear", "base", "bull"):
        scenario = scenarios[name]
        s2c = float(scenario["sales_to_capital"])
        if s2c <= 0:
            raise ProvisioningError(f"guardrail_nonpositive_sales_to_capital:{sector}:{name}")
        proxy = float(scenario["nopat_margin"]) - float(scenario["revenue_growth"]) / s2c
        if proxy <= 0:
            raise ProvisioningError(f"guardrail_incoherent_negative_fcff:{sector}:{name}")
        proxies[name] = proxy
    if not (proxies["bear"] < proxies["base"] < proxies["bull"]):
        raise ProvisioningError(f"guardrail_incoherent_non_monotonic:{sector}")

    # Override-able economic guardrails.
    violations: list[str] = []
    if int(block["firm_count"]) < MIN_FIRMS:
        violations.append("firm_count")
    if base_margin < THIN_MARGIN:
        violations.append("nopat_margin")

    applied: list[dict[str, str]] = []
    for guardrail in violations:
        rationale = overrides.get(guardrail)
        if not (isinstance(rationale, str) and rationale.strip()):
            raise ProvisioningError(f"guardrail_violation_requires_override:{sector}:{guardrail}")
        applied.append({"guardrail": guardrail, "rationale": rationale})

    # An override declared for a guardrail that is not actually violated keeps the
    # override set honest to the data.
    for name in overrides:
        if name not in violations:
            raise ProvisioningError(f"guardrail_unused_override:{sector}:{name}")

    return {"sector": sector, "applied_overrides": applied, "coherence": "ok"}


def _build_all(
    brackets_path: Path | str,
    sources_dir: Path | str,
) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """Assemble every sector block and run its guardrails once.

    Returns (sector, block, guardrail_result) per sector. Fails closed on any
    un-overridden guardrail violation or incoherence before a block can be treated
    as valid or emitted. Shared by generate_sector_blocks and guardrail_summary so
    the per-sector snapshot loading and build happen in exactly one place.
    """

    brackets = load_brackets(brackets_path)
    default_snapshot = brackets["snapshot"]
    cache: dict[str, dict[str, Any]] = {}

    def _snapshot_for(house: dict[str, Any]) -> dict[str, Any]:
        # A sector may name its own snapshot (a realized anchor is sourced from
        # EDGAR, not the Damodaran industry file); otherwise use the default.
        name = house.get("snapshot", default_snapshot)
        if name not in cache:
            cache[name] = load_snapshot(Path(sources_dir) / f"{name}.json")
        return cache[name]

    built: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for sector, house in brackets["sectors"].items():
        block = build_sector_block(sector, house, _snapshot_for(house))
        result = evaluate_guardrails(sector, block, house.get("guardrail_overrides"))
        built.append((sector, block, result))
    return built


def generate_sector_blocks(
    *,
    brackets_path: Path | str = DEFAULT_BRACKETS,
    sources_dir: Path | str = DEFAULT_SOURCES_DIR,
) -> dict[str, dict[str, Any]]:
    return {sector: block for sector, block, _ in _build_all(brackets_path, sources_dir)}


def guardrail_summary(
    *,
    brackets_path: Path | str = DEFAULT_BRACKETS,
    sources_dir: Path | str = DEFAULT_SOURCES_DIR,
) -> list[dict[str, Any]]:
    """Per-sector guardrail surfacing for `check`: applied overrides + coherence."""

    return [result for _, _, result in _build_all(brackets_path, sources_dir)]


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
            guardrails = guardrail_summary(brackets_path=args.brackets, sources_dir=args.sources_dir)
            print(json.dumps(
                {"status": "ok" if not issues else "drift", "issues": issues, "guardrails": guardrails},
                indent=2,
                sort_keys=True,
            ))
            return 0 if not issues else 1
        block = emit_sector_block(args.sector, brackets_path=args.brackets, sources_dir=args.sources_dir)
        sys.stdout.write(block)
        return 0
    except ProvisioningError as exc:
        print(json.dumps({"status": "rejected", "error": {"code": "provisioning_error", "message": str(exc)}}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
