from __future__ import annotations

from typing import Any


class FakeLLM:
    def __init__(self, *, model_handle: str = "fake-analyst-model") -> None:
        self.model_handle = model_handle

    def complete(self, prompt: str, *, context: dict[str, Any]) -> str:
        ticker = context.get("ticker", "UNKNOWN")
        return f"{self.model_handle}:{ticker}:{prompt}"


class FakeSenior:
    def __init__(self, *, senior_handle: str = "fake-senior-model", decided_by: str = "fake-senior") -> None:
        self.senior_handle = senior_handle
        self.decided_by = decided_by

    def gate(self, package: dict[str, Any]) -> dict[str, Any]:
        ticker = package.get("ticker", "UNKNOWN")
        return {"decision": "GO", "decided_by": self.decided_by, "ticker": ticker, "handle": self.senior_handle}

    def ratify(self, package: dict[str, Any]) -> dict[str, Any]:
        item_ids = list(package.get("required_item_ids", []))
        return {
            "decided_by": self.decided_by,
            "handle": self.senior_handle,
            "decisions": {
                item_id: {"decision": "ratified", "final": None, "rationale": f"accepted:{item_id}"}
                for item_id in item_ids
            },
        }
