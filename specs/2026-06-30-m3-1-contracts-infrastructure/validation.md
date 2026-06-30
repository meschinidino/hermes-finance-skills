# M3.1 Analyst Contracts And Infrastructure — Validation

## Technical Checks

After implementation, run:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

The `--no-sync` flag is intentional. M3.1 validation must not require live PyPI, EDGAR, FRED, Damodaran, price feeds, LLM credentials, or human Senior input.

## Expected Unit Tests

- M3.1 artifact models construct from valid fixtures.
- M3.1 artifact models reject missing required headers.
- M3.1 artifact models reject missing evidence.
- M3.1 artifact models reject bare numeric values where `Number` is required.
- Ratifiable collection finds nested ratifiables.
- Ratifiable collection preserves source artifact and field path.
- Ratifiable collection creates stable ids.
- Empty `SeniorReviewPackage` is rejected.
- Incomplete `SeniorDecisionPackage` is rejected.
- Complete `SeniorDecisionPackage` is accepted.
- Fake `LLM` returns deterministic structured content.
- Fake `Senior.gate` returns deterministic gate decisions.
- Fake `Senior.ratify` returns deterministic decisions for every required review item.
- Analyst bundle-shape validation accepts a complete future Analyst bundle fixture.
- Analyst bundle-shape validation rejects missing `prompt.md`.
- Analyst bundle-shape validation rejects missing eval files.
- Analyst bundle-shape validation rejects `no_llm: true`.

## Manual Validation

1. Confirm `specs/roadmap.md` lists M3.1-M3.7 as separate roadmap slices.
2. Confirm M3.1 implementation does not add any live LLM or live Senior dependency.
3. Confirm `resolver.analyze("AAPL")` still follows the M2b behavior until M3.2 adds Business and early gate wiring.
4. Confirm no runtime artifacts are committed under `/data`.

## Closure Criteria

M3.1 can be marked complete in `specs/roadmap.md` only after:
- contracts are implemented;
- audit helpers are implemented;
- ratifiable collection is implemented;
- fake test adapters are implemented;
- future Analyst bundle-shape validation is implemented;
- all M3.1 unit tests pass;
- full offline pytest passes;
- `python -m resolver AAPL` still passes with unchanged M2b behavior.

## Validation Result

Status: planned only. Implementation has not started.
