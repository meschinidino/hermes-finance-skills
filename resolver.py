from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from skills.audit import audit_analyst_artifact, audit_artifact, audit_m1_handoff, audit_senior_review_package
from skills.config import load_config
from skills.data.cost_of_capital.cost_of_capital import build_cost_of_capital_inputs
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.data.price.price import fetch_price
from skills.interfaces import LLM, PriceFeed, Senior, Storage
from skills.accountant_artifacts import EdgarFacts
from skills.analyst_artifacts import collect_ratifiables
from skills.serialization import artifact_model_to_payload
from skills.research.business.business import BusinessArtifact, EarlyGateResult, StopArtifact, build_business_artifact
from skills.research.capalloc.capalloc import build_capalloc_artifact
from skills.research.moat.moat import build_moat_artifact
from skills.storage import LocalStorage
from skills.synthesis.handoff.handoff import build_handoff
from skills.valuation.dcf.dcf import build_dcf_artifacts
from skills.valuation.method_router.method_router import route_method
from skills.valuation.normalize.normalize import normalize_financials
from skills.valuation.screens.screens import build_gate_card
from skills.valuation.spine.spine import build_spine


def analyze(
    ticker: str,
    *,
    as_of: date | None = None,
    config_path: Path | str = Path("config/conventions.yaml"),
    storage: Storage | None = None,
    senior: Senior | None = None,
    llm: LLM | None = None,
    price_feed: PriceFeed | None = None,
) -> dict[str, Any]:
    """Run the M1 walking skeleton route for a US-listed ticker."""

    normalized_ticker = ticker.upper().strip()
    if not normalized_ticker:
        raise ValueError("ticker is required")

    run_date = as_of or date.today()
    config = load_config(config_path)
    active_storage = storage or LocalStorage()

    edgar = fetch_edgar_facts(normalized_ticker)
    price = fetch_price(normalized_ticker, edgar=edgar, price_feed=price_feed, as_of=run_date)
    cost_of_capital = build_cost_of_capital_inputs(
        normalized_ticker,
        config,
        edgar=edgar,
        price=price,
        as_of=run_date,
    )
    normalized = normalize_financials(edgar)
    spine = build_spine(
        normalized,
        cost_of_capital,
        price,
        excess_cash_pct=config.invested_capital.excess_cash_pct,
        schema_version=config.schema_version,
    )
    handoff = build_handoff(
        normalized_ticker,
        edgar.cik,
        spine,
        price=price.price,
        as_of=run_date,
        schema_version=config.schema_version,
        flags=edgar.flags + price.flags + cost_of_capital.flags,
        source_accessions=_source_accessions(edgar),
    )

    run_dir = f"runs/{normalized_ticker}/{run_date.isoformat()}"
    spine_payload = artifact_model_to_payload(spine)
    active_storage.put_json(f"{run_dir}/spine.json", spine_payload)
    if active_storage.get_json(f"{run_dir}/spine.json") != spine_payload:
        raise RuntimeError("spine storage round-trip failed")

    handoff_path = f"{run_dir}/handoff.json"
    audit_m1_handoff(handoff, storage=active_storage, path=handoff_path)

    business_path = f"{run_dir}/business.json"
    business = build_business_artifact(
        edgar,
        as_of=run_date,
        schema_version=config.schema_version,
        run_dir=run_dir,
    )
    audit_analyst_artifact(business, storage=active_storage, path=business_path)
    gate_result = _run_business_early_gate(
        business,
        business_path=business_path,
        ticker=normalized_ticker,
        as_of=run_date,
        schema_version=config.schema_version,
        senior=senior or _OfflineEarlyGateSenior(),
        analyst_family=_declared_family(llm) if llm is not None else "offline-business-drafter",
        storage=active_storage,
        run_dir=run_dir,
    )
    if gate_result.decision == "NO-GO":
        stop_path = f"{run_dir}/business_stop.json"
        stop = StopArtifact(
            header=_header(config.schema_version, "early_gate"),
            ticker=normalized_ticker,
            as_of=run_date,
            gate_name="business_early_gate",
            gate_decision="NO-GO",
            stop_reason="business early gate halted the run",
            gate_rationale=gate_result.rationale,
            business_artifact_path=business_path,
            evidence_package=business.source_evidence_summary,
        )
        _put_m3_roundtrip(active_storage, stop_path, stop)
        payload = {
            "status": "halted",
            "ticker": normalized_ticker,
            "as_of": run_date.isoformat(),
            "business": active_storage.get_json(business_path),
            "early_gate": active_storage.get_json(f"{run_dir}/business_early_gate.json"),
            "stop_artifact": active_storage.get_json(stop_path),
        }
        return payload

    moat_path = f"{run_dir}/moat.json"
    moat = build_moat_artifact(
        edgar,
        spine,
        as_of=run_date,
        schema_version=config.schema_version,
        run_dir=run_dir,
    )
    audit_analyst_artifact(moat, storage=active_storage, path=moat_path)
    moat_review = collect_ratifiables(
        moat,
        ticker=normalized_ticker,
        as_of=run_date,
        header=_header(config.schema_version, "C-2-review"),
        source_artifact=moat_path,
    )
    audit_senior_review_package(moat_review, storage=active_storage, path=f"{run_dir}/moat_review_package.json")

    capalloc_path = f"{run_dir}/capalloc.json"
    capalloc = build_capalloc_artifact(
        edgar,
        spine,
        as_of=run_date,
        schema_version=config.schema_version,
        run_dir=run_dir,
    )
    audit_analyst_artifact(capalloc, storage=active_storage, path=capalloc_path)
    capalloc_review = collect_ratifiables(
        capalloc,
        ticker=normalized_ticker,
        as_of=run_date,
        header=_header(config.schema_version, "C-3-review"),
        source_artifact=capalloc_path,
    )
    audit_senior_review_package(capalloc_review, storage=active_storage, path=f"{run_dir}/capalloc_review_package.json")

    industry_classification = _industry_classification(normalized_ticker, config)
    gate_card = build_gate_card(
        edgar,
        price,
        industry_classification=industry_classification,
        schema_version=config.schema_version,
    )
    audit_artifact(gate_card, storage=active_storage, path=f"{run_dir}/gate_card.json")

    method_directive = route_method(
        normalized,
        edgar,
        config,
        industry_classification=industry_classification,
        schema_version=config.schema_version,
    )
    audit_artifact(method_directive, storage=active_storage, path=f"{run_dir}/method_directive.json")

    if method_directive.method == "DCF":
        valuation_range, expectations_line = build_dcf_artifacts(normalized, edgar, price, cost_of_capital, config)
        audit_artifact(valuation_range, storage=active_storage, path=f"{run_dir}/valuation_range.json")
        audit_artifact(expectations_line, storage=active_storage, path=f"{run_dir}/expectations_line.json")

    payload = active_storage.get_json(handoff_path)
    payload["business"] = active_storage.get_json(business_path)
    payload["early_gate"] = active_storage.get_json(f"{run_dir}/business_early_gate.json")
    payload["moat"] = active_storage.get_json(moat_path)
    payload["moat_review_package"] = active_storage.get_json(f"{run_dir}/moat_review_package.json")
    payload["capalloc"] = active_storage.get_json(capalloc_path)
    payload["capalloc_review_package"] = active_storage.get_json(f"{run_dir}/capalloc_review_package.json")
    payload["gate_card"] = active_storage.get_json(f"{run_dir}/gate_card.json")
    payload["method_directive"] = active_storage.get_json(f"{run_dir}/method_directive.json")
    if method_directive.method != "DCF":
        payload["valuation_deferred"] = method_directive.fallback_behavior
        return payload
    payload["valuation_range"] = active_storage.get_json(f"{run_dir}/valuation_range.json")
    payload["expectations_line"] = active_storage.get_json(f"{run_dir}/expectations_line.json")

    return payload


