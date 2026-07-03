from __future__ import annotations

import json
from io import BytesIO
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest
from pydantic import ValidationError

import resolver
import skills.control_flow as control_flow
from skills._primitives import Ratifiable
from skills.control_flow import (
    AzureFoundrySenior,
    RouteAuditError,
    RouteEvent,
    SeniorIdentity,
    analyst_identity_from_adapter,
    audit_route_events,
)
from skills.storage import LocalStorage
from skills.synthesis.review_packager.review_packager import FinalHandoff

RUN_DATE = date(2026, 7, 3)


def test_resolver_md_documents_route_and_escalation_matrix() -> None:
    text = Path("resolver.md").read_text(encoding="utf-8")

    assert "Routing Table" in text
    assert "Escalation Matrix" in text
    assert "B-5 Base-Rate" in text
    assert "MRNA follows the non-DCF" in text
    assert "Parallelism is deferred" in text


def test_final_handoff_exposes_signer_identity_and_canonical_revisit_triggers(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    filed = FinalHandoff.model_validate(storage.get_json("runs/AAPL/2026-07-03/final_handoff.json"))

    assert payload["final_lean_signed_by_provider"] == "offline"
    assert filed.final_lean_signed_by_model_family == "offline-senior"
    assert filed.revisit_triggers
    assert filed.revisit_if == filed.revisit_triggers


def test_final_handoff_rejects_revisit_alias_divergence(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)
    payload = storage.get_json("runs/AAPL/2026-07-03/final_handoff.json")
    payload["revisit_if"] = ["divergent trigger"]

    with pytest.raises(ValidationError, match="revisit_if must mirror"):
        FinalHandoff.model_validate(payload)


def test_final_lean_rejection_files_canonical_kill_memo(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage, senior=FinalLeanRejectingSenior())

    assert payload["status"] == "halted"
    assert payload["kill_memo_path"] == "runs/AAPL/2026-07-03/kill_memo.json"
    assert payload["kill_memo"]["halt_kind"] == "senior_overturn_without_replacement"
    assert storage.get_json(payload["kill_memo_path"]) == payload["kill_memo"]
    with pytest.raises(FileNotFoundError):
        storage.get_json("runs/AAPL/2026-07-03/final_handoff.json")


def test_gate_kill_files_kill_memo_and_no_final_handoff(tmp_path, monkeypatch) -> None:
    original = resolver.build_gate_card

    def forced_kill(*args, **kwargs):
        gate = original(*args, **kwargs)
        return gate.model_copy(
            update={
                "verdict": Ratifiable(
                    draft="KILL",
                    evidence=["forced test gate"],
                    decision=None,
                    decided_by=None,
                    final=None,
                )
            }
        )

    monkeypatch.setattr(resolver, "build_gate_card", forced_kill)
    storage = LocalStorage(tmp_path)
    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage)

    assert payload["status"] == "halted"
    assert payload["kill_memo"]["halt_kind"] == "gate_kill"
    with pytest.raises(FileNotFoundError):
        storage.get_json("runs/AAPL/2026-07-03/final_handoff.json")


def test_route_audit_rejects_missing_b5_on_dcf_route() -> None:
    events = [_event(step) for step in _dcf_steps_without_b5()]

    with pytest.raises(RouteAuditError, match="route step mismatch"):
        audit_route_events(events, method="DCF")


def test_route_audit_accepts_non_dcf_without_b3_or_b5() -> None:
    events = [_event(step) for step in _non_dcf_steps()]

    audit_route_events(events, method="rNPV")


def test_azure_foundry_senior_identity_from_env_and_alias_rejection(monkeypatch) -> None:
    monkeypatch.setenv("AZURE_FOUNDRY_ENDPOINT", "https://example-foundry.openai.azure.com")
    monkeypatch.setenv("AZURE_FOUNDRY_API_KEY", "test-key")
    monkeypatch.setenv("SENIOR_DEPLOYMENT_NAME", "senior-deepseek-v4-pro")

    senior = AzureFoundrySenior.from_env()

    assert senior.identity.provider == "azure-foundry"
    assert senior.identity.deployment == "senior-deepseek-v4-pro"
    assert senior.identity.model == "DeepSeek-V4-Pro"
    assert senior.identity.normalized_model == "deepseek-v4-pro"
    assert senior.identity.request_model == "senior-deepseek-v4-pro"

    with pytest.raises(ValidationError, match="July 24, 2026"):
        SeniorIdentity(
            provider="azure-foundry",
            deployment="deepseek-chat",
            model="DeepSeek-V4-Pro",
            model_family="deepseek-v4",
            adapter="live",
        )


