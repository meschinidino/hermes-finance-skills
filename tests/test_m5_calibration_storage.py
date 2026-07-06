from __future__ import annotations

import sqlite3
from datetime import date

import pytest
from pydantic import ValidationError

from skills.interfaces import supports_calibration_store
from skills.storage import CalibrationStore, LocalStorage
from skills.synthesis.calibration.calibration import (
    CalibrationCall,
    CalibrationReview,
    EscalationCorrectnessReview,
    RoutingCorrectnessReview,
)


def test_calibration_call_validates_required_fields_and_dates() -> None:
    with pytest.raises(ValidationError, match="calibration call text fields must be non-empty"):
        _call(id="")

    with pytest.raises(ValidationError, match="conviction_score must be between 0 and 10"):
        _call(conviction_score=11)

    with pytest.raises(ValidationError, match="review_by must be on or after the call date"):
        _call(review_by=date(2026, 7, 4))


def test_calibration_review_validates_required_fields() -> None:
    with pytest.raises(ValidationError, match="calibration review text fields must be non-empty"):
        CalibrationReview(
            call_id="",
            reviewed_at=date(2027, 7, 5),
            what_happened="base case tracked",
            cruxes_held=[],
            cruxes_broke=[],
            right_for_the_reasons=True,
        )

    with pytest.raises(ValidationError, match="calibration review text fields must be non-empty"):
        CalibrationReview(
            call_id="call-aapl",
            reviewed_at=date(2027, 7, 5),
            what_happened="",
            cruxes_held=[],
            cruxes_broke=[],
            right_for_the_reasons=True,
        )


def test_local_storage_initializes_calibration_tables_idempotently(tmp_path) -> None:
    LocalStorage(tmp_path)
    LocalStorage(tmp_path)

    with sqlite3.connect(tmp_path / "pack.db") as conn:
        tables = {row[0] for row in conn.execute("select name from sqlite_master where type = 'table'")}
        indexes = {row[0] for row in conn.execute("select name from sqlite_master where type = 'index'")}

    assert {
        "calibration_log",
        "calibration_calls",
        "calibration_reviews",
        "routing_correctness_reviews",
        "escalation_correctness_reviews",
    } <= tables
    assert {
        "idx_calibration_calls_ticker",
        "idx_calibration_reviews_call_id",
        "idx_routing_correctness_reviews_ticker",
        "idx_escalation_correctness_reviews_ticker",
    } <= indexes


