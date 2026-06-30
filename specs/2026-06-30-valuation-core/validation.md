# M2a Valuation Core — Validation

## Manual Validation

1. Run `analyze("AAPL")` after M2a implementation.
2. Confirm the run reports:
   - current price loaded from fixture or live price feed;
   - market capitalization computed from price and EDGAR shares;
   - FRED `DGS10` loaded from fixture or live response;
   - Damodaran ERP, synthetic-rating spread, and AAPL sector beta loaded from config;
   - forward DCF filed;
   - reverse-DCF Expectations Line filed.
3. Open the run directory under `data/runs/AAPL/{as_of}/`.
4. Confirm `valuation_range.json` is reloadable and is marked as a standalone M2a artifact, not a signed Handoff.
5. Confirm `expectations_line.json` is reloadable.
6. Pick one forward value and walk its derivation back to revenue, margin, reinvestment, WACC, terminal value, net debt, and shares.
7. Confirm the reverse-DCF low/high WACC-band edge results are the authoritative output. Any midpoint is a convenience field only and is not the headline implied value.

## Technical Checks

Run the project checks that exist after implementation:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/data/price
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/data/cost_of_capital
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/valuation/dcf
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

The `--no-sync` flag is intentional. CI must not require live PyPI, FRED, Damodaran, or price-feed access.

## Expected Unit Tests

- Price fixture maps current price to a `USD_per_share` `Number`.
- Price fixture plus EDGAR shares computes market capitalization with a derivation.
- Price-feed failure triggers book-equity weighting fallback and flags the weaker basis.
- FRED fixture maps `DGS10` to a risk-free `Number`.
- FRED unreachable path uses config fallback and flags the fallback.
- ERP and synthetic-rating spread load from config.
- AAPL unlevered beta loads from the updated Damodaran sector-beta config entry, not the old fabricated placeholder.
- Relevered beta, cost of equity, cost of debt, after-tax cost of debt, and WACC compute from hand-checked fixture values.
- Forward DCF computes enterprise value, equity value, and per-share value from hand-checked fixture drivers.
- Forward DCF emits exactly three schema-valid scenarios with unratified probability fields.
- Reverse DCF converges at the low WACC-band bound.
- Reverse DCF converges at the high WACC-band bound.
- Reverse DCF non-convergence returns band edges and failure metadata without a forced implied point.
- DCF artifacts serialize and reload without losing `Number` provenance or derivations.

## Expected Fault-Injection Tests

- Remove price provenance and assert audit rejection.
- Remove market-cap derivation and assert audit rejection.
- Remove FRED provenance and assert audit rejection unless the fallback path is explicitly flagged.
- Remove the Damodaran beta source date or source name and assert config validation failure.
- Restore the old fabricated AAPL beta placeholder and assert the M2a config check fails.
- Set WACC band low >= high and assert audit rejection.
- Set WACC outside sane bounds and assert audit rejection.
- Force reverse DCF to fail convergence and assert the artifact reports band edges instead of inventing a point.
- Remove derivation from a DCF output and assert audit rejection.
- Try to include `prompt.md` or `eval/` in an M2a Accountant bundle and assert bundle validation fails.

## Live Smoke

Live network checks are separate from offline CI. When credentials and network access are available:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/data/price/test_integration.py
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/data/cost_of_capital/test_integration.py
```

The live price smoke should verify the injected `PriceFeed` contract still matches the configured provider. The live cost-of-capital smoke should verify FRED `DGS10` is reachable and parsed correctly. Damodaran inputs may be refreshed by a documented manual or scripted process, but CI must consume the frozen/configured values.

Latest live-smoke result on 2026-06-30:
- FRED `DGS10` smoke passed.
- Live price provider smoke was documented unavailable: Yahoo Finance chart returned `HTTPError: HTTP Error 429: Too Many Requests`. The test now skips with that exact provider error instead of silently falling into the book-equity fallback path.

## Document Validation

Before starting implementation:
- confirm `specs/roadmap.md` has separate M2a and M2b lines;
- confirm the critical path names M2a and M2b separately;
- confirm this spec contains only M2a scope;
- confirm all three M2a skill bundles are Accountant bundles;
- confirm this spec does not require Screens, Base-Rate, Method Router, Analysts, prompts, evals, or Senior ratification.

## Responsive And Accessibility Checks

Not applicable in M2a. There is no UI surface.

## Closure Criteria

M2a can be marked complete in `specs/roadmap.md` only after:
- the M2a spec files are current;
- all M2a skill bundles include completed `SKILL.md` files;
- the frozen-fixture test suite passes offline;
- live endpoint smokes are either passing or documented with exact unavailability reasons;
- forward DCF produces a real AAPL valuation;
- reverse DCF produces a real AAPL Expectations Line across the WACC band;
- reverse non-convergence is handled without forcing a number;
- price-feed-down fallback is flagged;
- FRED-unreachable fallback is flagged;
- the AAPL beta placeholder is replaced with a source-backed current Damodaran sector beta;
- all M2a artifacts are schema-valid and provenance-complete per `specs/filing-rules.md`.

## Validation Result

Status: M2a complete after pre-landing review fixes.

Validated on 2026-06-30 with:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/data/price
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/data/cost_of_capital
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/valuation/dcf
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
RUN_LIVE_M2A=1 UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/data/price/test_integration.py skills/data/cost_of_capital/test_integration.py -q -rs
```

Results:
- Offline full suite: `34 passed, 3 skipped`.
- Price bundle offline: `3 passed, 1 skipped`.
- Cost-of-capital bundle offline: `3 passed, 1 skipped`.
- DCF bundle offline: `8 passed`.
- Resolver smoke: passed; files forward `valuation_range.json` and reverse `expectations_line.json`.
- Price-feed-down smoke: passed; files forward valuation using book-equity WACC weighting and files a blocked reverse-DCF Expectations Line.
- Live smoke: FRED passed; live price skipped with documented provider unavailability (`HTTP 429 Too Many Requests`).
