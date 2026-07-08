# M4.5 Phase 3 UBER Realized-Anchor DCF Calibration - Plan

> **IMPLEMENTED 2026-07-08.** UBER is calibrated to its own realized EDGAR financials via the
> `uber_realized` anchor. The original `internet_platform` industry-median approach was dead
> (negative, non-monotonic DCF values — see `advisor-finding.md`); this realized-anchor
> approach was designed per the finance-advisor decision, eng-reviewed (D2-C, D3-A folded),
> and shipped. Result: UBER renders bear 5.55 / base 16.42 / bull 38.81 (positive, monotonic,
> price 74.43), `price_at_or_below_bear` cleared, `price_at_or_above_bull` now surfaced as the
> legitimate "priced above realized-economics DCF" signal. `provision-sectors check` clean;
> full suite 320 passed / 3 skipped; AAPL/MRNA/CRM unchanged; UBER C-6 reconciles. The new
> algebraic coherence guardrail pins the dead-median class so it can never ship again.

## Objective

Fix UBER's `price_at_or_below_bear` miscalibration by calibrating its DCF to UBER's own
realized financials (internally-consistent growth, margin, reinvestment) rather than an
industry median, routed through the same guardrail/override provisioning system, and add a
provision-time coherence guardrail so an incoherent anchor can never again ship and halt
`analyze()`.

## Why realized, and why it is coherent (mechanism, measured)

The DCF value math is `fcff = revenue*nopat_margin - revenueGrowth$/sales_to_capital`
(`dcf.py:349-351`). A scenario is coherent (positive FCFF) only when
`nopat_margin > revenue_growth / sales_to_capital`. The industry median failed this hard
(0.046 vs 0.177/1.35 = 0.131). UBER's realized numbers pass it when the reinvestment view is
right:

- Realized NOPAT margin 0.08 (FY2025, inflecting up from 0.022).
- Realized ex-goodwill capital turnover ~2.30 (incl-goodwill 1.65 reflects past M&A, not
  marginal reinvestment).
- Faded growth ~0.13 (trailing 3yr CAGR ~0.18 is not sustainable constant over a 5yr forecast).
- Coherence: 0.08 > 0.13/2.30 = 0.057 → positive FCFF. 

## Feasibility (measured 2026-07-08, then reverted)

A throwaway `uber_realized` block with the brackets below was run through `analyze("UBER")`:

```
scenario   value    g     m      s2c    (price 74.43)
bear      +5.55    0.10  0.06   2.00
base     +16.42    0.13  0.08   2.30
bull     +38.81    0.16  0.11   2.50
```

Positive, monotonic, pipeline exit 0 (C-4 audit passed, C-6 reconciled). `price_at_or_below_bear`
cleared (bear 5.55 < price); `price_at_or_above_bull` now fires (price > bull 38.81), which is a
legitimate "priced above realized-economics DCF" signal. These brackets are the starting point,
to be finalized under eng-review and the coherence guardrail.

## Two-layer assembly (unchanged shape from Phase 2)

- **Realized snapshot** `config/sources/uber-realized-2026-01.json` — the sourced base drivers
  (`revenue_growth`, `after_tax_operating_margin`/nopat_margin, `sales_to_invested_capital`),
  `firm_count: 1`, `source_name`/`source_urls`/`base_value_decimals`, and a `captured_by` that
  cites the companyfacts periods and the derivation (FY2025 NOPAT margin; FY2025 ex-goodwill
  capital turnover; trailing-3yr revenue CAGR faded to the base rate).
- **House layer** `config/sector_brackets.yaml` — `uber_realized` sector: `industry_category`
  (the snapshot key), `tickers: ["UBER"]`, `rationale`, bear/bull `brackets`, and
  `guardrail_overrides` for `firm_count` and `nopat_margin`.
- Assembled into `config.dcf.sector_scenarios.uber_realized` by the provisioning tool and pasted
  into `conventions.yaml` (the generated runtime artifact).

## Guardrails (module constants + separate function + NEW coherence check)

