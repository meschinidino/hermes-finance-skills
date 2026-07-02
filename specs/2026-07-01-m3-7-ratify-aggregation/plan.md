# M3.7 Ratify Aggregation - Plan

## Objective

Implement the consolidated Senior ratification pass after the completed M2b and M3 draft-producing steps.

M3.7 must collect the B-4 Gate Card verdict plus C-2 Moat, C-3 Capital Allocation, C-4 Scenarios, C-5 Edge & Cruxes, and C-6 Risk review items into one `SeniorReviewPackage`, call the injected `Senior.ratify` exactly once on the GO path, and persist a complete `SeniorDecisionPackage` for M4 synthesis.

## Scope

In scope:

- A deterministic aggregation helper for M2b and M3 review items.
- Conversion of the B-4 `GateCard.verdict` `Ratifiable` into the same `ReviewItem` shape used by M3 Analyst drafts.
- One consolidated `SeniorReviewPackage` persisted under the run directory.
- One `Senior.ratify` call after C-6 Risk succeeds on the DCF GO path.
- A persisted `SeniorDecisionPackage` with a decision for every required review item.
- Offline fake Senior support for resolver tests.
- Audit checks proving incomplete Senior decisions fail closed.

Out of scope:

- Final Handoff synthesis.
- Conviction scoring.
- Review packager UI or prose synthesis.
- Calibration analytics.
- New Analyst bundles.
- New Senior gates.
- Live LLM drafting.
- Non-DCF valuation expansion.

## Proposed Architecture

```text
analyze(ticker)
   |- existing M1/M2/M3.6 path
   |- B-4 Gate Card verdict -> ReviewItem
   |- C-2 review package
   |- C-3 review package
   |- C-4 review package
   |- C-5 review package
   |- C-6 review package
   |- consolidate into one SeniorReviewPackage
   |- Senior.ratify(consolidated package) exactly once
   `- persist SeniorDecisionPackage
```

The consolidated package remains evidence-backed and source-addressable. The Senior decision package is the signing artifact M4 will consume.

## Implementation Steps

1. Add M3.7 helper functions beside the existing M3 contract utilities.
2. Add collection for B-4 `Ratifiable` values without changing accountant schemas.
3. Add package consolidation with stable ids and duplicate-id rejection.
4. Add a `ratify_review_package` helper that builds a `SeniorDecisionPackage` from the injected Senior response.
5. Wire resolver GO/DCF path after C-6 Risk.
6. Persist `senior_review_package.json` and `senior_decision_package.json`.
7. Add focused tests for aggregation, exactly-one ratify call, incomplete decision rejection, NO-GO behavior, and resolver payload shape.
8. Update `specs/roadmap.md` only after validation passes.

## Risks And Decisions

- M3.7 must not mutate Analyst artifacts into final assertions. The signed artifact is separate.
- The B-4 Gate Card verdict is the only M2b ratifiable currently present on the path.
- `Senior.ratify` must be called once after all required items are known; partial packages are not useful.
- Incomplete Senior responses must fail before persistence.
- Non-DCF routes remain method-deferred until the later valuation-method expansion can supply Risk inputs.

## Expected Result

After M3.7, offline `analyze("AAPL")` returns and stores:

- a consolidated Senior review package containing B-4 and C-2 through C-6 required judgments;
- a complete Senior decision package keyed by stable review item ids;
- no final Handoff synthesis or M4 behavior.
