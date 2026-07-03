# M4a Resolver Restructure - Validation

## Technical Checks

Run:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest tests/test_m2b_resolver.py tests/test_m3_2_business_gate.py tests/test_m3_7_ratify_aggregation.py tests/test_multi_ticker_ratify_paths.py
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

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
- AAPL and MRNA output parity checks pass;
- all existing M0-M3 tests pass unchanged;
- `python -m resolver AAPL` passes;
- no M4b or M4c features have been implemented.