- Existing economic guardrails as module constants in `sector_provisioning.py`
  (`MIN_FIRMS = 50`, `THIN_MARGIN = 0.10`, `UPPER_MARGIN = 0.60`) evaluated in a separate
  `evaluate_guardrails(block, overrides)` — `build_sector_block` stays pure. [eng-review D2-A/D3-A]
- `uber_realized` violates `MIN_FIRMS` (firm_count 1) and `THIN_MARGIN` (base margin 0.08) → both
  require a declared override with the quotable rationale (requirements §10).
- **NEW coherence guardrail** (the core fix) — ALGEBRAIC PROXY ONLY [eng-review D2-C]:
  `evaluate_guardrails` asserts, per scenario, `nopat_margin > revenue_growth / sales_to_capital`
  (positive-FCFF proxy) and that the proxy is ordered bear<base<bull. It does NOT run a DCF or
  read EDGAR — provisioning stays pure, offline config assembly. This catches an incoherent
  anchor at `provision-sectors check`/`emit` before it can reach `conventions.yaml` and halt
  `analyze()` on the C-4 audit, and would have caught the industry-median disaster
  (0.046 < 0.177/1.35). NOT override-able (coherence is not a judgment call). The full
  positive-value + monotonicity check on the real DCF output lives in the UBER validation test
  (which already runs `analyze()`), keeping the strong check without coupling the tool.

## Resolved (eng-review): realized anchor reuses `sector_scenarios`

Per the resume instruction and eng-review, `uber_realized` reuses `sector_scenarios` with
`firm_count: 1` and thin margin both handled via documented `guardrail_overrides` — NOT a
separate `anchor_kind` field. The firm-count override rationale states the guardrail is designed
for cross-sectional industry samples and does not apply to a company's own realized filings
(n=1 by construction). The `anchor_kind` split was considered and rejected as unneeded machinery
for a single realized anchor; revisit only if realized anchors proliferate.

## Components

- `skills/provisioning/sector_provisioning.py` — `MIN_FIRMS`/`THIN_MARGIN`/`UPPER_MARGIN`
  constants; `evaluate_guardrails(block, overrides)` (override contract + NEW coherence check)
  invoked from `generate_sector_blocks`/`check`, NOT from `build_sector_block`.
- `config/sources/uber-realized-2026-01.json` — realized snapshot.
- `config/sector_brackets.yaml` — `uber_realized` sector + `guardrail_overrides`.
- `config/conventions.yaml` — pasted `uber_realized` block.
- `skills/provisioning/test_sector_provisioning.py` — guardrail/override/coherence tests.
- UBER DCF + report + C-6 reconciliation tests (see validation).

No change to `resolver.py` dispatch or `analyze()`.

## What already exists (reuse, do not rebuild)

- Phase 2 provisioning tool (`load_snapshot`/`load_brackets`/`build_sector_block`/
  `generate_sector_blocks`/`check_config`/`emit_sector_block`/CLI) — extended, not rebuilt.
- Realized inputs are already in the committed `uber_companyfacts.json` and computed by the spine
  (`nopat_margin`, `capital_turnover`, `invested_capital_ex_gw`) — the derivation reads existing
  artifacts, no new extraction.
- Ticker→sector tagging is a pure config lookup (`method_router.py:34`); tagging UBER needs only a
  house-layer ticker entry.
- Sector→DCF wiring (`resolve_dcf_scenario_source`, `dcf.py:63`) already routes a
  `calibration_sector` into forward + reverse valuation.

## NOT in scope (considered, deferred)

- `internet_platform` / any industry-median anchor — empirically dead (`advisor-finding.md`).
- Global 24% bear-margin fix — broader root cause, kept as a `TODOS.md` Valuation item.
- Modelled margin/growth ramp inside the DCF — it stays constant-per-scenario.
- `anchor_kind` realized-vs-industry typing — proposed for discussion, not committed this phase
  unless eng-review prefers it over the override reuse.
- Automating realized-financials extraction — reads the committed fixture at authoring time.

## Failure modes (net-new codepaths)

