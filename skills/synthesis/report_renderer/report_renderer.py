from __future__ import annotations

import ast
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from skills._primitives import Number, Provenance
from skills.accountant_artifacts import ValuationRange
from skills.interfaces import Storage
from skills.research.edge_cruxes.edge_cruxes import EdgeCruxesArtifact
from skills.research.risk.risk import RiskArtifact
from skills.research.scenarios.scenarios import ScenarioSetArtifact
from skills.synthesis.review_packager.review_packager import FinalHandoff, RouteValuationDeferred


class ReportRenderWarning(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str


class ReportRenderResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_dir: str
    source_artifacts: list[str]
    output_path: str
    format: Literal["markdown"] = "markdown"
    warnings: list[ReportRenderWarning] = Field(default_factory=list)
    sections_rendered: list[str]


def render_report(storage: Storage, run_dir: str, *, output_path: str | None = None) -> ReportRenderResult:
    normalized_run_dir = _normalize_storage_run_dir(run_dir)
    final_path = f"{normalized_run_dir}/final_handoff.json"
    kill_path = f"{normalized_run_dir}/kill_memo.json"
    has_final = _exists_json(storage, final_path)
    has_kill = _exists_json(storage, kill_path)
    if has_final and has_kill:
        raise ValueError("run directory contains both final_handoff.json and kill_memo.json")
    if not has_final and not has_kill:
        raise ValueError("run directory contains neither final_handoff.json nor kill_memo.json")

    target_path = _normalize_output_path(output_path or f"{normalized_run_dir}/report.md")
    generated_at = datetime.now(timezone.utc).replace(microsecond=0)
    if has_kill:
        payload = storage.get_json(kill_path)
        markdown = _render_kill_report(payload, source_path=kill_path, generated_at=generated_at)
        sections = ["Header", "Kill Decision"]
        sources = [kill_path]
        warnings: list[ReportRenderWarning] = []
    else:
        handoff = FinalHandoff.model_validate(storage.get_json(final_path))
        _validate_auxiliary_consistency(storage, normalized_run_dir, handoff)
        markdown, warnings, sections = _render_handoff_report(
            handoff,
            source_path=final_path,
            generated_at=generated_at,
        )
        sources = [final_path]
        for name in ("risk.json", "edge_cruxes.json", "scenarios.json", "route_manifest.json"):
            path = f"{normalized_run_dir}/{name}"
            if _exists_json(storage, path):
                sources.append(path)

    _put_text(storage, target_path, markdown)
    return ReportRenderResult(
        run_dir=normalized_run_dir,
        source_artifacts=sources,
        output_path=target_path,
        warnings=warnings,
        sections_rendered=sections,
    )


def normalize_cli_run_dir(run_dir: str, *, data_root: str = "data") -> str:
    raw = run_dir.strip()
    if not raw:
        raise ValueError("run directory is required")
    raw_path = Path(raw)
    root_path = Path(data_root)
    if raw_path.is_absolute():
        try:
            raw = raw_path.resolve().relative_to(root_path.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError("absolute run directory must be below --data-root") from exc
    normalized = raw.replace("\\", "/").rstrip("/")
    if not normalized:
        raise ValueError("run directory is required")
    data_prefix = data_root.strip("/").replace("\\", "/") + "/"
    if normalized == data_root.strip("/"):
        raise ValueError("run directory must point below runs/")
    if normalized.startswith(data_prefix):
        normalized = normalized[len(data_prefix):]
    return _normalize_storage_run_dir(normalized)


def normalize_cli_output_path(output_path: str, *, data_root: str = "data") -> str:
    raw = output_path.strip()
    if not raw:
        raise ValueError("output path is required")
    raw_path = Path(raw)
    root_path = Path(data_root)
    if raw_path.is_absolute():
        try:
            raw = raw_path.resolve().relative_to(root_path.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError("absolute output path must be below --data-root") from exc
    normalized = raw.replace("\\", "/").strip("/")
    data_prefix = data_root.strip("/").replace("\\", "/") + "/"
    if normalized.startswith(data_prefix):
        normalized = normalized[len(data_prefix):]
    return _normalize_output_path(normalized)


def _render_handoff_report(
    handoff: FinalHandoff,
    *,
    source_path: str,
    generated_at: datetime,
) -> tuple[str, list[ReportRenderWarning], list[str]]:
    final_lean = handoff.lean.final
    if final_lean is None:
        raise ValueError("final handoff lean has no final value")
    valuation_lines, flags = _valuation_lines(handoff)
    provenance = _provenance_summary(handoff)
    warnings = [ReportRenderWarning(code=flag, message=flag) for flag in flags]
    sections = [
        "Header",
        "Decision",
        "Valuation",
        "Thesis",
        "Risks",
        "Falsifiable Cruxes",
        "Revisit Triggers",
        "Provenance Summary",
    ]
    lines = [
        f"# {handoff.ticker} Fundamental Analysis Report",
        "",
        "## Header",
        f"- Ticker: {handoff.ticker}",
        f"- As of: {handoff.as_of.isoformat()}",
        f"- Generated at: {generated_at.isoformat()}",
        f"- Terminal source: {source_path}",
        "",
        "## Decision",
        f"- Final lean: {final_lean}",
        f"- Conviction: {handoff.conviction} ({_format_number(handoff.conviction_score)})",
        f"- Review by: {handoff.review_by.isoformat()}",
        f"- Horizon: {handoff.horizon}",
        f"- Signed by: {handoff.final_lean_signed_by} ({handoff.final_lean_signed_by_provider}/{handoff.final_lean_signed_by_model})",
        "",
        "## Valuation",
        *valuation_lines,
        "",
        "## Thesis",
        _format_thesis(handoff.thesis),
        "",
        "### Whats Priced In",
        *_expectations_lines(handoff.whats_priced_in),
        "",
        "## Risks",
        f"- Kill metric: {_kill_metric_text(handoff.risk.kill_metric)}",
        f"- Bear-case narrative: {_normalize_prose(handoff.risk.bear_case_narrative)}",
        "- Tail risks:",
        *[f"  - {_tail_risk_text(item)}" for item in handoff.risk.tail_risks],
        "- Modellable risks:",
        *[f"  - {item.risk} (impact: {item.impact}; likelihood: {item.likelihood}; modeled effect: {item.modeled_effect})" for item in handoff.risk.modellable],
        "",
        "## Falsifiable Cruxes",
        *[f"{index}. {crux.claim} | Metric: {crux.metric} | Threshold: {crux.threshold}" for index, crux in enumerate(handoff.cruxes, start=1)],
        "",
        "## Revisit Triggers",
        *[f"- {trigger}" for trigger in handoff.revisit_if],
        "",
        "## Provenance Summary",
        f"- Displayed fact Numbers: {provenance['kind_counts'].get('fact', 0)}",
        f"- Displayed estimate Numbers: {provenance['kind_counts'].get('estimate', 0)}",
        f"- Displayed judgment Numbers: {provenance['kind_counts'].get('judgment', 0)}",
        f"- Source names: {_join_or_unavailable(provenance['source_names'])}",
        f"- Filing forms: {_join_or_unavailable(provenance['forms'])}",
        f"- Accessions: {_join_or_unavailable(provenance['accessions'])}",
        "- Displayed computed/external/judgment fields:",
        *[f"  - {item}" for item in provenance["non_filing_fields"]],
    ]
    return "\n".join(lines).rstrip() + "\n", warnings, sections


def _render_kill_report(payload: dict[str, Any], *, source_path: str, generated_at: datetime) -> str:
    ticker = str(payload.get("ticker") or "").strip()
    gate = str(payload.get("gate") or payload.get("halt_kind") or "").strip()
    reason = str(payload.get("reason") or payload.get("kill_reason") or payload.get("message") or "").strip()
    if not ticker or not gate or not reason:
        raise ValueError("kill_memo.json must include ticker, gate, and reason")
    return (
        f"# {ticker} Kill Report\n\n"
        "## Header\n"
        f"- Ticker: {ticker}\n"
        f"- Generated at: {generated_at.isoformat()}\n"
        f"- Source artifact: {source_path}\n\n"
        "## Kill Decision\n"
        f"- Gate: {gate}\n"
        f"- Reason: {_normalize_prose(reason)}\n"
    )


def _valuation_lines(handoff: FinalHandoff) -> tuple[list[str], list[str]]:
    flags: list[str] = []
    lines = [
        f"- Method: {getattr(handoff.valuation_range, 'method', 'unavailable')}",
        f"- Current price: {_format_number(handoff.price)}",
    ]
    if isinstance(handoff.valuation_range, RouteValuationDeferred):
        flags.append("method_deferred")
        lines.append(f"- Route-deferred valuation: {handoff.valuation_range.reason}")
        lines.append("- Valuation input flags:")
        lines.extend([f"  - {flag}" for flag in flags])
        return lines, flags

    scenarios = {scenario.name: scenario.value for scenario in handoff.valuation_range.scenarios}
    ordered_values: list[float] = []
    for name in ("bear", "base", "bull"):
        value = scenarios.get(name)
        if value is None:
            flags.append("missing_scenario_value")
            lines.append(f"- {name.title()} value: unavailable")
        else:
            ordered_values.append(value.value)
            lines.append(f"- {name.title()} value: {_format_number(value)}")
    if len(ordered_values) == 3:
        bear, base, bull = ordered_values
        if not bear < base < bull:
            flags.append("non_monotonic_scenarios")
        if handoff.price.value <= bear:
            flags.append("price_at_or_below_bear")
        if handoff.price.value >= bull:
            flags.append("price_at_or_above_bull")
    lines.append("- Valuation input flags:")
    lines.extend([f"  - {flag}" for flag in sorted(set(flags))] or ["  - none"])
    return lines, sorted(set(flags))


def _expectations_lines(value: Any) -> list[str]:
    if isinstance(value, RouteValuationDeferred):
        return [f"- Method: {value.method}", f"- Reason: {value.reason}"]
    lines = [f"- Frame: {value.frame}"]
    for key, number in value.implied.items():
        if number is not None:
            lines.append(f"- Implied {key}: {_format_number(number)}")
    return lines


def _provenance_summary(handoff: FinalHandoff) -> dict[str, Any]:
    displayed_numbers: list[tuple[str, Number]] = [
        ("price", handoff.price),
        ("conviction_score", handoff.conviction_score),
        ("risk.bear_case_value", handoff.risk.bear_case_value),
        ("risk.kill_metric.threshold_value", handoff.risk.kill_metric.threshold_value),
    ]
    if isinstance(handoff.valuation_range, ValuationRange):
        displayed_numbers.extend((f"valuation_range.scenarios.{scenario.name}.value", scenario.value) for scenario in handoff.valuation_range.scenarios)
    if not isinstance(handoff.whats_priced_in, RouteValuationDeferred):
        displayed_numbers.extend(
            (f"whats_priced_in.implied.{key}", number)
            for key, number in handoff.whats_priced_in.implied.items()
            if number is not None
        )
        displayed_numbers.extend((f"whats_priced_in.wacc_band.{key}", number) for key, number in handoff.whats_priced_in.wacc_band.items())

    kind_counts = Counter(number.kind for _, number in displayed_numbers)
    provenances = [number.provenance for _, number in displayed_numbers]
    provenances.extend(_data_room_sources(handoff))
    non_filing = [
        f"{field}: {number.kind}/{number.provenance.form}/{number.provenance.source_name or 'unknown source'}"
        for field, number in displayed_numbers
        if number.kind != "fact" or number.provenance.form in {"computed", "external"}
    ]
    return {
        "kind_counts": dict(kind_counts),
        "source_names": sorted({item.source_name for item in provenances if item.source_name}),
        "forms": sorted({item.form for item in provenances if item.form}),
        "accessions": sorted({item.accession for item in provenances if item.accession}),
        "non_filing_fields": non_filing or ["none"],
    }


def _data_room_sources(handoff: FinalHandoff) -> list[Provenance]:
    raw_sources = handoff.data_room.get("sources")
    if not isinstance(raw_sources, list):
        return []
    sources: list[Provenance] = []
    for item in raw_sources:
        if isinstance(item, dict):
            try:
                sources.append(Provenance.model_validate(item))
            except ValueError:
                continue
    return sources


def _validate_auxiliary_consistency(storage: Storage, run_dir: str, handoff: FinalHandoff) -> None:
    risk_path = f"{run_dir}/risk.json"
    if _exists_json(storage, risk_path):
        risk = RiskArtifact.model_validate(storage.get_json(risk_path))
        final_kill = handoff.risk.kill_metric
        draft_kill = risk.kill_metric.final or risk.kill_metric.draft
        if getattr(draft_kill, "metric", None) != final_kill.metric:
            raise ValueError("auxiliary risk.json conflicts with final_handoff.json kill metric")
        if risk.bear_case_value != handoff.risk.bear_case_value:
            raise ValueError("auxiliary risk.json conflicts with final_handoff.json bear-case value")

    edge_path = f"{run_dir}/edge_cruxes.json"
    if _exists_json(storage, edge_path):
        edge = EdgeCruxesArtifact.model_validate(storage.get_json(edge_path))
        cruxes = edge.cruxes.final if edge.cruxes and edge.cruxes.final is not None else edge.cruxes.draft if edge.cruxes else []
        if [item.claim for item in cruxes] != [item.claim for item in handoff.cruxes]:
            raise ValueError("auxiliary edge_cruxes.json conflicts with final_handoff.json cruxes")

    scenarios_path = f"{run_dir}/scenarios.json"
    if _exists_json(storage, scenarios_path):
        scenarios = ScenarioSetArtifact.model_validate(storage.get_json(scenarios_path))
        filed_values = {scenario.name: scenario.value for scenario in scenarios.scenarios}
        if isinstance(handoff.valuation_range, ValuationRange):
            final_values = {scenario.name: scenario.value for scenario in handoff.valuation_range.scenarios}
        else:
            final_values = dict(handoff.valuation_range.scenario_values)
        for name in ("bear", "base", "bull"):
            if filed_values.get(name) != final_values.get(name):
                raise ValueError("auxiliary scenarios.json conflicts with final_handoff.json valuation values")


def _format_number(number: Number) -> str:
    value = f"{number.value:,.2f}".rstrip("0").rstrip(".")
    return f"{value} {number.unit}"


def _kill_metric_text(kill_metric: Any) -> str:
    return (
        f"{kill_metric.metric} {kill_metric.threshold_direction} "
        f"{_format_number(kill_metric.threshold_value)} by {kill_metric.check_by.isoformat()}; "
        f"action: {kill_metric.thesis_action}"
    )


def _tail_risk_text(tail_risk: Any) -> str:
    parts = [tail_risk.risk, f"why not modelled: {tail_risk.why_not_modelled}"]
    if tail_risk.monitoring_signal:
        parts.append(f"monitoring signal: {tail_risk.monitoring_signal}")
    if tail_risk.missing_data_gap:
        parts.append(f"missing data gap: {tail_risk.missing_data_gap}")
    return "; ".join(parts)


def _normalize_prose(value: str) -> str:
    return " ".join(str(value).split())


def _join_or_unavailable(values: list[str]) -> str:
    return ", ".join(values) if values else "none reported"


def _format_thesis(value: str) -> str:
    text = _normalize_prose(value)
    formatted = _replace_dict_literals(text)
    return _normalize_prose(formatted)


def _replace_dict_literals(text: str) -> str:
    chunks: list[str] = []
    cursor = 0
    while cursor < len(text):
        start = text.find("{", cursor)
        if start == -1:
            chunks.append(text[cursor:])
            break
        end = _matching_brace_index(text, start)
        if end is None:
            chunks.append(text[cursor:])
            break
        chunks.append(text[cursor:start])
        literal = text[start : end + 1]
        try:
            parsed = ast.literal_eval(literal)
        except (SyntaxError, ValueError):
            chunks.append(literal)
        else:
            chunks.append(_format_moat_mechanism(parsed) if isinstance(parsed, dict) else literal)
        cursor = end + 1
    return "".join(chunks)


def _matching_brace_index(text: str, start: int) -> int | None:
    quote: str | None = None
    escaped = False
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def _format_moat_mechanism(value: dict[str, Any]) -> str:
    claim = _normalize_prose(str(value.get("claim") or ""))
    category = _humanize_token(value.get("mechanism_category"))
    evidence = _normalize_prose(str(value.get("mechanism_evidence") or ""))
    support = value.get("support_categories") or []
    support_text = ", ".join(_humanize_token(item) for item in support if str(item).strip())
    sentences = []
    if claim:
        sentences.append(claim)
    if category:
        sentences.append(f"Mechanism category: {category}.")
    if evidence:
        sentences.append(f"Mechanism evidence: {evidence}")
    if support_text:
        sentences.append(f"Supporting categories: {support_text}.")
    return " ".join(sentences) if sentences else _normalize_prose(str(value))


def _humanize_token(value: Any) -> str:
    return str(value or "").replace("_", " ").strip()


def _exists_json(storage: Storage, path: str) -> bool:
    try:
        storage.get_json(path)
    except FileNotFoundError:
        return False
    return True


def _put_text(storage: Storage, path: str, payload: str) -> None:
    writer = getattr(storage, "put_text", None)
    if not callable(writer):
        raise TypeError("storage does not implement put_text")
    writer(path, payload)


def _normalize_storage_run_dir(run_dir: str) -> str:
    normalized = run_dir.strip().replace("\\", "/").strip("/")
    parts = Path(normalized).parts
    if not normalized or normalized.startswith("/") or ".." in parts:
        raise ValueError("run directory must be storage-relative")
    if not normalized.startswith("runs/"):
        raise ValueError("run directory must start with runs/")
    return normalized


def _normalize_output_path(output_path: str) -> str:
    normalized = output_path.strip().replace("\\", "/").strip("/")
    if not normalized:
        raise ValueError("output path is required")
    parts = Path(normalized).parts
    if normalized.startswith("/") or ".." in parts:
        raise ValueError("output path must be storage-relative")
    if not normalized.endswith(".md"):
        raise ValueError("output path must be a Markdown file")
    return normalized