def test_azure_foundry_senior_uses_foundry_v1_chat_completions_shape(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.get_full_url()
        captured["timeout"] = timeout
        captured["headers"] = dict(req.headers)
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeHTTPResponse(
            {
                "id": "chatcmpl-test",
                "model": "DeepSeek-V4-Pro",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "decision": "GO",
                                    "rationale": "test go",
                                    "decided_by": "live-test-senior",
                                }
                            )
                        }
                    }
                ],
            }
        )

    monkeypatch.setattr(control_flow.request, "urlopen", fake_urlopen)
    senior = AzureFoundrySenior(
        endpoint="https://company-hq.services.ai.azure.com/openai/v1",
        api_key="test-key",
        deployment="senior-deepseek-v4-pro",
    )

    response = senior.gate({"ticker": "AAPL"})

    assert captured["url"] == "https://company-hq.services.ai.azure.com/openai/v1/chat/completions"
    assert "api-version" not in captured["url"]
    assert captured["body"]["model"] == "senior-deepseek-v4-pro"
    assert captured["body"]["messages"][0]["role"] == "system"
    assert captured["body"]["messages"][1]["role"] == "user"
    assert captured["headers"]["Api-key"] == "test-key"
    assert captured["headers"]["Content-type"] == "application/json"
    assert captured["timeout"] == 60
    assert response["decision"] == "GO"
    assert response["response_model"] == "DeepSeek-V4-Pro"


def test_azure_foundry_ratify_retries_malformed_decision_and_halts_with_raw_response(tmp_path, monkeypatch) -> None:
    captured_bodies = []

    def fake_urlopen(req, timeout):
        body = json.loads(req.data.decode("utf-8"))
        captured_bodies.append(body)
        system = body["messages"][0]["content"]
        package = json.loads(body["messages"][1]["content"])
        if "ratification pass" not in system:
            return _chat_response({"decision": "GO", "rationale": "test go", "decided_by": "live-test-senior"})
        bad_label = "DIG_RETRY" if "previous response did not match" in system else "DIG"
        return _chat_response(
            {
                "decided_by": "live-test-senior",
                "decisions": {item_id: bad_label for item_id in package["required_item_ids"]},
            }
        )

    monkeypatch.setattr(control_flow.request, "urlopen", fake_urlopen)
    senior = AzureFoundrySenior(
        endpoint="https://company-hq.services.ai.azure.com/openai/v1",
        api_key="test-key",
        deployment="senior-deepseek-v4-pro",
    )
    storage = LocalStorage(tmp_path)

    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage, senior=senior)

    assert payload["status"] == "halted"
    assert payload["kill_memo"]["halt_kind"] == "live_senior_api_failure"
    assert payload["kill_memo"]["gate"] == "consolidated_ratification"
    assert "raw_response" in payload["kill_memo"]["reason"]
    assert "DIG_RETRY" in payload["kill_memo"]["reason"]
    assert len(captured_bodies) == 3
    assert "previous response did not match" in captured_bodies[2]["messages"][0]["content"]
    assert "decision\" must be one of" not in payload["kill_memo"]["reason"]
    assert storage.get_json(payload["kill_memo_path"]) == payload["kill_memo"]
    with pytest.raises(FileNotFoundError):
        storage.get_json("runs/AAPL/2026-07-03/senior_decision_package.json")


def test_azure_foundry_ratify_well_formed_response_parses(monkeypatch) -> None:
    captured_bodies = []

    def fake_urlopen(req, timeout):
        body = json.loads(req.data.decode("utf-8"))
        captured_bodies.append(body)
        package = json.loads(body["messages"][1]["content"])
        return _chat_response(
            {
                "decided_by": "live-test-senior",
                "decisions": {
                    item_id: {"decision": "ratified", "final": None, "rationale": f"accepted {item_id}"}
                    for item_id in package["required_item_ids"]
                },
            }
        )

    monkeypatch.setattr(control_flow.request, "urlopen", fake_urlopen)
    senior = AzureFoundrySenior(
        endpoint="https://company-hq.services.ai.azure.com/openai/v1",
        api_key="test-key",
        deployment="senior-deepseek-v4-pro",
    )

    response = senior.ratify({"ticker": "AAPL", "required_item_ids": ["review_a", "review_b"]})

    assert response["decided_by"] == "live-test-senior"
    assert response["decisions"]["review_a"]["decision"] == "ratified"
    assert response["decisions"]["review_b"]["final"] is None
    assert len(captured_bodies) == 1
    assert "Each decision value must be an object" in captured_bodies[0]["messages"][0]["content"]


