# M3.1 Analyst Contracts And Infrastructure — Plan

## Objective

Create the typed and testable foundation for M3 before any Analyst bundle is implemented. M3.1 defines the artifacts, ratification collection mechanics, audit rules, and deterministic fake adapters that later M3 slices will use.

This slice should make it possible to construct, audit, store, and collect M3-shaped draft artifacts offline. It must not call live LLMs, invoke a real Senior, or implement the six Analyst skills yet.

## Scope

In scope:
- Pydantic artifacts for the M3 Analyst and Senior-review layer.
- Shared evidence and review-item shapes used by later Analyst bundles.
- Audit checks for Analyst invariants: evidence required, ratifiables required, no bare numeric boundary values, and no final decisions without Senior action.
- Ratifiable collection utilities that can walk M2b/M3 artifacts and build a review package.
- Senior decision package validation that rejects missing decisions.
- Deterministic fake `LLM` and fake `Senior` adapters for offline tests.
- Analyst bundle-shape validation rules that later M3 bundles can reuse.
- Unit tests for all of the above.

Out of scope:
- `C-1 Business`, `C-2 Moat`, `C-3 CapAlloc`, `C-4 Scenarios`, `C-5 Edge & Cruxes`, or `C-6 Risk` bundle implementation.
- Analyst prompts and eval cases beyond placeholder validation helpers for future bundle shape.
- Resolver calls to `Senior.gate` or `Senior.ratify`.
- Live LLM calls.
- Final M4 synthesis, conviction scoring, signed Handoff, or Review Packager behavior.
- New valuation engines.

## Prerequisites

M3.1 depends on:
- M0 primitives and interfaces: `Header`, `Number`, `Ratifiable`, `LLM`, `Senior`, and `Storage`.
- M1/M2 artifact patterns in `skills/m1_artifacts.py`.
- Existing audit/storage patterns in `skills/audit.py`.
- Existing bundle conventions from `specs/SKILL-template.md`.

M3.1 must not duplicate primitive, config, interface, or storage definitions.

## Proposed Architecture

M3.1 adds the contract layer that later M3 slices plug into:

```text
M2b artifacts + future M3 artifacts
   ├─ audit_analyst_artifact(...)
   ├─ collect_ratifiables(...)
   │    └─ SeniorReviewPackage
   └─ apply_senior_decisions(...)
        └─ SeniorDecisionPackage
```

The resolver does not need to invoke this path yet. M3.1 only proves the contracts can stand on their own and can be validated with deterministic tests.

## Artifact Contracts

Add or prepare pydantic artifacts for:
- `EvidenceRef`: source label, artifact path or filing reference, excerpt or summary, and optional provenance.
- `ReviewItem`: stable id, source artifact, field path, draft value, evidence, and ratification status.
- `BusinessBrief`: future output of `C-1`.
- `MoatAssessment`: future output of `C-2`.
- `CapitalAllocationAssessment`: future output of `C-3`.
- `ScenarioDraftPackage`: future output of `C-4`.
- `EdgeStatement`: future output of `C-5`.
- `RiskKillSheet`: future output of `C-6`.
- `EarlyGatePackage`: future input to `Senior.gate`.
- `EarlyGateResult`: future output of `Senior.gate`.
- `SeniorReviewPackage`: consolidated ratification input for M3.7.
- `SeniorDecisionPackage`: structured Senior decisions returned by `Senior.ratify`.

Where schemas overlap `specs/filing-rules.md`, M3.1 should use additive pydantic models rather than changing old M1/M2 outputs destructively.

## Implementation Steps

1. Add a clearly named M3 artifact module, likely `skills/m3_artifacts.py`, that imports M0 primitives.
2. Define shared evidence and review-item models.
3. Define the future Analyst artifact models with strict pydantic validation.
4. Define early gate and Senior review package models.
5. Add helper functions to serialize M3 artifacts using the existing `model_to_payload` pattern.
6. Add `collect_ratifiables` to recursively find `Ratifiable` values and produce stable review items.
7. Add Senior decision validation that requires a decision for every required review item.
8. Extend audit code or add M3-specific audit helpers for Analyst artifact and Senior package invariants.
9. Add deterministic fake `LLM` and fake `Senior` test adapters under the test surface, not production runtime defaults.
10. Add bundle-shape validation helpers for future Analyst bundles: `SKILL.md`, `prompt.md`, `eval/cases.jsonl`, eval runner, `resolver.entry`, and `no_llm: false`.
11. Add focused unit tests for model validation, ratifiable collection, audit rejection, storage round-trip, fake adapters, and bundle-shape validation.

## Risks And Decisions

- M3.1 should not overfit the future prompts. It should define contracts and validation, not Analyst prose behavior.
- The review-item ids must be stable because M3.7 will need to map Senior decisions back to draft fields.
- Recursive ratifiable collection must avoid silently collecting unrelated internal test data. It should include source artifact and field path metadata.
- Fake adapters are test tools, not production fallbacks. Production Analyst execution should still require explicit injected dependencies.
- M3.1 should avoid broad resolver changes. The next slice, M3.2, owns early gate resolver wiring.

## Expected Result

After M3.1 implementation:
- M3 artifact contracts exist and are schema-validated.
- Analyst-style artifacts can be audited for evidence and ratification invariants.
- Ratifiable values can be collected into a `SeniorReviewPackage`.
- Senior decisions can be validated for completeness.
- Offline tests can use deterministic fake `LLM` and fake `Senior` adapters.
- No Analyst bundle has been implemented yet.
- The roadmap remains positioned for M3.2 Business + early gate as the next slice.
