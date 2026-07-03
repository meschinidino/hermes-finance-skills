from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from skills.audit import audit_analyst_artifact, audit_artifact, audit_m1_handoff, audit_senior_decision_package, audit_senior_review_package
from skills.config import load_config
from skills.control_flow import (
    AnalystIdentity,
    AzureFoundrySenior,
    IdentityAuditError,
    LiveSeniorAPIError,
    RouteAuditError,
    RouteRecorder,
    analyst_identity_from_adapter,
    assert_independent,
    audit_route_events,
    file_kill_memo,
    senior_identity_from_adapter,
)
from skills.data.cost_of_capital.cost_of_capital import build_cost_of_capital_inputs
from skills.data.edgar.edgar import enabled_tickers, fetch_edgar_facts
from skills.data.price.price import fetch_price
from skills.interfaces import LLM, PriceFeed, Senior, Storage
from skills.accountant_artifacts import EdgarFacts
from skills.analyst_artifacts import ReviewSourceManifest, collect_accountant_ratifiables, collect_ratifiables, consolidate_review_packages, ratify_review_package
from skills.research.business.business import BusinessArtifact, EarlyGateResult, build_business_artifact
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
from skills.synthesis.review_packager.review_packager import build_final_lean_review_package, build_review_package
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
    route = RouteRecorder()

    edgar = fetch_edgar_facts(normalized_ticker)
    route.record("A-1", produced_artifacts=[f"runs/{normalized_ticker}/{run_date.isoformat()}/edgar_facts.memory"])
    price = fetch_price(normalized_ticker, edgar=edgar, price_feed=price_feed, as_of=run_date)
    route.record("A-2", produced_artifacts=[f"runs/{normalized_ticker}/{run_date.isoformat()}/price.memory"])
    cost_of_capital = build_cost_of_capital_inputs(
        normalized_ticker,
        config,
        edgar=edgar,
        price=price,
        as_of=run_date,
    )
    route.record("A-3", produced_artifacts=[f"runs/{normalized_ticker}/{run_date.isoformat()}/cost_of_capital.memory"])
    normalized = normalize_financials(edgar)
    route.record("B-1", produced_artifacts=[f"runs/{normalized_ticker}/{run_date.isoformat()}/normalized.memory"])
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
    route.record("B-2", produced_artifacts=[f"{run_dir}/spine.json"], audits=["audit_artifact"])

    handoff_path = f"{run_dir}/handoff.json"
    audit_m1_handoff(handoff, storage=active_storage, path=handoff_path)
    route.record("D-1", produced_artifacts=[handoff_path], audits=["audit_m1_handoff"])

    business_path = f"{run_dir}/business.json"
    business = build_business_artifact(
        edgar,
        as_of=run_date,
        schema_version=config.schema_version,
        run_dir=run_dir,
    )
    audit_analyst_artifact(business, storage=active_storage, path=business_path)
    route.record("C-1", produced_artifacts=[business_path], audits=["audit_analyst_artifact"])
    try:
        gate_result = _run_business_early_gate(
            business,
            business_path=business_path,
            ticker=normalized_ticker,
            as_of=run_date,
            schema_version=config.schema_version,
            senior=active_senior,
            analyst_identity=_analyst_identity_for_boundary(llm, "offline-business-drafter"),
            storage=active_storage,
            run_dir=run_dir,
        )
    except LiveSeniorAPIError as exc:
        return _live_senior_api_halt(
            active_storage,
            run_dir=run_dir,
            schema_version=config.schema_version,
            ticker=normalized_ticker,
            as_of=run_date,
            gate="business_early_gate",
            reason=str(exc),
            evidence_paths=[business_path],
            senior=active_senior,
        )
    except (IdentityAuditError, GateWiringError) as exc:
        return _identity_audit_halt(
            active_storage,
            run_dir=run_dir,
            schema_version=config.schema_version,
            ticker=normalized_ticker,
            as_of=run_date,
            gate="business_early_gate",
            reason=str(exc),
            evidence_paths=[business_path],
            senior=active_senior,
        )
    route.record("EARLY-GATE", produced_artifacts=[f"{run_dir}/business_early_gate.json"], senior_touchpoint="early_gate")
    if gate_result.decision == "NO-GO":
        payload = _halt(
            active_storage,
            run_dir=run_dir,
            schema_version=config.schema_version,
            ticker=normalized_ticker,
            as_of=run_date,
            halt_kind="business_no_go",
            gate="business_early_gate",
            reason=gate_result.rationale,
            evidence_paths=[business_path, f"{run_dir}/business_early_gate.json"],
            senior=active_senior,
        )
        payload["business"] = active_storage.get_json(business_path)
        payload["early_gate"] = active_storage.get_json(f"{run_dir}/business_early_gate.json")
        payload["stop_artifact"] = {
            **payload["kill_memo"],
            "gate_decision": "NO-GO",
            "business_artifact_path": business_path,
        }
        active_storage.put_json(f"{run_dir}/business_stop.json", payload["stop_artifact"])
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
    route.record("B-4", produced_artifacts=[f"{run_dir}/gate_card.json"], audits=["audit_artifact"])
    if gate_card.verdict.draft == "KILL":
        return _halt(
            active_storage,
            run_dir=run_dir,
            schema_version=config.schema_version,
            ticker=normalized_ticker,
            as_of=run_date,
            halt_kind="gate_kill",
            gate="B-4",
            reason=gate_card.kill_reason or "gate card verdict was KILL",
            evidence_paths=[f"{run_dir}/gate_card.json"],
            senior=active_senior,
        )
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
    route.record("B-6", produced_artifacts=[f"{run_dir}/method_directive.json"], audits=["audit_artifact"])

    if method_directive.method == "DCF":
        valuation_range, expectations_line = build_dcf_artifacts(normalized, edgar, price, cost_of_capital, config)
        audit_artifact(valuation_range, storage=active_storage, path=f"{run_dir}/valuation_range.json")
        audit_artifact(expectations_line, storage=active_storage, path=f"{run_dir}/expectations_line.json")
        route.record("B-3", produced_artifacts=[f"{run_dir}/valuation_range.json", f"{run_dir}/expectations_line.json"], audits=["audit_artifact"])

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
    base_rate_paths = _base_rate_anchor_paths(scenarios)
    if base_rate_paths:
        route.record("B-5", produced_artifacts=base_rate_paths, audits=["audit_artifact"])
    route.record("C-4", produced_artifacts=[scenario_path], audits=["audit_scenario_set"])
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
    route.record("C-5", produced_artifacts=[edge_cruxes_path], audits=["audit_edge_cruxes"])
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
    route.record("C-6", produced_artifacts=[risk_path], audits=["audit_risk_artifact"])
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
    try:
        senior_decision_package = ratify_review_package(
            senior_review_package,
            senior=active_senior,
            analyst_identity=_analyst_identity_for_boundary(llm, "offline-analyst-drafters"),
            header=_header(config.schema_version, "M3-7-ratify"),
        )
    except LiveSeniorAPIError as exc:
        return _live_senior_api_halt(
            active_storage,
            run_dir=run_dir,
            schema_version=config.schema_version,
            ticker=normalized_ticker,
            as_of=run_date,
            gate="consolidated_ratification",
            reason=str(exc),
            evidence_paths=[f"{run_dir}/senior_review_package.json"],
            senior=active_senior,
        )
    except IdentityAuditError as exc:
        return _identity_audit_halt(
            active_storage,
            run_dir=run_dir,
            schema_version=config.schema_version,
            ticker=normalized_ticker,
            as_of=run_date,
            gate="consolidated_ratification",
            reason=str(exc),
            evidence_paths=[f"{run_dir}/senior_review_package.json"],
            senior=active_senior,
        )
    audit_senior_decision_package(senior_decision_package, storage=active_storage, path=f"{run_dir}/senior_decision_package.json")
    route.record(
        "M3-7",
        produced_artifacts=[f"{run_dir}/senior_review_package.json", f"{run_dir}/senior_decision_package.json"],
        audits=["audit_senior_review_package", "audit_senior_decision_package"],
        senior_touchpoint="consolidated_ratification",
    )

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
    route.record("D-2", produced_artifacts=[f"{run_dir}/conviction.json"], audits=["ConvictionArtifact"])
    final_lean_review_package = build_final_lean_review_package(
        conviction,
        source_artifact=f"{run_dir}/conviction.json",
        header=_header(config.schema_version, "D-2-lean-review"),
    )
    audit_senior_review_package(final_lean_review_package, storage=active_storage, path=f"{run_dir}/final_lean_review_package.json")
    try:
        final_lean_decision_package = ratify_review_package(
            final_lean_review_package,
            senior=active_senior,
            analyst_identity=_analyst_identity_for_boundary(llm, "offline-synthesis-drafter"),
            header=_header(config.schema_version, "D-2-lean-ratify"),
        )
    except LiveSeniorAPIError as exc:
        return _live_senior_api_halt(
            active_storage,
            run_dir=run_dir,
            schema_version=config.schema_version,
            ticker=normalized_ticker,
            as_of=run_date,
            gate="final_lean_ratification",
            reason=str(exc),
            evidence_paths=[f"{run_dir}/final_lean_review_package.json"],
            senior=active_senior,
        )
    except IdentityAuditError as exc:
        return _identity_audit_halt(
            active_storage,
            run_dir=run_dir,
            schema_version=config.schema_version,
            ticker=normalized_ticker,
            as_of=run_date,
            gate="final_lean_ratification",
            reason=str(exc),
            evidence_paths=[f"{run_dir}/final_lean_review_package.json"],
            senior=active_senior,
        )
    audit_senior_decision_package(final_lean_decision_package, storage=active_storage, path=f"{run_dir}/final_lean_decision_package.json")
    route.record(
        "FINAL-LEAN",
        produced_artifacts=[f"{run_dir}/final_lean_review_package.json", f"{run_dir}/final_lean_decision_package.json"],
        audits=["audit_senior_review_package", "audit_senior_decision_package"],
        senior_touchpoint="final_lean_ratification",
    )
    final_lean_decision = final_lean_decision_package.decisions.get("final_lean")
    if final_lean_decision is not None and final_lean_decision.decision == "overturned" and final_lean_decision.final is None:
        payload = _halt(
            active_storage,
            run_dir=run_dir,
            schema_version=config.schema_version,
            ticker=normalized_ticker,
            as_of=run_date,
            halt_kind="senior_overturn_without_replacement",
            gate="final_lean_ratification",
            reason="Senior overturned the final Buy/Watch/Pass lean without providing a replacement final.",
            evidence_paths=[f"{run_dir}/final_lean_review_package.json", f"{run_dir}/final_lean_decision_package.json"],
            senior=active_senior,
            replacement_required=True,
            replacement_provided=False,
        )
        payload["final_lean_review_package"] = active_storage.get_json(f"{run_dir}/final_lean_review_package.json")
        payload["final_lean_decision_package"] = active_storage.get_json(f"{run_dir}/final_lean_decision_package.json")
        payload["returned_for_revision"] = {
            "halt_reason": "final_lean_overturned_without_replacement",
            "decision": "overturned",
            "replacement_final": None,
        }
        return payload
    route.record("D-3", produced_artifacts=[f"{run_dir}/final_handoff.json"], audits=["FinalHandoff"])
    try:
        audit_route_events(route.events, method=method_directive.method, storage=None)
    except RouteAuditError as exc:
        return _halt(
            active_storage,
            run_dir=run_dir,
            schema_version=config.schema_version,
            ticker=normalized_ticker,
            as_of=run_date,
            halt_kind="route_audit_violation",
            gate="route_audit",
            reason=str(exc),
            evidence_paths=[f"{run_dir}/senior_decision_package.json", f"{run_dir}/final_lean_decision_package.json"],
            senior=active_senior,
        )
    final_payload = artifact_model_to_payload(
        build_review_package(
            synthesis_payload,
            conviction,
            storage=active_storage,
            run_dir=run_dir,
            lean_decision_package=final_lean_decision_package,
        )
    )
    active_storage.put_json(f"{run_dir}/route_manifest.json", route.manifest_payload())
    return final_payload