def test_live_senior_http_error_files_kill_memo_with_response_body(tmp_path, monkeypatch) -> None:
    def failing_urlopen(req, timeout):
        raise HTTPError(
            req.get_full_url(),
            429,
            "Too Many Requests",
            hdrs=None,
            fp=BytesIO(b'{"error":{"message":"quota exceeded","code":"429"}}'),
        )

    monkeypatch.setattr(control_flow.request, "urlopen", failing_urlopen)
    senior = AzureFoundrySenior(
        endpoint="https://company-hq.services.ai.azure.com/openai/v1",
        api_key="test-key",
        deployment="senior-deepseek-v4-pro",
    )
    storage = LocalStorage(tmp_path)

    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage, senior=senior)

    assert payload["status"] == "halted"
    assert payload["kill_memo_path"] == "runs/AAPL/2026-07-03/kill_memo.json"
    assert payload["kill_memo"]["halt_kind"] == "live_senior_api_failure"
    assert payload["kill_memo"]["gate"] == "business_early_gate"
    assert "quota exceeded" in payload["kill_memo"]["reason"]
    assert storage.get_json(payload["kill_memo_path"]) == payload["kill_memo"]
    with pytest.raises(FileNotFoundError):
        storage.get_json("runs/AAPL/2026-07-03/final_handoff.json")


def test_live_senior_transport_error_files_kill_memo(tmp_path, monkeypatch) -> None:
    def failing_urlopen(req, timeout):
        raise URLError("connection refused")

    monkeypatch.setattr(control_flow.request, "urlopen", failing_urlopen)
    senior = AzureFoundrySenior(
        endpoint="https://company-hq.services.ai.azure.com/openai/v1",
        api_key="test-key",
        deployment="senior-deepseek-v4-pro",
    )
    storage = LocalStorage(tmp_path)

    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage, senior=senior)

    assert payload["status"] == "halted"
    assert payload["kill_memo"]["halt_kind"] == "live_senior_api_failure"
    assert payload["kill_memo"]["gate"] == "business_early_gate"
    assert "connection refused" in payload["kill_memo"]["reason"]
    assert storage.get_json(payload["kill_memo_path"]) == payload["kill_memo"]
    with pytest.raises(FileNotFoundError):
        storage.get_json("runs/AAPL/2026-07-03/final_handoff.json")


def test_same_actual_live_analyst_and_senior_identity_files_kill_memo_even_with_different_legacy_labels(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    identity = {
        "provider": "openai",
        "deployment": "shared-deployment",
        "model": "gpt-5",
        "model_family": "gpt-5",
        "adapter": "live",
        "metadata_source": "test-live",
    }
    llm = LiveAnalyst(identity=identity, model_handle="analyst-legacy-label")
    senior = LiveSenior(identity=identity, model_family="senior-legacy-label")

    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage, llm=llm, senior=senior)

    assert payload["status"] == "halted"
    assert payload["kill_memo_path"] == "runs/AAPL/2026-07-03/kill_memo.json"
    assert payload["kill_memo"]["halt_kind"] == "identity_audit_violation"
    assert payload["kill_memo"]["gate"] == "business_early_gate"
    assert storage.get_json(payload["kill_memo_path"]) == payload["kill_memo"]
    assert senior.gate_calls == 0
    with pytest.raises(FileNotFoundError):
        storage.get_json("runs/AAPL/2026-07-03/final_handoff.json")


def test_valid_live_adapter_with_only_identity_contract_is_accepted(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    llm = LiveAnalyst(
        identity={
            "provider": "openai",
            "deployment": "analyst-deployment",
            "model": "gpt-4.1",
            "model_family": "gpt-4.1",
            "adapter": "live",
            "metadata_source": "test-live",
        }
    )
    senior = LiveSenior(
        identity={
            "provider": "openai",
            "deployment": "senior-deployment",
            "model": "gpt-5",
            "model_family": "gpt-5",
            "adapter": "live",
            "metadata_source": "test-live",
        }
    )

    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage, llm=llm, senior=senior)

    assert payload["header"]["produced_by"] == "D-3"
    assert senior.gate_calls == 1
    assert senior.ratify_calls == 2
    assert storage.get_json("runs/AAPL/2026-07-03/senior_decision_package.json")["decided_by_adapter"] == "live"
    assert storage.get_json("runs/AAPL/2026-07-03/final_lean_decision_package.json")["decided_by_adapter"] == "live"


