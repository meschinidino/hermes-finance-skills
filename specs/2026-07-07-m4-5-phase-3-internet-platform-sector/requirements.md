# M4.5 Phase 3 UBER Realized-Anchor DCF Calibration - Requirements

## Context

UBER's rendered report carries `price_at_or_below_bear` (`report_renderer.py:240`): even the
model's bear DCF value sits above the observed price (74.43), because the global bear default
assumes a 24% NOPAT margin for every company (`conventions.yaml:45`) versus UBER's thin
marketplace margin.

The first Phase 3 attempt anchored UBER to the Damodaran `Software (Internet)` industry median
and was empirically dead: the median's 17.71% growth paired with its 4.59% margin are
independent cross-sectional statistics, jointly incoherent for a single-company DCF. Plugged
in, they produced negative, non-monotonic scenario values (bear -26.33 / base -49.18 /
bull +7.62) and halted the C-4 ordering audit. See `advisor-finding.md` for the full record.

**This spec supersedes that approach.** Per the finance-advisor decision, the anchor is now
UBER's *own realized financials* from its committed EDGAR companyfacts, with growth, margin,
and reinvestment internally consistent with each other. Measured realized inputs (FY2025, from
`skills/data/edgar/fixtures/uber_companyfacts.json`, confirmed via the spine):

| Realized metric | FY2025 value | Trajectory |
|-----------------|--------------|------------|
| Revenue | 52,017M | 3yr growth ~18% (16.95 / 17.96 / 18.28) |
| NOPAT margin (spine) | 8.02% | inflecting up: 2.23 → 4.77 → 8.02 |
| Capital turnover incl goodwill | 1.65 | declining as M&A bloats invested capital |
| Capital turnover ex goodwill | ~2.30 | the marginal-reinvestment view |

A measured feasibility run with a realized anchor (bear g0.10/m0.06/s2c2.00, base
g0.13/m0.08/s2c2.30, bull g0.16/m0.11/s2c2.50) produced **positive, monotonic** values
(bear +5.55 / base +16.42 / bull +38.81), completed the full pipeline (exit 0, C-6
reconciled), and cleared `price_at_or_below_bear` (bear 5.55 < price 74.43). The market price
sits above the bull case, so the report instead surfaces `price_at_or_above_bull` — a coherent
valuation opinion (UBER priced above a DCF anchored on its realized economics), not a broken
model.

## Functional Requirements

### The realized anchor

1. Activate a single-ticker calibration keyed `uber_realized`, tagging `UBER`, sourced from a
   committed realized snapshot under `config/sources/` (e.g. `uber-realized-2026-01.json`)
   holding the three base drivers plus `firm_count: 1`, source metadata, and `captured_by`
   provenance. No live EDGAR read at provision or analyze time.
2. Layer ownership follows the Phase 2 sourced-vs-judgment contract. [eng-review D3-A]
   - The **snapshot** records ONLY raw realized facts from the committed companyfacts /
     spine, with provenance: trailing-3yr revenue CAGR (~0.18), realized FY2025 NOPAT margin
     (0.08), and BOTH capital turnovers (incl-goodwill 1.65 and ex-goodwill ~2.30). It is a
     faithful, refreshable data record and must not bake in any judgment.
   - The **house layer** owns every judgment applied on top, each with written rationale:
     (a) the ex-goodwill `sales_to_capital` choice (marginal growth reinvests operating
     capital, not re-acquired goodwill; incl-goodwill 1.65 reflects past M&A); (b) the base
     `revenue_growth` fade (the DCF holds growth constant, so raw 18%/yr for five years is
     not internally consistent with a maturing platform — the faded base value and its fade
     basis are house judgment); and the bear/bull brackets.
   - `nopat_margin` base = realized FY2025 spine NOPAT margin (0.08) taken straight from the
     snapshot (no judgment adjustment).
