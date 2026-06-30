# M3.4 Scenarios - Plan

## Objective

Build the `C-4 Scenarios` Analyst slice as an offline, fixture-backed skeleton.

M3.4 must produce a schema-valid scenario set with bear/base/bull assumption drafts from existing artifacts. Each scenario must be driver-tied, base-rate anchored, evidence-backed, period-consistent, method-router aware, and collected as independently Senior-owned ratifiables for later M3.7 ratification.

This milestone is the first real proof that M3.1 collection handles nested ratifiables: the scenario set contains multiple nested `AnalystDraft` values at distinct field paths, and each scenario probability must require its own Senior decision. A partial decision set must not make the package ratified.

## Scope

In scope:
- A `C-4 Scenarios` Analyst bundle under `skills/research/scenarios/`.
- Deterministic offline drafting from existing filed artifacts and frozen fixtures.
- Bear/base/bull scenario assumption drafts.
- Scenario probabilities represented as independently Senior-owned ratifiables.
- Reuse of M3.1 `AnalystDraft`, `EvidenceRef`, evidence audit, period-consistency audit, ratifiable collection, and Analyst bundle validation.
- Reuse of existing `B-5 Base-Rate`, `B-6 Method Router`, `ValuationRange`, and `ExpectationsLine`.
- Audit-enforced brakes for evidence support, period consistency, base-rate anchoring, probability distribution coherence, value ordering, driver-name binding, and method-router respect.
- Resolver GO-branch wiring after Moat and CapAlloc.
- Offline tests proving nested ratifiable collection, partial Senior decisions, and all fail-closed coherence checks.

Out of scope:
- `C-5 Edge & Cruxes`.
- `C-6 Risk`.
- M3.7 consolidated `Senior.ratify`.
- A second Senior touchpoint.
- Live LLM drafting.
- New valuation methods or valuation engines.
- New artifact contracts, primitive types, storage interfaces, or persistence mechanisms.
- New external dependencies.
- Prompt-only enforcement.

## Dependencies And Invariants

M3.4 depends on completed M2a, M2b, M3.1, M3.2, and M3.3:

- `ValuationRange`, `Scenario`, `DcfAssumption`, and `ExpectationsLine`.
- `lookup_base_rate` and `BaseRateResult`.
- `route_method` and `MethodDirective`.
- `AnalystDraft`, `EvidenceRef`, `ReviewItem`, `SeniorReviewPackage`, and collection.
- M3.1 evidence audit and no-bare-number audit.
- M3.3 period-consistency audit against stored source artifacts.
- M3.1 Analyst bundle validation.
- Existing offline fake LLM and fake Senior adapters.

Standing invariants:

1. Brakes are audit-enforced, not prompt-enforced.
2. The bundle must pass the M3.1 Analyst validator with `no_llm: false`, full file set, and ratifiable drafts instead of assertions.
3. The offline skeleton must be substantive: fixture-backed, schema-valid, evidence-backed scenario artifacts with resolvable, period-consistent refs.
4. Scenario probabilities must be coherent as a distribution.
5. Scenario values must be ordered bear < base < bull.
6. Scenario driver names must bind to actual valuation driver names consumed by `B-3 DCF` or the filed `ExpectationsLine`.
7. Every scenario assumption must carry a resolved `B-5 Base-Rate` anchor reference.
8. Scenarios must respect `B-6 Method Router` and must not force plain DCF drivers when the router selects a non-DCF method.

## Proposed Architecture

```text
analyze(ticker)
   |- existing M1/M2 path
   |- C-1 Business and early GO/NO-GO gate
   |- if GO:
   |    |- C-2 Moat
   |    |- C-3 CapAlloc
   |    |- B-4 Gate Card
   |    |- B-6 Method Directive
   |    |- B-3 ValuationRange + ExpectationsLine when method == DCF
   |    `- C-4 Scenarios
   |         |- reads filed valuation, expectations, base-rate, router, and prior analyst artifacts
   |         |- emits bear/base/bull nested AnalystDraft probability items
   |         |- verifies base-rate anchors resolve
   |         |- verifies driver names bind to actual valuation inputs
   |         |- verifies method directive is respected
   |         `- collects one ReviewItem per scenario probability
   `- if NO-GO: unchanged stop behavior
```

The scenario drafter may reuse existing M2a `ValuationRange.scenarios` values and assumptions as the deterministic starting point, but M3.4 must not treat the M2a placeholder probabilities as Senior decisions. The output must make each scenario probability an undecided `AnalystDraft` or M3.1-compatible nested ratifiable draft.

## Skill Bundle Created In M3.4

The bundle is an Analyst bundle (`no_llm: false`):

```text
skills/research/scenarios/
|-- SKILL.md
|-- scenarios.py
|-- prompt.md
|-- resolver.entry
`-- eval/
    |-- cases.jsonl
    `-- eval_scenarios.py
```

`test_integration.py` is not required because M3.4 is offline. Tests may live inside the bundle and/or under the project `tests/` tree, matching the existing M3.2/M3.3 pattern.

## Artifact Shape

M3.4 should define the narrowest scenario artifact needed to exercise the M3.1 contract without adding a new global filing contract.

Expected shape:

```text
ScenarioSetArtifact
|-- header
|-- ticker
|-- as_of
|-- method_directive_path
|-- valuation_range_path | null
|-- expectations_line_path | null
|-- scenarios
|   |-- bear
|   |   |-- name
|   |   |-- value
|   |   |-- assumptions
|   |   `-- probability: AnalystDraft
|   |-- base
|   `-- bull
`-- source_evidence_summary
```

Each scenario probability draft must:

- be independently nested at a distinct field path;
- carry the draft probability as a provenance-backed `Number` or an object containing one, never as a bare float;
- carry non-empty evidence refs;
- carry a resolved base-rate anchor reference;
- carry Senior checklist area and rationale;
- remain `needs_ratification`;
- have no `decision`, `decided_by`, or `final` value before M3.7.

Scenario assumptions may reuse existing `DcfAssumption` and `Number` values from `ValuationRange` where DCF is selected. If the router selects a non-DCF method, the artifact must not emit DCF-specific driver assumptions as if they applied; it may file a method-deferred scenario artifact that explains the non-DCF routing and carries evidence for the deferral.

## Audit Brakes

M3.4 must add deterministic audit behavior for scenario artifacts. These checks live in the analyst layer because they evaluate coherence of judgment drafts, but they are accountant-type checks: deterministic, fail-closed, and prompt-independent.

Required brakes:

1. Evidence support. Existing M3.1 evidence checks apply to every scenario probability draft.
2. Period consistency. Existing M3.3 period checks apply to every scenario evidence ref and must resolve against stored sources.
3. Multi-ratifiable collection. The collector must emit one `ReviewItem` per scenario probability at distinct stable field paths.
4. Partial Senior decisions. A package with only one scenario probability decided must remain unratified.
5. Probability distribution coherence. Draft probabilities must be finite, non-negative, not greater than 1, and sum to 1.0 within tolerance.
6. Value ordering. Scenario values must be ordered bear < base < bull.
7. Driver-name binding. Scenario drivers must map to actual driver names consumed by `B-3 DCF` or present in the filed `ExpectationsLine`, not a decorative or hardcoded-only vocabulary.
8. Base-rate anchors. Every scenario assumption must carry a `B-5 Base-Rate` anchor whose referenced artifact resolves and whose source fields match the scenario driver being checked.
9. Method-router respect. If the filed `MethodDirective.method` is not `DCF`, scenarios must not impose DCF drivers or force a DCF valuation frame.
10. No bare numeric probability drafts. The probability coherence audit must extract values from `Number`-backed draft payloads so existing M3.1 no-bare-number audit remains authoritative.

If any brake requires changing M3.1 contracts, implementation must stop and flag the contract gap rather than work around it with a parallel collection path.

## Implementation Steps

1. Fill `skills/research/scenarios/SKILL.md` from `specs/SKILL-template.md`.
2. Add the Analyst bundle file set: implementation, prompt, eval cases, eval runner, and resolver entry.
3. Define a narrow `ScenarioSetArtifact` by composing existing M3.1/M2a types.
4. Build deterministic fixture-backed scenario drafting from filed valuation, expectations, base-rate, method-router, and prior analyst artifacts.
5. Add fixture data for a valid DCF-routed AAPL scenario set with bear/base/bull probabilities summing to 1.0.
6. Add fixture data for a router-selected non-DCF name and prove scenarios do not force DCF drivers on it.
7. Add audit checks for probability distribution coherence.
8. Add audit checks for bear/base/bull value ordering.
9. Add audit checks for driver-name binding against actual filed `ValuationRange` and/or `ExpectationsLine` driver names.
10. Add audit checks requiring each scenario assumption to carry a resolved `B-5 Base-Rate` anchor.
11. Add audit checks requiring method-router respect.
12. Prove `collect_ratifiables` emits one review item per nested scenario probability with distinct stable ids.
13. Prove a partial Senior decision set cannot make the review package ratified.
14. Wire the resolver GO branch after Moat and CapAlloc to file and collect Scenarios without calling `Senior.ratify`.
15. Keep all tests offline, deterministic, and no-network.

## Risks And Decisions

- The highest-risk issue is accidentally modeling scenarios as one combined draft. M3.4 must prove each scenario probability is separately ratifiable.
- Driver-name binding must compare against actual filed valuation artifacts. A hardcoded allow-list can be a fallback only if it is derived from those artifacts or tested against the current `B-3` output shape.
- Base-rate checks must resolve real `BaseRateResult` references. Checking for a text field named `base_rate_check` is insufficient.
- Method-router respect must use a filed or constructed `MethodDirective`, not a string copied into prompt context.
- Existing `ValuationRange.Scenario.probability` uses `Ratifiable[float]` from M2a. M3.4 may wrap or translate those probabilities into M3.1 `AnalystDraft` review items, but must not invent a new ratification contract. If existing collection cannot support this, stop and flag the needed contract change.
- A non-DCF route is not a failure. It is a method-respect case where scenario drafting must avoid DCF-only drivers.

## Expected Result

After M3.4 implementation, offline `analyze("AAPL")` with the M3.2 GO fakes can:

- produce a filed, evidence-backed scenario set artifact;
- collect bear/base/bull scenario probabilities as separate undecided review items;
- prove partial Senior decisions leave the package unratified;
- reject incoherent probability distributions;
- reject bear/base/bull value-ordering violations;
- reject scenario drivers that do not bind to actual valuation inputs;
- reject missing or unresolvable base-rate anchors;
- respect the method router for DCF and non-DCF names;
- keep exactly one Senior touchpoint in this milestone: the existing M3.2 early gate.

## Pre-Implementation Self-Review

- Scope is limited to `C-4 Scenarios`.
- The plan reuses M3.1, M2a, M2b, M3.2, and M3.3 infrastructure.
- The plan does not add a new valuation engine, method, primitive, storage abstraction, or global contract.
- The plan makes all brakes audit-enforced and prompt-independent.
- The plan requires multi-ratifiable proof with one review item per scenario probability.
- The plan requires partial Senior decision failure.
- The plan requires driver-name binding against actual valuation artifacts.
- The plan requires base-rate anchors to resolve, not merely exist.
- The plan requires method-router respect for non-DCF assets.
- The plan defers live LLM drafting, C-5, C-6, M3.7 ratify, and all new external dependencies.
