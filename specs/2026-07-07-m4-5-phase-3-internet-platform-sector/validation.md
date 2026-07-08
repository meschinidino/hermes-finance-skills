# M4.5 Phase 3 UBER Realized-Anchor DCF Calibration - Validation

## Headline acceptance (the real test)

Routing UBER to the realized anchor is not sufficient; the re-based valuation must be coherent
and improved.

- `test_uber_realized_scenarios_positive_and_monotonic` — UBER's forward valuation through the
  DCF with `calibration_sector="uber_realized"` yields all-positive, strictly monotonic
  bear<base<bull values (the industry-median attempt failed exactly here). **Headline proof.**
- `test_uber_bear_scenario_below_price_with_uber_realized` — bear scenario value is strictly
  below the observed price (74.43), so `report_renderer.py:240` no longer holds.
- `test_uber_report_no_longer_flags_price_at_or_below_bear` — render UBER's completed run; assert
  `price_at_or_below_bear` is absent. `price_at_or_above_bull` MAY be present and is acceptable
  (a legitimate "priced above realized-economics DCF" signal, not a defect).
- If no defensible bracket set produces a coherent bear-below-price range, STOP and report — do
  not force green (per requirements §5).

## Coherence guardrail tests (the core new capability)

The guardrail is the ALGEBRAIC FCFF proxy only (no DCF, no EDGAR) [eng-review D2-C]; the
full positive-value + monotonicity check on real DCF output is the headline UBER test above.

- `test_coherence_guardrail_rejects_negative_fcff_scenario` — a block whose scenario has
  `nopat_margin <= revenue_growth / sales_to_capital` fails `check`/`emit`. NOT override-able.
- `test_coherence_guardrail_rejects_internet_platform_median` — the exact dead industry-median
  block (base 0.046 margin vs 0.177/1.35 growth/s2c) is rejected by the proxy. **Pins the past
  failure so the incoherent-median class can never ship again.** [eng-review regression]
- `test_coherence_guardrail_rejects_non_monotonic_proxy` — a block whose per-scenario FCFF proxy
  is non-monotonic fails at provision time, before it can halt `analyze()` on the C-4 audit.
- `test_uber_realized_block_passes_coherence` — the committed `uber_realized` block passes.
- `test_coherence_guardrail_is_not_overridable` — a `guardrail_overrides` entry naming coherence
  is rejected (coherence is not a judgment call).
- `test_provisioning_stays_offline` — `evaluate_guardrails`/`check`/`emit` run with no EDGAR
  fixture and no ticker analysis available (proves the proxy adds no coupling). [eng-review D2-C]

## Guardrail + override tests

- `test_uber_realized_block_regenerates_from_snapshot_and_brackets` — the committed block
  reproduces field-for-field from `uber-realized-2026-01.json` + house brackets.
- `test_firm_count_override_required_and_surfaced` — firm_count 1 without an override fails
  closed; with the override, emits and surfaces the override + rationale.
- `test_thin_margin_override_required_and_surfaced` — base margin 0.08 (< THIN_MARGIN) without an
  override fails closed; with it, emits and reports the flag.
- `test_unused_override_declaration_fails_closed` — an override for a non-violated guardrail
  fails closed.
- `test_guardrail_thresholds_declared_in_one_place` — thresholds are the single module constants.

## Phase 2 invariants still hold

- `test_saas_block_regenerates_from_snapshot_and_brackets` — `saas` byte-for-byte identical.
- `test_saas_emits_without_guardrail_override` — the passing sector (309 firms, 0.326 margin)
  clears every guardrail and emits with an EMPTY override set (no spurious flag). [eng-review T1]
- `test_untagged_ticker_uses_global_scenario_source` — a ticker in no sector resolves to global
  `dcf.scenarios` (verify existing; add if absent). [eng-review T1]
- `test_check_config_reports_no_drift_on_committed_repo` — clean after `uber_realized` is emitted.
- `test_committed_config_still_loads` — CRM→`saas`, UBER→`uber_realized`, all others→no sector.

## Blast-radius verification (sector source feeds the whole UBER chain) [eng-review A2]

The sector `source` feeds BOTH forward DCF and reverse expectations (`dcf.py:57-58`), so
re-basing UBER moves C-4 scenarios, C-5 cruxes, and C-6 risk:

- `test_uber_c6_bear_case_value_reconciles_after_rebase` — UBER's C-6 risk `bear_case_value`
  reconciles to the filed scenarios within `BEAR_VALUE_RECONCILIATION_TOLERANCE` after the
  re-base. (The feasibility run already completed the full pipeline including C-6, so this is
  expected to hold; the test proves it.)
- The FULL suite must pass with UBER re-based — the two existing UBER end-to-end tests are robust
  by construction (`report_renderer` asserts moat/thesis text; `test_m4b_synthesis_skills` injects
  its own bear/bull), confirmed by running the suite.

## Provenance verification

- `test_uber_realized_snapshot_derivation_documented` — the snapshot `captured_by` names the
  companyfacts periods and the derivation rule (FY2025 NOPAT margin; FY2025 ex-goodwill capital
  turnover; trailing-3yr revenue CAGR faded to the base growth), and the base values match that
  derivation applied to the committed fixture.

## Commands

- Environment: this workspace has no `.venv`; step 0 is a venv (`python3 -m venv .venv` +
  `pip install pydantic PyYAML pytest`, or `uv` per AGENTS.md), then reproduce UBER's CURRENT
  `price_at_or_below_bear` as the baseline before changing anything.
- Full suite: `.venv/bin/python -m pytest` (or the AGENTS.md `uv` form) → all pass with UBER
  re-based; record passed/skipped counts. This is the blast-radius check.
- Focused: `... -m pytest skills/provisioning` → guardrail + coherence + activation tests pass.
- Provisioning check: `python -m resolver provision-sectors check` → `{"status":"ok",...}` with
  the `uber_realized` overrides and coherence status listed.
- Emit: `python -m resolver provision-sectors emit uber_realized` → paste-ready block.
- UBER re-render: `python -m resolver UBER` then
  `python -m resolver render-report --run-dir data/runs/UBER/<date>` → no `price_at_or_below_bear`;
  positive monotonic range.
- Unchanged smokes: `python -m resolver AAPL | MRNA | CRM` → succeed unchanged; CRM still `saas`.

## Manual checks

- Runtime reads only `conventions.yaml`; snapshot, house layer, guardrails, coherence check are
  authoring-time only.
- The `uber_realized` rationale reads as a standalone quotable footnote (requirements §10).
- Global 24% bear margin and all global DCF defaults untouched.

## Result (to record on completion)

Phase 3 complete when: `uber_realized` is provisioned and activated for UBER from its own realized
EDGAR financials; the coherence guardrail is in place and green; UBER's re-rendered report shows a
positive, monotonic range with a defensible bear below price and no `price_at_or_below_bear`;
UBER's C-6 reconciles; the `saas` block and AAPL/MRNA/CRM are unchanged; the full suite passes; and
provisioning stays offline and deterministic. If UBER's realized numbers cannot yield a coherent
range, the deliverable is the reported finding, not a forced config.
