# M4c Control Flow - Requirements

## Functional Requirements

1. M4c must add a live Senior adapter for Azure AI Foundry serving DeepSeek V4 Pro.
2. The live Senior adapter must read `AZURE_FOUNDRY_ENDPOINT`, `AZURE_FOUNDRY_API_KEY`, and `SENIOR_DEPLOYMENT_NAME` from environment-backed config.
3. The live Senior adapter must reject `deepseek-chat`.
4. The live Senior adapter must reject `deepseek-reasoner`.
5. Deprecated alias rejection must mention the July 24, 2026 DeepSeek alias deprecation date.
6. The offline Senior adapter must remain available for tests and eval.
7. The offline Senior adapter must be clearly identified as offline in persisted identity metadata.
8. Senior/Analyst independence checks must use actual provider/deployment/model-family/model identity.
9. Independence checks must not rely on declared labels such as `model_family`, `model_handle`, or `senior_handle`.
10. Independence checks must run before the business early gate.
11. Independence checks must run before M3.7 consolidated ratification.
12. Independence checks must run before final D-2 lean ratification.
13. Same-model-family-and-same-model Senior/Analyst pairs must be rejected.
14. Missing identity metadata in live mode must be rejected.
15. Final Handoff signing metadata must include the Senior provider, deployment, model family, and model that signed the final lean.
16. Senior decision packages must persist provider/deployment/model-family/model identity for the Senior that made the decisions.
17. `analyze()` must still use the existing halted-path response pattern for halted runs.
18. Halted runs must file a typed `KillMemo` under the run directory.
19. A `KillMemo` branch must not file a final Handoff.
20. Final Handoffs must include canonical `revisit_triggers`.
21. Every final Handoff must include C-5 falsifier-derived revisit triggers.
22. `resolver.md` must exist and must document the routing table and escalation matrix.
23. `resolver.py` must enforce the routing table and escalation matrix.
24. Route enforcement must be tested.
25. Standalone `python -m resolver` must support selecting the live Azure Foundry Senior path used by validation.
26. Live Senior selection must fail closed if credentials or identity metadata are missing; it must not silently fall back to the offline Senior.
27. M4c must not introduce a server, queue, or external orchestration framework.

## Senior Identity Requirements

Add or equivalent identity metadata must support:

- `provider`;
- `deployment`;
- `model`;
- `normalized_model`;
- `model_family`;
- `adapter`;
- optional `response_model`;
- optional `response_id`;
- optional `request_model`;
- optional `metadata_source`.

Identity rules:

- Live Senior connection must use `AZURE_FOUNDRY_ENDPOINT`, `AZURE_FOUNDRY_API_KEY`, and `SENIOR_DEPLOYMENT_NAME` from environment-backed config.
- Azure Foundry endpoint, API key, and deployment name must never be hardcoded.
- The live Senior must request the configured deployment name exactly.
- The configured deployment's documented underlying model identifier must be verified as `DeepSeek-V4-Pro` at configuration level.
- Live Senior provider identity must serialize as `azure-foundry`.
- Live Senior model identity must serialize as the configured deployment's documented underlying model identifier, `DeepSeek-V4-Pro`, preserving Azure casing.
- Live Senior normalized model identity must serialize as `deepseek-v4-pro`.
- Live Senior model family must serialize as `deepseek-v4`.
- Live Senior deployment identity must serialize as `SENIOR_DEPLOYMENT_NAME`.
- Response metadata must be recorded verbatim in `response_model` when available.
- Azure Foundry may return `DeepSeek-V4-Pro` or the deployment name rather than DeepSeek's lowercase public model string in response metadata; either is valid when the normalized model matches `deepseek-v4-pro` or the value matches `SENIOR_DEPLOYMENT_NAME`.
- TODO: confirm from a live API response whether the response `model` field returns `DeepSeek-V4-Pro` or the deployment name.
- Response metadata may augment identity but must not replace the verified configured deployment model.
- Response metadata triggers fail-closed behavior only when it contradicts the configured identity after normalization.
- All identity comparisons involving model strings must normalize by stripping whitespace and lowercasing before matching.
- Deprecated alias checks must apply the same strip-and-lowercase normalization.
- Configured display labels are not identity evidence.
- Offline adapters must use provider `offline` or an equivalently unmistakable offline provider marker.
- Offline identities must never be serialized as if they were live Azure Foundry, DeepSeek, OpenAI, Anthropic, or another real provider.