class GateWiringError(IdentityAuditError):
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
    identity = {
        "provider": "offline",
        "model": "offline-senior",
        "model_family": "offline-senior",
        "adapter": "offline",
        "metadata_source": "standalone-default",
    }

    def gate(self, package: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision": "GO",
            "rationale": "offline deterministic M3.2 early gate accepted audited Business artifact",
            "decided_by": self.decided_by,
            "ticker": package["ticker"],
            "senior_identity": self.identity,
        }

    def ratify(self, package: dict[str, Any]) -> dict[str, Any]:
        item_ids = list(package.get("required_item_ids", []))
        return {
            "decided_by": self.decided_by,
            "senior_identity": self.identity,
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
    analyst_identity: AnalystIdentity,
    storage: Storage,
    run_dir: str,
) -> EarlyGateResult:
    try:
        senior_identity = senior_identity_from_adapter(senior)
        assert_independent(analyst_identity, senior_identity)
    except IdentityAuditError as exc:
        raise GateWiringError(str(exc)) from exc

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
    senior_identity = senior_identity_from_adapter(senior, gate_response)
    result = EarlyGateResult(
        header=_header(schema_version, "early_gate"),
        ticker=ticker,
        as_of=as_of,
        gate_name="business_early_gate",
        decision=decision,
        rationale=str(gate_response.get("rationale") or gate_response.get("reason") or "no rationale supplied"),
        decided_by=str(gate_response.get("decided_by") or gate_response.get("senior") or senior_identity.model_family),
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


def _analyst_identity_for_boundary(llm: LLM | None, offline_fallback: str) -> AnalystIdentity:
    if llm is None:
        return analyst_identity_from_adapter(None, offline_fallback)
    return analyst_identity_from_adapter(llm, _declared_family(llm))


def _identity_audit_halt(
    storage: Storage,
    *,
    run_dir: str,
    schema_version: str,
    ticker: str,
    as_of: date,
    gate: str,
    reason: str,
    evidence_paths: list[str],
    senior: Senior,
) -> dict[str, Any]:
    return _halt(
        storage,
        run_dir=run_dir,
        schema_version=schema_version,
        ticker=ticker,
        as_of=as_of,
        halt_kind="identity_audit_violation",
        gate=gate,
        reason=reason,
        evidence_paths=evidence_paths,
        senior=senior,
    )


def _live_senior_api_halt(
    storage: Storage,
    *,
    run_dir: str,
    schema_version: str,
    ticker: str,
    as_of: date,
    gate: str,
    reason: str,
    evidence_paths: list[str],
    senior: Senior,
) -> dict[str, Any]:
    return _halt(
        storage,
        run_dir=run_dir,
        schema_version=schema_version,
        ticker=ticker,
        as_of=as_of,
        halt_kind="live_senior_api_failure",
        gate=gate,
        reason=reason,
        evidence_paths=evidence_paths,
        senior=senior,
    )


def _put_m3_roundtrip(storage: Storage, path: str, artifact) -> None:
    payload = artifact_model_to_payload(artifact)
    storage.put_json(path, payload)
    if storage.get_json(path) != payload:
        raise RuntimeError(f"storage round-trip failed: {path}")


def _halt(
    storage: Storage,
    *,
    run_dir: str,
    schema_version: str,
    ticker: str,
    as_of: date,
    halt_kind,
    gate: str,
    reason: str,
    evidence_paths: list[str],
    senior: Senior | None = None,
    replacement_required: bool = False,
    replacement_provided: bool = False,
) -> dict[str, Any]:
    senior_identity = senior_identity_from_adapter(senior) if senior is not None else None
    return file_kill_memo(
        storage=storage,
        run_dir=run_dir,
        header=_header(schema_version, "KILL"),
        ticker=ticker,
        as_of=as_of,
        halt_kind=halt_kind,
        gate=gate,
        reason=reason,
        evidence_paths=evidence_paths,
        senior_identity=senior_identity,
        replacement_required=replacement_required,
        replacement_provided=replacement_provided,
    )


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


def _base_rate_anchor_paths(scenarios) -> list[str]:
    paths = []
    for scenario in scenarios.scenarios:
        for assumption in scenario.assumptions:
            anchor = getattr(assumption, "base_rate_anchor", None)
            path = getattr(anchor, "artifact_path", None)
            if isinstance(path, str) and path.strip():
                paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the finance skill pack resolver.")
    parser.add_argument("ticker", help="US-listed ticker to analyze")
    parser.add_argument(
        "--senior",
        choices=["offline", "azure-foundry"],
        default="offline",
        help="Senior adapter to use. azure-foundry fails closed if environment identity is incomplete.",
    )
    args = parser.parse_args()
    try:
        senior = AzureFoundrySenior.from_env() if args.senior == "azure-foundry" else None
        print(json.dumps(analyze(args.ticker, senior=senior), indent=2, sort_keys=True))
    except IdentityAuditError as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "error": {
                        "code": "identity_audit_violation",
                        "message": str(exc),
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(1) from None
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
