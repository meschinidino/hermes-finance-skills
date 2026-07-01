# M3.5 Edge & Cruxes - Validation

## Technical Checks

After implementation, run:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/research/edge_cruxes
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

The `--no-sync` flag is intentional. M3.5 validation must run offline and must not require PyPI access, EDGAR, FRED, Damodaran, price feeds, live LLM credentials, network access, a human Senior, or a consolidated Senior ratification pass.

## Required Artifact Tests

1. Valid Edge & Cruxes artifact constructs from deterministic offline inputs.
2. Valid artifact passes M3.1 evidence audit.
3. Valid artifact passes M3.3 period-consistency audit.
4. Valid artifact includes `Header`, ticker, and as-of date.
5. Valid artifact includes source artifact references.
6. Valid artifact includes a no-trade steelman draft.
7. Valid artifact includes a counterparty draft.
8. Valid artifact includes a structural-mispricing draft.
9. Valid artifact includes a variant-view draft.
10. Valid artifact includes catalysts.
11. Valid edge-asserted artifact includes exactly three edge cruxes.
12. Valid artifact includes source evidence summary.
13. Every Analyst draft has non-empty evidence refs.
14. Every Analyst draft has resolvable evidence refs.
15. Every Analyst draft has Senior checklist area and rationale.
16. Every Analyst draft remains undecided before M3.7.
17. Required fields are not placeholder-only strings.
18. Draft payloads with bare numeric values are rejected where `Number` is required.
19. Fixture with sufficient evidence produces an audited artifact.
20. Fixture with missing required evidence fails closed.
21. Deterministic fake LLM output, if used by the drafter seam, is identical across repeated runs.
22. Edge & Cruxes drafter performs no network access.

## Required Steelman Tests

1. Non-empty no-trade steelman passes.
2. Steelman with evidence support passes.
3. Empty steelman is rejected.
4. Placeholder steelman is rejected.
5. Purely bullish steelman is rejected.
6. Steelman without a pass, uncertainty, downside, opportunity-cost, or market-efficiency argument is rejected.
7. Steelman failure identifies the offending field.

## Required Counterparty Tests

1. Plausible counterparty with mechanism and evidence passes.
2. Empty counterparty is rejected.
3. "No one" and trivial variants are rejected.
4. "Nobody" and trivial variants are rejected.
5. Contemptuous counterparties are rejected.
6. Circular "the market" counterparties without mechanism are rejected.
7. Counterparty without evidence is rejected.
8. Counterparty failure identifies the offending condition.

## Required Structural Mispricing Tests

1. Structural-mispricing draft with valid mechanism and persistence reason passes.
2. Explicit no-structural-edge/pass framing with evidence passes.
3. Structural-mispricing draft that asserts edge without a mechanism is rejected.
4. Structural-mispricing draft that asserts edge without a persistence reason is rejected.
5. Empty structural-mispricing draft is rejected.
6. Placeholder structural-mispricing draft is rejected.
7. Structural-mispricing failure identifies the offending condition.

## Required Variant View Tests

1. Evidence-backed variant view passes.
2. Explicit fairly-priced/pass view with evidence passes.
3. Empty variant view is rejected.
4. Unsupported variant view is rejected.
5. Generic market-misunderstanding language without evidence is rejected.
6. Variant-view failure identifies the offending condition.

## Required Catalyst Tests

1. Concrete catalyst with timing passes.
2. Multiple concrete catalysts pass.
3. Empty catalyst list is rejected.
4. Catalyst without timing or observation window is rejected.
5. Generic "market realizes value" catalyst is rejected.
6. Catalyst without evidence is rejected.
7. Catalyst failure identifies the offending condition.

## Required Crux Tests

1. Edge asserted with exactly three `edge_crux` records passes.
2. Edge asserted with fewer than three edge cruxes is rejected.
3. Edge asserted with more than three edge cruxes is rejected.
4. Edge asserted with any `pass_falsifier` is rejected.
5. No-edge/pass with zero cruxes passes.
6. No-edge/pass with a well-formed `pass_falsifier` passes.
7. No-edge/pass with a malformed `pass_falsifier` is rejected.
8. No-edge/pass with any `edge_crux` is rejected.
9. Filed crux with claim, kind, metric, threshold direction, threshold value, check-by date, and evidence passes.
10. Filed crux missing claim is rejected.
11. Filed crux missing metric is rejected.
12. Filed crux missing threshold direction is rejected.
13. Filed crux missing threshold value is rejected.
14. Filed crux missing check-by date is rejected.
15. Filed crux missing evidence or explicit missing-data gap is rejected.
11. Falsifiability is not accepted based on keywords in free text.
12. Duplicate cruxes are rejected.
18. Crux not connected to filed artifacts or explicit missing-data gap is rejected.
19. Crux failure identifies the offending crux.

## Required Ratifiable Collection Tests

1. Valid artifact collects into a `SeniorReviewPackage`.
2. Review item ids are stable across repeated deterministic runs.
3. Each collected review item preserves source artifact identity.
4. Each collected review item preserves source field path.
5. Each collected review item preserves evidence refs.
6. Each collected review item preserves Senior checklist mapping.
7. Collected items remain undecided before M3.7.
8. Collection does not call `Senior.ratify`.
9. Package is not treated as final Senior approval in M3.5.

## Required Bundle-Validation Tests