class GateWiringError(ValueError):
    pass


class _OfflineEarlyGateSenior:
    model_family = "offline-senior"
    decided_by = "offline-senior"

    def gate(self, package: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision": "GO",
            "rationale": "offline deterministic M3.2 early gate accepted audited Business artifact",
            "decided_by": self.decided_by,
            "ticker": package["ticker"],
        }

    def ratify(self, package: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("M3.2 does not implement consolidated ratification")


def _run_business_early_gate(
    business: BusinessArtifact,
    *,
    business_path: str,
    ticker: str,
    as_of: date,
    schema_version: str,
    senior: Senior,
    analyst_family: str,
    storage: Storage,
    run_dir: str,
) -> EarlyGateResult:
    senior_family = _declared_family(senior)
    if not analyst_family or not senior_family:
        raise GateWiringError("analyst and senior adapters must declare model families")
    if analyst_family == senior_family:
        raise GateWiringError(f"analyst and senior model families must differ: {analyst_family}")

    gate_response = senior.gate(
        {
            "gate_name": "business_early_gate",
            "ticker": ticker,
            "as_of": as_of.isoformat(),
            "business_artifact_path": business_path,
            "business_artifact": artifact_model_to_payload(business),
        }
    )
    decision = str(gate_response.get("decision", "")).upper()
    if decision not in {"GO", "NO-GO"}:
        raise ValueError(f"invalid early gate decision: {decision}")
    result = EarlyGateResult(
        header=_header(schema_version, "early_gate"),
        ticker=ticker,
        as_of=as_of,
        gate_name="business_early_gate",
        decision=decision,
        rationale=str(gate_response.get("rationale") or gate_response.get("reason") or "no rationale supplied"),
        decided_by=str(gate_response.get("decided_by") or gate_response.get("senior") or senior_family),
        business_artifact_path=business_path,
    )
    _put_m3_roundtrip(storage, f"{run_dir}/business_early_gate.json", result)
    return result


def _declared_family(adapter: Any) -> str | None:
    if adapter is None:
        return None
    for attr in ("model_family", "model_handle", "senior_handle"):
        value = getattr(adapter, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _put_m3_roundtrip(storage: Storage, path: str, artifact) -> None:
    payload = artifact_model_to_payload(artifact)
    storage.put_json(path, payload)
    if storage.get_json(path) != payload:
        raise RuntimeError(f"storage round-trip failed: {path}")


def _header(schema_version: str, produced_by: str):
    from datetime import datetime, timezone

    from skills._primitives import Header

    return Header(schema_version=schema_version, produced_by=produced_by, produced_at=datetime.now(timezone.utc))


def _source_accessions(edgar: EdgarFacts) -> list[str]:
    accessions: set[str] = set()
    for values in edgar.facts:
        for number in values[1]:
            accession = number.provenance.accession
            if accession and accession != "explicit-zero":
                accessions.add(accession)
    return sorted(accessions)


def _industry_classification(ticker: str, config) -> str:
    for sector, beta in config.betas.items():
        if ticker.upper() in {item.upper() for item in beta.tickers}:
            return sector
    raise ValueError(f"missing_industry_classification:{ticker}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the finance skill pack resolver.")
    parser.add_argument("ticker", help="US-listed ticker to analyze")
    args = parser.parse_args()
    print(json.dumps(analyze(args.ticker), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
