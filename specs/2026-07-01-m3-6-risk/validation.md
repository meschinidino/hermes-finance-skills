# M3.6 Risk - Validation

## Technical Checks

After implementation, run:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/research/risk
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

The `--no-sync` flag is intentional. M3.6 validation must run offline and must not require PyPI access, EDGAR, FRED, Damodaran, price feeds, live LLM credentials, network access, a human Senior, or a consolidated Senior ratification pass.

## Required Artifact Tests

1. Valid Risk artifact constructs from deterministic offline inputs.
2. Valid artifact passes M3.1 evidence audit.
3. Valid artifact passes M3.3 period-consistency audit.
4. Valid artifact includes `Header`, ticker, and as-of date.
5. Valid artifact includes source artifact references.
6. Valid artifact includes a pre-mortem draft.
7. Valid artifact includes a bear-case narrative draft.
8. Valid artifact includes a modellable risk register draft.
9. Valid artifact includes a tail-risk draft.
10. Valid artifact includes bear-case value.
11. Valid artifact includes a kill metric draft.
12. Valid artifact includes a risk-completeness draft.
13. Valid artifact includes source evidence summary.
14. Every Analyst draft has non-empty evidence refs.
15. Every Analyst draft has resolvable evidence refs.
16. Every Analyst draft has Senior checklist area and rationale.
17. Every Analyst draft remains undecided before M3.7.
18. Required fields are not placeholder-only strings.
19. Draft payloads with bare numeric values are rejected where `Number` is required.
20. Bear-case value is a `Number` with provenance and derivation.
21. Fixture with sufficient evidence produces an audited artifact.
22. Fixture with missing required evidence fails closed.
23. Deterministic fake LLM output, if used by the drafter seam, is identical across repeated runs.
24. Risk drafter performs no network access.

## Required Pre-Mortem Tests

1. Non-empty pre-mortem passes.
2. Pre-mortem with evidence support passes.
3. Pre-mortem that explains how the investment loses money passes.
4. Empty pre-mortem is rejected.
5. Placeholder pre-mortem is rejected.
6. Purely bullish pre-mortem is rejected.
7. Pre-mortem without a concrete time horizon is rejected.
8. Pre-mortem without evidence is rejected.
9. Pre-mortem failure identifies the offending field.

## Required Bear-Case Narrative Tests

1. Credible short-seller bear narrative passes.
2. Bear narrative with evidence support passes.
3. Bear narrative connected to scenario or valuation evidence passes.
4. Empty bear narrative is rejected.
5. Placeholder bear narrative is rejected.
6. Generic downside lists without a central mechanism are rejected.
7. Unsupported short-seller claims are rejected.
8. Bear narrative failure identifies the offending condition.

## Required Modellable Risk Tests

1. One or more modellable risks pass.
2. Multiple modellable risks pass.
3. Modellable risk with impact, likelihood, modeled effect, and evidence passes.
4. Empty modellable risk register is rejected.
5. Modellable risk missing impact is rejected.
6. Modellable risk missing likelihood is rejected.
7. Modellable risk missing modeled effect is rejected.
8. Modellable risk missing evidence is rejected.
9. Modellable risk with invalid impact or likelihood enum is rejected.
10. Modellable risk failure identifies the offending risk.

## Required Tail-Risk Tests

1. One or more tail risks pass.
2. Tail risk with why-not-modelled explanation passes.
3. Tail risk with monitoring signal or explicit missing-data gap passes.
4. Empty tail-risk bucket is rejected.
5. Tail risk missing why-not-modelled explanation is rejected.
6. Tail risk missing monitoring signal or missing-data gap is rejected.
7. Tail risk with likelihood scoring is rejected.
8. Tail risk blended into the modellable register is rejected.
9. Duplicate risks across modellable and tail buckets are rejected.
10. Tail-risk failure identifies the offending condition.

## Required Bear-Case Value Tests

