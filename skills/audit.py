from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel

from skills._primitives import Number
from skills.m1_artifacts import ExpectationsLine, Spine, ValuationRange, iter_numbers, model_to_payload
from skills.interfaces import Storage


class AuditError(ValueError):
    pass


def audit_m1_handoff(handoff: BaseModel, *, storage: Storage | None = None, path: str | None = None) -> None:
    numbers = iter_numbers(handoff)
    if not numbers:
        raise AuditError("no numbers found")

    for number in numbers:
        _audit_number(number)

    spine = _find_spine(handoff)
    _audit_spine(spine)

    if storage and path:
        payload = model_to_payload(handoff)
        storage.put_json(path, payload)
        reloaded = storage.get_json(path)
        if reloaded != payload:
            raise AuditError("storage round-trip failed")


def audit_artifact(artifact: BaseModel, *, storage: Storage | None = None, path: str | None = None) -> None:
    numbers = iter_numbers(artifact)
    if not numbers:
        raise AuditError("artifact has no numbers")
    for number in numbers:
        _audit_number(number, require_input_refs=True)
    if isinstance(artifact, ValuationRange):
        _audit_valuation_range(artifact)
    if isinstance(artifact, ExpectationsLine):
        _audit_expectations_line(artifact)
    if storage and path:
        payload = model_to_payload(artifact)
        storage.put_json(path, payload)
        if storage.get_json(path) != payload:
            raise AuditError("storage round-trip failed")


def _audit_number(number: Number, *, require_input_refs: bool = False) -> None:
    if number.provenance is None:
        raise AuditError("number missing provenance")
    if number.kind == "fact" and number.provenance.form not in {"10-K", "10-Q", "DEF 14A", "Form 4"}:
        raise AuditError("fact must trace to accepted filing form")
    if number.kind != "fact" and not number.derivation:
        raise AuditError("estimate missing derivation")
    if require_input_refs and number.provenance.form == "computed" and "inputs:" not in (number.derivation or ""):
        raise AuditError("computed estimate derivation missing input references")
    if not math.isfinite(number.value):
        raise AuditError("number must be finite")


def _find_spine(value: Any) -> Spine:
    if isinstance(value, Spine):
        return value
    if isinstance(value, BaseModel):
        for item in value.__dict__.values():
            try:
                return _find_spine(item)
            except AuditError:
                pass
    if isinstance(value, dict):
        for item in value.values():
            try:
                return _find_spine(item)
            except AuditError:
                pass
    raise AuditError("handoff missing spine")


def _audit_spine(spine: Spine) -> None:
    for year, ic, roic, wacc, margin, turnover in zip(
        spine.years,
        spine.invested_capital_incl_gw,
        spine.roic_incl_gw,
        spine.wacc,
        spine.nopat_margin,
        spine.capital_turnover,
        strict=True,
    ):
        if ic.value <= 0:
            raise AuditError(f"{year} invested capital must be positive")
        if not 0 < wacc.value < 0.30:
            raise AuditError(f"{year} WACC out of bounds")
        if abs(roic.value) >= 2.0:
            raise AuditError(f"{year} ROIC out of bounds")
        if abs((margin.value * turnover.value) - roic.value) > 0.000001:
            raise AuditError(f"{year} margin-turnover reconciliation failed")


def _audit_valuation_range(valuation: ValuationRange) -> None:
    if len(valuation.scenarios) != 3:
        raise AuditError("valuation range requires exactly three scenarios")
    if [scenario.name for scenario in valuation.scenarios] != ["bear", "base", "bull"]:
        raise AuditError("valuation range requires bear/base/bull scenarios")
    for scenario in valuation.scenarios:
        if scenario.probability.decision is not None:
            raise AuditError("M2a probabilities must remain unratified")


def _audit_expectations_line(expectations: ExpectationsLine) -> None:
    low = expectations.wacc_band["low"].value
    high = expectations.wacc_band["high"].value
    if low >= high:
        raise AuditError("WACC band low must be below high")
    if not 0 < low < 0.30 or not 0 < high < 0.30:
        raise AuditError("WACC band out of bounds")
    for edge, result in expectations.reverse_band_results.items():
        if edge not in {"low", "high"}:
            raise AuditError("unexpected reverse DCF edge")
        if not result.converged and result.implied_revenue_growth is not None:
            raise AuditError("non-converged reverse DCF must not force an implied point")
