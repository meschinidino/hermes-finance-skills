from __future__ import annotations

from typing import Any, Protocol


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


class LLM(Protocol):
    def complete(self, prompt: str, *, context: dict[str, Any]) -> str:
        ...


class PriceFeed(Protocol):
    def quote(self, ticker: str) -> dict[str, Any]:
        ...