1. Bear-case value as a provenance-complete `Number` passes.
2. Bear-case value derived from bear scenario or valuation inputs passes.
3. Bear-case value with derivation input references passes.
4. Bare numeric bear-case value is rejected.
5. Bear-case value missing provenance is rejected.
6. Bear-case value missing derivation is rejected.
7. Bear-case value with incompatible units is rejected.
8. Bear-case value disconnected from source valuation or scenario evidence is rejected.
9. Non-finite bear-case value is rejected.
10. Bear-case value failure identifies the offending condition.

## Required Kill-Metric Tests

1. Kill metric with metric, threshold direction, threshold value, observation window, thesis action, and evidence passes.
2. Kill metric connected to a thesis crux, bear scenario, risk, business driver, or valuation driver passes.
3. Empty kill metric is rejected.
4. Placeholder kill metric is rejected.
5. Kill metric missing metric name is rejected.
6. Kill metric missing threshold direction is rejected.
7. Kill metric missing threshold value is rejected.
8. Kill metric missing observation window is rejected.
9. Kill metric missing thesis action is rejected.
10. Kill metric without evidence is rejected.
11. Falsifiability is not accepted based on keywords in free text.
12. Kill-metric failure identifies the offending condition.

## Required Risk-Completeness Tests

1. Risk-completeness draft stating decision readiness passes.
2. Risk-completeness draft naming unverifiable items passes.
3. Risk-completeness draft naming confidence-raising or confidence-lowering evidence passes.
4. Empty risk-completeness draft is rejected.
5. Risk-completeness draft without evidence or missing-data gaps is rejected.
6. Risk-completeness draft with final Senior decision metadata before M3.7 is rejected.

## Required Ratifiable Collection Tests

1. Valid artifact collects into a `SeniorReviewPackage`.
2. Review item ids are stable across repeated deterministic runs.
3. Each collected review item preserves source artifact identity.
4. Each collected review item preserves source field path.
5. Each collected review item preserves evidence refs.
6. Each collected review item preserves Senior checklist mapping.
7. Collected items remain undecided before M3.7.
8. Collection does not call `Senior.ratify`.
9. Package is not treated as final Senior approval in M3.6.

## Required Bundle-Validation Tests

1. The real `skills/research/risk/` bundle passes M3.1 Analyst-shaped bundle validation.
2. `SKILL.md` declares `type: analyst`.
3. `SKILL.md` declares `no_llm: false`.
4. `SKILL.md` declares an LLM dependency.
5. `SKILL.md` declares ratifiable draft output contracts.
6. `SKILL.md` does not declare a final assertion output contract.
7. The implementation includes `test_risk.py` or an explicit M3.6 test module under `tests/`.
8. Bundle validation fails if `prompt.md` is removed or absent in a test copy.
9. Bundle validation fails if `eval/cases.jsonl` is removed or absent in a test copy.
10. Bundle validation fails if `eval/eval_risk.py` is removed or absent in a test copy.
11. Bundle validation fails if the output contract is changed to a bare assertion in a test copy.
12. Bundle validation fails if `no_llm` changes to `true`.

## Required Resolver Integration Tests

1. `analyze("AAPL")` reaches Risk after the M3.2 early gate GO path.
2. `analyze("AAPL")` reaches Risk after Edge & Cruxes.
3. `analyze("AAPL")` does not run Risk after an M3.2 NO-GO stop.
4. `analyze("AAPL")` files or returns the Risk artifact.
5. `analyze("AAPL")` audits the artifact before collection.
6. Risk audit failure prevents ratifiable collection.
7. Filed artifact survives storage round-trip.
8. Offline resolver run calls no live LLM.
9. Offline resolver run calls no real human Senior.
10. Offline resolver run calls `Senior.gate` only for the existing M3.2 early gate.
11. Offline resolver run does not call `Senior.ratify`.
12. Repeated offline resolver runs produce deterministic drafts.

