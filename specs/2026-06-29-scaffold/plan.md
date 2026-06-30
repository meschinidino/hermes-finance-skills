# M0 Scaffold — Plan

## Objective

Create the portable foundation the walking skeleton depends on: root resolver, typed primitives, injected interfaces, validated conventions config, and writable local storage.

## Scope

In scope:
- Root `resolver.py` with an `analyze()` entry stub.
- Top-level `/skills` package with shared primitives and interfaces.
- Top-level `/config/conventions.yaml` with the M1 convention subset.
- Top-level `/data` runtime storage created on demand and ignored by git.
- Local file storage plus SQLite calibration-log initialization.
- Pydantic v2 models for primitives and config.
- Focused pytest scaffold tests that run without network access.

Out of scope:
- EDGAR, price, FRED, normalization, WACC, ROIC, handoff schemas, LLM calls, and Senior decisions.

## Proposed Architecture

```text
resolver.py
skills/
  _primitives.py
  config.py
  interfaces.py
  storage.py
  data/
  valuation/
  research/
  synthesis/
config/
  conventions.yaml
data/
  cache/
  runs/
  pack.db
```

M0 keeps the root resolver separate from skills. Skills are portable employees; resolver sequencing remains above them.

## Implementation Steps

1. Add project metadata and gitignore rules.
2. Add conventions config and a strict PyYAML + pydantic config loader for the known M0/M1 subset.
3. Add pydantic primitive models for provenance-bearing artifacts.
4. Add Protocol definitions for `Senior`, `Storage`, `LLM`, and `PriceFeed`.
5. Add local storage that writes JSON artifacts and initializes SQLite.
6. Add `analyze()` stub that loads config, verifies storage writability, and writes a stub run artifact.
7. Add pytest scaffold tests.

## Risks And Decisions

- M0 owns the primitive and config contracts. M1 must reuse them instead of restating or replacing them.
- The `skills` package name is intentionally generic because the repo convention says portable skills live at `/skills`.
- The M0 run artifact is explicitly a stub and must not be treated as a financial handoff.

## Expected Result

`uv run python -m resolver AAPL` returns a stub payload, writes `data/runs/AAPL/{as_of}/m0_stub.json`, and leaves the repository ready for M1 implementation.
