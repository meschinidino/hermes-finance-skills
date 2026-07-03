from __future__ import annotations

import json
import os
from datetime import date
from typing import Any, Literal
from urllib import request
from urllib.error import HTTPError, URLError

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from skills._primitives import Header
from skills.interfaces import Storage
from skills.serialization import artifact_model_to_payload

DEEPSEEK_ALIAS_DEPRECATION = "July 24, 2026"
DEPRECATED_DEEPSEEK_ALIASES = {"deepseek-chat", "deepseek-reasoner"}
EXPECTED_AZURE_SENIOR_MODEL = "DeepSeek-V4-Pro"
EXPECTED_AZURE_SENIOR_MODEL_NORMALIZED = "deepseek-v4-pro"
EXPECTED_AZURE_SENIOR_FAMILY = "deepseek-v4"


class ControlFlowError(ValueError):
    pass


class IdentityAuditError(ControlFlowError):
    pass


class RouteAuditError(ControlFlowError):
    pass


class LiveSeniorAPIError(ControlFlowError):
    pass


class SeniorIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    provider: str
    deployment: str | None = None
    model: str
    normalized_model: str | None = None
    model_family: str
    adapter: Literal["offline", "live", "test"] = "offline"
    response_model: str | None = None
    response_id: str | None = None
    request_model: str | None = None
    metadata_source: str | None = None

    @model_validator(mode="before")
    @classmethod
    def fill_normalized_model(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if not data.get("normalized_model") and data.get("model"):
            data["normalized_model"] = normalize_identity_value(str(data["model"]))
        return data

    @model_validator(mode="after")
    def validate_identity(self) -> SeniorIdentity:
        fields = {
            "provider": self.provider,
            "deployment": self.deployment,
            "model": self.model,
            "model_family": self.model_family,
            "response_model": self.response_model,
            "request_model": self.request_model,
        }
        for field_name, value in fields.items():
            if value is None:
                continue
            normalized = normalize_identity_value(value)
            if normalized in DEPRECATED_DEEPSEEK_ALIASES:
                raise IdentityAuditError(
                    f"{field_name} uses deprecated DeepSeek alias {value!r}; "
                    f"deepseek-chat and deepseek-reasoner are deprecated {DEEPSEEK_ALIAS_DEPRECATION}"
                )
        if self.adapter == "live":
            required = {
                "provider": self.provider,
                "deployment": self.deployment,
                "model": self.model,
                "model_family": self.model_family,
            }
            missing = [name for name, value in required.items() if not str(value or "").strip()]
            if missing:
                raise IdentityAuditError(f"live identity missing required fields: {', '.join(missing)}")
        if self.provider == "azure-foundry" and self.adapter == "live":
            if normalize_identity_value(self.model) != EXPECTED_AZURE_SENIOR_MODEL_NORMALIZED:
                raise IdentityAuditError(
                    "Azure Foundry Senior deployment must document underlying model "
                    f"{EXPECTED_AZURE_SENIOR_MODEL}"
                )
            if normalize_identity_value(self.model_family) != EXPECTED_AZURE_SENIOR_FAMILY:
                raise IdentityAuditError("Azure Foundry Senior model family must be deepseek-v4")
            if self.response_model:
                normalized_response = normalize_identity_value(self.response_model)
                normalized_deployment = normalize_identity_value(self.deployment or "")
                if normalized_response not in {EXPECTED_AZURE_SENIOR_MODEL_NORMALIZED, normalized_deployment}:
                    raise IdentityAuditError("Senior response metadata contradicts configured Azure Foundry identity")
        if self.adapter == "offline" and normalize_identity_value(self.provider) != "offline":
            raise IdentityAuditError("offline identity must serialize with provider offline")
        return self


class AnalystIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    provider: str
    deployment: str | None = None
    model: str
    normalized_model: str | None = None
    model_family: str
    adapter: Literal["offline", "live", "test"] = "offline"
    response_model: str | None = None
    request_model: str | None = None
    metadata_source: str | None = None

    @model_validator(mode="before")
    @classmethod
    def fill_normalized_model(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if not data.get("normalized_model") and data.get("model"):
            data["normalized_model"] = normalize_identity_value(str(data["model"]))
        return data

    @model_validator(mode="after")
    def validate_identity(self) -> AnalystIdentity:
        for field_name in ("provider", "deployment", "model", "model_family", "response_model", "request_model"):
            value = getattr(self, field_name)
            if value is not None and normalize_identity_value(value) in DEPRECATED_DEEPSEEK_ALIASES:
                raise IdentityAuditError(
                    f"{field_name} uses deprecated DeepSeek alias {value!r}; "
                    f"deepseek-chat and deepseek-reasoner are deprecated {DEEPSEEK_ALIAS_DEPRECATION}"
                )
        if self.adapter == "live":
            missing = [
                name
                for name in ("provider", "model", "model_family")
                if not str(getattr(self, name) or "").strip()
            ]
            if missing:
                raise IdentityAuditError(f"live analyst identity missing required fields: {', '.join(missing)}")
        if self.adapter == "offline" and normalize_identity_value(self.provider) != "offline":
            raise IdentityAuditError("offline analyst identity must serialize with provider offline")
        return self


class KillMemo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    header: Header
    ticker: str
    as_of: date
    status: Literal["halted"]
    halt_kind: Literal[
        "gate_kill",
        "business_no_go",
        "senior_overturn_without_replacement",
        "route_audit_violation",
        "identity_audit_violation",
        "live_senior_api_failure",
    ]
    gate: str
    reason: str
    evidence_paths: list[str]
    senior_identity: dict[str, Any] | None = None
    replacement_required: bool = False
    replacement_provided: bool = False

    @model_validator(mode="after")
    def validate_memo(self) -> KillMemo:
        if not self.reason.strip():
            raise ValueError("KillMemo requires reason")
        if self.halt_kind in {
            "gate_kill",
            "business_no_go",
            "senior_overturn_without_replacement",
            "route_audit_violation",
            "live_senior_api_failure",
        } and not self.evidence_paths:
            raise ValueError("KillMemo requires evidence paths for filed-artifact halts")
        if self.replacement_provided and not self.replacement_required:
            raise ValueError("KillMemo replacement_provided cannot be true unless replacement_required is true")
        return self


class RouteEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    step_id: str
    produced_artifacts: list[str] = Field(default_factory=list)
    audits: list[str] = Field(default_factory=list)
    senior_touchpoint: Literal["none", "early_gate", "consolidated_ratification", "final_lean_ratification"] = "none"
    halted: bool = False


DOCUMENTED_ROUTE_STEPS = (
    "A-1",
    "A-2",
    "A-3",
    "B-1",
    "B-2",
    "D-1",
    "C-1",
    "EARLY-GATE",
    "B-4",
    "B-6",
    "B-3",
    "B-5",
    "C-4",
    "C-5",
    "C-6",
    "M3-7",
    "D-2",
    "FINAL-LEAN",
    "D-3",
)

ALLOWED_SENIOR_TOUCHPOINTS = {
    "EARLY-GATE": "early_gate",
    "M3-7": "consolidated_ratification",
    "FINAL-LEAN": "final_lean_ratification",
}


class RouteRecorder:
    def __init__(self) -> None:
        self.events: list[RouteEvent] = []

    def record(
        self,
        step_id: str,
        *,
        produced_artifacts: list[str] | None = None,
        audits: list[str] | None = None,
        senior_touchpoint: Literal["none", "early_gate", "consolidated_ratification", "final_lean_ratification"] = "none",
        halted: bool = False,
    ) -> None:
        self.events.append(
            RouteEvent(
                step_id=step_id,
                produced_artifacts=produced_artifacts or [],
                audits=audits or [],
                senior_touchpoint=senior_touchpoint,
                halted=halted,
            )
        )

    def manifest_payload(self) -> dict[str, Any]:
        return {"events": [event.model_dump(mode="json") for event in self.events]}


def normalize_identity_value(value: str) -> str:
    return str(value).strip().lower()


def senior_identity_payload(identity: SeniorIdentity) -> dict[str, Any]:
    return identity.model_dump(mode="json", exclude_none=True)


def senior_identity_from_adapter(senior: Any, response: dict[str, Any] | None = None) -> SeniorIdentity:
    base = _identity_payload_from_adapter(senior)
    if base is None:
        legacy = _legacy_identity_label(senior) or "offline-senior"
        base = {
            "provider": "offline",
            "model": legacy,
            "model_family": legacy,
            "adapter": "offline",
            "metadata_source": "legacy-offline",
        }
    payload = dict(base)
    if response:
        if isinstance(response.get("senior_identity"), dict):
            payload.update(response["senior_identity"])
        response_model = response.get("response_model") or response.get("model")
        response_id = response.get("response_id") or response.get("id")
        if response_model is not None:
            payload["response_model"] = str(response_model)
        if response_id is not None:
            payload["response_id"] = str(response_id)
    try:
        return SeniorIdentity.model_validate(payload)
    except ValidationError as exc:
        raise IdentityAuditError(f"senior identity metadata is invalid: {exc}") from exc


def analyst_identity_from_adapter(adapter: Any, fallback_model: str | None = None) -> AnalystIdentity:
    base = _identity_payload_from_adapter(adapter)
    if base is None:
        legacy = _legacy_identity_label(adapter) or fallback_model
        if legacy is None:
            raise IdentityAuditError("analyst adapter must declare identity metadata or a legacy offline model label")
        base = {
            "provider": "offline",
            "model": legacy,
            "model_family": legacy,
            "adapter": "offline",
            "metadata_source": "legacy-offline",
        }
    try:
        return AnalystIdentity.model_validate(base)
    except ValidationError as exc:
        raise IdentityAuditError(f"analyst identity metadata is invalid: {exc}") from exc


def assert_independent(analyst: AnalystIdentity, senior: SeniorIdentity) -> None:
    analyst_family = normalize_identity_value(analyst.model_family)
    senior_family = normalize_identity_value(senior.model_family)
    analyst_model = normalize_identity_value(analyst.response_model or analyst.model)
    senior_model = normalize_identity_value(senior.response_model or senior.model)
    if analyst_family == senior_family and analyst_model == senior_model:
        raise IdentityAuditError(
            f"analyst and senior identities must differ: family={senior_family} model={senior_model}"
        )


def audit_route_events(events: list[RouteEvent], *, method: str, storage: Storage | None = None) -> None:
    step_ids = [event.step_id for event in events]
    expected = list(DOCUMENTED_ROUTE_STEPS)
    if method != "DCF":
        expected.remove("B-3")
        expected.remove("B-5")
    if step_ids != expected:
        raise RouteAuditError(f"route step mismatch: expected {expected}, got {step_ids}")
    for event in events:
        allowed_touchpoint = ALLOWED_SENIOR_TOUCHPOINTS.get(event.step_id, "none")
        if event.senior_touchpoint != allowed_touchpoint:
            raise RouteAuditError(f"undocumented Senior touchpoint at {event.step_id}")
        if event.step_id == "D-3" and event.halted:
            raise RouteAuditError("D-3 must not run on halted paths")
        if storage is not None:
            for artifact in event.produced_artifacts:
                try:
                    storage.get_json(artifact)
                except Exception as exc:
                    raise RouteAuditError(f"route artifact missing before downstream consumption: {artifact}") from exc
        if event.step_id == "B-5" and method == "DCF":
            anchors = [
                artifact
                for artifact in event.produced_artifacts
                if "/base_rate_" in artifact and artifact.endswith(".json")
            ]
            if len(anchors) != 3:
                raise RouteAuditError("C-4 DCF route requires three filed B-5 base-rate anchors")


def file_kill_memo(
    *,
    storage: Storage,
    run_dir: str,
    header: Header,
    ticker: str,
    as_of: date,
    halt_kind: KillMemo.model_fields["halt_kind"].annotation,
    gate: str,
    reason: str,
    evidence_paths: list[str],
    senior_identity: SeniorIdentity | None = None,
    replacement_required: bool = False,
    replacement_provided: bool = False,
) -> dict[str, Any]:
    memo = KillMemo(
        header=header,
        ticker=ticker,
        as_of=as_of,
        status="halted",
        halt_kind=halt_kind,
        gate=gate,
        reason=reason,
        evidence_paths=evidence_paths,
        senior_identity=senior_identity_payload(senior_identity) if senior_identity else None,
        replacement_required=replacement_required,
        replacement_provided=replacement_provided,
    )
    path = f"{run_dir}/kill_memo.json"
    payload = artifact_model_to_payload(memo)
    storage.put_json(path, payload)
    if storage.get_json(path) != payload:
        raise RuntimeError("kill memo storage round-trip failed")
    return {
        "status": "halted",
        "ticker": ticker,
        "as_of": as_of.isoformat(),
        "kill_memo_path": path,
        "kill_memo": payload,
    }


class AzureFoundrySenior:
    provider = "azure-foundry"

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        deployment: str,
        documented_model: str = EXPECTED_AZURE_SENIOR_MODEL,
    ) -> None:
        if not endpoint.strip() or not api_key.strip() or not deployment.strip():
            raise IdentityAuditError("Azure Foundry Senior requires endpoint, api key, and deployment")
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.deployment = deployment.strip()
        self.documented_model = documented_model.strip()
        self.identity = SeniorIdentity(
            provider="azure-foundry",
            deployment=self.deployment,
            model=self.documented_model,
            model_family=EXPECTED_AZURE_SENIOR_FAMILY,
            adapter="live",
            request_model=self.deployment,
            metadata_source="environment",
        )
        self.model_family = self.identity.model_family
        self.decided_by = f"azure-foundry:{self.deployment}"

    @classmethod
    def from_env(cls) -> AzureFoundrySenior:
        return cls(
            endpoint=os.environ.get("AZURE_FOUNDRY_ENDPOINT", ""),
            api_key=os.environ.get("AZURE_FOUNDRY_API_KEY", ""),
            deployment=os.environ.get("SENIOR_DEPLOYMENT_NAME", ""),
        )

    def gate(self, package: dict[str, Any]) -> dict[str, Any]:
        response = self._chat(
            system="You are the Senior signer. Return strict JSON with decision GO or NO-GO, rationale, decided_by.",
            payload=package,
        )
        decision = str(response.get("decision", "GO")).upper()
        if decision not in {"GO", "NO-GO"}:
            raise ValueError(f"invalid Azure Senior gate decision: {decision}")
        return {
            "decision": decision,
            "rationale": str(response.get("rationale") or response.get("reason") or "Azure Foundry Senior gate decision"),
            "decided_by": str(response.get("decided_by") or self.decided_by),
            "senior_identity": senior_identity_payload(self.identity),
            "response_model": response.get("response_model"),
            "response_id": response.get("response_id"),
        }

    def ratify(self, package: dict[str, Any]) -> dict[str, Any]:
        response = self._chat(
            system="You are the Senior signer. Return strict JSON with decided_by and decisions for every required item.",
            payload=package,
        )
        decisions = response.get("decisions")
        if not isinstance(decisions, dict):
            raise ValueError("Azure Senior ratify response requires decisions")
        return {
            "decided_by": str(response.get("decided_by") or self.decided_by),
            "decisions": decisions,
            "senior_identity": senior_identity_payload(self.identity),
            "response_model": response.get("response_model"),
            "response_id": response.get("response_id"),
        }

    def _chat(self, *, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.endpoint}/chat/completions"
        body = json.dumps(
            {
                "model": self.deployment,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(payload, sort_keys=True)},
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            headers={"api-key": self.api_key, "content-type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise LiveSeniorAPIError(
                f"live Senior API failure: HTTP {exc.code} {exc.reason}; response_body={error_body}"
            ) from exc
        except URLError as exc:
            raise LiveSeniorAPIError(f"live Senior API failure: {exc.reason}") from exc
        except TimeoutError as exc:
            raise LiveSeniorAPIError(f"live Senior API failure: {exc}") from exc
        content = raw["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        parsed["response_model"] = raw.get("model")
        parsed["response_id"] = raw.get("id")
        response_identity = self.identity.model_copy(
            update={"response_model": parsed.get("response_model"), "response_id": parsed.get("response_id")}
        )
        SeniorIdentity.model_validate(response_identity.model_dump())
        return parsed


def _identity_payload_from_adapter(adapter: Any) -> dict[str, Any] | None:
    if adapter is None:
        return None
    identity = getattr(adapter, "identity", None)
    if callable(identity):
        identity = identity()
    if isinstance(identity, BaseModel):
        return identity.model_dump(mode="json", exclude_none=True)
    if isinstance(identity, dict):
        return dict(identity)
    return None


def _legacy_identity_label(adapter: Any) -> str | None:
    if adapter is None:
        return None
    for attr in ("model_family", "model_handle", "senior_handle"):
        value = getattr(adapter, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
