# M4c Control Flow - Validation

## Technical Checks

Run offline checks:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver MRNA
```

Run live Senior checks only when Azure Foundry credentials are configured:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest -m live_senior
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL --senior azure-foundry
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver MRNA --senior azure-foundry
```

The full offline pytest command is required. Focused M4c tests are not sufficient to mark M4c complete.

## Required Unit Tests

1. Azure Foundry Senior adapter reads `AZURE_FOUNDRY_ENDPOINT`, `AZURE_FOUNDRY_API_KEY`, and `SENIOR_DEPLOYMENT_NAME` from environment-backed config.
2. Azure Foundry Senior adapter requests the configured deployment name exactly.
3. Azure Foundry Senior adapter verifies the configured deployment's documented underlying model identifier is `DeepSeek-V4-Pro`.
4. Azure Foundry Senior adapter rejects `deepseek-chat`.
5. Azure Foundry Senior adapter rejects `deepseek-reasoner`.
6. Alias rejection error mentions July 24, 2026.
7. Azure Foundry Senior adapter records response metadata verbatim in `response_model` when present.
8. Azure Foundry Senior adapter accepts response metadata that returns either `DeepSeek-V4-Pro` or the configured deployment name.
9. Azure Foundry Senior adapter normalizes model strings by stripping whitespace and lowercasing before identity comparisons.
10. Azure Foundry Senior adapter fails closed if response metadata contradicts the configured deployment identity after normalization.
11. Deprecated alias checks normalize model strings by stripping whitespace and lowercasing.
12. Offline Senior exposes offline provider/model-family/model identity.
13. Offline Senior identity is persisted in offline decision packages.
14. Independence check accepts distinct offline Analyst and offline Senior identities.
15. Independence check accepts an offline Analyst fixture and live Azure Foundry Senior identity.
16. Independence check rejects same normalized model family and same normalized model.
17. Independence check allows shared provider/cloud infrastructure when model families differ.
18. Independence check rejects missing live Senior provider.
19. Independence check rejects missing live Senior deployment.
20. Independence check rejects missing live Senior model.
21. Independence check rejects missing live Senior model family.
22. Independence check rejects missing live Analyst provider.
23. Independence check rejects missing live Analyst model.
24. Independence check rejects missing live Analyst model family.
25. Independence check rejects identity supplied only by legacy declared-family attributes.
26. `SeniorDecisionPackage` validates required Senior identity fields.
27. `SeniorDecisionPackage` still validates `ratified_as_is_rate`.
28. Final Handoff validates required final lean Senior provider/model-family/model metadata.
29. `KillMemo` validates required fields.
30. `KillMemo` rejects empty reason.
31. `KillMemo` rejects missing evidence paths when the halt depends on filed artifacts.
32. Final Handoff rejects missing `revisit_triggers`.
33. Final Handoff rejects empty `revisit_triggers`.
34. Final Handoff rejects omitted C-5 falsifier-derived triggers.
35. If `revisit_if` remains, final Handoff rejects divergence between `revisit_if` and `revisit_triggers`.

## Required Resolver Tests

1. GO-path AAPL route records every documented route step in order.
2. GO-path MRNA route records every documented route step in order and does not fabricate DCF artifacts.
3. Business early gate runs exactly once.
4. M3.7 consolidated ratification runs exactly once on GO paths.
5. Final lean ratification runs exactly once on final-Handoff paths.
6. No Senior touchpoint occurs outside the route table.
7. B-5 Base-Rate artifacts required by C-4 scenarios are filed before C-4 consumes them.
8. Route audit fails if a C-4 scenario references a missing or unaudited B-5 artifact.
9. D-2 runs after M3.7 ratification.
10. D-3 runs after final lean ratification.
11. D-3 does not run on business `NO-GO`.
12. D-3 does not run on gate-card `KILL`.
13. D-3 does not run when final lean is overturned without replacement.
14. Route audit fails if a required step is omitted.
15. Route audit fails if a required step is reordered across a dependency.
16. Route audit fails if an undocumented Senior touchpoint is added.
17. Route audit fails if a required artifact is not filed before downstream consumption.
18. Route audit failure files a `KillMemo` and returns a halted payload.
19. Escalation-matrix failure files a `KillMemo` and returns a halted payload.
20. Business `NO-GO` files a `KillMemo` and returns the halted payload shape.
21. Final-lean-overturned-without-replacement files a `KillMemo` and returns the halted payload shape.
22. Gate-card `KILL` files a `KillMemo` and returns the halted payload shape.
23. Halted payload includes `kill_memo_path`.
24. Halted payload includes the filed `kill_memo`.
25. Halted path does not file `final_handoff.json`.
26. Final Handoff includes final lean signer provider/deployment/model-family/model identity.
27. Final Handoff includes C-5 falsifier-derived `revisit_triggers`.

