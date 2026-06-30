from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel

from skills._primitives import Number
from skills.m1_artifacts import Spine, iter_numbers, model_to_payload
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


def _audit_number(number: Number) -> None:
    if number.provenance is None:
        raise AuditError("number missing provenance")
    if number.kind == "fact" and number.provenance.form not in {"10-K", "10-Q", "DEF 14A", "Form 4"}:
        raise AuditError("fact must trace to accepted filing form")
    if number.kind != "fact" and not number.derivation:
        raise AuditError("estimate missing derivation")
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
