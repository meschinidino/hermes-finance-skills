from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import ConfigDict, field_validator, model_validator

from skills._primitives import StrictModel


class CalibrationCall(StrictModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    id: str
    date: date
    ticker: str
    lean: str
    conviction: str
    conviction_score: int
    base_value: float
    bear_value: float
    review_by: date
    kill_metric: str

    @field_validator("id", "ticker", "lean", "conviction", "kill_metric", mode="before")
    @classmethod
    def require_non_empty_text(cls, value: object) -> object:
        if not str(value or "").strip():
            raise ValueError("calibration call text fields must be non-empty")
        return value

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, value: object) -> object:
        return str(value).strip().upper()

    @model_validator(mode="after")
    def validate_call(self) -> CalibrationCall:
        if self.conviction_score < 0 or self.conviction_score > 10:
            raise ValueError("conviction_score must be between 0 and 10")
        if self.review_by < self.date:
            raise ValueError("review_by must be on or after the call date")
        return self


class CalibrationReview(StrictModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    call_id: str
    reviewed_at: date
    what_happened: str
    cruxes_held: list[str]
    cruxes_broke: list[str]
    right_for_the_reasons: bool

    @field_validator("call_id", "what_happened", mode="before")
    @classmethod
    def require_non_empty_text(cls, value: object) -> object:
        if not str(value or "").strip():
            raise ValueError("calibration review text fields must be non-empty")
        return value


class RoutingCorrectnessReview(StrictModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    id: str
    date: date
    ticker: str
    run_id: str | None = None
    expected_route: str
    actual_route: str
    correct: bool
    rationale: str

    @field_validator("id", "ticker", "expected_route", "actual_route", "rationale", mode="before")
    @classmethod
    def require_non_empty_text(cls, value: object) -> object:
        if not str(value or "").strip():
            raise ValueError("routing review text fields must be non-empty")
        return value

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, value: object) -> object:
        return str(value).strip().upper()


class EscalationCorrectnessReview(StrictModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    id: str
    date: date
    ticker: str
    run_id: str | None = None
    touchpoint: Literal["early_gate", "consolidated_ratification", "final_lean_ratification"]
    expected_escalation: str
    actual_escalation: str
    correct: bool
    rationale: str

    @field_validator("id", "ticker", "expected_escalation", "actual_escalation", "rationale", mode="before")
    @classmethod
    def require_non_empty_text(cls, value: object) -> object:
        if not str(value or "").strip():
            raise ValueError("escalation review text fields must be non-empty")
        return value

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, value: object) -> object:
        return str(value).strip().upper()
