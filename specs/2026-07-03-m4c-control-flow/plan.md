# M4c Control Flow - Plan

## Objective

Complete the resolver control-flow layer so `analyze()` has auditable routing, enforced escalation rules, live Senior wiring, identity-based independence checks, formal KILL halt handling, and final Handoff revisit triggers derived from C-5 falsifiers.

M4c is a correctness and governance slice. It must not add new research or valuation skill behavior. It makes the existing route explicit, audited, and impossible to bypass by accident.

## Scope

In scope:

- Live Senior adapter wired to Azure AI Foundry serving DeepSeek V4 Pro.
- Azure Foundry connection uses environment configuration only: `AZURE_FOUNDRY_ENDPOINT`, `AZURE_FOUNDRY_API_KEY`, and `SENIOR_DEPLOYMENT_NAME`.
- The live Senior requests the configured deployment name, and that deployment's documented underlying model identifier is verified as `DeepSeek-V4-Pro`, which normalizes to `deepseek-v4-pro`, at configuration level.
- Rejection of deprecated DeepSeek aliases `deepseek-chat` and `deepseek-reasoner`, which are deprecated July 24, 2026.
- Identity-based Senior/Analyst independence checks using actual provider/deployment/model-family/model identity from adapter configuration and response metadata.
- Offline Senior adapter remains available for tests and eval, clearly identified as offline.
- Senior identity is persisted with every Senior decision and exposed through final Handoff signing metadata.
- General KILL halt mechanism with a typed `KillMemo` artifact filed to the run directory.
- Existing M4b final-lean-overturned-without-replacement halt becomes a `KillMemo` case.
- Gate-card `KILL` becomes a first-class KILL halt case.
- Existing halted-path response shape is preserved: `analyze()` returns a halted payload containing the filed halt artifact.
- Final Handoff schema is completed with canonical `revisit_triggers`.
- C-5 Edge `pass_falsifiers` are wired into final Handoff `revisit_triggers`.
- Every final Handoff carries at least the falsifier-derived revisit triggers.
- `resolver.md` is created as the canonical routing table and escalation matrix.
- `resolver.py` enforces the routing table and escalation matrix through auditable route-manifest checks.
- Standalone resolver CLI can select the live Senior path used by validation, without silently falling back to the offline Senior.
- Full tests for KILL, revisit triggers, live Senior identity, and negative independence cases.

Out of scope:

- New Accountant or Analyst bundles.
- New valuation methods.
- Calibration analytics beyond reporting the live-run `ratified_as_is_rate` from the existing Senior decision packages.
- Performance work unless a parallel step is trivially safe and audit-neutral.
- Broad resolver refactors not needed to enforce the route.
- Changing the two constitutionally allowed Senior touchpoint classes: early gate and ratification. The M4b final lean sign-off remains the final synthesis ratification substep, not an Analyst touchpoint.

## Current State

M4b currently produces complete final Handoffs and has a narrow halted path when the Senior overturns the final Buy/Watch/Pass lean without a replacement. That path returns `status="halted"` and files a typed `FinalLeanReturnedForRevision`.

M4c replaces that one-off halt artifact with the general `KillMemo` mechanism. It also upgrades declared-label independence checks in the early gate and ratification code to actual identity checks.

## Senior Wiring Plan

Add a concrete live Senior adapter for Azure AI Foundry serving DeepSeek V4 Pro.

The adapter contract must expose actual identity, not only configured labels:

```text
SeniorIdentity:
  provider: "azure-foundry"
  deployment: value of SENIOR_DEPLOYMENT_NAME
  model: "DeepSeek-V4-Pro"        # Azure documented underlying deployment model, recorded with provider casing
  normalized_model: "deepseek-v4-pro"
  model_family: "deepseek-v4"
  adapter: "live"
  response_model: provider-returned model/deployment value recorded verbatim when present
  response_id: provider-returned response/request id when present
```

Rules:

1. The live Senior must read `AZURE_FOUNDRY_ENDPOINT`, `AZURE_FOUNDRY_API_KEY`, and `SENIOR_DEPLOYMENT_NAME` from environment-backed config. These values must never be hardcoded.
2. The live Senior must request the configured deployment name exactly.
3. Configuration must verify the configured deployment's documented underlying model identifier is `DeepSeek-V4-Pro`.
4. All model identity comparisons must normalize by stripping whitespace and lowercasing before matching. The expected normalized Senior model is `deepseek-v4-pro`.
5. The adapter must reject configured aliases `deepseek-chat` and `deepseek-reasoner` wherever they appear as deployment, model, documented model, or family config values, after applying the same strip-and-lowercase normalization.
6. The adapter must capture response metadata verbatim when the provider returns it. Azure may return `DeepSeek-V4-Pro` or the deployment name rather than DeepSeek's lowercase public model string; record that value as `response_model`.
7. Live validation confirmed the response `model` field returns `DeepSeek-V4-Pro`; record that value verbatim as `response_model`.
8. If response metadata is absent, the adapter may fall back only to the actual adapter request identity and verified deployment configuration, never to a user-supplied display label.
9. If response metadata contradicts the configured identity after normalization, the adapter must fail closed. Returning the deployment name is not a contradiction when it matches `SENIOR_DEPLOYMENT_NAME`.
10. The offline Senior must expose provider/model-family/model identity as offline/test identity, for example provider `offline`, model `offline-senior`, model_family `offline`, adapter `offline`.
11. Tests and eval may keep using the offline Senior by explicit construction or default test wiring.

## Independence Check Plan

Replace declared-family checks with identity-based checks.

The independence check must compare actual Analyst identity to actual Senior identity at every Senior boundary:

