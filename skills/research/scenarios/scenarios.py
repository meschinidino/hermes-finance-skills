from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import ValidationError, model_validator

from skills._primitives import Header, Number, Provenance
from skills.audit import AuditError, audit_analyst_artifact, audit_artifact
from skills.interfaces import Storage
from skills.accountant_artifacts import (
    BaseRateForecast,
    BaseRateResult,
    DcfAssumption,
    ExpectationsLine,
    MethodDirective,
    ValuationRange,
)
from skills.analyst_artifacts import AnalystDraft, EvidenceRef, M3Model
from skills.valuation.base_rate.base_rate import lookup_base_rate

SCENARIO_ORDER = ("bear", "base", "bull")
PROBABILITY_TOLERANCE = 0.000001
DCF_ONLY_DRIVERS = {
    "starting_revenue",
    "forecast_years",
    "terminal_growth",
    "net_debt",
    "diluted_shares",
    "revenue_growth",
    "nopat_margin",
    "sales_to_capital",
    "wacc",
}
DIRECT_DRIVER_METRIC_MAP = {
    "revenue_growth": "revenue_growth",
    "nopat_margin": "margin_expansion",
}


class BaseRateAnchor(M3Model):
    artifact_path: str


class ScenarioAssumptionDraft(M3Model):
    driver: str
    value: Number | None = None
    base_rate_anchor: BaseRateAnchor | None = None
    evidence_refs: list[EvidenceRef]
    rationale: str

    @model_validator(mode="after")
    def validate_assumption(self) -> ScenarioAssumptionDraft:
        if not self.driver.strip():
            raise ValueError("scenario assumption requires driver")
        if not self.evidence_refs:
            raise ValueError("scenario assumption requires evidence refs")
        if not self.rationale.strip():
            raise ValueError("scenario assumption requires rationale")
        return self


class ScenarioEntry(M3Model):
    name: Literal["bear", "base", "bull"]
    value: Number | None = None
    assumptions: list[ScenarioAssumptionDraft]
    probability: AnalystDraft | None = None

    @model_validator(mode="after")
    def validate_entry_content(self) -> ScenarioEntry:
        if not self.assumptions:
            raise ValueError(f"{self.name} scenario requires assumptions or method-deferral evidence")
        return self


class ScenarioSetArtifact(M3Model):
    header: Header
    ticker: str
    as_of: date
    status: Literal["drafted", "method_deferred"]
    method_directive_path: str
    valuation_range_path: str | None = None
    expectations_line_path: str | None = None
    scenarios: list[ScenarioEntry]
    source_evidence_summary: dict[str, str]

    @model_validator(mode="after")
    def validate_scenario_set(self) -> ScenarioSetArtifact:
        if [scenario.name for scenario in self.scenarios] != list(SCENARIO_ORDER):
            raise ValueError("scenario set requires bear/base/bull order")
        for key, value in self.source_evidence_summary.items():
            if not key.strip() or not value.strip() or value.strip().lower() in {"todo", "stub", "not implemented"}:
                raise ValueError("scenario source evidence summary must be substantive")
        if self.status == "drafted":
            for scenario in self.scenarios:
                if scenario.value is None:
                    raise ValueError(f"{scenario.name} scenario requires value")
                if scenario.probability is None:
                    raise ValueError(f"{scenario.name} scenario requires probability draft")
        return self


