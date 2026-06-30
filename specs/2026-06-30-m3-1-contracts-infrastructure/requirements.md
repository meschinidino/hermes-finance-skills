# M3.1 Analyst Contracts And Infrastructure — Requirements

## Functional Requirements

1. M3.1 must define strict pydantic contracts for the M3 Analyst and Senior-review layer.
2. M3.1 must reuse existing M0 primitives, including `Header`, `Provenance`, `Number`, and `Ratifiable`.
3. M3.1 must reuse existing `Storage` for artifact persistence tests.
4. M3.1 must not implement any C-1 through C-6 Analyst bundle.
5. M3.1 must not call a live LLM.
6. M3.1 must not call a real Senior.
7. M3.1 must not wire `Senior.gate` or `Senior.ratify` into `resolver.analyze`.
8. Every fileable M3.1 artifact must carry a `Header`.
9. Every numeric field crossing a skill boundary must use `Number`.
10. Any non-fact `Number` must include derivation under the existing primitive rules.
11. Any Analyst judgment must be represented as a draft needing ratification, not as an asserted final claim.
12. Every Analyst draft must include non-empty evidence references.
13. Analyst audit must reject any claim whose evidence references are missing or empty.
14. Analyst audit must reject any `EvidenceRef` whose trace target is empty, null, or otherwise unresolvable.
15. An evidence ref being present is insufficient; it must point somewhere via artifact path, filing reference, or external source reference.
16. Analyst audit must reject any bare numeric boundary value where a `Number` is required.
17. Analyst audit must reject any Analyst artifact that asserts a final judgment without a Senior decision.
18. M3.1 must provide a shared `EvidenceRef` model.
19. M3.1 must provide a shared base ratifiable Analyst draft type.
20. The base Analyst draft type must carry evidence refs and Senior-checklist mapping.
21. The base Analyst draft type must be general enough for Business, Moat, Capital Allocation, Scenarios, Edge & Cruxes, and Risk artifacts.
22. M3.1 must provide a shared `ReviewItem` model with stable id, source artifact, source field path, draft value, evidence refs, checklist mapping, requiredness, and decision state.
23. `ReviewItem` must not include a stored `ratified` boolean.
24. M3.1 must provide a `SeniorReviewPackage` model.
25. `SeniorReviewPackage` must reject empty review-item lists.
26. `SeniorReviewPackage` must preserve ticker, as-of date, header, review items, and source artifact summary.
27. `SeniorReviewPackage` must not include a stored `ratified` boolean or any setter that marks the package ratified.
28. M3.1 must provide a `SeniorDecisionPackage` model.
29. `SeniorDecisionPackage` must carry decisions keyed by stable review item id.
30. `SeniorDecisionPackage` must not include a stored `ratified` boolean or any setter that marks the decision package ratified.
31. Ratified status must be a derived property only, computed from every required `ReviewItem` having a Senior decision.
32. A ratified-with-missing-decision state must be unrepresentable in the contract, not merely caught by an optional validation call.
33. M3.1 must provide a recursive ratifiable collection utility.
34. Ratifiable collection must preserve source artifact identity.
35. Ratifiable collection must preserve nested source field paths.
36. Ratifiable collection must produce stable ids for the same artifact and field path.
37. Ratifiable collection must preserve evidence refs and Senior-checklist mapping.
38. M3.1 must provide a synthetic test-only multi-ratifiable artifact shape with multiple nested `AnalystDraft`s at distinct field paths.
39. The synthetic multi-ratifiable artifact must not implement a C-4 Scenarios bundle.
40. Collection from the synthetic multi-ratifiable artifact must emit one `ReviewItem` per nested draft with distinct stable ids.
41. Senior decision completeness for the synthetic multi-ratifiable artifact must require a separate decision for each collected `ReviewItem`.
42. M3.1 must provide deterministic fake `LLM` and fake `Senior` adapters for offline tests.
43. Fake adapters must live under a test-only helper surface, not as production defaults.
44. The offline test harness must wire two different deterministic fakes: one for Analyst `LLM`, one for `Senior`.
45. No M3.1 artifact, collector, or audit contract may assume the Senior shares the Analyst model handle.
46. A future resolver must be able to inject a Senior from a different model family than the Analyst without changing M3.1 contracts.
47. M3.1 tests must prove the fake `LLM` handle and fake `Senior` handle are distinct.
48. The fake Senior must be constructible with zero reference to any `LLM` object.
49. The fake Senior constructor must not take, store, or require an LLM handle.
50. M3.1 must provide bundle-validation rules for Accountant-shaped and Analyst-shaped skill bundles.
51. Accountant-shaped bundles must declare no LLM dependency and `no_llm: true`.
52. Analyst-shaped bundles must declare an LLM dependency and `no_llm: false`.
53. Analyst-shaped bundles must declare their output contract shape as ratifiable Analyst drafts, such as `AnalystDraft` or another `needs_ratification` contract.
54. Analyst assertion detection must be declaration-based: bundle validation checks declared output contract metadata and fails any Analyst bundle declaring a bare assertion or final-value output type.
55. Assertion detection must not depend on executing the bundle, calling an LLM, or inspecting generated prose.
56. Analyst-shaped bundles must emit `needs_ratification` drafts, never final assertions.
57. Bundle validation must fail closed when an Accountant bundle declares an LLM dependency.
58. Bundle validation must fail closed when an Analyst bundle declares an assertion output rather than a ratifiable draft output.
59. Analyst bundle validation must require `SKILL.md`, implementation file, `prompt.md`, `eval/cases.jsonl`, eval runner, and `resolver.entry`.
60. M3.1 must not alter M0-M2b resolver behavior.

