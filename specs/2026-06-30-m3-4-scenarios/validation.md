# M3.4 Scenarios - Validation

## Technical Checks

After implementation, run:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/research/scenarios
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

The `--no-sync` flag is intentional. M3.4 validation must run offline and must not require PyPI access, EDGAR, FRED, Damodaran, price feeds, live LLM credentials, network access, a human Senior, or a consolidated Senior ratification pass.

## Required Scenario Artifact Tests

1. Valid scenario artifact constructs from deterministic offline inputs.
2. Valid scenario artifact passes M3.1 evidence audit.
3. Valid scenario artifact passes M3.3 period-consistency audit.
4. Valid scenario artifact includes `Header`, ticker, and as-of date.
5. Valid scenario artifact includes exactly bear, base, and bull scenarios.
6. Valid scenario artifact preserves bear/base/bull order.
7. Each scenario includes one or more driver-tied assumptions.
8. Each scenario includes a scenario value with `Number` provenance.
9. Each scenario includes an independently ratifiable probability draft.
10. Every scenario probability draft is an `AnalystDraft` or M3.1-compatible nested ratifiable draft.
11. Every scenario probability draft has `needs_ratification` semantics.
12. Every scenario probability draft carries the probability as a provenance-backed `Number` or object containing one.
13. Bare numeric probability drafts are rejected by M3.1 no-bare-number audit.
14. Every scenario probability draft has non-empty evidence refs.
15. Every scenario probability draft has a resolvable evidence target.
16. Every scenario probability draft has Senior-checklist area and rationale.
17. Every scenario probability remains undecided before M3.7.
18. Scenario artifact references a method directive.
19. DCF-routed scenario artifact references valuation and expectations artifacts when available.
20. Required scenario fields are not placeholder-only strings.
21. Fixture with sufficient scenario evidence produces an audited scenario artifact.
22. Fixture with missing required scenario evidence fails closed.
23. Deterministic fake LLM output, if used by the Scenarios drafter seam, is identical across repeated runs.
24. Scenarios drafter performs no network access.

## Required Multi-Ratifiable Tests

1. Valid scenario artifact collects into exactly one review item per scenario probability.
2. Bear probability review item has a distinct stable id.
3. Base probability review item has a distinct stable id.
4. Bull probability review item has a distinct stable id.
5. Review item ids are stable across repeated deterministic runs.
6. Each collected review item preserves source artifact identity.
7. Each collected review item preserves its distinct source field path.
8. Each collected review item preserves evidence refs.
9. Each collected review item preserves Senior-checklist mapping.
10. Each scenario probability requires its own Senior decision.
11. A package with only base decided remains unratified.
12. A package with only bear and base decided remains unratified.
13. A package with all required scenario probabilities decided is ratified.
14. Collection does not call `Senior.ratify`.
15. Test assertions prove the milestone exercises per-scenario Senior decisions rather than one combined decision.
16. If this cannot pass with existing M3.1 collection contracts, implementation stops and flags the contract change instead of flattening.

## Required Probability Coherence Tests

1. Probabilities that sum to 1.0 within tolerance pass.
2. Distribution bear=0.25, base=0.50, bull=0.25 passes.
3. Distribution bear=0.3, base=0.6, bull=0.5 is rejected.
4. Negative bear probability is rejected.
5. Negative base probability is rejected.
6. Negative bull probability is rejected.
7. Probability greater than 1 is rejected.
8. Missing probability draft is rejected.
9. Non-finite probability is rejected.
10. Probability coherence failure reports the offending condition.

## Required Value-Ordering Tests

1. Bear value < base value < bull value passes.
2. Bear value equal to base value is rejected.
3. Bear value greater than base value is rejected.
4. Base value equal to bull value is rejected.
5. Base value greater than bull value is rejected.
6. Value ordering compares scenario `Number.value` values.
7. Value-ordering failure identifies the offending scenario order.

## Required Driver-Name Binding Tests

