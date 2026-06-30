# M2b Gates And Routing — Validation

## Manual Validation

1. Run `analyze("AAPL")` after M2b implementation.
2. Confirm the run reports:
   - Screens completed;
   - `gate_card.json` filed;
   - Altman variant selected and recorded;
   - Beneish M-Score, Piotroski F-Score, and smoke checks filed;
   - Method Router directive filed or logged as a run artifact;
   - DCF invoked only because the router selected DCF.
3. Open the run directory under `data/runs/AAPL/{as_of}/`.
4. Confirm `gate_card.json` is reloadable and matches `specs/filing-rules.md` §4.
5. Pick one Altman output and walk its derivation back to the selected variant and sourced inputs.
6. Pick one Beneish output and confirm a lit flag populates scrutiny metadata rather than a halt.
7. Confirm the method directive is the resolver's valuation input, not an unused side artifact.

## Technical Checks

Run the project checks that exist after implementation:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/valuation/screens
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/valuation/base_rate
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/valuation/method_router
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

The `--no-sync` flag is intentional. CI must not require live PyPI, EDGAR, FRED, Damodaran, price-feed, or Mauboussin-source access.

## Expected Unit Tests

- Manufacturer fixture selects manufacturer Altman Z.
- Non-manufacturer fixture selects Z-double-prime non-manufacturer.
- Emerging-market fixture selects Z-double-prime plus 3.25.
- Altman variant is recorded in the Gate Card and in the output derivation.
- Altman zone maps correctly from hand-checked fixture values.
- Beneish M-Score computes from hand-checked fixture values.
- `Beneish M-Score > -1.78` sets a flag and adds scrutiny to `dig_items`.
- A lit screen produces a flagged Gate Card, not a halt or forced `KillMemo`.
- Piotroski F-Score computes from hand-checked fixture values.
- Smoke checks populate restatement, auditor-change, NI/CFO gap, DSO trend, and inventory trend fields.
- Every screen `Number` preserves provenance and computed derivation.
- Base-rate lookup returns the expected bucket for a known forecast fixture.
- Base-rate lookup returns `low_probability_bucket=True` for the configured low-probability threshold case.
- Base-rate lookup cites the matched Mauboussin reference class.
- Method Router classifies a fixture cash-generator as `cash-generator`.
- Method Router emits `method="DCF"` for the cash-generator fixture.
- Method Router classifies an optionality/pre-revenue fixture as `optionality`.
- Method Router emits `rNPV`, `SOTP`, or `NAV` for the optionality/pre-revenue fixture, not `DCF`.
- Method directive includes sourced indicators and routing reason.
- Accountant bundle validation rejects `prompt.md` or `eval/` under M2b bundles.

## Expected Resolver Integration Tests

- Resolver calls the Method Router before the valuation step.
- Resolver invokes `B-3 DCF` when the router returns a DCF directive for a cash-generator.
- Resolver does not invoke `B-3 DCF` when the router returns an optionality/pre-revenue directive.
- Resolver files or returns the deferred method directive when the selected method is not yet implemented.
- The old unconditional DCF path is absent from the resolver valuation flow.
- `analyze("AAPL")` still produces M2a valuation artifacts only through the router-selected DCF branch.
- Gate Card and method directive both survive storage round-trip.

## Expected Fault-Injection Tests

- Remove provenance from an Altman input and assert audit rejection.
- Remove derivation from a computed screen output and assert audit rejection.
- Remove industry classification needed for Altman variant selection and assert fail-closed behavior.
- Force a manufacturer fixture through the non-manufacturer Altman variant and assert test failure.
- Force a non-manufacturer fixture through the manufacturer Altman variant and assert test failure.
- Set Beneish M-Score above `-1.78` and assert the run flags scrutiny without halting.
- Remove the Mauboussin reference-class citation and assert base-rate artifact rejection.
- Supply a forecast that has no matching base-rate bucket and assert explicit no-match failure, not an invented probability.
- Remove sourced indicators from the method directive and assert audit rejection.
- Force an optionality/pre-revenue fixture to DCF and assert router validation failure.
- Reintroduce unconditional DCF invocation in the resolver and assert the integration test fails.

## Live Smoke

Live network checks are separate from offline CI. M2b is expected to be fixture-backed and offline. If an implementation chooses a live source for industry classification, base-rate refresh, or smoke-check enrichment, it must add a separate `test_integration.py` under the affected skill bundle and document the exact live unavailability reason when skipped.

No live smoke is required for a purely fixture-backed M2b implementation.

## Document Validation

Before starting implementation:
- confirm this spec lives under `specs/2026-06-30-gates-and-routing/`;
- confirm the triplet contains `plan.md`, `requirements.md`, and `validation.md`;
- confirm this spec contains only M2b scope;
- confirm all three M2b skill bundles are Accountant bundles;
- confirm the bundle shapes follow `specs/SKILL-template.md`;
- confirm this spec does not require Analysts, prompts, evals, Senior gates, Senior ratification, or new valuation engines;
- confirm DCF changes are limited to conditional invocation through the router;
- confirm the validation plan includes manufacturer, non-manufacturer, and emerging-market Altman variant tests;
- confirm the validation plan includes a lit-screen flagged-Gate-Card test;
- confirm the validation plan includes a known-forecast base-rate bucket test;
- confirm the validation plan includes a resolver integration assertion that cash-generators get DCF and optionality names route away from DCF;
- confirm Gate Card and all M2b outputs must be schema-valid per `specs/filing-rules.md`.

## Responsive And Accessibility Checks

Not applicable in M2b. There is no UI surface.

## Closure Criteria

M2b can be marked complete in `specs/roadmap.md` only after:
- the M2b spec files are current;
- all M2b skill bundles include completed `SKILL.md` files;
- the frozen-fixture test suite passes offline;
- Gate Card artifacts are schema-valid and provenance-complete;
- manufacturer, non-manufacturer, and emerging-market Altman variant selection is tested;
- lit screens flag scrutiny without auto-kill behavior;
- base-rate lookup returns the expected known-forecast bucket;
- Method Router is wired into resolver valuation invocation;
- cash-generator fixtures invoke DCF through the router;
- optionality/pre-revenue fixtures route away from DCF;
- live endpoint smokes, if any, are either passing or documented with exact unavailability reasons.

## Validation Result

Status: implemented and validated.

Document-validated on 2026-06-30:
- M2b is scoped to `B-4 Screens`, `B-5 Base-Rate`, and `B-6 Method Router`.
- All M2b bundles are specified as Accountant bundles with no `prompt.md` or `eval/`.
- The Method Router is specified as resolver-wired and load-bearing, not a standalone unused skill.
- DCF invocation is specified as conditional on the router directive.
- The validation plan includes manufacturer, non-manufacturer, and emerging-market Altman variant checks plus lit-screen, base-rate, router integration, and filing-schema checks.

Implementation-validated on 2026-06-30:
- `B-4 Screens`, `B-5 Base-Rate`, and `B-6 Method Router` bundles were added with completed Accountant `SKILL.md` files and resolver entries.
- `GateCard`, `BaseRateResult`, and `MethodDirective` were added as pydantic artifacts.
- `analyze("AAPL")` files `gate_card.json` and `method_directive.json`; DCF runs only when the directive selects `DCF`.
- Optionality/pre-revenue routing was verified to defer valuation and not call DCF.
- Validation commands passed:
  - `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest`
  - `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL`
