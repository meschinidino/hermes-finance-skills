from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from typing import Any, Literal

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


OutcomeDirection = Literal["up", "down", "flat", "unknown"]
LeakPhase = Literal["P0", "P1", "P2", "P3", "P4", "P5", "P6", "D2", "D3", "route", "escalation", "none"]


class CalibrationReview(StrictModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    id: str | None = None
    call_id: str
    reviewed_at: date
    reviewed_by: str | None = None
    outcome_direction: OutcomeDirection = "unknown"
    what_happened: str
    cruxes_held: list[str]
    cruxes_broke: list[str]
    right_for_the_reasons: bool
    primary_leak_phase: LeakPhase = "none"
    supersedes_review_id: str | None = None
    notes: str | None = None

    @field_validator("call_id", "what_happened", mode="before")
    @classmethod
    def require_non_empty_text(cls, value: object) -> object:
        if not str(value or "").strip():
            raise ValueError("calibration review text fields must be non-empty")
        return value

    @field_validator("id", "reviewed_by", "supersedes_review_id", "notes", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_review(self) -> CalibrationReview:
        if not self.right_for_the_reasons and self.primary_leak_phase == "none":
            raise ValueError("missed calibration reviews require a primary leak phase")
        if not self.what_happened.strip() and not self.cruxes_held and not self.cruxes_broke:
            raise ValueError("review requires outcome detail")
        return self


class HitRateBucket(StrictModel):
    calls_count: int
    reviewed_count: int
    hits: int
    misses: int
    hit_rate: float


class CorrectnessRate(StrictModel):
    observations_count: int
    correct_count: int
    incorrect_count: int
    rate: float


class CorrectnessFinding(StrictModel):
    observation_id: str | None = None
    ticker: str | None = None
    as_of: date | None = None
    findings: list[str]


class CalibrationAnalytics(StrictModel):
    generated_at: datetime
    as_of: date | None = None
    calls_count: int
    reviews_count: int
    reviewed_calls_count: int
    open_reviews_count: int
    hit_rate_by_conviction_band: dict[str, HitRateBucket]
    directional_bias: dict[str, dict[str, int]]
    leak_by_phase: dict[str, int]
    routing_correctness_rate: CorrectnessRate
    escalation_correctness_rate: CorrectnessRate
    routing_findings: list[CorrectnessFinding]
    escalation_findings: list[CorrectnessFinding]


CONVICTION_BANDS = ("Low", "Med", "High")


def build_calibration_analytics(storage: Any, *, as_of: date | str | None = None) -> CalibrationAnalytics:
    report_as_of = _coerce_date(as_of, field_name="as_of") if as_of is not None else None
    calls = _filter_on_or_before(_records_as_dicts(_list_from_store(storage, "list_calibration_calls")), "date", report_as_of)
    reviews = _filter_on_or_before(_records_as_dicts(_list_from_store(storage, "list_calibration_reviews")), "reviewed_at", report_as_of)
    routing_reviews = _filter_on_or_before_any(_records_as_dicts(_list_routing_records(storage)), ("date", "as_of"), report_as_of)
    escalation_reviews = _filter_on_or_before_any(_records_as_dicts(_list_escalation_records(storage)), ("date", "as_of"), report_as_of)

    calls_by_id = {str(call.get("id")): call for call in calls if call.get("id") is not None}
    latest_reviews = {
        call_id: review
        for call_id, review in _latest_non_superseded_review_by_call(reviews).items()
        if call_id in calls_by_id
    }
    routing_rate, routing_findings = _correctness_rate_and_findings(routing_reviews, correct_field="correct")
    escalation_rate, escalation_findings = _correctness_rate_and_findings(escalation_reviews, correct_field="correct")

    return CalibrationAnalytics(
        generated_at=datetime.now(timezone.utc),
        as_of=report_as_of,
        calls_count=len(calls),
        reviews_count=len(reviews),
        reviewed_calls_count=len(latest_reviews),
        open_reviews_count=max(0, len(calls_by_id) - len(latest_reviews)),
        hit_rate_by_conviction_band=_hit_rate_by_conviction_band(calls_by_id, latest_reviews),
        directional_bias=_directional_bias(calls_by_id, latest_reviews),
        leak_by_phase=_leak_by_phase(latest_reviews),
        routing_correctness_rate=CorrectnessRate(**routing_rate),
        escalation_correctness_rate=CorrectnessRate(**escalation_rate),
        routing_findings=[CorrectnessFinding(**finding) for finding in routing_findings],
        escalation_findings=[CorrectnessFinding(**finding) for finding in escalation_findings],
    )


def _list_from_store(storage: Any, method_name: str) -> list[Any]:
    method = getattr(storage, method_name, None)
    if method is None or not callable(method):
        raise TypeError(f"storage does not implement CalibrationStore method {method_name}")
    return list(method())


def _list_routing_records(storage: Any) -> list[Any]:
    method = getattr(storage, "list_routing_correctness_reviews", None)
    if method is None:
        method = getattr(storage, "list_route_health", None)
    if method is None or not callable(method):
        raise TypeError("storage does not implement CalibrationStore method list_routing_correctness_reviews")
    return list(method())


def _list_escalation_records(storage: Any) -> list[Any]:
    method = getattr(storage, "list_escalation_correctness_reviews", None)
    if method is None:
        method = getattr(storage, "list_route_health", None)
    if method is None or not callable(method):
        raise TypeError("storage does not implement CalibrationStore method list_escalation_correctness_reviews")
    return list(method())


def _records_as_dicts(records: list[Any]) -> list[dict[str, Any]]:
    return [_record_as_dict(record) for record in records]


def _record_as_dict(record: Any) -> dict[str, Any]:
    if isinstance(record, dict):
        return dict(record)
    model_dump = getattr(record, "model_dump", None)
    if callable(model_dump):
        return dict(model_dump(mode="json"))
    if is_dataclass(record):
        return dict(asdict(record))
    if hasattr(record, "__dict__"):
        return dict(vars(record))
    raise TypeError(f"unsupported calibration record type: {type(record).__name__}")


def _filter_on_or_before(records: list[dict[str, Any]], field: str, as_of: date | None) -> list[dict[str, Any]]:
    if as_of is None:
        return records
    return [record for record in records if record.get(field) is not None and _coerce_date(record[field], field_name=field) <= as_of]


def _filter_on_or_before_any(records: list[dict[str, Any]], fields: tuple[str, ...], as_of: date | None) -> list[dict[str, Any]]:
    if as_of is None:
        return records
    filtered = []
    for record in records:
        field = next((candidate for candidate in fields if record.get(candidate) is not None), None)
        if field is not None and _coerce_date(record[field], field_name=field) <= as_of:
            filtered.append(record)
    return filtered


def _latest_non_superseded_review_by_call(reviews: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    superseded_ids = {
        str(review["supersedes_review_id"])
        for review in reviews
        if review.get("supersedes_review_id") not in (None, "")
    }
    active_reviews = [review for review in reviews if _review_identity(review) not in superseded_ids]
    latest: dict[str, dict[str, Any]] = {}
    for review in active_reviews:
        call_id = review.get("call_id")
        if call_id is None:
            continue
        normalized_call_id = str(call_id)
        current = latest.get(normalized_call_id)
        if current is None or _review_sort_key(review) > _review_sort_key(current):
            latest[normalized_call_id] = review
    return latest


def _review_identity(review: dict[str, Any]) -> str:
    if review.get("id") not in (None, ""):
        return str(review["id"])
    return f"{review.get('call_id')}:{review.get('reviewed_at')}:{review.get('what_happened')}"


def _review_sort_key(review: dict[str, Any]) -> tuple[date, str]:
    return _coerce_date(review.get("reviewed_at"), field_name="reviewed_at"), _review_identity(review)


def _hit_rate_by_conviction_band(
    calls_by_id: dict[str, dict[str, Any]],
    latest_reviews: dict[str, dict[str, Any]],
) -> dict[str, HitRateBucket]:
    buckets = {
        band: {"calls_count": 0, "reviewed_count": 0, "hits": 0, "misses": 0, "hit_rate": 0.0}
        for band in CONVICTION_BANDS
    }
    for call in calls_by_id.values():
        band = _normalize_conviction(call.get("conviction"))
        buckets.setdefault(band, {"calls_count": 0, "reviewed_count": 0, "hits": 0, "misses": 0, "hit_rate": 0.0})
        buckets[band]["calls_count"] += 1

    for call_id, review in latest_reviews.items():
        band = _normalize_conviction(calls_by_id[call_id].get("conviction"))
        buckets.setdefault(band, {"calls_count": 0, "reviewed_count": 0, "hits": 0, "misses": 0, "hit_rate": 0.0})
        buckets[band]["reviewed_count"] += 1
        if bool(review.get("right_for_the_reasons")):
            buckets[band]["hits"] += 1
        else:
            buckets[band]["misses"] += 1

    for bucket in buckets.values():
        reviewed = int(bucket["reviewed_count"])
        bucket["hit_rate"] = float(bucket["hits"]) / reviewed if reviewed else 0.0
    return {band: HitRateBucket(**bucket) for band, bucket in buckets.items()}


def _directional_bias(
    calls_by_id: dict[str, dict[str, Any]],
    latest_reviews: dict[str, dict[str, Any]],
) -> dict[str, dict[str, int]]:
    bias: dict[str, dict[str, int]] = {}
    for call_id, review in latest_reviews.items():
        lean = str(calls_by_id[call_id].get("lean") or "unknown")
        direction = str(review.get("outcome_direction") or "unknown")
        bias.setdefault(lean, {})
        bias[lean][direction] = bias[lean].get(direction, 0) + 1
    return bias


def _leak_by_phase(latest_reviews: dict[str, dict[str, Any]]) -> dict[str, int]:
    leaks: dict[str, int] = {}
    for review in latest_reviews.values():
        if bool(review.get("right_for_the_reasons")):
            continue
        phase = str(review.get("primary_leak_phase") or "none")
        leaks[phase] = leaks.get(phase, 0) + 1
    return dict(sorted(leaks.items()))


def _correctness_rate_and_findings(records: list[dict[str, Any]], *, correct_field: str) -> tuple[dict[str, float | int], list[dict[str, Any]]]:
    total = len(records)
    correct = sum(1 for record in records if bool(record.get(correct_field)))
    findings = []
    for record in records:
        if bool(record.get(correct_field)):
            continue
        rationale = str(record.get("rationale") or "").strip()
        findings.append(
            {
                "observation_id": record.get("id"),
                "ticker": record.get("ticker"),
                "as_of": _coerce_date(record.get("date") or record.get("as_of"), field_name="date") if record.get("date") or record.get("as_of") else None,
                "findings": [rationale] if rationale else [],
            }
        )
    return (
        {
            "observations_count": total,
            "correct_count": correct,
            "incorrect_count": total - correct,
            "rate": float(correct) / total if total else 0.0,
        },
        findings,
    )


def _normalize_conviction(value: Any) -> str:
    if value is None:
        return "unknown"
    normalized = str(value).strip()
    for band in CONVICTION_BANDS:
        if normalized.lower() == band.lower():
            return band
    return normalized or "unknown"


def _coerce_date(value: Any, *, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"invalid {field_name}: {value}") from exc
    raise ValueError(f"invalid {field_name}: {value!r}")


def record_calibration_review(storage: Any, review_payload: dict[str, Any]) -> CalibrationReview:
    missing = [
        name
        for name in ("append_calibration_review", "get_calibration_call")
        if not callable(getattr(storage, name, None))
    ]
    if missing:
        raise TypeError(f"storage does not implement CalibrationStore methods: {', '.join(missing)}")

    raw_call_id = review_payload.get("call_id")
    if not isinstance(raw_call_id, str) or not raw_call_id.strip():
        raise ValueError("review requires call_id")
    call_id = raw_call_id.strip()
    if storage.get_calibration_call(call_id) is None:
        raise ValueError(f"unknown calibration call id: {call_id}")

    normalized_payload = {
        **review_payload,
        "call_id": call_id,
        "cruxes_held": review_payload.get("cruxes_held", []),
        "cruxes_broke": review_payload.get("cruxes_broke", []),
    }
    review = CalibrationReview.model_validate(normalized_payload)
    storage.append_calibration_review(review)
    return review


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
