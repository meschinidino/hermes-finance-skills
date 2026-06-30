# M0 Scaffold — Validation

## Manual Validation

```text
uv run --no-sync python -m resolver AAPL
```

Expected:
- JSON is printed to stdout.
- `status` is `m0_stub`.
- `data/runs/AAPL/{as_of}/m0_stub.json` exists.
- `data/pack.db` exists.

## Technical Checks

```text
uv run --no-sync pytest
uv run --no-sync python -m resolver AAPL
git status --short --ignored
```

## Closure Criteria

M0 can be marked complete when:
- the scaffold spec exists,
- pydantic primitive validators reject invalid forms, missing provenance, and missing derivations,
- the root resolver stub runs,
- local storage writes and reloads JSON,
- config validation is covered by tests,
- runtime data is ignored by git,
- the roadmap records M0 completion.