3. Because the realized base growth and s2c are house-owned (not straight snapshot values),
   the assembly rule needs a documented "realized base may be house-overridden" path: for a
   realized anchor, base `revenue_growth` and `sales_to_capital` come from the house layer
   (validated against the snapshot's raw facts for provenance), while base `nopat_margin`
   still rounds from the snapshot. Bear/bull come from the house bracket layer as in Phase 1/2.
4. Activating `uber_realized` must not change UBER's `asset_class` or valuation method; UBER
   stays on the DCF path, only re-based (same `calibration_sector` design as SaaS).

### Coherence guarantees (the core lesson from the dead attempt)

5. Every scenario value MUST be positive and the set MUST be monotonic (bear < base < bull). If
   UBER's own realized numbers cannot produce a coherent set within defensible brackets, STOP
   and report the finding — do not force it (this is the failure the industry-median attempt
   hit).
6. The provisioning tool MUST gain a coherence guardrail that catches an incoherent scenario
   set at provision time (`check`/`emit`), not only at `analyze()` runtime. [eng-review D2-C]
   The guardrail is the ALGEBRAIC FCFF proxy only — assert per scenario
   `nopat_margin > revenue_growth / sales_to_capital` and that the proxy is ordered
   bear<base<bull. It MUST NOT run a DCF, read EDGAR, or otherwise couple provisioning to
   `analyze()`; the provisioning tool stays pure, offline config assembly. The full
   positive-value + monotonicity check on the real DCF output lives in the UBER validation
   test (which already runs `analyze()`), not in the guardrail. The algebraic proxy is
   sufficient to catch the dead industry-median class (0.046 < 0.177/1.35).
7. Brackets MUST be chosen so UBER's resulting bear scenario value falls below the observed
   price with a defensible business case (a genuine bear below price), satisfying the original
   acceptance criterion. A resulting `price_at_or_above_bull` is acceptable and is a legitimate
   valuation signal, not a defect.

### Guardrail + override reuse

8. The anchor MUST flow through the same guardrail/override system as the (superseded) plan:
   `MIN_FIRMS`/`THIN_MARGIN`/`UPPER_MARGIN` module constants in `sector_provisioning.py`
   [eng-review D2-A], and a separate `evaluate_guardrails(block, overrides)` function invoked
   by `generate`/`check`, with `build_sector_block` staying pure assembly + schema validation
   [eng-review D3-A].
9. `uber_realized` has `firm_count: 1` (violates `MIN_FIRMS`) and a base `nopat_margin` of 0.08
   (violates `THIN_MARGIN`), so both guardrails MUST be overridden with a written house
   rationale. The firm-count override rationale must explain that the guardrail is designed for
   cross-sectional industry samples and does not apply to a company's own realized filings,
   where n=1 is correct by construction. [see eng-review open question on `anchor_kind`]

### Rationale text (quotable)

10. The `uber_realized` block `rationale` and its guardrail-override rationale MUST be
    standalone, quotable sentences fit to paste into a report footnote for a domain expert,
    substantially:
    > "UBER is calibrated to its own realized EDGAR financials (FY2025 NOPAT margin ~8%,
    > ex-goodwill capital turnover ~2.3, trailing revenue growth faded from ~18%) rather than to
    > an industry median, because internet-platform cross-sectional medians pair a high-growth
    > cohort's growth with a low-margin cohort's margin and are jointly incoherent for a single
    > company; the firm-count guardrail is waived because a company's own filings are n=1 by
    > construction, not a thin sample."

### Invariants

11. The committed `saas` block must still regenerate byte-for-byte; Phase 3 adds an anchor, it
    does not perturb `saas`.
12. `check` must be clean on the committed repository after `uber_realized` is emitted into
    `conventions.yaml`, including the guardrail-override and coherence reporting.
13. Runtime unchanged in shape: `analyze()` reads only `conventions.yaml`; the snapshot, house
    layer, guardrails, and coherence checks are authoring-time only.
14. AAPL, MRNA, and CRM behavior unchanged. UBER behavior changes by design and its new
    behavior is asserted (positive/monotonic range, flag cleared, C-6 reconciled), not merely
    allowed.
15. Full `pytest` suite must pass with UBER re-based, including a UBER-specific C-6
    `bear_case_value` reconciliation check.
16. No network, LLM, Senior, or Analyst call added; provisioning stays offline and deterministic.
17. No new runtime dependency (PyYAML + pydantic only).

## Resolved Decisions

1. **Anchor = UBER realized, not an industry median** (finance-advisor decision). Industry
   medians are jointly incoherent for one company; the subject's own filings are internally
   consistent by construction. `internet_platform` is abandoned.
2. **Ex-goodwill capital turnover for base `sales_to_capital`**, because marginal growth
   reinvestment funds operating capital, not re-acquired goodwill; incl-goodwill (1.65)
   understates forward reinvestment efficiency and pushes FCFF negative.
3. **Growth is faded, not raw trailing.** The DCF holds growth constant over the forecast, so a
   raw 18%/yr-for-five-years base is not internally consistent with a maturing platform; base
   uses a documented faded rate.
4. **`price_at_or_above_bull` is an acceptable outcome**, not a defect: it states that the
   market prices UBER above a DCF built on its realized economics. The original acceptance test
   (a defensible bear below price) is still met.
5. **Reuse the guardrail/override system**, with `firm_count: 1` and thin margin overridden by
   written rationale (per the resume instruction). Whether realized anchors deserve a distinct
   `anchor_kind` exempt from the industry firm-count guardrail is raised for eng-review.

## Non-Goals

- No `internet_platform`, Transportation, AAPL, or additional sector this phase.
- No change to the global 24% bear-margin default (still a `TODOS.md` item).
- No modelled margin/growth ramp inside the DCF (it stays constant-per-scenario); the anchor
  works within that constraint.
- No live EDGAR read in the shipped tool; realized capture is an authoring-time step from the
  committed fixture.
- No automatic in-place rewrite of `conventions.yaml`; emit-review-paste stays the update path.
