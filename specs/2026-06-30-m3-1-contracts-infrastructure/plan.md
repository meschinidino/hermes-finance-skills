# M3.1 Analyst Contracts And Infrastructure — Plan

## Objective

Define the contract layer that makes M3 Analyst work auditable before any Analyst bundle exists. M3.1 should let the repo construct typed M3-shaped artifacts, audit evidence-backed drafts, store them through the existing `Storage` interface, and collect required Senior decisions into a review package while running fully offline.

This milestone is infrastructure only. It does not add C-1 through C-6 Analyst bundle behavior, does not call a live LLM, does not call a real Senior, and does not change resolver routing or escalation.

## Scope

In scope:
- Typed pydantic contracts for M3 artifact foundations and Senior-review packages.
- A shared ratifiable draft shape for Analyst claims, evidence references, and Senior-checklist mapping.
- A recursive ratifiable collector that preserves source artifact identity, field path, evidence, and required-vs-optional status.
- Audit helpers for Analyst artifacts and Senior review packages.
- Structural ratification where ratified status is a derived property only, computed from every required review item having a Senior decision. No stored `ratified` boolean or setter exists.
- Deterministic fake `LLM` and fake `Senior` adapters for offline tests, wired as distinct handles.
- Bundle-validation rules for both Accountant-shaped and Analyst-shaped skill bundles.
- Tests that prove fail-closed behavior for unsupported claims, mixed role shapes, incomplete decisions, and deterministic offline paths.

Out of scope:
- Any C-1, C-2, C-3, C-4, C-5, or C-6 bundle implementation.
- Any real LLM call or real Senior call.
- Resolver routing, parallelism, early gate wiring, consolidated ratification wiring, or escalation changes.
- New persistence mechanisms. M3.1 reuses existing `Storage`, JSON artifact conventions, and M0 primitives.
- New EDGAR, WACC, valuation, method-routing, or synthesis behavior.

## Dependencies And Invariants

M3.1 reuses:
- `Header`, `Provenance`, `Number`, and `Ratifiable` primitives from M0.
- `Storage` from the existing injection interface.
- Existing `model_to_payload` and audit/storage patterns where appropriate.
- Existing skill-bundle layout conventions from `specs/SKILL-template.md`.

M3.1 must not duplicate M0 primitives, create a second storage abstraction, or introduce host-specific Hermes coupling.

## Proposed Architecture

```text
Future M3 Analyst artifact
   ├─ contains AnalystDraft / ratifiable fields
   ├─ references EvidenceRef entries
   └─ passes audit_analyst_artifact(...)

audit_analyst_artifact(...)
   ├─ rejects unsupported claims
   ├─ rejects evidence refs with no resolvable trace target
   ├─ rejects bare numbers at boundaries
   └─ rejects asserted Analyst judgments

collect_ratifiables(...)
   ├─ walks nested pydantic artifacts
   ├─ emits stable ReviewItem ids
   └─ builds SeniorReviewPackage

SeniorDecisionPackage
   └─ carries decisions; ratified status is derived, never stored
```

The contracts deliberately keep `LLM` and `Senior` independent. Analyst drafting depends on an injected `LLM`; Senior gate and ratification depend on an injected `Senior`. The artifacts, collector, and audit helpers must accept the products of those roles without assuming that both roles share a model provider, client object, identity, or handle. The fake Senior used in tests must be constructible with zero reference to any LLM object; if a Senior constructor takes or stores an LLM handle, the seam is already coupled and M3.1 fails.

## Base Types To Design

### EvidenceRef

Shared evidence reference for Analyst claims. It should include:
- source label;
- one trace target, such as artifact path, filing reference, or external source reference;
- excerpt or summary;
- optional `Provenance`;
- enough stable metadata for a reviewer to find the source again.

Presence is not enough. An `EvidenceRef` with blank or null trace targets is unresolvable and must be rejected by Analyst audit.

### AnalystDraft

Base ratifiable draft type for M3 Analyst claims. It should carry:
- the draft value or structured claim;
- evidence references, not just free-text evidence;
- Senior-checklist mapping, such as checklist area, required decision kind, and review rationale;
- `needs_ratification = true` by default;
- no final assertion unless a Senior decision package later supplies a decision.

This base type is the Analyst analog of the provenance invariant: unsupported claims do not exist. There is no flag-and-pass path for claims without evidence linkage.

### ReviewItem

Collected review item for the Senior. It should include:
- stable id;
- source artifact name;
- source field path;
- draft value;
- evidence references;
- Senior-checklist mapping;
- whether the item is required;
- Senior decision fields.

It must not include a stored `ratified` boolean. If callers need ratified status, it is derived from the item or package decisions.

### SeniorReviewPackage

Consolidated package of required and optional review items. It should include:
- header;
- ticker;
- as-of date;
- source artifact summary;
- review items.

An empty package is invalid. A package may be constructed before decisions, but there is no settable field that can mark it ratified. Ratified status is derived from the package's required review items and the associated Senior decisions.

### SeniorDecisionPackage

Structured Senior decisions keyed by stable review item id. It should include:
- header;
- ticker;
- as-of date;
- decided_by;
- decision map keyed by review item id;
- validation against a corresponding review package or required-item list.