## Required Negative-Path Tests

M4c introduces control-flow failure modes. Each must have at least one test:

1. Same-family Senior/Analyst rejected:
   - Configure Analyst and Senior actual identity with the same normalized model family and same normalized model.
   - Expect the independence check to reject before the Senior call.
2. Same family/response-model rejected:
   - Configure different declared labels but response metadata that unambiguously confirms the same underlying model family and model.
   - Expect the independence check to reject.
3. Declared-label-only identity rejected:
   - Provide only `model_family` or `model_handle`.
   - Expect live independence validation to reject it.
4. Deprecated alias rejected:
   - Configure Azure Foundry Senior deployment, documented model, or model family with `deepseek-chat` or `deepseek-reasoner`.
   - Expect adapter construction or first call to fail closed.
5. Missing live metadata rejected:
   - Simulate live Senior without provider/deployment/model/model-family identity.
   - Expect `identity_audit_violation` and no final Handoff.
6. Live selector fallback rejected:
   - Invoke the standalone live Senior selector with missing credentials or missing identity metadata.
   - Expect an explicit failure or `identity_audit_violation`, never offline Senior fallback.
7. Gate KILL:
   - Force or fixture a gate-card `KILL` verdict.
   - Expect `KillMemo`, halted payload, and no final Handoff.
8. Final lean overturned without replacement:
   - Use a Senior test double that overturns `final_lean` with no replacement.
   - Expect `KillMemo`, halted payload, and no final Handoff.
9. Route mismatch:
   - Remove or reorder a route step in a test route manifest.
   - Expect route audit failure and `KillMemo`.
10. B-5 route omission:
   - Remove the B-5 Base-Rate step or required filed B-5 artifact from a route manifest used by C-4.
   - Expect route audit failure before final Handoff.
11. Falsifier omission:
   - Build a final Handoff from an edge artifact containing `pass_falsifier` records but remove those triggers.
   - Expect validation failure.
12. Handoff signing metadata omission:
   - Remove final lean signer provider/deployment/model-family/model fields.
   - Expect validation failure.

## Live Senior Validation

Before marking M4c complete, run end-to-end live Senior validation on both AAPL and MRNA.

Required live run assertions:

- The Senior adapter used provider `azure-foundry`.
- The requested deployment was `SENIOR_DEPLOYMENT_NAME`.
- The configured deployment's documented model identifier was verified as `DeepSeek-V4-Pro`.
- The configured deployment model normalized to `deepseek-v4-pro`.
- No deprecated alias was used.
- Actual response metadata was captured verbatim in `response_model` when available.
- Response metadata returning `DeepSeek-V4-Pro` was accepted after normalization.
- Response metadata returning the deployment name was accepted when it matched `SENIOR_DEPLOYMENT_NAME`.
- Live validation confirmed the response `model` field returns `DeepSeek-V4-Pro`; record that value verbatim as `response_model`.
- Senior identity metadata was persisted in decision packages.
- Final Handoff signing metadata includes provider/deployment/model-family/model.
- `ratified_as_is_rate` is reported for the consolidated M3.7 package.
- `ratified_as_is_rate` is reported for final lean ratification.
- The run produced real Senior ratification decisions, not offline deterministic decisions.