## Artifact Requirements

### EvidenceRef

`EvidenceRef` must include:
- source label;
- artifact path, filing reference, or external source reference;
- excerpt or summary;
- optional `Provenance`;
- enough information for a reviewer to trace the claim.

At least one trace target must be non-empty and resolvable. A blank string, null value, or metadata-only reference must be rejected by Analyst audit.

### AnalystDraft

The base Analyst draft type must include:
- draft value or structured claim;
- evidence refs;
- Senior-checklist area or key;
- Senior-checklist rationale;
- requiredness;
- `needs_ratification` semantics;
- optional Senior decision fields that are empty until a Senior decision package is applied.

It must reject empty evidence refs. It must not permit a final asserted judgment without Senior decision metadata.

### ReviewItem

`ReviewItem` must include:
- stable id;
- source artifact name;
- source field path;
- draft value;
- evidence refs;
- Senior-checklist mapping;
- whether the item is required;
- Senior decision fields.

It must not include a settable `ratified` field. Ratified status is derived from whether a required item has a Senior decision.

### SeniorReviewPackage

`SeniorReviewPackage` must include:
- header;
- ticker;
- as-of date;
- review items;
- source artifact summary.

It must reject empty item lists.

It must not include a stored or settable `ratified` field. Package-level ratified status is derived from required item decisions only.

### SeniorDecisionPackage

`SeniorDecisionPackage` must include:
- header;
- ticker;
- as-of date;
- decisions keyed by stable review item id;
- decided_by;
- validation against required item ids.

It must not include a stored or settable `ratified` field. Completeness is derived by comparing required review item ids to decisions. A missing required decision means the derived status is not ratified; there is no representable contradictory state.

## Forward-Compatibility Requirements

The base Analyst draft type must cover these future artifact needs without redesign:

- Business: evidence-backed business-quality claims and early GO/NO-GO concerns.
- Moat: durability claims, competitive evidence, and rejection of unsupported moat assertions.
- Capital Allocation: capital allocation quality drafts and management behavior evidence.
- Scenarios: assumption drafts tied to drivers, base-rate checks, and Senior-owned probabilities.
- Edge & Cruxes: steelman, counterparty, variant view, catalysts, and exactly three falsifiable cruxes.
- Risk: premortem, bear narrative, two-bucket risk register, tail risks, bear-case value, and kill metric.

The common requirement is that each judgment is a draft with evidence refs, checklist mapping, source path, requiredness, and Senior decision state.

M3.1 must test this against a synthetic, test-only scenario-shaped artifact with multiple nested drafts. The fixture should model the structural pressure of bear/base/bull driver assumptions without becoming a C-4 bundle. Each nested draft must collect to a distinct review item and require its own Senior decision.