1. Scenario drivers matching filed `ValuationRange.scenarios[].assumptions[].driver` pass.
2. Scenario drivers matching filed `ExpectationsLine.implied` keys pass where applicable.
3. Scenario driver not present in actual filed valuation or expectations artifacts is rejected.
4. Decorative driver name that does not connect to valuation inputs is rejected.
5. Driver binding failure identifies the invalid driver.
6. Test setup mutates the filed valuation artifact driver names and proves the audit follows the artifact, not only a hardcoded list.
7. Test assertions prove driver-name binding compares against actual `B-3`/`ExpectationsLine` driver names.

## Required Base-Rate Anchor Tests

1. Scenario assumption with a resolved `B-5 BaseRateResult` anchor passes.
2. Scenario assumption without a base-rate anchor is rejected.
3. Scenario assumption with an unresolvable base-rate anchor is rejected.
4. Scenario assumption whose base-rate anchor resolves to a non-`B-5` artifact is rejected.
5. Scenario assumption whose base-rate metric conflicts with the scenario driver is rejected when a direct mapping exists.
6. Resolved base-rate anchor must include a probability `Number`.
7. Resolved base-rate anchor must include a citation.
8. A string saying "base-rate checked" without a resolved anchor is rejected.
9. Base-rate failure identifies the scenario and driver.
10. Test assertions prove base-rate checks resolve real references rather than checking field presence.

## Required Method-Router Tests

1. DCF method directive allows DCF scenario drivers.
2. Scenario artifact with missing method directive reference is rejected.
3. Scenario artifact with unresolvable method directive reference is rejected.
4. Scenario artifact whose method directive resolves to a non-`B-6` artifact is rejected.
5. Non-DCF method directive rejects DCF-only scenario drivers.
6. Optionality/pre-revenue fixture classified as non-DCF is not forced into plain DCF.
7. Non-DCF fixture may produce a method-deferred scenario artifact.
8. Method-router failure identifies the selected method and offending DCF driver.
9. Test assertions prove method-router checks resolve real directives rather than checking a copied field.

## Required Bundle-Validation Tests

1. The real `skills/research/scenarios/` bundle passes M3.1 Analyst-shaped bundle validation.
2. `SKILL.md` declares `type: analyst`.
3. `SKILL.md` declares `no_llm: false`.
4. `SKILL.md` declares an LLM dependency.
5. `SKILL.md` declares ratifiable draft output contracts.
6. `SKILL.md` does not declare a final assertion output contract.
7. Bundle validation fails if `prompt.md` is removed or absent in a test copy.
8. Bundle validation fails if `eval/cases.jsonl` is removed or absent in a test copy.
9. Bundle validation fails if `eval/eval_scenarios.py` is removed or absent in a test copy.
10. Bundle validation fails if the output contract is changed to a bare assertion in a test copy.
11. Bundle validation fails if `no_llm` changes to `true` in a test copy.

## Required Resolver Integration Tests

1. `analyze("AAPL")` reaches Scenarios after the M3.2 early gate GO path in offline fake configuration.
2. `analyze("AAPL")` reaches Scenarios after Moat and CapAlloc.
3. `analyze("AAPL")` does not run Scenarios after an M3.2 NO-GO stop.
4. `analyze("AAPL")` files or returns the scenario artifact.
5. `analyze("AAPL")` audits the scenario artifact before collection.
6. Scenario audit failure prevents scenario ratifiable collection.
7. Filed scenario artifact survives storage round-trip.
8. Offline resolver run calls no live LLM.
9. Offline resolver run calls no real human Senior.
10. Offline resolver run does not call a second `Senior.gate`.
11. Offline resolver run does not call `Senior.ratify`.
12. Repeated offline resolver runs produce deterministic scenario drafts.

## Manual Validation

Before marking M3.4 complete:

1. Confirm only `C-4 Scenarios` was implemented.
2. Confirm no `C-5` or `C-6` Analyst bundle was implemented.
3. Confirm no consolidated M3.7 `Senior.ratify` behavior was added.
4. Confirm no second Senior touchpoint was added.
5. Confirm no live LLM call was added.
6. Confirm no real human Senior call is required for tests.
7. Confirm no new M3 contracts were invented.
8. Confirm no new storage abstraction or persistence mechanism was added.
9. Confirm Scenarios drafts reuse M3.1 `AnalystDraft` or compatible M3.1 draft infrastructure.
10. Confirm scenario evidence support is enforced by audit.
11. Confirm `prompt.md` has no enforcement role beyond bundle shape and eval documentation.
12. Confirm period-consistency audit compares claimed period to resolved source period.
13. Confirm base-rate anchors resolve to real `B-5` artifacts.
14. Confirm method-router checks resolve to real `B-6` directives.
15. Confirm driver-name binding compares against actual filed valuation or expectations artifacts.
16. Confirm multi-ratifiable collection emits one item per scenario probability.
17. Confirm partial Senior decisions do not mark the package ratified.
18. Confirm runtime artifacts under `/data` are not committed.

## Document Validation

Before implementation:

1. Confirm this spec lives under `specs/2026-06-30-m3-4-scenarios/`.
2. Confirm the triplet contains exactly `plan.md`, `requirements.md`, and `validation.md`.
3. Confirm the triplet scopes only M3.4: `C-4 Scenarios`.
4. Confirm the triplet specifies offline deterministic drafting and defers live LLM drafting.
5. Confirm the triplet requires reuse of M3.1 infrastructure.
6. Confirm the triplet requires reuse of `B-5 Base-Rate`.
7. Confirm the triplet requires reuse of `B-6 Method Router`.
8. Confirm the triplet requires reuse of `ValuationRange` and `ExpectationsLine`.
9. Confirm the triplet does not require new valuation engines, methods, contracts, storage, or dependencies.
10. Confirm the triplet makes evidence support audit-enforced, not prompt-enforced.
11. Confirm the triplet requires Analyst-shaped bundle validation.
12. Confirm the triplet requires multi-ratifiable proof.
13. Confirm the triplet requires partial-decision rejection.
14. Confirm the triplet requires probability coherence rejection.
15. Confirm the triplet requires value-ordering rejection.
16. Confirm the triplet requires driver-name binding rejection.
17. Confirm the triplet requires base-rate-anchor rejection.
18. Confirm the triplet requires method-router-respect rejection.
19. Confirm the triplet does not include C-5, C-6, M3.7 ratify, live LLM drafting, or a second Senior touchpoint.

## Responsive And Accessibility Checks

Not applicable in M3.4. There is no UI surface.

## Closure Criteria

M3.4 can be marked complete in `specs/roadmap.md` only after:

- the M3.4 spec files are current;
- the `C-4 Scenarios` bundle exists and passes Analyst-shaped bundle validation;
- scenario drafting is deterministic and offline;
- scenario artifacts are schema-valid and evidence-backed;
- scenario probability drafts collect as separate undecided review items;
- partial Senior decisions cannot mark scenario probabilities ratified;
- incoherent probabilities fail audit;
- bear/base/bull value-ordering violations fail audit;
- unbound scenario drivers fail audit;
- missing or unresolvable base-rate anchors fail audit;
- non-DCF router directives are respected;
- full offline pytest passes;
- `python -m resolver AAPL` passes in the offline fake configuration.

## Pre-Landing Self-Review

Before landing implementation, explicitly answer:

1. Did the multi-ratifiable test genuinely exercise per-scenario Senior decisions rather than one combined decision?
2. Did partial Senior decisions fail to mark the package ratified?
3. Did driver-name binding compare against actual `B-3`/`ExpectationsLine` driver names rather than only a hardcoded list?
4. Did base-rate checks resolve real `B-5 BaseRateResult` references rather than checking a field is present?
5. Did method-router checks resolve real `B-6 MethodDirective` references rather than checking a copied field?
6. Did all coherence checks fail closed through audit, not prompt text?
7. Did the bundle pass M3.1 Analyst validation with `no_llm: false` and full file set?
8. Did the resolver path preserve exactly one Senior touchpoint for this milestone?
9. Was anything waved through? If yes, document it before marking M3.4 complete.