## Independence Requirements

The independence check must accept actual Analyst and Senior identities and reject:

- same normalized model family and same normalized model;
- same normalized model family and same normalized response-confirmed model when response metadata unambiguously identifies the underlying model;
- live Senior missing provider;
- live Senior missing deployment;
- live Senior missing model;
- live Senior missing model family;
- live Analyst missing provider;
- live Analyst missing model;
- live Analyst missing model family;
- deprecated DeepSeek aliases on either side;
- identity provided only through legacy declared-family attributes;
- test doubles that pretend to be live without actual identity metadata.

The check may allow:

- distinct offline Analyst and offline Senior identities in offline tests;
- live Azure Foundry Senior with offline deterministic Analyst fixtures only when the Analyst identity is explicitly offline;
- shared cloud infrastructure providers when model families differ;
- distinct live model families or distinct live models when both identities are actual.

## Senior Decision Metadata Requirements

`SeniorDecisionPackage` or its successor must include:

- existing `decided_by`;
- `decided_by_provider`;
- `decided_by_deployment`;
- `decided_by_model`;
- `decided_by_model_family`;
- `decided_by_adapter`;
- optional `decided_by_response_model`;
- optional `decided_by_response_id`.

Final Handoff must expose the identity for the final lean signer. It may also include the earlier consolidated package identities in the data room, but the final lean signer must be directly inspectable without parsing nested artifacts.

Existing `ratified_as_is_rate` must remain meaningful and must be reported in validation for live AAPL and MRNA runs.

## KILL And Halt Requirements

M4c must define one typed terminal artifact for halted control flow: `KillMemo`.

`KillMemo` must include:

- `header`;
- `ticker`;
- `as_of`;
- `status`;
- `halt_kind`;
- `gate`;
- `reason`;
- `evidence_paths`;
- `senior_identity` when a Senior decision caused the halt;
- `replacement_required`;
- `replacement_provided`.

Required halt kinds:

- `gate_kill`;
- `business_no_go`;
- `senior_overturn_without_replacement`;
- `route_audit_violation`;
- `identity_audit_violation`.

Required KILL/halt branches:

1. Gate-card verdict is `KILL`.
2. Business early gate returns `NO-GO`.
3. Final lean is overturned without replacement.
4. Routing-table enforcement fails.
5. Escalation-matrix enforcement fails.
6. Live Senior identity metadata is missing or invalid.

Halt behavior:

- The memo must be filed before `analyze()` returns.
- The returned payload must include `status="halted"`.
- The returned payload must include the filed `kill_memo`.
- The returned payload must include the path to the filed memo.
- No final Handoff may be filed after a halt.
- Existing tests that assert halted behavior should migrate to the `KillMemo` shape.

## Handoff Revisit Trigger Requirements

The final Handoff schema must use canonical `revisit_triggers`.

Rules:

- `revisit_triggers` is required.
- `revisit_triggers` must be non-empty.
- C-5 `pass_falsifier` records must be converted into revisit trigger strings or structured trigger records.
- Falsifier-derived triggers must preserve metric, threshold, and check-by date when available.
- Edge crux-derived triggers may also be included.
- Risk kill-metric triggers may also be included.
- If `revisit_if` remains for backward compatibility, it must mirror `revisit_triggers`.
- A final Handoff with C-5 falsifiers omitted from `revisit_triggers` must fail validation.

