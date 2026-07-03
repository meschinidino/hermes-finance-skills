# M4a Resolver Restructure - Requirements

## Functional Requirements

1. M4a must introduce a real synthesis boundary for current resolver output assembly.
2. The synthesis boundary must consume already-built current artifacts and path metadata.
3. The synthesis boundary must produce the same payload keys currently returned by `analyze()` on GO paths.
4. The synthesis boundary must preserve current nested payload values for D-1, M2, M3, M3.7, and route manifest artifacts.
5. `analyze("AAPL")` must still return DCF-specific `valuation_range` and `expectations_line` payloads.
6. `analyze("MRNA")` must still return non-DCF `valuation_deferred` behavior and must not add DCF artifacts.
7. The current M3.2 NO-GO path must keep returning the existing halted payload shape.
8. All current artifact file paths under the run directory must remain stable.
9. `handoff.json` must remain the existing D-1 bare handoff artifact.
10. Existing Senior gate and ratify call counts must remain unchanged.
11. Existing audit calls must still run before artifacts are exposed through the boundary.
12. Storage round-trip behavior must remain unchanged.

## Boundary Requirements

- M4a must not implement `D-2 Conviction`.
- M4a must not implement `D-3 Review Packager`.
- M4a must not implement the final filing-rules `Handoff`.
- M4a must not change the D-1 bare handoff schema.
- M4a must not add conviction labels, conviction scores, lean synthesis, sizing inputs, or revisit triggers.
- M4a must not add KILL halt behavior.
- M4a must not add or change escalation routing.
- M4a must not add parallel execution.
- M4a must not wire C-5 `pass_falsifiers`; that belongs to M4c.
- M4a must not upgrade model independence checks; that belongs to M4c.
- M4a must not add dependencies.
- M4a must not require live network or live LLM access.

## Data Requirements

- The synthesis input contract must identify ticker, as-of date, run directory, method, route manifest, and required artifact paths.
- Optional DCF paths must be explicit and only present when the method route produced DCF artifacts.
- The boundary must not invent numbers, judgments, evidence, or Senior decisions.
- The boundary must not pass bare numeric values across skill boundaries.
- The boundary must preserve serialized pydantic artifact payloads without lossy transformation.
- Missing required filed artifacts must fail closed.
- DCF route assembly must fail closed if either `valuation_range.json` or `expectations_line.json` is missing.
- Non-DCF route assembly must not require DCF-only artifacts.
- AAPL and MRNA post-restructure payloads must diff equal to pre-restructure payloads after excluding volatile timestamps and generated run identifiers.

## Acceptance Criteria

- The end-of-`analyze()` payload assembly is no longer an inline accretion block in `resolver.py`.
- Current `analyze()` output for AAPL is byte-equivalent to the pre-M4a output except for volatile timestamps and generated run identifiers.
- Current `analyze()` output for MRNA is byte-equivalent to the pre-M4a output except for volatile timestamps and generated run identifiers.
- Current halted output behavior is unchanged.
- All existing M0-M3 tests pass unchanged, with zero modifications to pre-existing test files.
- `python -m resolver AAPL` passes.
