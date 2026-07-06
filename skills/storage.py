from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from skills.synthesis.calibration.calibration import (
    CalibrationCall,
    CalibrationReview,
    EscalationCorrectnessReview,
    RoutingCorrectnessReview,
)


@runtime_checkable
class CalibrationStore(Protocol):
    def append_calibration_call(self, call: CalibrationCall) -> None:
        ...

    def append_calibration_review(self, review: CalibrationReview) -> None:
        ...

    def append_routing_correctness_review(self, review: RoutingCorrectnessReview) -> None:
        ...

    def append_escalation_correctness_review(self, review: EscalationCorrectnessReview) -> None:
        ...

    def get_calibration_call(self, call_id: str) -> CalibrationCall | None:
        ...

    def list_calibration_calls(self, *, ticker: str | None = None) -> list[CalibrationCall]:
        ...

    def list_calibration_reviews(self, *, call_id: str | None = None) -> list[CalibrationReview]:
        ...

    def list_routing_correctness_reviews(
        self, *, ticker: str | None = None
    ) -> list[RoutingCorrectnessReview]:
        ...

    def list_escalation_correctness_reviews(
        self, *, ticker: str | None = None
    ) -> list[EscalationCorrectnessReview]:
        ...


class LocalStorage:
    def __init__(self, root: Path | str = Path("data")) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "cache").mkdir(exist_ok=True)
        (self.root / "runs").mkdir(exist_ok=True)
        self.db_path = self.root / "pack.db"
        self._init_db()

    def put_json(self, path: str, payload: dict[str, Any]) -> None:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def get_json(self, path: str) -> dict[str, Any]:
        return json.loads(self._resolve(path).read_text(encoding="utf-8"))

    def append_log(self, table: str, payload: dict[str, Any]) -> None:
        if table != "calibration_log":
            raise ValueError("M0 only supports calibration_log")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "insert into calibration_log(payload_json) values (?)",
                (json.dumps(payload, sort_keys=True),),
            )
            conn.commit()

    def append_calibration_call(self, call: CalibrationCall) -> None:
        record = CalibrationCall.model_validate(call)
        payload_json = _payload_json(record)
        with sqlite3.connect(self.db_path) as conn:
            _execute_idempotent_insert(
                conn,
                table="calibration_calls",
                record_id=record.id,
                payload_json=payload_json,
                statement=
                """
                insert into calibration_calls (
                    id, call_date, ticker, lean, conviction, conviction_score,
                    base_value, bear_value, review_by, kill_metric, payload_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params=(
                    record.id,
                    record.date.isoformat(),
                    record.ticker,
                    record.lean,
                    record.conviction,
                    record.conviction_score,
                    record.base_value,
                    record.bear_value,
                    record.review_by.isoformat(),
                    record.kill_metric,
                    payload_json,
                ),
            )
            conn.commit()

    def append_calibration_review(self, review: CalibrationReview) -> None:
        record = CalibrationReview.model_validate(review)
        payload_json = _payload_json(record)
        with sqlite3.connect(self.db_path) as conn:
            if _calibration_call_payload(conn, record.call_id) is None:
                raise ValueError(f"unknown calibration call id: {record.call_id}")
            existing = conn.execute(
                "select payload_json from calibration_reviews where call_id = ?",
                (record.call_id,),
            ).fetchall()
            if any(row[0] == payload_json for row in existing):
                return
            try:
                conn.execute(
                    """
                    insert into calibration_reviews (
                        call_id, reviewed_at, what_happened, cruxes_held_json,
                        cruxes_broke_json, right_for_the_reasons, payload_json
                    ) values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.call_id,
                        record.reviewed_at.isoformat(),
                        record.what_happened,
                        json.dumps(record.cruxes_held, sort_keys=True),
                        json.dumps(record.cruxes_broke, sort_keys=True),
                        int(record.right_for_the_reasons),
                        payload_json,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                if _calibration_review_payload_exists(conn, record.call_id, payload_json):
                    return
                raise ValueError(f"calibration review insert conflict for call_id: {record.call_id}") from exc
            conn.commit()

    def append_routing_correctness_review(self, review: RoutingCorrectnessReview) -> None:
        record = RoutingCorrectnessReview.model_validate(review)
        payload_json = _payload_json(record)
        with sqlite3.connect(self.db_path) as conn:
            _execute_idempotent_insert(
                conn,
                table="routing_correctness_reviews",
                record_id=record.id,
                payload_json=payload_json,
                statement=
                """
                insert into routing_correctness_reviews (
                    id, review_date, ticker, run_id, expected_route, actual_route,
                    correct, rationale, payload_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params=(
                    record.id,
                    record.date.isoformat(),
                    record.ticker,
                    record.run_id,
                    record.expected_route,
                    record.actual_route,
                    int(record.correct),
                    record.rationale,
                    payload_json,
                ),
            )
            conn.commit()

    def append_escalation_correctness_review(self, review: EscalationCorrectnessReview) -> None:
        record = EscalationCorrectnessReview.model_validate(review)
        payload_json = _payload_json(record)
        with sqlite3.connect(self.db_path) as conn:
            _execute_idempotent_insert(
                conn,
                table="escalation_correctness_reviews",
                record_id=record.id,
                payload_json=payload_json,
                statement=
                """
                insert into escalation_correctness_reviews (
                    id, review_date, ticker, run_id, touchpoint, expected_escalation,
                    actual_escalation, correct, rationale, payload_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params=(
                    record.id,
                    record.date.isoformat(),
                    record.ticker,
                    record.run_id,
                    record.touchpoint,
                    record.expected_escalation,
                    record.actual_escalation,
                    int(record.correct),
                    record.rationale,
                    payload_json,
                ),
            )
            conn.commit()

    def get_calibration_call(self, call_id: str) -> CalibrationCall | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "select payload_json from calibration_calls where id = ?",
                (call_id,),
            ).fetchone()
        if row is None:
            return None
        return CalibrationCall.model_validate(json.loads(row["payload_json"]))

    def list_calibration_calls(self, *, ticker: str | None = None) -> list[CalibrationCall]:
        query = "select payload_json from calibration_calls"
        params: tuple[str, ...] = ()
        if ticker is not None:
            query += " where ticker = ?"
            params = (ticker.strip().upper(),)
        query += " order by call_date, id"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [CalibrationCall.model_validate(json.loads(row["payload_json"])) for row in rows]

    def list_calibration_reviews(self, *, call_id: str | None = None) -> list[CalibrationReview]:
        query = "select payload_json from calibration_reviews"
        params: tuple[str, ...] = ()
        if call_id is not None:
            query += " where call_id = ?"
            params = (call_id,)
        query += " order by reviewed_at, id"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [CalibrationReview.model_validate(json.loads(row["payload_json"])) for row in rows]

    def list_routing_correctness_reviews(
        self, *, ticker: str | None = None
    ) -> list[RoutingCorrectnessReview]:
        query = "select payload_json from routing_correctness_reviews"
        params: tuple[str, ...] = ()
        if ticker is not None:
            query += " where ticker = ?"
            params = (ticker.strip().upper(),)
        query += " order by review_date, id"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [RoutingCorrectnessReview.model_validate(json.loads(row["payload_json"])) for row in rows]

    def list_escalation_correctness_reviews(
        self, *, ticker: str | None = None
    ) -> list[EscalationCorrectnessReview]:
        query = "select payload_json from escalation_correctness_reviews"
        params: tuple[str, ...] = ()
        if ticker is not None:
            query += " where ticker = ?"
            params = (ticker.strip().upper(),)
        query += " order by review_date, id"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [EscalationCorrectnessReview.model_validate(json.loads(row["payload_json"])) for row in rows]

    def _resolve(self, path: str) -> Path:
        normalized = Path(path)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ValueError("storage paths must be relative to the storage root")
        return self.root / normalized

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                create table if not exists calibration_log (
                    id integer primary key autoincrement,
                    payload_json text not null,
                    created_at text not null default current_timestamp
                )
                """
            )
            conn.execute(
                """
                create table if not exists calibration_calls (
                    id text primary key,
                    call_date text not null,
                    ticker text not null,
                    lean text not null,
                    conviction text not null,
                    conviction_score integer not null,
                    base_value real not null,
                    bear_value real not null,
                    review_by text not null,
                    kill_metric text not null,
                    payload_json text not null,
                    created_at text not null default current_timestamp
                )
                """
            )
            conn.execute(
                """
                create table if not exists calibration_reviews (
                    id integer primary key autoincrement,
                    call_id text not null,
                    reviewed_at text not null,
                    what_happened text not null,
                    cruxes_held_json text not null,
                    cruxes_broke_json text not null,
                    right_for_the_reasons integer not null,
                    payload_json text not null,
                    created_at text not null default current_timestamp
                )
                """
            )
            conn.execute(
                """
                create table if not exists routing_correctness_reviews (
                    id text primary key,
                    review_date text not null,
                    ticker text not null,
                    run_id text,
                    expected_route text not null,
                    actual_route text not null,
                    correct integer not null,
                    rationale text not null,
                    payload_json text not null,
                    created_at text not null default current_timestamp
                )
                """
            )
            conn.execute(
                """
                create table if not exists escalation_correctness_reviews (
                    id text primary key,
                    review_date text not null,
                    ticker text not null,
                    run_id text,
                    touchpoint text not null,
                    expected_escalation text not null,
                    actual_escalation text not null,
                    correct integer not null,
                    rationale text not null,
                    payload_json text not null,
                    created_at text not null default current_timestamp
                )
                """
            )
            conn.execute("create index if not exists idx_calibration_calls_ticker on calibration_calls(ticker)")
            conn.execute("create index if not exists idx_calibration_reviews_call_id on calibration_reviews(call_id)")
            conn.execute(
                """
                create unique index if not exists idx_calibration_reviews_call_payload
                on calibration_reviews(call_id, payload_json)
                """
            )
            conn.execute(
                "create index if not exists idx_routing_correctness_reviews_ticker on routing_correctness_reviews(ticker)"
            )
            conn.execute(
                "create index if not exists idx_escalation_correctness_reviews_ticker on escalation_correctness_reviews(ticker)"
            )
            conn.commit()


def _payload_json(record: Any) -> str:
    return json.dumps(record.model_dump(mode="json"), sort_keys=True)


def _calibration_call_payload(conn: sqlite3.Connection, call_id: str) -> str | None:
    row = conn.execute("select payload_json from calibration_calls where id = ?", (call_id,)).fetchone()
    if row is None:
        return None
    return str(row[0])


def _calibration_review_payload_exists(conn: sqlite3.Connection, call_id: str, payload_json: str) -> bool:
    row = conn.execute(
        "select 1 from calibration_reviews where call_id = ? and payload_json = ?",
        (call_id, payload_json),
    ).fetchone()
    return row is not None


def _execute_idempotent_insert(
    conn: sqlite3.Connection,
    *,
    table: str,
    record_id: str,
    payload_json: str,
    statement: str,
    params: tuple[Any, ...],
) -> None:
    try:
        conn.execute(statement, params)
    except sqlite3.IntegrityError as exc:
        row = conn.execute(f"select payload_json from {table} where id = ?", (record_id,)).fetchone()
        if row is not None and row[0] == payload_json:
            return
        raise ValueError(f"{table} id already exists with different payload: {record_id}") from exc
