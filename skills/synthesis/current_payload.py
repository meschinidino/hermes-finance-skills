from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from skills.analyst_artifacts import ReviewSourceManifest
from skills.interfaces import Storage


@dataclass(frozen=True)
class CurrentSynthesisInput:
    ticker: str
    as_of: date
    run_dir: str
    method: str
    route_manifest: ReviewSourceManifest
    handoff_path: str
    business_path: str
    moat_path: str
    capalloc_path: str
    scenario_path: str
    edge_cruxes_path: str
    risk_path: str
    valuation_range_path: str | None
    expectations_line_path: str | None
    valuation_deferred: str | None


def assemble_current_payload(storage: Storage, synthesis_input: CurrentSynthesisInput) -> dict[str, Any]:
    """Assemble today's resolver payload from already-filed artifacts.

    This is the M4a synthesis boundary. It deliberately preserves the current
    D-1/M2/M3 return shape and does not synthesize final M4 handoff fields.
    """

    run_dir = synthesis_input.run_dir
    payload = _required_json(storage, synthesis_input.handoff_path)
    payload["business"] = _required_json(storage, synthesis_input.business_path)
    payload["business_review_package"] = _required_json(storage, f"{run_dir}/business_review_package.json")
    payload["early_gate"] = _required_json(storage, f"{run_dir}/business_early_gate.json")
    payload["moat"] = _required_json(storage, synthesis_input.moat_path)
    payload["moat_review_package"] = _required_json(storage, f"{run_dir}/moat_review_package.json")
    payload["capalloc"] = _required_json(storage, synthesis_input.capalloc_path)
    payload["capalloc_review_package"] = _required_json(storage, f"{run_dir}/capalloc_review_package.json")
    payload["gate_card"] = _required_json(storage, f"{run_dir}/gate_card.json")
    payload["gate_card_review_package"] = _required_json(storage, f"{run_dir}/gate_card_review_package.json")
    payload["method_directive"] = _required_json(storage, f"{run_dir}/method_directive.json")
    payload["scenarios"] = _required_json(storage, synthesis_input.scenario_path)
    payload["scenarios_review_package"] = _required_json(storage, f"{run_dir}/scenarios_review_package.json")
    payload["edge_cruxes"] = _required_json(storage, synthesis_input.edge_cruxes_path)
    payload["edge_cruxes_review_package"] = _required_json(storage, f"{run_dir}/edge_cruxes_review_package.json")
    payload["risk"] = _required_json(storage, synthesis_input.risk_path)
    payload["risk_review_package"] = _required_json(storage, f"{run_dir}/risk_review_package.json")
    payload["senior_review_package"] = _required_json(storage, f"{run_dir}/senior_review_package.json")
    payload["senior_decision_package"] = _required_json(storage, f"{run_dir}/senior_decision_package.json")
    payload["route_review_manifest"] = synthesis_input.route_manifest.model_dump(mode="json")

    if synthesis_input.method == "DCF":
        if not synthesis_input.valuation_range_path or not synthesis_input.expectations_line_path:
            raise ValueError("DCF synthesis requires valuation_range_path and expectations_line_path")
        payload["valuation_range"] = _required_json(storage, synthesis_input.valuation_range_path)
        payload["expectations_line"] = _required_json(storage, synthesis_input.expectations_line_path)
    else:
        if synthesis_input.valuation_deferred is None:
            raise ValueError(f"{synthesis_input.method} synthesis requires valuation_deferred")
        payload["valuation_deferred"] = synthesis_input.valuation_deferred

    return payload


def _required_json(storage: Storage, path: str) -> dict[str, Any]:
    try:
        return storage.get_json(path)
    except FileNotFoundError as exc:
        raise ValueError(f"missing required synthesis artifact: {path}") from exc