def build_scenario_set_artifact(
    *,
    ticker: str,
    as_of: date,
    schema_version: str,
    storage: Storage,
    run_dir: str,
    method_directive_path: str,
    valuation_range_path: str | None = None,
    expectations_line_path: str | None = None,
) -> ScenarioSetArtifact:
    method_directive = _load_method_directive(storage, method_directive_path)
    audit_artifact(method_directive)
    if method_directive.method != "DCF":
        return _build_non_dcf_scenarios(
            ticker=ticker,
            as_of=as_of,
            schema_version=schema_version,
            method_directive=method_directive,
            method_directive_path=method_directive_path,
        )
    if valuation_range_path is None:
        raise AuditError("DCF scenarios require valuation range path")
    valuation = _load_valuation_range(storage, valuation_range_path)
    audit_artifact(valuation)
    expectations = _load_expectations_line(storage, expectations_line_path) if expectations_line_path else None
    if expectations is not None:
        audit_artifact(expectations)

    entries: list[ScenarioEntry] = []
    for valuation_scenario in valuation.scenarios:
        growth = _require_assumption(valuation_scenario.assumptions, "revenue_growth")
        anchor_path = f"{run_dir}/base_rate_{valuation_scenario.name}_revenue_growth.json"
        base_rate = _base_rate_for_assumption(
            growth,
            schema_version=schema_version,
            produced_at=valuation.header.produced_at,
        )
        audit_artifact(base_rate, storage=storage, path=anchor_path)
        evidence = _evidence_ref(
            source_label="B-3 valuation scenario",
            artifact_path=valuation_range_path,
            summary=f"{valuation_scenario.name} DCF scenario supplies the revenue_growth driver and value.",
            period=growth.value.provenance.period,
            tag="computed:scenario_probability_evidence",
        )
        assumption = ScenarioAssumptionDraft(
            driver=growth.driver,
            value=growth.value,
            base_rate_anchor=BaseRateAnchor(artifact_path=anchor_path),
            evidence_refs=[evidence],
            rationale="Scenario probability is anchored to the filed DCF revenue-growth driver and B-5 outside-view base rate.",
        )
        probability_number = _probability_number(
            float(valuation_scenario.probability.draft),
            scenario=valuation_scenario.name,
            period=growth.value.provenance.period,
            produced_at=valuation.header.produced_at,
        )
        entries.append(
            ScenarioEntry(
                name=valuation_scenario.name,
                value=valuation_scenario.value,
                assumptions=[assumption],
                probability=AnalystDraft(
                    draft={
                        "scenario": valuation_scenario.name,
                        "probability": probability_number,
                        "base_rate_anchor_path": anchor_path,
                    },
                    evidence_refs=[evidence],
                    checklist_area=f"scenario_probability_{valuation_scenario.name}",
                    checklist_rationale=f"Senior must independently ratify the {valuation_scenario.name} scenario probability.",
                ),
            )
        )
    return ScenarioSetArtifact(
        header=Header(schema_version=schema_version, produced_by="C-4", produced_at=datetime.now(timezone.utc)),
        ticker=ticker,
        as_of=as_of,
        status="drafted",
        method_directive_path=method_directive_path,
        valuation_range_path=valuation_range_path,
        expectations_line_path=expectations_line_path,
        scenarios=entries,
        source_evidence_summary={
            "method_directive": method_directive_path,
            "valuation_range": valuation_range_path,
            "expectations_line": expectations_line_path or "not filed",
            "base_rate": "one filed B-5 BaseRateResult anchor per scenario revenue_growth assumption",
        },
    )


def audit_scenario_set(artifact: ScenarioSetArtifact, *, storage: Storage, path: str | None = None) -> None:
    audit_analyst_artifact(artifact, storage=storage, path=path)
    method_directive = _load_method_directive(storage, artifact.method_directive_path)
    if method_directive.header.produced_by != "B-6":
        raise AuditError("scenario method directive must resolve to B-6")
    audit_artifact(method_directive)
    if method_directive.method != "DCF":
        _audit_non_dcf_method(artifact, method_directive)
        return
    if not artifact.valuation_range_path:
        raise AuditError("DCF scenario artifact missing valuation range reference")
    valuation = _load_valuation_range(storage, artifact.valuation_range_path)
    audit_artifact(valuation)
    expectations = _load_expectations_line(storage, artifact.expectations_line_path) if artifact.expectations_line_path else None
    if expectations is not None:
        audit_artifact(expectations)
    valid_drivers = _valid_driver_names(valuation, expectations)
    _audit_probabilities(artifact)
    _audit_value_ordering(artifact)
    for scenario in artifact.scenarios:
        for assumption in scenario.assumptions:
            if assumption.driver not in valid_drivers:
                raise AuditError(f"scenario {scenario.name} unbound driver: {assumption.driver}")
            if assumption.base_rate_anchor is None:
                raise AuditError(f"scenario {scenario.name} driver {assumption.driver} missing base-rate anchor")
            base_rate = _load_base_rate(storage, assumption.base_rate_anchor.artifact_path)
            if base_rate.header.produced_by != "B-5":
                raise AuditError(f"scenario {scenario.name} driver {assumption.driver} base-rate anchor is not B-5")
            audit_artifact(base_rate)
            expected_metric = DIRECT_DRIVER_METRIC_MAP.get(assumption.driver)
            if expected_metric is None:
                raise AuditError(f"scenario {scenario.name} driver {assumption.driver} has no direct base-rate metric mapping")
            if base_rate.forecast.metric != expected_metric:
                raise AuditError(
                    f"scenario {scenario.name} driver {assumption.driver} base-rate metric mismatch: "
                    f"expected {expected_metric}, got {base_rate.forecast.metric}"
                )
            if base_rate.probability is None:
                raise AuditError(f"scenario {scenario.name} driver {assumption.driver} base-rate missing probability")
            if not base_rate.citation.strip():
                raise AuditError(f"scenario {scenario.name} driver {assumption.driver} base-rate missing citation")


