# M3.7 Ratify Aggregation - Validation

## Technical Checks

Run:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest tests/test_m3_7_ratify_aggregation.py
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

## Required Tests

1. Consolidating review packages preserves all review item ids.
2. Consolidating review packages rejects duplicate ids.
3. B-4 Gate Card verdict converts into a required review item.
4. Consolidated package includes B-4, C-2, C-3, C-4, C-5, and C-6 source artifacts.
5. `Senior.ratify` is called exactly once on the full GO/DCF resolver path.
6. Resolver persists `senior_review_package.json`.
7. Resolver persists `senior_decision_package.json`.
8. Decision package contains every required review item id.
9. Incomplete Senior decision responses fail closed.
10. NO-GO path does not call `Senior.ratify`.

## Manual Validation

Before marking M3.7 complete:

1. Confirm no final Handoff synthesis was added.
2. Confirm no new Senior gate was added.
3. Confirm the Senior ratify pass is injected and not hardcoded.
4. Confirm M3.7 stays offline with fake Senior defaults.
5. Confirm runtime artifacts remain under `/data` or test temp storage.

## Closure Criteria

M3.7 can be marked complete in `specs/roadmap.md` only after:

- the M3.7 spec files are current;
- the consolidated review package includes all required B-4 and C-2 through C-6 ratifiables;
- `Senior.ratify` is called exactly once on the GO/DCF path;
- the Senior decision package is complete and audited;
- full offline pytest passes;
- `python -m resolver AAPL` passes.

Validation run on 2026-07-01:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest tests/test_m3_7_ratify_aggregation.py
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

Result: M3.7 is closed. The focused M3.7 suite passed, full offline pytest passed, and the resolver AAPL smoke passed.