It must not include a stored `ratified` boolean. Completeness is derived by comparing required review item ids to the decision map. A ratified-with-missing-decision state is unrepresentable because nothing can store or set that state.

## Forward Compatibility

M3.1 designs the base ratifiable draft type but does not implement the C-* artifact specializations.

The base type must cover:
- M3.2 Business: business-quality claims, GO/NO-GO concerns, and source-backed evidence snippets.
- M3.3 Moat: moat durability drafts, competitive evidence, and Senior checklist mapping for unsupported-moat rejection.
- M3.3 Capital Allocation: capital allocation quality drafts, management behavior evidence, and ratifiable judgment calls.
- M3.4 Scenarios: bear/base/bull assumption drafts, driver-tied evidence, base-rate checks, and Senior-owned probabilities.
- M3.5 Edge & Cruxes: no-trade steelman, counterparty, variant view, catalysts, and exactly three falsifiable crux drafts.
- M3.6 Risk: premortem, bear case, two-bucket risk register, tail risks, bear-case value, and kill metric drafts.
- M3.7 Ratify aggregation: collection of all required M2b/M3 ratifiables into one consolidated package.

The general shape is enough because all of those artifacts need the same cross-cutting contract: draft value, evidence references, checklist mapping, requiredness, source path, and Senior decision state.

M3.1 must exercise the M3.4-style nested shape with a synthetic test-only artifact, not a C-4 bundle. That fixture should contain multiple nested AnalystDrafts at distinct field paths, such as bear/base/bull driver assumptions. The collector must emit one `ReviewItem` per nested draft with distinct stable ids, and `SeniorDecisionPackage` completeness must require a separate decision for each.

## Role Shape Validation

Bundle validation must encode two distinct shapes:
- Accountant-shaped bundle: declares no LLM dependency, is deterministic, emits computed artifacts or facts, and uses `no_llm: true`.
- Analyst-shaped bundle: declares an LLM dependency, emits evidence-backed drafts needing ratification, provides prompt/eval surfaces, and uses `no_llm: false`.

Assertion detection is declaration-based. Bundle metadata must declare the output contract shape. An Analyst bundle whose declared output contract is a bare assertion or final-value artifact fails validation without executing the bundle or reading generated prose.

Validation fails closed on mixed shapes:
- Accountant bundle with an LLM dependency fails.
- Analyst bundle that emits assertions rather than ratifiable drafts fails.
- Analyst bundle missing `prompt.md`, eval cases, eval runner, implementation file, `SKILL.md`, or `resolver.entry` fails.

## Implementation Steps

1. Add an M3 artifact contract module that imports M0 primitives.
2. Define `EvidenceRef`, `AnalystDraft`, `ReviewItem`, `SeniorReviewPackage`, and `SeniorDecisionPackage`.
3. Add collector utilities that recursively find ratifiable Analyst drafts and produce stable review item ids.
4. Add Analyst audit helpers that reject unsupported claims, unresolvable evidence refs, bare boundary numbers, asserted Analyst judgments, and empty packages.
5. Add deterministic fake `LLM` and fake `Senior` adapters under the test-only surface.
6. Add bundle-shape validation helpers for Accountant and Analyst bundles.
7. Add offline tests for construction, audit, storage, collection, distinct fake handles, fake Senior construction without an LLM, synthetic multi-ratifiable collection, role-shape failures, and deterministic replay.

## Expected Result

After M3.1, the repo has the contract and validation foundation for Analyst slices. M3 artifacts can be constructed, audited, serialized through existing storage, and collected into a Senior review package offline. The next implementation slice remains M3.2 Business + early gate.

## Pre-Landing Self-Review

- Independence seam: The plan keeps `LLM` and `Senior` as separate injection points and requires a test with two distinct deterministic handles.
- Independence seam tightened: The fake Senior must be constructible with no LLM object, so the M3.1 seam cannot bake in shared model-family coupling.
- Role shapes: The plan makes Accountant and Analyst bundle shapes mutually exclusive and requires fail-closed mixed-shape tests.
- Assertion detection mechanism: Named as declaration-based output-contract validation, not bundle execution or content inspection.
- Structural ratification: The plan requires no stored `ratified` boolean and no setter. Ratified status is derived from required review item decisions, so a ratified-with-missing-decision state is unrepresentable.
- Evidence resolvability: The plan rejects evidence refs whose trace target is blank or null; populated-looking hollow evidence is not accepted.
- Validation cases: The plan covers valid artifact audit, unsupported-claim rejection, unresolvable-evidence rejection, incomplete ratification unrepresentability, multi-ratifiable scenario-shape collection, role-shape failures, and deterministic offline construct-audit-store-collect.
- Forward compatibility: The base type appears sufficient for M3.4 Scenarios because assumptions, probabilities, base-rate checks, and driver evidence can all be represented as multiple nested draft values plus evidence refs plus checklist mapping; the synthetic multi-ratifiable test is present and in scope because it is not a C-4 bundle. It also appears sufficient for M3.5 Edge because cruxes and counterparty claims can be represented as structured draft values with required evidence and checklist areas. No waved-through implementation details are hidden in this plan; specialization details are intentionally deferred to M3.2-M3.7.
