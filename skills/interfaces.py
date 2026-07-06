from __future__ import annotations

from typing import Any, Protocol, TypeGuard

from skills.storage import CalibrationStore


class Senior(Protocol):
    def gate(self, package: dict[str, Any]) -> dict[str, Any]:
        ...

    def ratify(self, package: dict[str, Any]) -> dict[str, Any]:
        ...


class Storage(Protocol):
    def put_json(self, path: str, payload: dict[str, Any]) -> None:
        ...

    def get_json(self, path: str) -> dict[str, Any]:
        ...

    def append_log(self, table: str, payload: dict[str, Any]) -> None:
        ...


def supports_calibration_store(storage: object) -> TypeGuard[CalibrationStore]:
    required_methods = (
        "append_calibration_call",
        "append_calibration_review",
        "append_routing_correctness_review",
        "append_escalation_correctness_review",
        "get_calibration_call",
        "list_calibration_calls",
        "list_calibration_reviews",
        "list_routing_correctness_reviews",
        "list_escalation_correctness_reviews",
    )
    return all(callable(getattr(storage, method, None)) for method in required_methods)


class LLM(Protocol):
    def complete(self, prompt: str, *, context: dict[str, Any]) -> str:
        ...


class PriceFeed(Protocol):
    def quote(self, ticker: str) -> dict[str, Any]:
        ...
