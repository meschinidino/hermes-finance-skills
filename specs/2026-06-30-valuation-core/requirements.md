# M2a Valuation Core — Requirements

## Functional Requirements

1. `analyze("AAPL")` must run through the completed M1 path and then produce M2a valuation artifacts.
2. `A-2 Price` must supply current price as a `Number` with external provenance.
3. `A-2 Price` must compute market capitalization from current price and EDGAR shares outstanding.
4. If the price feed is unavailable, `A-2 Price` must complete with the documented book-equity weighting fallback and must flag the fallback.
5. `A-3 Cost of Capital` must fetch the risk-free rate from FRED `DGS10` in live mode.
6. If FRED is unreachable, `A-3 Cost of Capital` must use `risk_free_fallback` from config and must flag the fallback.
7. `A-3 Cost of Capital` must read ERP and synthetic-rating spread from `config/conventions.yaml`.
8. `A-3 Cost of Capital` must replace the fabricated AAPL beta placeholder with the current Damodaran unlevered beta for AAPL's sector in `config/conventions.yaml`.
9. `A-3 Cost of Capital` must relever beta using the configured tax rate and observed capital structure.
10. `A-3 Cost of Capital` must emit cost of equity, pre-tax cost of debt, after-tax cost of debt, and WACC-band inputs as provenance-complete `Number` values.
11. `B-3 DCF` must implement one core engine with two modes: forward and reverse.
12. Forward DCF must compute value from explicit revenue, margin, reinvestment, tax, WACC, terminal, net debt, and share-count drivers.
13. Reverse DCF must goal-seek market-implied expectations from observed price using the same cash-flow and discounting core as forward mode.
14. Reverse DCF must solve at both low and high WACC band bounds.
15. Reverse DCF non-convergence must report the attempted WACC band edges and failure reason; it must not force or interpolate an implied point.
16. `B-3 DCF` must file a `ValuationRange` artifact for forward valuation.
17. `B-3 DCF` must file an `ExpectationsLine` artifact for reverse DCF.
18. Every emitted `Number` must include complete `Provenance`.
19. Every computed or estimated `Number` must include a derivation string that references input `Number` values.
20. Each M2a skill must be a completed Accountant folder bundle following `specs/SKILL-template.md`.

## Non-Functional Requirements

- M2a must stay portable and standalone.
- Runtime state must stay under `/data`.
- Skill code must live under `/skills`.
- Frozen CI fixtures must live under `tests/fixtures/`.
- The dependency tree must stay small and consistent with `specs/tech-stack.md`; DCF goal-seek should use stdlib numeric routines unless a heavier dependency is explicitly justified.
- CI must run offline from frozen fixtures.
- Live FRED and price calls may run only in separate integration smoke tests.
- Accountants must fail closed and never impute missing concepts.
- M2a must not add Screens, Base-Rate, Method Router, Analysts, prompts, evals, or Senior judgment.

## Content And Data Requirements

### Price Inputs

Required inputs:
- current price from the injected `PriceFeed`;
- shares outstanding from EDGAR;
- book equity from EDGAR for fallback weighting.

Required outputs:
- current price, `unit="USD_per_share"`;
- market capitalization, `unit="USD_millions"`;
- weighting basis flag: `market_cap` or `book_equity_fallback`.

### Cost Of Capital Inputs

Required inputs:
- FRED `DGS10` risk-free rate, frozen into fixtures for CI;
- config `risk_free_fallback`;
- config ERP from Damodaran;
- config synthetic-rating spread from Damodaran;
- current Damodaran unlevered beta for AAPL's sector;
- configured marginal tax rate;
- market capitalization from `A-2 Price` or book-equity fallback;
- debt from EDGAR.

Required formulas:

```text
D = TotalDebt
E = MarketCap, or BookEquity when price feed is unavailable
D_to_E = D / E
betaL = beta_unlevered * (1 + (1 - tax_rate) * D_to_E)
Ke = Rf + betaL * ERP
Kd = Rf + synthetic_rating_spread
Kd_after_tax = Kd * (1 - tax_rate)
WACC = (E / (E + D)) * Ke + (D / (E + D)) * Kd_after_tax
```

M2a must introduce a WACC band convention suitable for reverse DCF. The band must be explicit, config-backed or derivation-backed, and represented as low/high `Number` values.

### DCF Inputs

The forward DCF must use explicit assumptions for:
- starting revenue;
- forecast revenue growth;
- operating or NOPAT margin;
- reinvestment or invested-capital turnover;
- tax rate;
- forecast duration;
- terminal growth or terminal return assumptions;
- WACC band;
- net debt or excess cash;
- diluted shares.

The reverse DCF must solve for market-implied:
- revenue growth;
- margin;
- duration;
- terminal ROIC or terminal economics.

The first M2a implementation may use conservative, config-backed default drivers where no Analyst judgment exists, but each default must be marked as an estimate with derivation and must not be presented as a Senior-approved scenario.

## Artifact Requirements

### ValuationRange

Forward DCF output must satisfy the `ValuationRange` schema in `specs/filing-rules.md`:
- exactly three scenarios: `bear`, `base`, and `bull`;
- `method="DCF"`;
- each scenario value is a `Number`;
- scenario assumption values are `Number` values;
- probability fields are present only to satisfy the schema, remain unratified, carry explicit M2a boundary evidence, and must not be used for Senior-approved weighting.

Because Senior ratification is out of scope, M2a files a schema-valid standalone `ValuationRange` but does not allow that artifact to masquerade as a final signed Handoff. M3 owns ratification and probability weighting.

### ExpectationsLine

Reverse DCF output must satisfy the `ExpectationsLine` schema:
- `frame="DCF"`;
- `frame_justification` explains that M2a covers a plain operating-company DCF for AAPL only;
- `wacc_band.low` and `wacc_band.high` are provenance-complete `Number` values;
- implied values are provenance-complete when convergence succeeds;
- non-convergence is represented structurally without forcing a numeric point.

If the current schema cannot represent non-convergence without invalid `Number` values, M2a implementation must first extend the schema additively or file an explicit validation issue before coding around it.

## Acceptance Criteria

- `analyze("AAPL")` writes reloadable M2a valuation artifacts.
- Offline tests pass using frozen fixtures only.
- Forward DCF returns a real AAPL valuation from fixture-backed inputs.
- Reverse DCF returns a fixture-backed Expectations Line for AAPL.
- Forward DCF files a schema-valid standalone `ValuationRange` without fake probability ratification.
- Reverse DCF convergence is tested at both WACC-band bounds.
- Reverse DCF non-convergence is tested and does not force a number.
- Price-feed failure completes with book-equity weighting flagged.
- FRED failure completes with config fallback flagged.
- The fabricated AAPL beta stand-in is gone from `config/conventions.yaml` by the end of M2a implementation.
- All M2a outputs are schema-valid and provenance-complete per `specs/filing-rules.md`.
