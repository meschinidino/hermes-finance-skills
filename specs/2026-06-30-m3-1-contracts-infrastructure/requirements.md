# M3.1 Analyst Contracts And Infrastructure — Requirements

## Functional Requirements

1. M3.1 must define pydantic contracts for the M3 Analyst and Senior-review layer.
2. M3.1 must reuse existing M0 primitives instead of redefining them.
3. M3.1 must not implement any Analyst bundle.
4. M3.1 must not call a live LLM.
5. M3.1 must not call a real Senior.
6. M3.1 must not wire `Senior.gate` or `Senior.ratify` into `resolver.analyze`.
7. Every M3.1 artifact must use strict pydantic validation.
8. Every M3.1 artifact must carry a `Header` when it represents a fileable artifact.
9. Every numeric field crossing a skill boundary must use `Number`.
10. Any non-fact `Number` must include a derivation.
11. Any judgment field that will require Senior sign-off must use `Ratifiable`.
12. Every `Ratifiable` must include non-empty evidence.
13. M3.1 must provide a shared evidence reference model.
14. M3.1 must provide a shared review-item model with a stable id and source field path.
15. M3.1 must provide a `SeniorReviewPackage` model.
16. M3.1 must provide a `SeniorDecisionPackage` model.
17. `SeniorDecisionPackage` validation must reject missing decisions for required review items.
18. M3.1 must provide a utility to collect ratifiables from nested pydantic artifacts.
19. Ratifiable collection must preserve source artifact identity and field path.
20. Ratifiable collection must produce stable review item ids.
21. M3.1 must provide audit helpers for Analyst artifact invariants.
22. M3.1 must reject Analyst artifacts with missing evidence.
23. M3.1 must reject Analyst artifacts that pass bare numeric values where `Number` is required.
24. M3.1 must reject Senior review packages with no review items.
25. M3.1 must reject Senior decision packages with undecided required items.
26. M3.1 must provide deterministic fake `LLM` and fake `Senior` adapters for tests.
27. Fake adapters must live in tests or a test-only helper surface.
28. Fake adapters must not become production defaults.
29. M3.1 must provide reusable validation for future Analyst bundle shape.
30. Analyst bundle-shape validation must require `SKILL.md`, implementation file, `prompt.md`, `eval/cases.jsonl`, eval runner, and `resolver.entry`.
31. Analyst bundle-shape validation must reject `no_llm: true` for Analyst bundles.

## Artifact Requirements

### EvidenceRef

`EvidenceRef` must include:
- source label;
- artifact path, filing reference, or external source reference;
- excerpt or summary;
- optional `Provenance`;
- enough information for a reviewer to trace the claim.

### ReviewItem

`ReviewItem` must include:
- stable id;
- source artifact name;
- source field path;
- draft value;
- evidence list;
- whether the item is required;
- ratification status.

### Future Analyst Artifacts

M3.1 must define contracts for future artifacts without implementing their producing skills:
- `BusinessBrief`;
- `MoatAssessment`;
- `CapitalAllocationAssessment`;
- `ScenarioDraftPackage`;
- `EdgeStatement`;
- `RiskKillSheet`.

The contracts must reflect the roadmap shape enough that later slices do not need to redesign the review package.

### Early Gate Artifacts

M3.1 must define:
- `EarlyGatePackage`;
- `EarlyGateResult`.

These contracts must support M3.2 but must not wire the gate into the resolver yet.

### Senior Review Artifacts

`SeniorReviewPackage` must include:
- header;
- ticker;
- as-of date;
- review items;
- source artifact summary.

`SeniorDecisionPackage` must include:
- header;
- ticker;
- as-of date;
- decisions keyed by stable review item id;
- decided_by;
- validation that every required review item has a decision.

## Non-Functional Requirements

- M3.1 must stay portable and standalone.
- M3.1 must keep runtime state under `/data` when storage is exercised.
- M3.1 must not add heavy dependencies.
- M3.1 must run offline.
- M3.1 tests must not require network, live LLM credentials, or a human Senior.
- M3.1 must follow existing pydantic v2 style.
- M3.1 must follow existing audit and storage patterns.
- M3.1 must not alter M0-M2b behavior except by adding reusable contracts and tests.

## Test Requirements

M3.1 must include tests for:
- constructing each M3.1 artifact model;
- rejecting missing evidence;
- rejecting missing ratifiables where required;
- rejecting bare numeric values where `Number` is required;
- collecting nested ratifiables from a sample artifact;
- preserving source field paths during collection;
- producing stable review item ids;
- rejecting an empty `SeniorReviewPackage`;
- rejecting incomplete Senior decisions;
- accepting a complete Senior decision package;
- storage round-trip of at least one M3.1 artifact;
- fake `LLM` deterministic response behavior;
- fake `Senior.gate` deterministic behavior;
- fake `Senior.ratify` deterministic behavior;
- Analyst bundle-shape validation happy path;
- Analyst bundle-shape validation failure for missing `prompt.md`;
- Analyst bundle-shape validation failure for missing eval files;
- Analyst bundle-shape validation failure for `no_llm: true`.

## Acceptance Criteria

- Roadmap lists M3.1-M3.7 as separate slices.
- M3.1 spec contains only contracts and infrastructure scope.
- M3.1 pydantic contracts exist.
- M3.1 audit helpers reject missing evidence and incomplete decisions.
- Ratifiable collection works on nested artifacts.
- Deterministic fake `LLM` and fake `Senior` adapters support offline tests.
- Future Analyst bundle-shape validation exists and is tested.
- Existing M0-M2b tests still pass.
- `analyze("AAPL")` behavior remains unchanged by M3.1 except for harmless imports or additive contracts.