def test_missing_live_analyst_identity_files_identity_kill_memo(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    senior = LiveSenior(
        identity={
            "provider": "openai",
            "deployment": "senior-deployment",
            "model": "gpt-5",
            "model_family": "gpt-5",
            "adapter": "live",
            "metadata_source": "test-live",
        }
    )

    payload = resolver.analyze("AAPL", as_of=RUN_DATE, storage=storage, llm=UnidentifiedLiveAnalyst(), senior=senior)

    assert payload["status"] == "halted"
    assert payload["kill_memo_path"] == "runs/AAPL/2026-07-03/kill_memo.json"
    assert payload["kill_memo"]["halt_kind"] == "identity_audit_violation"
    assert payload["kill_memo"]["gate"] == "business_early_gate"
    assert storage.get_json(payload["kill_memo_path"]) == payload["kill_memo"]
    with pytest.raises(FileNotFoundError):
        storage.get_json("runs/AAPL/2026-07-03/final_handoff.json")


def test_incomplete_live_analyst_identity_files_identity_kill_memo(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    senior = LiveSenior(
        identity={
            "provider": "openai",
            "deployment": "senior-deployment",
            "model": "gpt-5",
            "model_family": "gpt-5",
            "adapter": "live",
            "metadata_source": "test-live",
        }
    )

    payload = resolver.analyze(
        "AAPL",
        as_of=RUN_DATE,
        storage=storage,
        llm=LiveAnalyst(
            identity={
                "provider": "openai",
                "deployment": "analyst-deployment",
                "model_family": "gpt-4.1",
                "adapter": "live",
                "metadata_source": "test-live",
            }
        ),
        senior=senior,
    )

    assert payload["status"] == "halted"
    assert payload["kill_memo"]["halt_kind"] == "identity_audit_violation"
    assert payload["kill_memo"]["gate"] == "business_early_gate"
    assert storage.get_json(payload["kill_memo_path"]) == payload["kill_memo"]


def test_legacy_offline_analyst_fixture_identity_stays_marked_offline() -> None:
    identity = analyst_identity_from_adapter(LegacyOfflineAnalyst(), "unused-fallback")

    assert identity.provider == "offline"
    assert identity.adapter == "offline"
    assert identity.model == "offline-fixture-analyst"
    assert identity.metadata_source == "legacy-offline"


class FinalLeanRejectingSenior:
    model_family = "offline-senior"
    identity = {
        "provider": "offline",
        "model": "offline-senior",
        "model_family": "offline-senior",
        "adapter": "offline",
    }

    def gate(self, package):
        return {"decision": "GO", "rationale": "test go", "decided_by": "rejecting-senior", "senior_identity": self.identity}

    def ratify(self, package):
        item_ids = list(package["required_item_ids"])
        if item_ids == ["final_lean"]:
            return {
                "decided_by": "rejecting-senior",
                "senior_identity": self.identity,
                "decisions": {"final_lean": {"decision": "overturned", "final": None, "rationale": "reject final lean"}},
            }
        return {
            "decided_by": "rejecting-senior",
            "senior_identity": self.identity,
            "decisions": {
                item_id: {"decision": "ratified", "final": None, "rationale": f"accepted:{item_id}"}
                for item_id in item_ids
            },
        }


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _chat_response(content):
    return FakeHTTPResponse(
        {
            "id": "chatcmpl-test",
            "model": "DeepSeek-V4-Pro",
            "choices": [{"message": {"content": json.dumps(content)}}],
        }
    )


class LiveAnalyst:
    def __init__(self, *, identity: dict[str, str], model_handle: str | None = None) -> None:
        self.identity = identity
        if model_handle is not None:
            self.model_handle = model_handle

    def complete(self, prompt: str, *, context: dict) -> str:
        return prompt


class UnidentifiedLiveAnalyst:
    def complete(self, prompt: str, *, context: dict) -> str:
        return prompt


class LegacyOfflineAnalyst:
    model_handle = "offline-fixture-analyst"

    def complete(self, prompt: str, *, context: dict) -> str:
        return prompt


class LiveSenior:
    def __init__(self, *, identity: dict[str, str], model_family: str = "senior-legacy-label") -> None:
        self.identity = identity
        self.model_family = model_family
        self.decided_by = "live-test-senior"
        self.gate_calls = 0
        self.ratify_calls = 0

    def gate(self, package):
        self.gate_calls += 1
        return {
            "decision": "GO",
            "rationale": "live test go",
            "decided_by": self.decided_by,
            "senior_identity": self.identity,
        }

    def ratify(self, package):
        self.ratify_calls += 1
        item_ids = list(package["required_item_ids"])
        return {
            "decided_by": self.decided_by,
            "senior_identity": self.identity,
            "decisions": {
                item_id: {"decision": "ratified", "final": None, "rationale": f"accepted:{item_id}"}
                for item_id in item_ids
            },
        }


def _dcf_steps_without_b5() -> list[str]:
    return [
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
        "C-4",
        "C-5",
        "C-6",
        "M3-7",
        "D-2",
        "FINAL-LEAN",
        "D-3",
    ]


def _non_dcf_steps() -> list[str]:
    return [
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
        "C-4",
        "C-5",
        "C-6",
        "M3-7",
        "D-2",
        "FINAL-LEAN",
        "D-3",
    ]


def _event(step: str) -> RouteEvent:
    touchpoints = {
        "EARLY-GATE": "early_gate",
        "M3-7": "consolidated_ratification",
        "FINAL-LEAN": "final_lean_ratification",
    }
    return RouteEvent(step_id=step, senior_touchpoint=touchpoints.get(step, "none"))