## Resolver Documentation Requirements

Create `resolver.md` at the project root or another clearly linked canonical location. It must document:

- all resolver steps in order;
- step id;
- role type;
- required input artifacts;
- produced output artifacts;
- audit check before output is visible;
- halt behavior;
- Senior touchpoint classification;
- escalation owner;
- escalation condition;
- AAPL DCF route behavior;
- MRNA rNPV/non-DCF route behavior;
- parallelism decision.

The routing table must include at least:

- A-1 EDGAR;
- A-2 Price;
- A-3 Cost of Capital;
- B-1 Normalize;
- B-2 Spine;
- D-1 bare Handoff;
- C-1 Business;
- business early gate;
- B-4 Screens;
- B-5 Base-Rate;
- B-6 Method Router;
- B-3 DCF when routed;
- C-4 Scenarios;
- C-5 Edge/Cruxes;
- C-6 Risk;
- M3.7 consolidated ratification;
- D-2 Conviction;
- final lean ratification;
- D-3 Review Packager.

The escalation matrix must define at least:

- audit failure;
- missing source artifact;
- KILL gate;
- business NO-GO;
- unsupported valuation method;
- Senior identity conflict;
- Senior overturn without replacement;
- live Senior API failure;
- route-table mismatch.

## Resolver Enforcement Requirements

`resolver.py` must enforce the documented route.

Enforcement must check:

- required steps ran before dependent steps;
- required artifacts were filed;
- required audits ran before artifacts were consumed downstream;
- B-5 Base-Rate artifacts required by C-4 scenarios were filed and audited before scenario consumption;
- Senior touchpoints occurred only where the route allows;
- early gate happened exactly once on GO and NO-GO paths;
- consolidated M3.7 ratification happened exactly once on GO paths that reach synthesis;
- final lean ratification happened exactly once on final-Handoff paths;
- D-3 did not run on any halt path;
- non-DCF routes did not fabricate DCF-only artifacts;
- KILL/halt branches filed a `KillMemo`.

The enforcement mechanism must be covered by tests that fail on missing, reordered, or extra undocumented route steps.

## Parallelism Requirements

M4c does not need to implement parallelism.

If parallelism is implemented, each parallelized step must be proven trivially safe:

- no shared mutable writes;
- no ordering dependency;
- no dependency on an artifact produced by the other parallel step;
- no Senior touchpoint;
- no audit dependency.

If that proof is not straightforward, parallelism must be deferred and `resolver.md` must say it is deferred because it is performance work, not correctness work.

## Negative Requirements

- M4c must not trust declared model labels for independence.
- M4c must not silently downgrade from live Senior to offline Senior.
- M4c must not call deprecated DeepSeek aliases.
- M4c must not produce a final Handoff after a KILL/halt.
- M4c must not make routing enforcement doc-only.
- M4c must not add new Senior touchpoint classes beyond the existing gate/ratify pattern.
- M4c must not add calibration analytics beyond reporting existing ratification summary values for validation.

## Acceptance Criteria

- Live Senior adapter uses Azure Foundry environment config, requests `SENIOR_DEPLOYMENT_NAME`, and verifies the deployment model identifier is `DeepSeek-V4-Pro`, normalized to `deepseek-v4-pro`.
- Offline Senior remains available and identified.
- Same-model-family-and-model Senior/Analyst pairs are rejected by negative tests.
- AAPL live Senior run completes with real Senior ratification decisions.
- MRNA live Senior run completes with real Senior ratification decisions.
- Live AAPL and MRNA validation reports include `ratified_as_is_rate`.
- Gate-card `KILL` path files a `KillMemo` and returns a halted payload.
- Final-lean-overturned-without-replacement files a `KillMemo` and returns a halted payload.
- Final Handoff contains `revisit_triggers` with C-5 falsifier-derived triggers.
- `resolver.md` exists and matches enforced resolver behavior.
- Full pytest suite passes.
