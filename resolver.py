from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from skills.audit import audit_analyst_artifact, audit_artifact, audit_m1_handoff, audit_senior_decision_package, audit_senior_review_package
from skills.config import load_config
from skills.data.cost_of_capital.cost_of_capital import build_cost_of_capital_inputs
from skills.data.edgar.edgar import enabled_tickers, fetch_edgar_facts
from skills.data.price.price import fetch_price
from skills.interfaces import LLM, PriceFeed, Senior, Storage
from skills.accountant_artifacts import EdgarFacts
from skills.analyst_artifacts import ReviewSourceManifest, collect_accountant_ratifiables, collect_ratifiables, consolidate_review_packages, ratify_review_package
from skills.research.business.business import BusinessArtifact, EarlyGateResult, StopArtifact, build_business_artifact
from skills.research.capalloc.capalloc import build_capalloc_artifact
from skills.research.edge_cruxes.edge_cruxes import audit_edge_cruxes, build_edge_cruxes_artifact
from skills.research.moat.moat import build_moat_artifact
from skills.research.risk.risk import audit_risk_artifact, build_risk_artifact
from skills.research.scenarios.scenarios import audit_scenario_set, build_scenario_set_artifact
from skills.serialization import artifact_model_to_payload
from skills.storage import LocalStorage
from skills.synthesis.conviction.conviction import build_conviction
from skills.synthesis.current_payload import CurrentSynthesisInput, assemble_current_payload
from skills.synthesis.handoff.handoff import build_handoff
from skills.synthesis.m4b_payload import SynthesisPayload
from skills.synthesis.review_packager.review_packager import FinalLeanReturnedForRevision, build_final_lean_review_package, build_review_package
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
    active_senior = senior or _OfflineSenior()

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
        senior=active_senior,
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

    business_review = collect_ratifiables(
        business,
        ticker=normalized_ticker,
        as_of=run_date,
        header=_header(config.schema_version, "C-1-review"),
        source_artifact=business_path,
    )
    audit_senior_review_package(business_review, storage=active_storage, path=f"{run_dir}/business_review_package.json")

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
    gate_card_review = collect_accountant_ratifiables(
        gate_card,
        ticker=normalized_ticker,
        as_of=run_date,
        header=_header(config.schema_version, "B-4-review"),
        source_artifact=f"{run_dir}/gate_card.json",
    )
    audit_senior_review_package(gate_card_review, storage=active_storage, path=f"{run_dir}/gate_card_review_package.json")

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

    scenario_path = f"{run_dir}/scenarios.json"
    valuation_range_path = f"{run_dir}/valuation_range.json" if method_directive.method == "DCF" else None
    expectations_line_path = f"{run_dir}/expectations_line.json" if method_directive.method == "DCF" else None
    scenarios = build_scenario_set_artifact(
        ticker=normalized_ticker,
        as_of=run_date,
        schema_version=config.schema_version,
        storage=active_storage,
        run_dir=run_dir,
        method_directive_path=f"{run_dir}/method_directive.json",
        valuation_range_path=valuation_range_path,
        expectations_line_path=expectations_line_path,
    )
    audit_scenario_set(scenarios, storage=active_storage)
    _put_m3_roundtrip(active_storage, scenario_path, scenarios)
    scenario_review = collect_ratifiables(
        scenarios,
        ticker=normalized_ticker,
        as_of=run_date,
        header=_header(config.schema_version, "C-4-review"),
        source_artifact=scenario_path,
    )
    audit_senior_review_package(scenario_review, storage=active_storage, path=f"{run_dir}/scenarios_review_package.json")

    edge_cruxes_path = f"{run_dir}/edge_cruxes.json"
    edge_cruxes = build_edge_cruxes_artifact(
        ticker=normalized_ticker,
        as_of=run_date,
        schema_version=config.schema_version,
        storage=active_storage,
        run_dir=run_dir,
        business_path=business_path,
        moat_path=moat_path,
        capalloc_path=capalloc_path,
        scenarios_path=scenario_path,
        gate_card_path=f"{run_dir}/gate_card.json",
        method_directive_path=f"{run_dir}/method_directive.json",
        spine_path=f"{run_dir}/spine.json",
        valuation_range_path=valuation_range_path,
        expectations_line_path=expectations_line_path,
    )
    audit_edge_cruxes(edge_cruxes, storage=active_storage, path=edge_cruxes_path)
    edge_cruxes_review = collect_ratifiables(
        edge_cruxes,
        ticker=normalized_ticker,
        as_of=run_date,
        header=_header(config.schema_version, "C-5-review"),
        source_artifact=edge_cruxes_path,
    )
    audit_senior_review_package(edge_cruxes_review, storage=active_storage, path=f"{run_dir}/edge_cruxes_review_package.json")

    risk_path = f"{run_dir}/risk.json"
    risk = build_risk_artifact(
        ticker=normalized_ticker,
        as_of=run_date,
        schema_version=config.schema_version,
        storage=active_storage,
        run_dir=run_dir,
        business_path=business_path,
        moat_path=moat_path,
        capalloc_path=capalloc_path,
        scenarios_path=scenario_path,
        edge_cruxes_path=edge_cruxes_path,
        gate_card_path=f"{run_dir}/gate_card.json",
        method_directive_path=f"{run_dir}/method_directive.json",
        spine_path=f"{run_dir}/spine.json",
        valuation_range_path=valuation_range_path,
        expectations_line_path=expectations_line_path,
    )
    audit_risk_artifact(risk, storage=active_storage, path=risk_path)
    risk_review = collect_ratifiables(
        risk,
        ticker=normalized_ticker,
        as_of=run_date,
        header=_header(config.schema_version, "C-6-review"),
        source_artifact=risk_path,
    )
    audit_senior_review_package(risk_review, storage=active_storage, path=f"{run_dir}/risk_review_package.json")
    route_manifest = build_review_source_manifest(
        method=method_directive.method,
        run_dir=run_dir,
        business_path=business_path,
        moat_path=moat_path,
        capalloc_path=capalloc_path,
        scenario_path=scenario_path,
        edge_cruxes_path=edge_cruxes_path,
        risk_path=risk_path,
        valuation_range_path=valuation_range_path,
        expectations_line_path=expectations_line_path,
    )
    context_sources = {source: f"{method_directive.method} route context" for source in route_manifest.required_context_sources}
    senior_review_package = consolidate_review_packages(
        [gate_card_review, business_review, moat_review, capalloc_review, scenario_review, edge_cruxes_review, risk_review],
        ticker=normalized_ticker,
        as_of=run_date,
        header=_header(config.schema_version, "M3-7-review"),
        manifest=route_manifest,
        context_sources=context_sources,
    )
    audit_senior_review_package(senior_review_package, storage=active_storage, path=f"{run_dir}/senior_review_package.json")
    senior_decision_package = ratify_review_package(
        senior_review_package,
        senior=active_senior,
        analyst_family=_declared_family(llm) if llm is not None else "offline-analyst-drafters",
        header=_header(config.schema_version, "M3-7-ratify"),
    )
    audit_senior_decision_package(senior_decision_package, storage=active_storage, path=f"{run_dir}/senior_decision_package.json")

    current_payload = assemble_current_payload(
        active_storage,
        CurrentSynthesisInput(
            ticker=normalized_ticker,
            as_of=run_date,
            run_dir=run_dir,
            method=method_directive.method,
            route_manifest=route_manifest,
            handoff_path=handoff_path,
            business_path=business_path,
            moat_path=moat_path,
            capalloc_path=capalloc_path,
            scenario_path=scenario_path,
            edge_cruxes_path=edge_cruxes_path,
            risk_path=risk_path,
            valuation_range_path=valuation_range_path,
            expectations_line_path=expectations_line_path,
            valuation_deferred=None if method_directive.method == "DCF" else method_directive.fallback_behavior,
        ),
    )
    synthesis_payload = SynthesisPayload.model_validate(current_payload)
    conviction = build_conviction(synthesis_payload, storage=active_storage, run_dir=run_dir)
    final_lean_review_package = build_final_lean_review_package(
        conviction,
        source_artifact=f"{run_dir}/conviction.json",
        header=_header(config.schema_version, "D-2-lean-review"),
    )
    audit_senior_review_package(final_lean_review_package, storage=active_storage, path=f"{run_dir}/final_lean_review_package.json")
    final_lean_decision_package = ratify_review_package(
        final_lean_review_package,
        senior=active_senior,
        analyst_family=_declared_family(llm) if llm is not None else "offline-synthesis-drafter",
        header=_header(config.schema_version, "D-2-lean-ratify"),
    )
    audit_senior_decision_package(final_lean_decision_package, storage=active_storage, path=f"{run_dir}/final_lean_decision_package.json")
    final_lean_decision = final_lean_decision_package.decisions.get("final_lean")
    if final_lean_decision is not None and final_lean_decision.decision == "overturned" and final_lean_decision.final is None:
        returned_path = f"{run_dir}/final_lean_returned_for_revision.json"
        returned = FinalLeanReturnedForRevision(
            header=_header(config.schema_version, "D-2-lean-returned-for-revision"),
            ticker=normalized_ticker,
            as_of=run_date,
            status="halted",
            halt_reason="final_lean_overturned_without_replacement",
            message="Senior overturned the final Buy/Watch/Pass lean without providing a replacement final.",
            final_lean_review_package_path=f"{run_dir}/final_lean_review_package.json",
            final_lean_decision_package_path=f"{run_dir}/final_lean_decision_package.json",
            decided_by=final_lean_decision_package.decided_by,
            decision="overturned",
            replacement_final=None,
        )
        _put_m3_roundtrip(active_storage, returned_path, returned)
        return {
            "status": "halted",
            "ticker": normalized_ticker,
            "as_of": run_date.isoformat(),
            "final_lean_review_package": active_storage.get_json(f"{run_dir}/final_lean_review_package.json"),
            "final_lean_decision_package": active_storage.get_json(f"{run_dir}/final_lean_decision_package.json"),
            "returned_for_revision": active_storage.get_json(returned_path),
        }
    return artifact_model_to_payload(
        build_review_package(
            synthesis_payload,
            conviction,
            storage=active_storage,
            run_dir=run_dir,
            lean_decision_package=final_lean_decision_package,
        )
    )


