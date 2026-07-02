# M3.7 Ratify Aggregation - Requirements

## Functional Requirements

1. M3.7 must collect all required B-4 and M3 ratifiables on the GO/DCF path.
2. M3.7 must include `GateCard.verdict`.
3. M3.7 must include C-2 Moat review items.
4. M3.7 must include C-3 Capital Allocation review items.
5. M3.7 must include C-4 Scenario review items.
6. M3.7 must include C-5 Edge & Cruxes review items.
7. M3.7 must include C-6 Risk review items.
8. M3.7 must persist one consolidated `SeniorReviewPackage`.
9. M3.7 must call `Senior.ratify` exactly once after all included artifacts pass audit.
10. M3.7 must persist one `SeniorDecisionPackage`.
11. Every required review item id must have a Senior decision.
12. Missing required Senior decisions must fail closed.
13. Duplicate review item ids must fail closed.
14. Senior decisions must be keyed by stable review item id.
15. The persisted decision package must audit and survive storage round-trip.

## Boundary Requirements

- M3.7 must not add a new `Senior.gate`.
- M3.7 must not call `Senior.ratify` on the M3.2 NO-GO path.
- M3.7 must not call `Senior.ratify` before C-6 Risk passes audit.
- M3.7 must not implement final Handoff synthesis.
- M3.7 must not implement conviction scoring.
- M3.7 must not add live LLM requirements.
- M3.7 must not add dependencies.
- M3.7 must preserve standalone portability and injected Senior behavior.

## Data Requirements

- The consolidated package must carry ticker, as-of date, header, review items, and source artifact summary.
- Each review item must preserve source artifact, source field path, draft, evidence refs, checklist area, and checklist rationale.
- The B-4 Gate Card verdict review item must use evidence that resolves to the filed Gate Card artifact.
- The Senior decision package must carry `decided_by`, required item ids, and decisions.
- Senior final values must not contain bare numeric payloads.

## Acceptance Criteria

- A consolidated package for AAPL contains B-4 plus C-2 through C-6 review items.
- `Senior.ratify` is called exactly once on the full GO/DCF path.
- `Senior.ratify` is not called on the NO-GO path.
- Incomplete Senior decisions are rejected.
- `analyze("AAPL")` includes `senior_review_package` and `senior_decision_package`.
- Full offline tests and resolver smoke pass.