- Business early gate.
- Consolidated M3.7 ratification.
- Final D-2 lean ratification.

The check must reject if:

- model family and model are identical;
- normalized model family and normalized model are identical;
- the Senior response metadata contradicts the configured Senior identity;
- either side has missing identity in live mode;
- either side uses a deprecated alias that hides the real model;
- a test double declares a live-looking identity without response/request metadata support.

Provider equality is not a rejection condition by itself. Azure may be shared infrastructure for both Analyst and Senior; model-family independence is the invariant, infrastructure independence is not required. Offline identities remain allowed only when explicitly classified as offline. Offline Analyst and offline Senior may be distinct offline identities, but they must still not collapse to the same model family and model identity.

## Signing Metadata Plan

Extend Senior decision metadata so consumers can see who signed and with what model identity.

Minimum persisted fields:

- Existing `decided_by` string remains.
- `decided_by_provider`.
- `decided_by_deployment`.
- `decided_by_model`.
- `decided_by_model_family`.
- `decided_by_adapter`.
- Optional `decided_by_response_model`.
- Optional `decided_by_response_id`.

The final Handoff must surface the Senior identity that signed the final lean. Earlier decision packages must retain their own Senior identity metadata for audit.

## KILL Halt Plan

Introduce a typed `KillMemo` artifact and a shared helper that files it and returns the existing halted payload pattern.

Minimum schema:

```text
KillMemo:
  header
  ticker
  as_of
  status: "halted"
  halt_kind
  gate
  reason
  evidence_paths
  senior_identity
  replacement_required
  replacement_provided
```

Required KILL/halt cases for M4c:

1. Gate-card verdict `KILL`.
2. Business early gate `NO-GO`.
3. Final lean overturned without replacement.
4. Resolver routing-table or escalation-matrix audit violation.
5. Missing required live Senior identity metadata in live mode.

The filed `KillMemo` is the only terminal artifact for that halt branch. A final Handoff must not be filed after a KILL/halt branch.

## Revisit Trigger Plan

Complete the final Handoff schema with canonical `revisit_triggers`.

Rules:

1. `revisit_triggers` is required and non-empty.
2. C-5 `pass_falsifiers` must be included when present.
3. Final Handoffs must carry at least the falsifier-derived triggers.
4. Existing crux-derived and risk kill-metric triggers may remain, but they are not a substitute for falsifier-derived triggers when C-5 filed falsifiers.
5. If the code keeps `revisit_if` for compatibility, `revisit_triggers` is canonical and `revisit_if` must be a mirror or deprecated alias, not a divergent second source.

## Routing And Escalation Plan

Create `resolver.md` with:

- ordered routing table;
- required artifact inputs and outputs for each step;
- halt behavior for each step;
- Senior touchpoint classification;
- escalation matrix;
- route-manifest audit requirements;
- B-5 Base-Rate artifact handling;
- explicit non-DCF behavior for MRNA/rNPV route;
- parallelism status.

`resolver.py` must enforce this table, not merely link to it. The enforcement mechanism should be small and auditable:

- one typed route table or manifest in code;
- one route audit that checks planned steps, produced artifacts, Senior touchpoints, and halt branches;
- tests that fail when a step is added, removed, reordered, or bypasses required audit.

Parallelism is deferred for M4c unless a step is trivially safe:

- no shared mutable artifact writes;
- no ordering dependency;
- no Senior touchpoint;
- no audit dependency on a previous artifact.

If no step meets that bar, `resolver.md` must explicitly state parallelism is deferred because it is performance work, not correctness work.

## Implementation Steps

1. Define actual identity metadata models for Analyst and Senior adapters.
2. Add the Azure AI Foundry live Senior adapter that requests `SENIOR_DEPLOYMENT_NAME` and verifies the configured deployment model identifier is `DeepSeek-V4-Pro`, normalized to `deepseek-v4-pro`.
3. Preserve and identify the offline Senior adapter for tests/eval.
4. Replace declared-family checks with identity-based independence checks at all Senior boundaries.
5. Extend `SeniorDecisionPackage` and final Handoff signing metadata with provider/deployment/model-family/model identity fields.
6. Define `KillMemo` and the shared halted-return helper.
7. Convert business `NO-GO` and final-lean-overturned-without-replacement into `KillMemo` branches.
8. Add gate-card `KILL` halt handling.
9. Add resolver routing table and route audit enforcement.
10. Create `resolver.md` with the routing table, escalation matrix, KILL conditions, and parallelism decision.
11. Add canonical `revisit_triggers` to final Handoff and wire C-5 `pass_falsifiers`.
12. Add the standalone CLI/config selector needed to run the live Senior validation commands.
13. Add required tests and live validation commands.

## Risks And Decisions

- The identity check must not trust `model_family`, `model_handle`, `senior_handle`, or display names as proof of independence.
- The configured Azure Foundry deployment model identifier is intentionally specific because the DeepSeek alias names are deprecated on July 24, 2026. Compare model strings using normalized lowercase/stripped forms.
- KILL/halt branches must file one terminal memo and stop. They must not produce partial final Handoffs.
- Route enforcement should be data-driven enough to audit, but not turned into a separate orchestration framework.
- Parallelism is explicitly secondary. A slower serial resolver that is auditable is acceptable for M4c.

## Expected Result

After M4c, `analyze()` either returns a final Handoff with Senior provider/deployment/model-family/model signing metadata and falsifier-derived revisit triggers, or returns a halted payload containing a filed typed `KillMemo`. The resolver route and escalation behavior are documented in `resolver.md` and enforced by tests and runtime route audit.