class GateWiringError(ValueError):
    pass


def build_review_source_manifest(
    *,
    method: str,
    run_dir: str,
    business_path: str,
    moat_path: str,
    capalloc_path: str,
    scenario_path: str,
    edge_cruxes_path: str,
    risk_path: str,
    valuation_range_path: str | None,
    expectations_line_path: str | None,
) -> ReviewSourceManifest:
    review_sources = (
        f"{run_dir}/gate_card.json",
        business_path,
        moat_path,
        capalloc_path,
        scenario_path,
        edge_cruxes_path,
        risk_path,
    )
    context_sources = [f"{run_dir}/method_directive.json"]
    if method == "DCF":
        if not valuation_range_path or not expectations_line_path:
            raise ValueError("DCF route contract requires valuation_range and expectations_line")
        context_sources.extend([valuation_range_path, expectations_line_path])
    return ReviewSourceManifest(
        method=method,
        required_sources=review_sources,
        required_context_sources=tuple(context_sources),
    )


class _OfflineSenior:
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
        item_ids = list(package.get("required_item_ids", []))
        return {
            "decided_by": self.decided_by,
            "decisions": {
                item_id: {"decision": "ratified", "final": None, "rationale": f"offline deterministic ratification accepted {item_id}"}
                for item_id in item_ids
            },
        }


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
    # Offline defaults compare placeholder labels ("offline-business-drafter" vs
    # "offline-senior"); live wiring must still provide real model-family labels.
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
    try:
        print(json.dumps(analyze(args.ticker), indent=2, sort_keys=True))
    except ValueError as exc:
        error = str(exc)
        if not error.startswith("unknown_ticker:"):
            raise
        requested_ticker = error.split(":", 1)[1].upper()
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "error": {
                        "code": "unknown_ticker",
                        "requested_ticker": requested_ticker,
                        "enabled_tickers": enabled_tickers(),
                        "message": "ticker not enabled in this deployment",
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