| Codepath | Realistic failure | Test? | Handling | Silent? |
|----------|-------------------|-------|----------|---------|
| coherence guardrail (algebraic proxy) | incoherent anchor ships, `analyze()` halts | proxy-rejection test + internet_platform-median regression test | fail `check`/`emit` closed | no |
| net-debt-driven negative value (proxy passes, value negative) | anchor passes proxy but DCF value negative | full-pipeline UBER positive+monotonic test [D2-C] | UBER validation test fails | no |
| firm_count/thin-margin override | single-company anchor rejected, or stale override | override tests | `ProvisioningError` | no |
| growth-fade derivation | base growth too high → near-zero/negative value | headline UBER value test | coherence guardrail catches | no |
| UBER re-base | C-6 `bear_case_value` drifts | C-6 reconciliation test | audit fails closed | no |

No silent-and-untested-and-unhandled failure mode.

## Parallelization

Sequential — every task centers on `skills/provisioning/` plus the two config files and the
realized snapshot. No parallel lanes.

## Acceptance (headline)

`provision-sectors check` clean with guardrail-overrides AND coherence visible; the `saas` block
still regenerates exactly; UBER re-renders with a positive, monotonic range whose bear is
defensibly below price (flag cleared); UBER's C-6 reconciles; full `pytest` green; AAPL/MRNA/CRM
unchanged. If a defensible coherent range cannot be built from UBER's realized numbers, STOP and
report rather than force it.

## Implementation Tasks
Synthesized from this review. Each derives from a specific finding. Checkbox as you ship.

- [ ] **T1 (P1, human ~1h / CC ~15min)** — provisioning — Capture UBER realized snapshot: raw trailing CAGR, NOPAT margin, both capital turnovers, `firm_count 1`, `captured_by` provenance [D3-A]. File: `config/sources/uber-realized-2026-01.json`. Verify: snapshot loads, values match the fixture.
- [ ] **T2 (P1, human ~1h / CC ~15min)** — provisioning — House layer `uber_realized`: faded base growth + ex-gw s2c (with rationale), brackets, `firm_count`/thin-margin overrides, quotable rationale [D3-A]. File: `config/sector_brackets.yaml`.
- [ ] **T3 (P1, human ~2h / CC ~25min)** — provisioning — Constants + `evaluate_guardrails()`: override contract + algebraic coherence proxy (`margin > growth/s2c`, ordered), not override-able, no DCF/EDGAR [D2-C]. File: `sector_provisioning.py`. Verify: `pytest skills/provisioning`.
- [ ] **T4 (P1, human ~30min / CC ~10min)** — provisioning — Realized-base assembly path (base growth/s2c from house layer, base margin from snapshot); emit into `conventions.yaml` [D3-A]. Verify: `provision-sectors check`.
- [ ] **T5 (P1, human ~2h / CC ~25min)** — tests — Coherence tests incl the `internet_platform`-median regression pin + offline-proof; override suite; provenance test. File: `test_sector_provisioning.py`.
- [ ] **T6 (P1, human ~1h / CC ~15min)** — tests — UBER realized: positive+monotonic via `analyze`, bear<price, flag cleared, C-6 reconciliation, full suite green. Files: `test_sector_provisioning.py`, `tests/`.
- [ ] **T7 (P2, human ~30min / CC ~10min)** — valuation — Finalize brackets so UBER bear is defensibly below price; if no coherent range, STOP and report. File: `config/sector_brackets.yaml`.
- [ ] **T8 (P2, human ~15min / CC ~5min)** — docs — Resolve the BLOCKED banner; update roadmap M4.5 status. Files: `plan.md`, `specs/roadmap.md`.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 2 | CLEAR | realized-anchor pass: 2 arch findings folded, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | n/a (no UI) |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **OUTSIDE VOICE:** Codex rate-limited (usage cap, resets Jul 10); Claude-subagent fallback not auto-run per operator agent policy — offered to user, informational, does not gate.
- **VERDICT:** ENG CLEARED — ready to implement. Realized-anchor rewrite reviewed; D2-C (coherence guardrail = algebraic proxy only, full check in the UBER test) and D3-A (snapshot holds raw realized facts, house layer owns fade + ex-gw judgment) folded; `anchor_kind` resolved to reuse+override; internet_platform-median regression test pinned. Scope accepted as-is. Feasibility measured (bear +5.55/base +16.42/bull +38.81, flag clears) before locking.

NO UNRESOLVED DECISIONS