## Non-Functional Requirements

- M3.1 must run fully offline.
- M3.1 tests must not require network, live LLM credentials, or human Senior input.
- M3.1 must keep dependencies small and must not add heavy runtime dependencies.
- M3.1 must stay portable and standalone.
- M3.1 must follow existing pydantic v2 style.
- M3.1 must follow existing audit and storage patterns.
- Runtime state created during validation must stay under `/data` or test temp directories.
- There must be no flag-and-pass path for missing evidence or missing Senior decisions.
- There must be no stored `ratified` field or setter that can create contradictory ratification state.
- Failures must be explicit validation or audit failures, not warnings.

## Test Requirements

M3.1 must include tests for:
- constructing a valid M3 artifact;
- valid M3 artifact passing Analyst audit;
- artifact with an unsupported claim and no evidence ref being rejected by audit;
- artifact with an `EvidenceRef` whose trace target is blank or null being rejected by audit;
- bare numeric boundary values being rejected where `Number` is required;
- recursive collection finding nested ratifiable drafts;
- collection preserving source artifact identity and field path;
- collection producing stable ids across repeated runs;
- collection preserving evidence refs and Senior-checklist mapping;
- synthetic multi-ratifiable artifact collecting one review item per nested draft with distinct stable ids;
- synthetic multi-ratifiable artifact requiring one Senior decision per collected required item;
- empty `SeniorReviewPackage` being rejected;
- review and decision packages exposing no settable `ratified` field;
- derived ratified status remaining false when one required item lacks a Senior decision;
- incomplete `SeniorDecisionPackage` being rejected;
- complete `SeniorDecisionPackage` being accepted;
- deterministic fake `LLM` returning identical content across runs;
- deterministic fake `Senior.gate` returning identical decisions across runs;
- deterministic fake `Senior.ratify` returning identical decisions across runs;
- fake `LLM` handle and fake `Senior` handle being distinct objects or identities;
- fake `Senior` being constructible without passing or storing any fake `LLM` object;
- Accountant-shaped bundle with no LLM dependency passing validation;
- Analyst-shaped bundle with LLM dependency and ratifiable draft output passing validation;
- Accountant-shaped bundle declaring an LLM dependency failing validation;
- Analyst-shaped bundle declaring a bare assertion output contract failing validation;
- Analyst bundle missing `prompt.md` failing validation;
- Analyst bundle missing eval files failing validation;
- full construct -> audit -> store -> collect path running offline with no network and deterministic identical fake outputs across runs.

## Acceptance Criteria

- The M3.1 triplet scopes only contracts and infrastructure.
- Requirements encode the independence seam between `LLM` and `Senior`.
- Requirements encode separate Accountant and Analyst role shapes.
- Requirements encode structural ratification as derived-only and unrepresentable when incomplete.
- M3.1 implementation can later prove artifacts are constructible, auditable, storable through existing `Storage`, and collectible into a review package.
- Existing M0-M2b behavior remains unchanged until later milestones wire resolver behavior.

## Pre-Landing Self-Review

- Requirement 1, independence seam: Covered by requirements 42-49 and test cases for distinct fake handles plus fake Senior construction with no LLM reference. No contract may depend on a shared model handle.
- Requirement 2, role shapes: Covered by requirements 50-59 and role-shape tests for mixed Accountant/Analyst failures.
- Requirement 3, structural ratification: Covered by requirements 22-32 plus tests proving no `ratified` setter exists. Ratified state is derived-only, so incomplete ratification is unrepresentable rather than validation-caught.
- Validation cases requested by the milestone are all represented in Test Requirements.
- Forward compatibility for M3.4 Scenarios is covered by draft value plus checklist mapping plus evidence refs, and exercised by the synthetic multi-ratifiable test that is explicitly in scope because it is not a C-4 bundle. Senior-owned probabilities fit as required review items. M3.5 Edge also fits because steelman, counterparty, cruxes, and catalysts are structured draft values with required evidence refs. The assertion-detection mechanism is declaration-based output-contract validation. No known base-type gap is being waved through.
