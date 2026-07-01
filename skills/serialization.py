from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from skills._primitives import to_jsonable


def artifact_model_to_payload(model: BaseModel) -> dict[str, Any]:
    payload = to_jsonable(model)
    if not isinstance(payload, dict):
        raise TypeError("expected model to serialize to object")
    return payload