## Manual Validation

Before marking M3.6 complete:

1. Confirm only `C-6 Risk` was implemented.
2. Confirm no M3.7 consolidated ratification behavior was added.
3. Confirm no final Handoff synthesis was added.
4. Confirm no sizing inputs were added.
5. Confirm no calibration analytics were added.
6. Confirm no second Senior touchpoint was added.
7. Confirm no live LLM call was added.
8. Confirm no real human Senior call is required for tests.
9. Confirm no new M3 contracts were invented.
10. Confirm no new storage abstraction or persistence mechanism was added.
11. Confirm Risk drafts reuse M3.1 `AnalystDraft` or compatible M3.1 draft infrastructure.
12. Confirm evidence support is enforced by audit.
13. Confirm `prompt.md` has no enforcement role beyond bundle shape and eval documentation.
14. Confirm period-consistency audit compares claimed period to resolved source period.
15. Confirm pre-mortem rejection catches upside-only drafts.
16. Confirm bear-case rejection catches generic downside lists without a mechanism.
17. Confirm tail risks are non-empty and separated from modellable risks.
18. Confirm bear-case value is provenance-complete.
19. Confirm kill-metric falsifiability is field-based, not keyword-based.
20. Confirm runtime artifacts under `/data` are not committed.

## Document Validation

Before implementation:

1. Confirm this spec lives under `specs/2026-07-01-m3-6-risk/`.
2. Confirm the triplet contains exactly `plan.md`, `requirements.md`, and `validation.md`.
3. Confirm the triplet scopes only M3.6: `C-6 Risk`.
4. Confirm the triplet specifies offline deterministic drafting and defers live LLM drafting.
5. Confirm the triplet requires reuse of M3.1 infrastructure.
6. Confirm the triplet requires reuse of completed M3.2 through M3.5 artifacts.
7. Confirm the triplet does not require new valuation engines, methods, contracts, storage, or dependencies.
8. Confirm the triplet makes evidence support audit-enforced, not prompt-enforced.
9. Confirm the triplet requires Analyst-shaped bundle validation.
10. Confirm the triplet requires pre-mortem enforcement.
11. Confirm the triplet requires short-seller bear-case enforcement.
12. Confirm the triplet requires separate modellable and tail-risk buckets.
13. Confirm the triplet requires bear-case value as a provenance-complete `Number`.
14. Confirm the triplet requires kill-metric falsifiability through typed fields.
15. Confirm the triplet does not include M3.7, final Handoff synthesis, sizing, calibration, live LLM drafting, or a second Senior touchpoint.

## Responsive And Accessibility Checks

Not applicable in M3.6. There is no UI surface.

## Closure Criteria

M3.6 can be marked complete in `specs/roadmap.md` only after:

- the M3.6 spec files are current;
- the `C-6 Risk` bundle exists and passes Analyst-shaped bundle validation;
- drafting is deterministic and offline;
- Risk artifacts are schema-valid and evidence-backed;
- all Risk drafts collect as undecided review items;
- malformed pre-mortem, bear narrative, risk bucket, bear-case value, kill metric, and risk-completeness drafts fail audit;
- tail risks are non-empty and separate from modellable risks;
- bear-case value is provenance-complete;
- kill-metric falsifiability is enforced by metric, threshold direction, threshold value, observation window, and thesis action;
- full offline pytest passes;
- `python -m resolver AAPL` passes in the offline fake configuration.

## Pre-Landing Self-Review

Before landing implementation, explicitly answer:

1. Did this change add only C-6 behavior?
2. Did this change avoid M3.7 ratification and final Handoff synthesis?
3. Did this change preserve exactly two Senior touchpoints overall?
4. Did this change keep tail risks outside the modellable risk matrix?
5. Did this change keep every Analyst judgment ratifiable and undecided?
6. Did this change keep validation offline and deterministic?
