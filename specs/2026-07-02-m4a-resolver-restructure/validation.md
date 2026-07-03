# M4a Resolver Restructure - Validation

## Technical Checks

Run:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

The full pytest command is the required validation gate. Focused M4a tests are useful diagnostics, but they are not sufficient to mark M4a complete.

## Required Tests

1. The synthesis boundary assembles the current AAPL DCF payload keys.
2. The synthesis boundary assembles the current MRNA non-DCF payload keys.
3. The AAPL payload still includes `valuation_range` and `expectations_line`.
4. The MRNA payload still excludes `valuation_range` and `expectations_line`.
5. The MRNA payload still includes `valuation_deferred`.
6. The payload still includes `senior_review_package`, `senior_decision_package`, and `route_review_manifest` on GO paths.
7. The M3.2 NO-GO halted payload shape is unchanged.
8. Missing required artifact paths fail closed in the synthesis boundary.
9. DCF assembly fails closed when either DCF artifact path is absent.
10. Non-DCF assembly does not require DCF artifact paths.
11. `Senior.gate` is still called exactly once on the current GO path.
12. `Senior.ratify` is still called exactly once on the current GO path.
13. Existing tests do not need assertion changes to pass.
14. Full test suite passes with all pre-existing M0-M3 tests unchanged.
15. Git diff for pre-existing files under `tests/` is empty; any new M4a test file is listed separately.

## Output Equivalence Checks

Before marking M4a complete:

1. Produce pre-restructure `analyze("AAPL")` and `analyze("MRNA")` payloads from the resolver before the M4a boundary change, using fixed `as_of` dates and isolated storage roots.
2. Produce post-restructure `analyze("AAPL")` and `analyze("MRNA")` payloads from the current resolver with the same dates and isolated storage roots.
3. Serialize both sets with stable JSON key ordering.
4. Report the raw diff.
5. Report a normalized diff after removing volatile timestamp fields such as `produced_at` and `retrieved_at`, plus any generated run-id fields if present.
6. List and explain every remaining difference. The expected result is no remaining difference.

## Manual Validation

Before marking M4a complete:

1. Confirm no `D-2 Conviction` or `D-3 Review Packager` skill was added.
2. Confirm no final filing-rules `Handoff` fields were added.
3. Confirm no new Senior touchpoint was added.
4. Confirm no control-flow features from M4c were implemented.
5. Confirm runtime artifacts remain under `/data` or test temp storage.
6. Confirm the new boundary is documented by code names that make its M4b extension point obvious.

## Closure Criteria

M4a can be marked complete in `specs/roadmap.md` only after:

- the M4a spec files are current;
- the resolver uses the new synthesis boundary for current output assembly;
- AAPL and MRNA pre/post output equivalence checks pass, with only timestamp or run-id differences;
- all existing M0-M3 tests pass unchanged;
- `python -m resolver AAPL` passes;
- the user has reviewed the validation report;
- no M4b or M4c features have been implemented.