def test_calibration_call_append_get_and_ticker_filter_round_trip(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    aapl = _call(id="call-aapl", ticker="aapl")
    mrna = _call(
        id="call-mrna",
        ticker="MRNA",
        lean="Watch",
        conviction="Low",
        conviction_score=2,
        base_value=75.0,
        bear_value=50.0,
    )

    storage.append_calibration_call(aapl)
    storage.append_calibration_call(mrna)

    assert storage.get_calibration_call("call-aapl") == aapl.model_copy(update={"ticker": "AAPL"})
    assert storage.get_calibration_call("missing") is None
    assert storage.list_calibration_calls(ticker="aapl") == [aapl.model_copy(update={"ticker": "AAPL"})]
    assert storage.list_calibration_calls(ticker="MRNA") == [mrna]
    assert storage.list_calibration_calls() == [aapl.model_copy(update={"ticker": "AAPL"}), mrna]


def test_calibration_review_append_and_call_filter_round_trip(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    storage.append_calibration_call(_call(id="call-aapl"))
    storage.append_calibration_call(_call(id="call-mrna", ticker="MRNA"))
    first = CalibrationReview(
        call_id="call-aapl",
        reviewed_at=date(2027, 7, 5),
        what_happened="base case tracked",
        cruxes_held=["services growth"],
        cruxes_broke=[],
        right_for_the_reasons=True,
    )
    second = CalibrationReview(
        call_id="call-mrna",
        reviewed_at=date(2027, 7, 6),
        what_happened="trial failed",
        cruxes_held=[],
        cruxes_broke=["approval timing"],
        right_for_the_reasons=False,
    )

    storage.append_calibration_review(first)
    storage.append_calibration_review(second)

    assert storage.list_calibration_reviews(call_id="call-aapl") == [first]
    assert storage.list_calibration_reviews(call_id="call-mrna") == [second]
    assert storage.list_calibration_reviews() == [first, second]


def test_calibration_review_append_rejects_missing_call_id(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    review = CalibrationReview(
        call_id="missing",
        reviewed_at=date(2027, 7, 5),
        what_happened="no matching call",
        cruxes_held=[],
        cruxes_broke=[],
        right_for_the_reasons=False,
    )

    with pytest.raises(ValueError, match="unknown calibration call id: missing"):
        storage.append_calibration_review(review)

    assert storage.list_calibration_reviews() == []


def test_calibration_review_append_is_idempotent_for_identical_payload(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    storage.append_calibration_call(_call(id="call-aapl"))
    review = CalibrationReview(
        call_id="call-aapl",
        reviewed_at=date(2027, 7, 5),
        what_happened="base case tracked",
        cruxes_held=["services growth"],
        cruxes_broke=[],
        right_for_the_reasons=True,
    )

    storage.append_calibration_review(review)
    storage.append_calibration_review(review)

    assert storage.list_calibration_reviews() == [review]


def test_calibration_review_insert_conflict_is_idempotent_at_sqlite_boundary(tmp_path, monkeypatch) -> None:
    storage = LocalStorage(tmp_path)
    storage.append_calibration_call(_call(id="call-aapl"))
    review = CalibrationReview(
        call_id="call-aapl",
        reviewed_at=date(2027, 7, 5),
        what_happened="base case tracked",
        cruxes_held=["services growth"],
        cruxes_broke=[],
        right_for_the_reasons=True,
    )
    storage.append_calibration_review(review)

    real_connect = sqlite3.connect

    class EmptyRows:
        def fetchall(self):
            return []

    class RaceConnection:
        def __init__(self, path):
            self._conn = real_connect(path)
            self._masked_precheck = False

        def __enter__(self):
            self._conn.__enter__()
            return self

        def __exit__(self, *args):
            return self._conn.__exit__(*args)

        def execute(self, statement, params=()):
            normalized = " ".join(statement.split())
            if (
                not self._masked_precheck
                and normalized == "select payload_json from calibration_reviews where call_id = ?"
            ):
                self._masked_precheck = True
                return EmptyRows()
            return self._conn.execute(statement, params)

        def commit(self):
            return self._conn.commit()

        @property
        def row_factory(self):
            return self._conn.row_factory

        @row_factory.setter
        def row_factory(self, value):
            self._conn.row_factory = value

    monkeypatch.setattr("skills.storage.sqlite3.connect", RaceConnection)

    storage.append_calibration_review(review)

    monkeypatch.setattr("skills.storage.sqlite3.connect", real_connect)
    assert storage.list_calibration_reviews() == [review]


def test_routing_and_escalation_review_append_and_ticker_filter_round_trip(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    routing = RoutingCorrectnessReview(
        id="route-aapl",
        date=date(2026, 7, 5),
        ticker="aapl",
        expected_route="DCF",
        actual_route="DCF",
        correct=True,
        rationale="cash generator route matched",
    )
    escalation = EscalationCorrectnessReview(
        id="escalation-aapl",
        date=date(2026, 7, 5),
        ticker="aapl",
        touchpoint="early_gate",
        expected_escalation="Senior",
        actual_escalation="Senior",
        correct=True,
        rationale="documented touchpoint",
    )

    storage.append_routing_correctness_review(routing)
    storage.append_escalation_correctness_review(escalation)

    assert storage.list_routing_correctness_reviews(ticker="AAPL") == [
        routing.model_copy(update={"ticker": "AAPL"})
    ]
    assert storage.list_routing_correctness_reviews(ticker="MRNA") == []
    assert storage.list_escalation_correctness_reviews(ticker="AAPL") == [
        escalation.model_copy(update={"ticker": "AAPL"})
    ]
    assert storage.list_escalation_correctness_reviews(ticker="MRNA") == []


def test_primary_key_appends_are_idempotent_for_identical_payloads(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    call = _call(id="call-aapl")
    route = RoutingCorrectnessReview(
        id="route-aapl",
        date=date(2026, 7, 5),
        ticker="AAPL",
        expected_route="DCF",
        actual_route="DCF",
        correct=True,
        rationale="cash generator route matched",
    )
    escalation = EscalationCorrectnessReview(
        id="escalation-aapl",
        date=date(2026, 7, 5),
        ticker="AAPL",
        touchpoint="early_gate",
        expected_escalation="Senior",
        actual_escalation="Senior",
        correct=True,
        rationale="documented touchpoint",
    )

    storage.append_calibration_call(call)
    storage.append_calibration_call(call)
    storage.append_routing_correctness_review(route)
    storage.append_routing_correctness_review(route)
    storage.append_escalation_correctness_review(escalation)
    storage.append_escalation_correctness_review(escalation)

    assert storage.list_calibration_calls() == [call]
    assert storage.list_routing_correctness_reviews() == [route]
    assert storage.list_escalation_correctness_reviews() == [escalation]


def test_primary_key_appends_reject_same_id_with_different_payload(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    storage.append_calibration_call(_call(id="call-aapl"))

    with pytest.raises(ValueError, match="calibration_calls id already exists with different payload"):
        storage.append_calibration_call(_call(id="call-aapl", conviction_score=7))


def test_supports_calibration_store_capability_check(tmp_path) -> None:
    storage = LocalStorage(tmp_path)

    class JsonOnlyStorage:
        def put_json(self, path: str, payload: dict) -> None:
            pass

        def get_json(self, path: str) -> dict:
            return {}

        def append_log(self, table: str, payload: dict) -> None:
            pass

    assert isinstance(storage, CalibrationStore)
    assert supports_calibration_store(storage)
    assert not supports_calibration_store(JsonOnlyStorage())


def _call(
    *,
    id: str = "call-aapl",
    ticker: str = "AAPL",
    lean: str = "Buy",
    conviction: str = "High",
    conviction_score: int = 8,
    base_value: float = 250.0,
    bear_value: float = 150.0,
    review_by: date = date(2027, 7, 5),
) -> CalibrationCall:
    return CalibrationCall(
        id=id,
        date=date(2026, 7, 5),
        ticker=ticker,
        lean=lean,
        conviction=conviction,
        conviction_score=conviction_score,
        base_value=base_value,
        bear_value=bear_value,
        review_by=review_by,
        kill_metric="revenue growth below 3%",
    )