def _build_non_dcf_scenarios(
    *,
    ticker: str,
    as_of: date,
    schema_version: str,
    method_directive: MethodDirective,
    method_directive_path: str,
) -> ScenarioSetArtifact:
    evidence = _evidence_ref(
        source_label="B-6 method directive",
        artifact_path=method_directive_path,
        summary=f"{method_directive.method} route selected for {method_directive.asset_class}; scenarios use route-specific optionality drivers and no DCF artifacts.",
        period="M3.4",
        tag="computed:non_dcf_scenario_evidence",
    )
    produced_at = datetime.now(timezone.utc)
    route_specs = {
        "bear": {
            "value": 12.0,
            "probability": 0.30,
            "drivers": [
                ("rNPV_program_probability", 0.15, "ratio", "Priority pipeline probability remains low after clinical or regulatory setbacks."),
                ("rNPV_launch_timing_years", 4.0, "years", "Launch conversion is delayed beyond the valuation horizon that would matter for current holders."),
                ("rNPV_cash_runway_years", 2.0, "years", "Cash runway tightens before enough milestones convert into commercial products."),
            ],
        },
        "base": {
            "value": 32.0,
            "probability": 0.45,
            "drivers": [
                ("rNPV_program_probability", 0.35, "ratio", "A subset of respiratory or therapeutic programs advances without assuming portfolio-wide success."),
                ("rNPV_launch_timing_years", 3.0, "years", "Material launches or approvals arrive within an investable monitoring window."),
                ("rNPV_cash_runway_years", 3.0, "years", "Existing resources fund priority readouts with manageable dilution risk."),
            ],
        },
        "bull": {
            "value": 65.0,
            "probability": 0.25,
            "drivers": [
                ("rNPV_program_probability", 0.55, "ratio", "Multiple programs convert into credible commercial assets."),
                ("rNPV_launch_timing_years", 2.0, "years", "Approvals or launches arrive soon enough to change the revenue-reset narrative."),
                ("rNPV_cash_runway_years", 4.0, "years", "Cash runway remains sufficient to fund readouts and launches without punitive financing."),
            ],
        },
    }
    scenarios = []
    for name in SCENARIO_ORDER:
        spec = route_specs[name]
        scenarios.append(
            ScenarioEntry(
                name=name,
                value=_route_value_number(
                    float(spec["value"]),
                    method=method_directive.method,
                    scenario=name,
                    produced_at=produced_at,
                    method_directive_path=method_directive_path,
                ),
                assumptions=[
                    ScenarioAssumptionDraft(
                        driver=driver,
                        value=_route_driver_number(
                            value,
                            driver=driver,
                            unit=unit,
                            scenario=name,
                            produced_at=produced_at,
                            method_directive_path=method_directive_path,
                        ),
                        base_rate_anchor=None,
                        evidence_refs=[evidence],
                        rationale=rationale,
                    )
                    for driver, value, unit, rationale in spec["drivers"]
                ],
                probability=AnalystDraft(
                    draft={
                        "scenario": name,
                        "method": method_directive.method,
                        "probability": _probability_number(
                            float(spec["probability"]),
                            scenario=name,
                            period=f"M3.4-{method_directive.method}",
                            produced_at=produced_at,
                        ),
                    },
                    evidence_refs=[evidence],
                    checklist_area=f"scenario_probability_{name}",
                    checklist_rationale=f"Senior must ratify the {name} probability for the {method_directive.method} route.",
                ),
            )
        )
    return ScenarioSetArtifact(
        header=Header(schema_version=schema_version, produced_by="C-4", produced_at=produced_at),
        ticker=ticker,
        as_of=as_of,
        status="drafted",
        method_directive_path=method_directive_path,
        valuation_range_path=None,
        expectations_line_path=None,
        scenarios=scenarios,
        source_evidence_summary={
            "method_directive": method_directive_path,
            "method": method_directive.method,
            "routing_reason": method_directive.routing_reason,
            "route_drivers": "rNPV program probability, launch timing, cash runway, and dilution/financing risk",
        },
    )