Required report fields for each ticker:

```text
ticker
senior_provider
senior_deployment
senior_model_family
senior_model
senior_response_model
m3_7_required_count
m3_7_ratified_as_is_count
m3_7_modified_count
m3_7_rejected_count
m3_7_ratified_as_is_rate
final_lean_outcome
final_lean_ratified_as_is_rate
handoff_or_kill_memo_path
```

The live validation output must include AAPL and MRNA. If a live Senior run halts because the Senior rejects or overturns a decision, the run may still satisfy live validation only if the halt is represented by a valid `KillMemo` and the ratification summary is reported.

## Manual Validation

Before marking M4c complete:

1. Confirm `resolver.md` exists.
2. Confirm `resolver.md` lists the route table and escalation matrix.
3. Confirm route behavior is enforced in code, not only documented.
4. Confirm all Senior boundaries call the identity-based independence check.
5. Confirm no Senior boundary relies on `model_family`, `model_handle`, or `senior_handle` as identity proof.
6. Confirm the live Senior uses Azure Foundry provider identity, requests `SENIOR_DEPLOYMENT_NAME`, and verifies the deployment model identifier is `DeepSeek-V4-Pro`, normalized to `deepseek-v4-pro`.
7. Confirm deprecated DeepSeek aliases are blocked.
8. Confirm offline Senior remains available for tests/eval and is serialized as offline.
9. Confirm standalone live Senior selection cannot silently fall back to offline Senior.
10. Confirm B-5 Base-Rate appears in `resolver.md` and route audit enforcement where C-4 depends on it.
11. Confirm final Handoff exposes final lean signer provider/deployment/model-family/model.
12. Confirm `revisit_triggers` include C-5 falsifier-derived triggers.
13. Confirm business `NO-GO`, gate `KILL`, and final-lean-overturn-without-replacement all use `KillMemo`.
14. Confirm no final Handoff is filed on halted paths.
15. Confirm parallelism is either absent or documented as trivially safe.

## Output Checks

For live `analyze("AAPL")`:

- Returns a final Handoff or a valid `KillMemo` halt.
- Uses Azure Foundry with the configured Senior deployment verified as `DeepSeek-V4-Pro`, normalized to `deepseek-v4-pro`.
- Persists Senior identity metadata.
- Reports M3.7 `ratified_as_is_rate`.
- Reports final lean `ratified_as_is_rate`.
- Includes `revisit_triggers` if a final Handoff is produced.

For live `analyze("MRNA")`:

- Returns a final Handoff or a valid `KillMemo` halt.
- Uses Azure Foundry with the configured Senior deployment verified as `DeepSeek-V4-Pro`, normalized to `deepseek-v4-pro`.
- Does not fabricate DCF-only artifacts.
- Persists Senior identity metadata.
- Reports M3.7 `ratified_as_is_rate`.
- Reports final lean `ratified_as_is_rate`.
- Includes falsifier-derived `revisit_triggers` if a final Handoff is produced.

For forced KILL:

- Returns `status="halted"`.
- Files `kill_memo.json` or another documented `KillMemo` path under the run directory.
- Returned payload includes the filed memo.
- No `final_handoff.json` exists.

## Closure Criteria

M4c can be marked complete in `specs/roadmap.md` only after:

- the M4c spec files are current;
- `resolver.md` exists and is accurate;
- live Azure Foundry Senior wiring is implemented with environment config and deployment-model verification for `DeepSeek-V4-Pro`, normalized to `deepseek-v4-pro`;
- deprecated aliases are rejected;
- identity-based independence checks replace declared-label checks;
- Senior decision metadata includes provider/deployment/model-family/model identity;
- `KillMemo` is the typed halt artifact for required halt branches;
- final Handoff has canonical `revisit_triggers`;
- C-5 falsifier-derived triggers are present in every final Handoff;
- routing table and escalation matrix are enforced by tests and runtime audit;
- required negative-path tests pass;
- full offline pytest passes;
- live Senior AAPL and MRNA validations have been run and reported.
