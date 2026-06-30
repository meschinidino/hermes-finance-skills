# M1 Walking Skeleton — Validation

## Manual Validation

1. Run `analyze("AAPL")`.
2. Confirm the run reports:
   - CIK `0000320193`
   - at least five annual fiscal years pulled
   - all required facts sourced
   - Spine filed
   - handoff filed
3. Open `data/runs/AAPL/{as_of}/spine.json` and confirm every numeric field is a `Number`.
4. Open `data/runs/AAPL/{as_of}/handoff.json` and confirm the handoff is explicitly marked as an M1 walking skeleton.
5. Pick one computed ROIC value and walk its derivation back to:
   - NOPAT
   - EBIT
   - invested capital
   - debt, equity, cash, goodwill
   - EDGAR accession numbers

## Technical Checks

Run the project checks that exist after implementation:

```text
uv run --no-sync pytest
uv run --no-sync pytest skills/valuation/spine
uv run --no-sync python -m resolver AAPL
```

If the package uses a different module name after implementation, update this file to the exact command before closing M1.

## Expected Unit Tests

- Config loads and validates the M1 subset.
- Storage writes and reloads JSON artifacts.
- CIK resolver maps `AAPL` to `0000320193` using the frozen fixture.
- EDGAR extraction resolves the required concepts with the documented fallback order.
- Missing required concepts fail closed with `unresolved_concept`.
- Less than five annual periods raises or records `insufficient_history`.
- NOPAT, invested capital, ROIC, WACC, spread, margin, and turnover compute correctly from hand-checked fixture values.
- `margin * turnover == ROIC_incl` within tolerance.
- Price-feed failure triggers book-equity WACC fallback and preserves ROIC.
- FRED failure uses `risk_free_fallback` and flags the fallback.
- Missing goodwill becomes zero only with an explicit flag.

## Expected Fault-Injection Tests

- Remove provenance from a fact and assert audit rejection.
- Remove derivation from an estimate and assert audit rejection.
- Change a value so `IC_incl_gw <= 0` and assert audit rejection.
- Change a value so `WACC <= 0` or `WACC >= 0.30` and assert audit rejection.
- Change a value so `abs(ROIC_incl) >= 2.0` and assert audit rejection.
- Break storage round-trip serialization and assert the run fails before filing.

## Live Smoke

Live network checks are not CI requirements. When credentials and network access are available, run one live AAPL smoke against EDGAR, FRED, and the configured price feed to confirm the adapters still match the external APIs.

## Responsive And Accessibility Checks

Not applicable in M1. There is no UI surface.

## Closure Criteria

M1 can be marked complete in `specs/roadmap.md` only after:
- the M1 spec files are current,
- all M1 skill bundles include completed `SKILL.md` files,
- the frozen-fixture test suite passes,
- the M1 audit gate passes on the happy path,
- fault-injection tests fail closed,
- `analyze("AAPL")` writes reloadable `spine.json` and `handoff.json`,
- any unavailable live checks are documented with the exact reason.