def _audit_non_dcf_method(artifact: ScenarioSetArtifact, method_directive: MethodDirective) -> None:
    if method_directive.method == "DCF":
        raise AuditError("DCF method directive cannot use non-DCF scenario audit")
    if artifact.status != "drafted":
        raise AuditError(f"{method_directive.method} scenario artifact must be drafted, not deferred")
    _audit_probabilities(artifact)
    _audit_value_ordering(artifact)
    for scenario in artifact.scenarios:
        if scenario.value is None:
            raise AuditError(f"{method_directive.method} scenario {scenario.name} requires route value")
        if scenario.probability is None:
            raise AuditError(f"{method_directive.method} scenario {scenario.name} missing ratifiable probability")
        for assumption in scenario.assumptions:
            if assumption.driver in DCF_ONLY_DRIVERS:
                raise AuditError(f"method {method_directive.method} rejects DCF-only driver {assumption.driver}")
            if not assumption.driver.startswith(f"{method_directive.method}_"):
                raise AuditError(f"scenario {scenario.name} missing method-appropriate driver evidence")
            if assumption.value is None:
                raise AuditError(f"{method_directive.method} scenario {scenario.name} driver {assumption.driver} missing value")
            if not assumption.evidence_refs:
                raise AuditError(f"{method_directive.method} scenario {scenario.name} driver {assumption.driver} missing evidence")


def _audit_probabilities(artifact: ScenarioSetArtifact) -> None:
    values: list[float] = []
    for scenario in artifact.scenarios:
        if scenario.probability is None:
            raise AuditError(f"scenario {scenario.name} missing probability draft")
        draft = scenario.probability.draft
        if not isinstance(draft, dict):
            raise AuditError(f"scenario {scenario.name} probability draft must be structured")
        probability = draft.get("probability")
        if not isinstance(probability, Number):
            raise AuditError(f"scenario {scenario.name} probability draft must contain Number probability")
        value = probability.value
        if value < 0:
            raise AuditError(f"scenario {scenario.name} probability is negative")
        if value > 1:
            raise AuditError(f"scenario {scenario.name} probability exceeds 1")
        values.append(value)
    total = sum(values)
    if abs(total - 1.0) > PROBABILITY_TOLERANCE:
        raise AuditError(f"scenario probabilities sum to {total:.6f}, not 1.0")


def _audit_value_ordering(artifact: ScenarioSetArtifact) -> None:
    values = {scenario.name: scenario.value.value if scenario.value is not None else None for scenario in artifact.scenarios}
    if values["bear"] is None or values["base"] is None or values["bull"] is None:
        raise AuditError("drafted scenarios require bear/base/bull values")
    if values["bear"] >= values["base"]:
        raise AuditError("scenario value ordering failed: bear must be less than base")
    if values["base"] >= values["bull"]:
        raise AuditError("scenario value ordering failed: base must be less than bull")


def _valid_driver_names(valuation: ValuationRange, expectations: ExpectationsLine | None) -> set[str]:
    drivers = {assumption.driver for scenario in valuation.scenarios for assumption in scenario.assumptions}
    if expectations is not None:
        drivers.update(expectations.implied.keys())
    return drivers


def _base_rate_for_assumption(assumption: DcfAssumption, *, schema_version: str, produced_at: datetime) -> BaseRateResult:
    metric = DIRECT_DRIVER_METRIC_MAP.get(assumption.driver)
    if metric is None:
        raise AuditError(f"driver {assumption.driver} has no direct base-rate metric mapping")
    rate = assumption.value
    if metric == "margin_expansion":
        rate = _computed_number(0.01, "computed:scenario_margin_expansion_rate", assumption.value.provenance.period, "percent", produced_at)
    forecast = BaseRateForecast(
        metric=metric,
        rate=rate,
        horizon=_computed_number(5, "computed:scenario_base_rate_horizon", assumption.value.provenance.period, "years", produced_at),
        company_size_decile=_computed_number(3, "computed:scenario_base_rate_size_decile", assumption.value.provenance.period, "x", produced_at),
    )
    return lookup_base_rate(forecast, schema_version=schema_version, produced_at=produced_at)