1. The real `skills/research/edge_cruxes/` bundle passes M3.1 Analyst-shaped bundle validation.
2. `SKILL.md` declares `type: analyst`.
3. `SKILL.md` declares `no_llm: false`.
4. `SKILL.md` declares an LLM dependency.
5. `SKILL.md` declares ratifiable draft output contracts.
6. `SKILL.md` does not declare a final assertion output contract.
7. Bundle validation fails if `prompt.md` is removed or absent in a test copy.
8. Bundle validation fails if `eval/cases.jsonl` is removed or absent in a test copy.
9. Bundle validation fails if `eval/eval_edge_cruxes.py` is removed or absent in a test copy.
10. Bundle validation fails if the output contract is changed to a bare assertion in a test copy.
11. Bundle validation fails if `no_llm` changes to `true`.

## Required Resolver Integration Tests

1. `analyze("AAPL")` reaches Edge & Cruxes after the M3.2 early gate GO path.
2. `analyze("AAPL")` reaches Edge & Cruxes after Scenarios.
3. `analyze("AAPL")` does not run Edge & Cruxes after an M3.2 NO-GO stop.
4. `analyze("AAPL")` files or returns the Edge & Cruxes artifact.
5. `analyze("AAPL")` audits the artifact before collection.
6. Edge & Cruxes audit failure prevents ratifiable collection.
7. Filed artifact survives storage round-trip.
8. Offline resolver run calls no live LLM.
9. Offline resolver run calls no real human Senior.
10. Offline resolver run does not call `Senior.gate`.
11. Offline resolver run does not call `Senior.ratify`.
12. Repeated offline resolver runs produce deterministic drafts.

## Manual Validation

Before marking M3.5 complete:

1. Confirm only `C-5 Edge & Cruxes` was implemented.
2. Confirm no `C-6 Risk` bundle was implemented.
3. Confirm no consolidated M3.7 `Senior.ratify` behavior was added.
4. Confirm no second Senior touchpoint was added.
5. Confirm no live LLM call was added.
6. Confirm no real human Senior call is required for tests.
7. Confirm no new M3 contracts were invented.
8. Confirm no new storage abstraction or persistence mechanism was added.
9. Confirm Edge & Cruxes drafts reuse M3.1 `AnalystDraft` or compatible M3.1 draft infrastructure.
10. Confirm evidence support is enforced by audit.
11. Confirm `prompt.md` has no enforcement role beyond bundle shape and eval documentation.
12. Confirm period-consistency audit compares claimed period to resolved source period.
13. Confirm counterparty rejection catches trivial and contemptuous text.
14. Confirm structural-mispricing rejection catches edge assertions without mechanism or persistence.
15. Confirm explicit no-structural-edge/pass framing is accepted when evidence-backed.
16. Confirm exactly-three edge-crux enforcement is deterministic for edge assertions.
16a. Confirm no-edge/pass does not manufacture mandatory cruxes and only audits filed pass-falsifiers.
17. Confirm crux falsifiability is field-based, not keyword-based.
18. Confirm runtime artifacts under `/data` are not committed.

## Document Validation

Before implementation:

1. Confirm this spec lives under `specs/2026-07-01-m3-5-edge-cruxes/`.
2. Confirm the triplet contains exactly `plan.md`, `requirements.md`, and `validation.md`.
3. Confirm the triplet scopes only M3.5: `C-5 Edge & Cruxes`.
4. Confirm the triplet specifies offline deterministic drafting and defers live LLM drafting.
5. Confirm the triplet requires reuse of M3.1 infrastructure.
6. Confirm the triplet requires reuse of completed M3.2 through M3.4 artifacts.
7. Confirm the triplet does not require new valuation engines, methods, contracts, storage, or dependencies.
8. Confirm the triplet makes evidence support audit-enforced, not prompt-enforced.
9. Confirm the triplet requires Analyst-shaped bundle validation.
10. Confirm the triplet requires no-trade steelman enforcement.
11. Confirm the triplet requires non-trivial counterparty enforcement.
12. Confirm the triplet requires structural mispricing as its own draft with a no-edge/pass escape valve.
13. Confirm the triplet requires exactly three field-falsifiable edge cruxes only when an edge is asserted.
14. Confirm the triplet does not include C-6, M3.7 ratify, live LLM drafting, or a second Senior touchpoint.

## Responsive And Accessibility Checks

Not applicable in M3.5. There is no UI surface.

## Closure Criteria

M3.5 can be marked complete in `specs/roadmap.md` only after:

- the M3.5 spec files are current;
- the `C-5 Edge & Cruxes` bundle exists and passes Analyst-shaped bundle validation;
- drafting is deterministic and offline;
- Edge & Cruxes artifacts are schema-valid and evidence-backed;
- all Edge & Cruxes drafts collect as undecided review items;
- malformed steelman, counterparty, structural-mispricing, variant-view, catalyst, and crux drafts fail audit;
- exactly three edge cruxes are enforced for edge assertions;
- zero-or-more pass-falsifiers are allowed for no-edge/pass, and malformed filed pass-falsifiers are rejected;
- crux falsifiability is enforced by kind, metric, threshold direction, threshold value, and check-by date fields;
- full offline pytest passes;
- `python -m resolver AAPL` passes in the offline fake configuration.

## Pre-Landing Self-Review

Before landing implementation, explicitly answer:

1. Did this change add only C-5 behavior?
2. Did it avoid adding a Senior ratification call?
3. Did it keep every judgment ratifiable and undecided?
4. Did it enforce no-trade steelman and non-trivial counterparty checks in code?
5. Did it make structural_mispricing its own required draft with the no-edge escape valve?
6. Did it enforce crux falsifiability through typed fields instead of keyword checks?
7. Did it enforce exactly three falsifiable cruxes in code?
8. Did it avoid prompt-only enforcement?
9. Did it avoid new dependencies?
