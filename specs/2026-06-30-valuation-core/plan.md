# M2a Valuation Core — Plan

## Objective

Build the deterministic valuation core that turns the M1 financial spine into two auditable valuation outputs for `AAPL`: a forward DCF valuation and a reverse-DCF Expectations Line. This slice thickens the existing Accountant path only; it does not add gates, routing, Analysts, or Senior judgment.

## Scope

In scope:
- `A-2 Price` as a real current-price adapter that supplies current price and market capitalization.
- `A-3 Cost of Capital` as a real cost-of-capital adapter using FRED, Damodaran config, and a source-backed AAPL sector beta.
- `B-3 DCF` as one DCF engine with forward and reverse modes.
- Frozen fixtures for AAPL price, FRED `DGS10`, Damodaran inputs, and the existing AAPL financial spine inputs.
- Schema-valid `ValuationRange` and `ExpectationsLine` artifacts with complete `Number` provenance and derivations.
- M2a resolver wiring from the existing M1 path into valuation artifacts.

Out of scope:
- `B-4 Screens`, `B-5 Base-Rate`, and `B-6 Method Router`; these belong to M2b.
- Analyst skills, prompts, evals, Senior ratification, scenario probability judgment, and business narrative.
- New data providers beyond FRED, Damodaran config, and the injected price feed.
- Non-US, non-XBRL, optionality/pre-revenue, NAV, SOTP, or rNPV valuation methods.

## Prerequisite

M2a depends on the completed M1 path in `specs/2026-06-29-walking-skeleton/`: EDGAR facts, normalization, Spine, config loading, storage, primitives, and audit enforcement. M2a must reuse M0/M1 contracts rather than duplicating `Provenance`, `Number`, `Header`, `Storage`, `Config`, or filing schemas.

## Proposed Architecture

The resolver remains the orchestrator and stays a simple standalone Python path:

```text
analyze("AAPL")
   ├─ A-1 EDGAR
   ├─ B-1 Normalize
   ├─ B-2 Spine
   ├─ A-2 Price
   ├─ A-3 Cost of Capital
   └─ B-3 DCF
        ├─ forward mode → ValuationRange
        └─ reverse mode → ExpectationsLine
        ↓
      Storage + audit gate
```

`B-3 DCF` owns one valuation core. Forward mode values the company from explicit drivers; reverse mode uses the same cash-flow and discounting core to solve for market-implied expectations from the observed price.

## Skill Bundles Created Or Completed In M2a

All M2a bundles are Accountants (`no_llm: true`). Each must fill `specs/SKILL-template.md` and include no `prompt.md` or `eval/`.

```text
skills/data/price/
├── SKILL.md
├── price.py
├── test_price.py
├── test_integration.py
└── resolver.entry

skills/data/cost_of_capital/
├── SKILL.md
├── cost_of_capital.py
├── test_cost_of_capital.py
├── test_integration.py
└── resolver.entry

skills/valuation/dcf/
├── SKILL.md
├── dcf.py
├── test_dcf.py
└── resolver.entry
```

`test_integration.py` is required for `price` and `cost_of_capital` because they hit live endpoints. `dcf` is pure compute and should not have a live endpoint smoke unless a future implementation introduces one.

## Implementation Steps

1. Fill or update the three M2a `SKILL.md` files from `specs/SKILL-template.md`.
2. Freeze CI fixtures under `tests/fixtures/`:
   - AAPL current price response.
   - FRED `DGS10` response.
   - Damodaran cost-of-capital inputs used by AAPL.
   - DCF input/output golden cases derived from the AAPL fixture path.
3. Complete `A-2 Price`:
   - read current price from injected `PriceFeed`;
   - combine price with EDGAR shares to compute market capitalization;
   - if the feed is down, use the documented book-equity fallback path and flag the substitution as non-fatal.
4. Complete `A-3 Cost of Capital`:
   - read risk-free rate from FRED `DGS10`, with config fallback when FRED is unreachable;
   - read ERP and synthetic-rating spread from `config/conventions.yaml`;
   - retire the fabricated AAPL beta placeholder by replacing it with the current Damodaran unlevered beta for AAPL's sector, source-dated in config;
   - relever beta from capital structure and compute cost of equity, after-tax debt, and WACC band inputs.
5. Build `B-3 DCF`:
   - use one core cash-flow and discounting engine for both modes;
   - forward mode computes enterprise value, equity value, and per-share value from explicit drivers;
   - reverse mode solves market-implied growth, margin, and duration from price.
6. Add reverse-DCF band behavior:
   - solve across the low and high WACC band bounds, not only at a point estimate;
   - report both band-edge implications when convergence succeeds;
   - on non-convergence, report the attempted band edges and the failure reason without forcing a numeric midpoint.
7. File `valuation_range.json` and `expectations_line.json` under the run directory.
8. Extend the audit gate only as needed to reject M2a artifacts with missing provenance, missing derivations, invalid schema shape, or forced reverse-DCF outputs.

## Risks And Decisions

- Reverse DCF can be ill-conditioned. The implementation must make non-convergence explicit and must not invent an implied value to satisfy the schema.
- The WACC band is more decision-relevant than a false point estimate. Reverse DCF must converge at both bounds or file a structured non-convergence result.
- Live sources are allowed only outside offline CI. Frozen fixtures are the CI contract; live smokes are separate checks.
- Price failure is non-fatal because book-equity weighting is documented, but the artifact must flag the weaker weighting basis.
- FRED failure is non-fatal only when the configured fallback is present and provenance-marked as a fallback.
- The current config contains a fabricated AAPL beta stand-in. M2a is not complete until that placeholder is removed and replaced by a current Damodaran sector beta.

## Expected Result

Running `analyze("AAPL")` after M2a implementation produces:
- a current-price-derived market capitalization when the fixture or live price feed is available;
- a fallback-flagged book-equity weighting path when price is unavailable;
- cost of capital based on FRED `DGS10`, Damodaran ERP, Damodaran synthetic-rating spread, and a real Damodaran AAPL sector beta;
- a schema-valid forward `ValuationRange`;
- a schema-valid reverse-DCF `ExpectationsLine` with WACC-band implications;
- complete provenance and derivations for every emitted `Number`.
