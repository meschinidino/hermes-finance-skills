from __future__ import annotations

from datetime import date, datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, model_validator

FilingForm = Literal["10-K", "10-Q", "DEF 14A", "Form 4", "computed", "external"]
NumberKind = Literal["fact", "estimate", "judgment"]
NumberUnit = Literal["USD_millions", "ratio", "percent", "shares", "USD_per_share", "years", "x"]
Decision = Literal["ratified", "overturned"]


class StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Provenance(StrictModel):
    tag: str
    form: FilingForm
    period: str
    accession: str | None
    source_name: str | None
    retrieved_at: datetime


class Number(StrictModel):
    value: float
    unit: NumberUnit
    kind: NumberKind
    provenance: Provenance
    derivation: str | None = None

    @model_validator(mode="before")
    @classmethod
    def require_provenance(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("provenance"):
            raise ValueError("numbers require provenance")
        return data

    @model_validator(mode="after")
    def validate_provenance_and_derivation(self) -> Number:
        if self.kind != "fact" and not self.derivation:
            raise ValueError("non-fact numbers require a derivation")
        return self


class Header(StrictModel):
    schema_version: str
    produced_by: str
    produced_at: datetime


T = TypeVar("T")


class Ratifiable(StrictModel, Generic[T]):
    draft: T
    evidence: list[str]
    needs_ratification: bool = True
    decision: Decision | None = None
    decided_by: str | None = None
    final: T | None = None

    @model_validator(mode="after")
    def validate_evidence(self) -> Ratifiable[T]:
        if not self.evidence:
            raise ValueError("ratifiable drafts require evidence")
        return self


def to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    return value