def _probability_number(value: float, *, scenario: str, period: str, produced_at: datetime) -> Number:
    return Number(
        value=value,
        unit="ratio",
        kind="judgment",
        provenance=Provenance(
            tag=f"computed:scenario_probability_{scenario}",
            form="computed",
            period=period,
            accession=None,
            source_name="C-4 Scenarios deterministic draft",
            retrieved_at=produced_at,
        ),
        derivation=f"draft probability from C-4 scenario construction; inputs: filed {scenario} scenario evidence and method directive",
    )


def _computed_number(value: float, tag: str, period: str, unit: str, produced_at: datetime) -> Number:
    return Number(
        value=float(value),
        unit=unit,
        kind="estimate",
        provenance=Provenance(tag=tag, form="computed", period=period, accession=None, source_name="C-4 Scenarios", retrieved_at=produced_at),
        derivation=f"deterministic scenario base-rate support input; inputs: {tag}",
    )


def _route_value_number(
    value: float,
    *,
    method: str,
    scenario: str,
    produced_at: datetime,
    method_directive_path: str,
) -> Number:
    return Number(
        value=value,
        unit="USD_per_share",
        kind="estimate",
        provenance=Provenance(
            tag=f"computed:{method}:scenario_value_{scenario}",
            form="computed",
            period=f"M3.4-{method}",
            accession=None,
            source_name="C-4 Scenarios",
            retrieved_at=produced_at,
        ),
        derivation=f"inputs: {method_directive_path}; route-specific {method} scenario value from filed method directive and authored C-4 optionality drivers.",
    )


def _route_driver_number(
    value: float,
    *,
    driver: str,
    unit: str,
    scenario: str,
    produced_at: datetime,
    method_directive_path: str,
) -> Number:
    return Number(
        value=float(value),
        unit=unit,
        kind="estimate",
        provenance=Provenance(
            tag=f"computed:{driver}_{scenario}",
            form="computed",
            period=f"M3.4-{scenario}",
            accession=None,
            source_name="C-4 Scenarios",
            retrieved_at=produced_at,
        ),
        derivation=f"inputs: {method_directive_path}; route-specific driver assumption for {scenario} scenario.",
    )


def _evidence_ref(*, source_label: str, artifact_path: str, summary: str, period: str, tag: str) -> EvidenceRef:
    return EvidenceRef(
        source_label=source_label,
        excerpt_or_summary=summary,
        artifact_path=artifact_path,
        claimed_period=None,
        provenance=Provenance(
            tag=tag,
            form="computed",
            period=period,
            accession=None,
            source_name=source_label,
            retrieved_at=datetime.now(timezone.utc),
        ),
    )


def _require_assumption(assumptions: list[DcfAssumption], driver: str) -> DcfAssumption:
    for assumption in assumptions:
        if assumption.driver == driver:
            return assumption
    raise AuditError(f"valuation scenario missing required driver: {driver}")


def _load_valuation_range(storage: Storage, path: str) -> ValuationRange:
    try:
        return ValuationRange.model_validate(storage.get_json(_required_path(path, "valuation range")))
    except ValidationError as exc:
        raise AuditError("scenario valuation range reference did not resolve to ValuationRange") from exc


def _load_expectations_line(storage: Storage, path: str | None) -> ExpectationsLine | None:
    if path is None:
        return None
    try:
        return ExpectationsLine.model_validate(storage.get_json(_required_path(path, "expectations line")))
    except ValidationError as exc:
        raise AuditError("scenario expectations line reference did not resolve to ExpectationsLine") from exc


def _load_base_rate(storage: Storage, path: str) -> BaseRateResult:
    try:
        return BaseRateResult.model_validate(storage.get_json(_required_path(path, "base-rate anchor")))
    except ValidationError as exc:
        raise AuditError("scenario base-rate anchor did not resolve to BaseRateResult") from exc


def _load_method_directive(storage: Storage, path: str) -> MethodDirective:
    try:
        return MethodDirective.model_validate(storage.get_json(_required_path(path, "method directive")))
    except ValidationError as exc:
        raise AuditError("scenario method directive reference did not resolve to MethodDirective") from exc


def _required_path(path: str | None, label: str) -> str:
    if not isinstance(path, str) or not path.strip():
        raise AuditError(f"scenario artifact missing {label} reference")
    return path.strip()
